import argparse
import inspect
import json
import types
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, NoReturn, TypeVar, Union, get_args, get_origin, overload

from pydantic import BaseModel, Field, TypeAdapter, ValidationError, create_model
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    CliPositionalArg,
    CliSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    SettingsError,
)

from argdantic.docstrings import parse_docstring
from argdantic.errors import ExitCode, InputRejected, fail

F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


class FlatMarker:
    """Marks a model parameter whose fields become top-level flags."""


Flat = Annotated[T, FlatMarker()]
Arg = CliPositionalArg
_POSITIONAL = CliPositionalArg.__metadata__[0]


class InputModel(BaseSettings):
    """Base for the input model argdantic builds from a command's signature."""

    model_config = SettingsConfigDict(
        cli_kebab_case=True,
        cli_implicit_flags=True,
        cli_avoid_json=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Read only flags and defaults, never the environment."""
        return (init_settings,)


@dataclass(frozen=True)
class SafetyHints:
    """MCP-style tool annotations. Stored, not acted on yet."""

    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
    open_world: bool = False


@dataclass(frozen=True)
class ModelParam:
    """
    A parameter annotated with a pydantic model.

    Attributes:
        empty_when_unset: validate from `{}` when no flag is given, so errors keep their full path.
        declared: the field as declared, with the default the flags update.
    """

    empty_when_unset: bool
    declared: FieldInfo

    @property
    def instance(self) -> BaseModel | None:
        """The default instance, without calling a factory."""
        default = self.declared.default
        return default if isinstance(default, BaseModel) else None

    def base(self) -> BaseModel | None:
        """
        The default the flags update: the instance, or a new one from the factory.

        None when the factory takes the validated data, because it can run only during validation.
        """
        if self.declared.default_factory_takes_validated_data:
            return None
        default = self.declared.get_default(call_default_factory=True)
        return default if isinstance(default, BaseModel) else None


@dataclass(frozen=True)
class CommandSpec:
    """
    Everything argdantic knows about one command, built once at registration.

    Attributes:
        flag_model: the model that builds the parser, with Flat fields in place of their parameter.
        flat: each Flat parameter, with the raw keys of its fields.
        positionals: the field names of the positionals, in signature order.
        positional_only: the positional-only parameters, passed by place.
        var_positional: the `*args` parameter, passed unpacked.
    """

    name: str
    fn: Callable[..., Any]
    model: type[InputModel]
    output: TypeAdapter[Any]
    hints: SafetyHints
    summary: str
    model_params: dict[str, ModelParam]
    flag_model: type[InputModel]
    flat: dict[str, frozenset[str]]
    positionals: tuple[str, ...]
    positional_only: tuple[str, ...]
    var_positional: str | None


def _kebab_case(name: str) -> str:
    return name.replace("_", "-")


def _pascal_case(name: str) -> str:
    return name.title().replace("_", "")


def _without_none(annotation: Any) -> Any:
    """`X` for `X | None`, any other annotation as it is."""
    if get_origin(annotation) in (Union, types.UnionType):
        members = [member for member in get_args(annotation) if member is not type(None)]
        return members[0] if len(members) == 1 else annotation
    return annotation


def _model_class(annotation: Any, *, optional: bool = False) -> type[BaseModel] | None:
    """The pydantic model class an annotation names, through `Annotated` and, if `optional`, `X | None`, or None."""
    if get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    if optional:
        annotation = _without_none(annotation)
    return annotation if isinstance(annotation, type) and issubclass(annotation, BaseModel) else None


def _is_variadic(annotation: Any) -> bool:
    """Whether a positional of this type takes many values: a collection, as pydantic-settings decides `nargs`."""
    annotation = _without_none(annotation)
    origin = get_origin(annotation) or annotation
    return isinstance(origin, type) and issubclass(origin, Collection) and not issubclass(origin, str | bytes)


def _deep_merge(base: Mapping[str, Any] | BaseModel, update: Mapping[str, Any]) -> dict[str, Any]:
    """A new dict: a mapping in `update` merges into a mapping or model in `base`, any other value replaces."""
    if isinstance(base, BaseModel):
        # read attributes, not model_dump, so serialization settings do not change the values
        base = {_raw_key(info, name): getattr(base, name) for name, info in type(base).model_fields.items()}
    merged = dict(base)
    for key, value in update.items():
        nested = isinstance(value, Mapping) and isinstance(merged.get(key), Mapping | BaseModel)
        merged[key] = _deep_merge(merged[key], value) if nested else value
    return merged


def _raw_key(info: FieldInfo, name: str) -> str:
    """The key pydantic-settings gives a field's value in the raw dict, and the base of its flag."""
    alias = info.validation_alias
    return alias if isinstance(alias, str) else info.alias or name


def _is_flat(annotation: Any) -> bool:
    return get_origin(annotation) is Annotated and any(isinstance(m, FlatMarker) for m in annotation.__metadata__)


def _flat_fields(
    param_name: str,
    model_class: type[BaseModel],
    instance: BaseModel | None,
) -> dict[str, Any]:
    """The flag model's fields for a Flat parameter, keyed `<param>__<field>`, with the defaults the run uses."""
    fields = {}
    for name, info in model_class.model_fields.items():
        key = _raw_key(info, name)
        field = FieldInfo.from_field(
            info.default if instance is None else getattr(instance, name),
            default_factory=info.default_factory if instance is None else None,
            alias=key,
            validation_alias=key,
            description=info.description,
        )
        fields[f"{param_name}__{name}"] = (info.annotation, field)
    return fields


def _annotation(param: inspect.Parameter) -> Any:
    """The parameter's annotation, with a positional-only parameter as `Arg[T]` and `*args: T` as `Arg[list[T]]`."""
    if param.kind is param.POSITIONAL_ONLY:
        return Arg[param.annotation]
    if param.kind is param.VAR_POSITIONAL:
        return Arg[list[param.annotation]]
    return param.annotation


def _check_flag_names(owners: list[tuple[str, str]]) -> None:
    """Raise when two parameters or Flat fields give the same top-level flag."""
    seen: dict[str, str] = {}
    for flag, owner in owners:
        if flag in seen:
            raise ValueError(f"flag `--{flag}` comes from {seen[flag]} and {owner}")
        seen[flag] = owner


def _build_spec(fn: Callable[..., Any], hints: SafetyHints) -> CommandSpec:
    fn_name = getattr(fn, "__name__", None)
    if fn_name is None:
        raise TypeError(f"a command must be a named function, got {fn!r}")
    signature = inspect.signature(fn, eval_str=True)
    summary, descriptions = parse_docstring(inspect.getdoc(fn) or "")

    fields: dict[str, Any] = {}
    flag_fields: dict[str, Any] = {}
    flat: dict[str, frozenset[str]] = {}
    model_params: dict[str, ModelParam] = {}
    owners: list[tuple[str, str]] = []
    positionals: list[str] = []
    variadic: str | None = None
    for param_name, param in signature.parameters.items():
        annotation = _annotation(param)
        model_class = _model_class(annotation)
        is_flat = _is_flat(annotation)
        if is_flat and model_class is None:
            raise TypeError(
                f"Flat needs a pydantic model, got {get_args(annotation)[0]!r} for parameter '{param_name}'"
            )

        default = ... if param.default is param.empty else param.default
        field = default if isinstance(default, FieldInfo) else FieldInfo.from_field(default)
        declared = FieldInfo.from_annotated_attribute(annotation, field)
        if _POSITIONAL in declared.metadata:
            if _model_class(annotation, optional=True) is not None:
                raise TypeError(f"a positional cannot be a pydantic model, got parameter '{param_name}'")
            if variadic is not None:
                raise ValueError(
                    f"positional '{param_name}' follows the list positional '{variadic}', which must be the last one"
                )
            variadic = param_name if _is_variadic(declared.annotation) else None
            positionals.append(param_name)
        if _model_class(annotation, optional=True) is not None:
            model_params[param_name] = ModelParam(
                empty_when_unset=model_class is not None and declared.is_required(),
                declared=declared,
            )

        described = FieldInfo.from_annotation(annotation).description or field.description
        if not described and param_name in descriptions:
            annotation = Annotated[annotation, Field(description=descriptions[param_name])]
        fields[param_name] = (annotation, field)

        if model_class is None or not is_flat:
            flag_fields[param_name] = fields[param_name]
            owners.append((_kebab_case(_raw_key(declared, param_name)), f"`{param_name}`"))
            continue
        flag_fields.update(_flat_fields(param_name, model_class, model_params[param_name].instance))
        keys = [_raw_key(info, name) for name, info in model_class.model_fields.items()]
        owners.extend((_kebab_case(key), f"`{param_name}: Flat[{model_class.__name__}]`") for key in keys)
        flat[param_name] = frozenset(keys)
    _check_flag_names(owners)

    model = create_model(
        _pascal_case(fn_name),
        __base__=InputModel,
        __doc__=summary,
        **fields,
    )
    flag_model = model
    if flat:
        flag_model = create_model(
            _pascal_case(fn_name),
            __base__=InputModel,
            __doc__=summary,
            **flag_fields,
        )
    returns = Any if signature.return_annotation is signature.empty else signature.return_annotation
    return CommandSpec(
        name=_kebab_case(fn_name),
        fn=fn,
        model=model,
        output=TypeAdapter(returns),
        hints=hints,
        summary=summary,
        model_params=model_params,
        flag_model=flag_model,
        flat=flat,
        positionals=tuple(positionals),
        positional_only=tuple(name for name, p in signature.parameters.items() if p.kind is p.POSITIONAL_ONLY),
        var_positional=next((name for name, p in signature.parameters.items() if p.kind is p.VAR_POSITIONAL), None),
    )


class Parser(argparse.ArgumentParser):
    """
    An ArgumentParser that raises its errors instead of printing usage and exiting.

    It keeps the paragraphs of a description, which argparse joins into one by default.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("formatter_class", argparse.RawDescriptionHelpFormatter)
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> NoReturn:
        raise InputRejected(message)

    def _check_value(self, action: argparse.Action, value: Any) -> None:
        """
        Raise COMMAND_NOT_FOUND for an unknown command.

        argparse calls this hook for each value it checks against choices. On its own it reports an unknown command
        only as text.
        """
        if isinstance(action, argparse._SubParsersAction) and value not in action.choices:
            raise InputRejected.command_not_found(self.prog, list(action.choices), value)
        super()._check_value(action, value)

    def _match_argument(self, action: argparse.Action, arg_strings_pattern: str) -> int:
        """
        Raise `missing_value` for a flag given without its value.

        argparse calls this hook while parsing, once for each flag, to count its values. On its own it reports a
        missing value only as text. A value flag has a single spelling, so `option_strings[0]` is the flag as typed.
        """
        try:
            return super()._match_argument(action, arg_strings_pattern)
        except argparse.ArgumentError:
            raise InputRejected.missing_value(action.dest, action.option_strings[0]) from None


def _flags(parser: argparse.ArgumentParser) -> list[str]:
    """
    Every flag spelling a leaf accepts, except help.

    argparse has no public way to list the flags of a parser, so this reads its private `_actions`.
    """
    return [
        option
        for action in parser._actions
        if not isinstance(action, argparse._HelpAction)
        for option in action.option_strings
    ]


def _defer_missing_positionals(parser: argparse.ArgumentParser) -> None:
    """
    Let pydantic report a missing positional as a `missing` field error.

    argparse checks only `required` before it rejects a missing positional, and only as text. The usage line comes
    from `nargs`, so it stays correct. argparse then leaves the value unset, as for a missing required flag.
    """
    for action in parser._actions:
        if not action.option_strings:
            action.required = False


@dataclass(frozen=True)
class Leaf:
    """What a run needs from the subparser argparse picked."""

    spec: CommandSpec
    source: CliSettingsSource[Any]
    flags: list[str]


class App:
    """
    A CLI: a named tree of commands that runs from an argv list.

    Args:
        name: the program name in usage lines and errors. For a mounted App, also the token that selects it on the
            command line.
        description: the help text, printed as written after the common indentation is removed. Its first line is
            the summary in the parent's `--help`.
    """

    def __init__(self, name: str, *, description: str | None = None) -> None:
        self.name = name
        self.description = inspect.cleandoc(description) if description else None
        self._children: dict[str, CommandSpec | App] = {}

    @overload
    def command(self, fn: F) -> F: ...

    @overload
    def command(
        self,
        *,
        read_only: bool = False,
        destructive: bool = False,
        idempotent: bool = False,
        open_world: bool = False,
    ) -> Callable[[F], F]: ...

    def command(
        self,
        fn: F | None = None,
        *,
        read_only: bool = False,
        destructive: bool = False,
        idempotent: bool = False,
        open_world: bool = False,
    ) -> F | Callable[[F], F]:
        """Register a function as a command, used bare (`@app.command`) or called (`@app.command(...)`)."""
        hints = SafetyHints(
            read_only=read_only,
            destructive=destructive,
            idempotent=idempotent,
            open_world=open_world,
        )

        def register(fn: F) -> F:
            spec = _build_spec(fn, hints)
            self._register(spec.name, spec)
            return fn

        return register if fn is None else register(fn)

    def add(self, app: "App") -> None:
        """Mount another App as a group, selected on the command line by its name."""
        if not isinstance(app, App):
            raise TypeError(f"add takes an App, got {app!r}; register a function with @app.command")
        if app._reaches(self):
            raise ValueError(f"mounting '{app.name}' on '{self.name}' makes a cycle")
        self._register(app.name, app)

    def _register(self, name: str, child: "CommandSpec | App") -> None:
        if name in self._children:
            raise ValueError(f"'{self.name}' already has a command or group named '{name}'")
        self._children[name] = child

    def _reaches(self, app: "App") -> bool:
        """Whether `app` is this App or is mounted anywhere below it."""
        return app is self or any(isinstance(child, App) and child._reaches(app) for child in self._children.values())

    @property
    def _summary(self) -> str:
        return parse_docstring(self.description or "")[0]

    def _parser(self) -> argparse.ArgumentParser:
        # stop argparse from expanding a prefix such as --ti to --title
        parser = Parser(prog=self.name, description=self.description, allow_abbrev=False)
        self._add_children(parser)
        return parser

    def _add_children(self, parser: argparse.ArgumentParser) -> None:
        """
        Add a subparser for each child, recursively for groups.

        Each group on the path overwrites `_level` and `_choices`, so a missing command is reported at the deepest
        group. `_choices` is a tuple, because pydantic-settings parses every list in argparse's result as input. The
        subparsers are not `required=True`, or argparse would reject a missing command with its own text.
        """
        parser.set_defaults(_level=parser.prog, _choices=tuple(self._children))
        subparsers = parser.add_subparsers(dest="_command_name")
        for name, child in self._children.items():
            # argparse 3.14.0 puts colour codes in a default prog, and error messages show the prog
            prog = f"{parser.prog} {name}"
            # argparse applies % formatting to help text, so double each literal %
            summary = (child._summary if isinstance(child, App) else child.summary).replace("%", "%%")
            if isinstance(child, App):
                subparser = subparsers.add_parser(
                    name,
                    prog=prog,
                    help=summary,
                    description=child.description,
                    allow_abbrev=False,
                )
                child._add_children(subparser)
                continue
            subparser = subparsers.add_parser(
                name,
                prog=prog,
                help=summary,
                description=child.summary,
                allow_abbrev=False,
            )
            source = CliSettingsSource(child.flag_model, root_parser=subparser)
            _defer_missing_positionals(subparser)
            subparser.set_defaults(_leaf=Leaf(child, source, _flags(subparser)))

    def __call__(self, argv: Sequence[str] | None = None) -> NoReturn:
        """Run the command named in argv (default `sys.argv[1:]`), print its result or error and exit."""
        try:
            output = self._run(argv)
        except Exception as error:
            fail(error)
        if output is not None:
            print(output)
        raise SystemExit(ExitCode.OK)

    @staticmethod
    def _inputs(leaf: Leaf, parsed_args: argparse.Namespace) -> dict[str, Any]:
        """The raw values from the flags, with the model parameter defaults applied."""
        raw = leaf.source(parsed_args=parsed_args)()
        fields = leaf.spec.model.model_fields
        # pop all groups first, because a Flat parameter can have the name of a field in another Flat model
        groups = {name: {key: raw.pop(key) for key in keys if key in raw} for name, keys in leaf.spec.flat.items()}
        raw.update({_raw_key(fields[name], name): group for name, group in groups.items() if group})
        for name, param in leaf.spec.model_params.items():
            key = _raw_key(fields[name], name)
            if key not in raw:
                if param.empty_when_unset:
                    raw[key] = {}
            elif isinstance(raw[key], Mapping) and (base := param.base()) is not None:
                raw[key] = _deep_merge(base, raw[key])
        return raw

    def _run(self, argv: Sequence[str] | None) -> str | None:
        """The rendered result, or None when there is nothing to print."""
        parsed_args, leftovers = self._parser().parse_known_args(argv)
        if not hasattr(parsed_args, "_leaf"):
            raise InputRejected.command_not_found(parsed_args._level, list(parsed_args._choices))
        leaf: Leaf = parsed_args._leaf
        spec = leaf.spec
        flat, positionals = frozenset(spec.flat), frozenset(spec.positionals)
        try:
            command_inputs = spec.model(**self._inputs(leaf, parsed_args))
        except (ValidationError, SettingsError) as error:
            raise InputRejected.from_parse(spec.model, leftovers, leaf.flags, error, flat, positionals) from None
        if leftovers:
            raise InputRejected.from_parse(spec.model, leftovers, leaf.flags, flat=flat, positionals=positionals)
        by_keyword = dict(command_inputs)
        by_place = [by_keyword.pop(name) for name in spec.positional_only]
        unpacked = by_keyword.pop(spec.var_positional) if spec.var_positional else []
        result = spec.fn(*by_place, *unpacked, **by_keyword)
        if result is None:
            return None
        return json.dumps(spec.output.dump_python(result, mode="json"))

import argparse
import inspect
import json
import types
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, NoReturn, TypeVar, Union, get_args, get_origin, overload

from pydantic import BaseModel, Field, TypeAdapter, ValidationError, create_model
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    SettingsError,
)

from argdantic.docstrings import parse_docstring
from argdantic.errors import ExitCode, InputRejected, fail

F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


class _FlatMarker:
    """Marks a model parameter whose fields become top-level flags."""


# `Flat[Model]` reads as `Model` to a type checker, and drops the parameter name from the model's flags
Flat = Annotated[T, _FlatMarker()]


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
        # no env input, only flags and defaults
        return (init_settings,)


@dataclass(frozen=True)
class SafetyHints:
    """MCP-style tool annotations. Stored, not acted on yet."""

    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
    open_world: bool = False


@dataclass(frozen=True)
class _ModelParam:
    """A parameter annotated with a pydantic model."""

    # with no default and no flags, the model validates from `{}` inside the input model, so each missing field
    # and each bad env value is reported on its own path
    empty_when_unset: bool
    # the field as the author declared it, with the default the flags given for this parameter update
    declared: FieldInfo

    @property
    def instance(self) -> BaseModel | None:
        """The default instance, without calling a factory."""
        default = self.declared.default
        return default if isinstance(default, BaseModel) else None

    def base(self) -> BaseModel | None:
        """The default the flags update: the instance, or a new one from the factory."""
        # a factory that takes the validated data has nothing to give before validation
        if self.declared.default_factory_takes_validated_data:
            return None
        default = self.declared.get_default(call_default_factory=True)
        return default if isinstance(default, BaseModel) else None


@dataclass(frozen=True)
class CommandSpec:
    """Everything argdantic knows about one command, built once at registration."""

    name: str
    fn: Callable[..., Any]
    model: type[InputModel]
    output: TypeAdapter[Any]
    hints: SafetyHints
    summary: str
    model_params: dict[str, _ModelParam]
    # builds the parser: `model` with each Flat model's fields in place of its parameter
    flag_model: type[InputModel]
    # each Flat parameter, with the raw keys of its model's fields
    flat: dict[str, frozenset[str]]


def _kebab_case(name: str) -> str:
    return name.replace("_", "-")


def _pascal_case(name: str) -> str:
    return name.title().replace("_", "")


def _model_class(annotation: Any, *, optional: bool = False) -> type[BaseModel] | None:
    """The pydantic model class an annotation names, through `Annotated` and, if `optional`, `X | None`, or None."""
    if get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    if optional and get_origin(annotation) in (Union, types.UnionType):
        members = [member for member in get_args(annotation) if member is not type(None)]
        annotation = members[0] if len(members) == 1 else None
    return annotation if isinstance(annotation, type) and issubclass(annotation, BaseModel) else None


def _deep_merge(base: Mapping[str, Any] | BaseModel, update: Mapping[str, Any]) -> dict[str, Any]:
    """A new dict: a mapping in `update` merges into a mapping or model in `base`, any other value replaces."""
    if isinstance(base, BaseModel):
        # read by attribute under the raw keys, so the author's serialization settings play no part
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
    return get_origin(annotation) is Annotated and any(isinstance(m, _FlatMarker) for m in annotation.__metadata__)


def _inlined(info: FieldInfo, name: str, default: Any) -> FieldInfo:
    """A copy of a Flat model's field for the flag model, with the default the run uses (`...` keeps its own)."""
    own = default is ...
    # the flag model keys this field by another name. pydantic-settings takes the flag from the alias and the raw
    # key from the validation alias, so both hold the raw key the field has in its own model
    key = _raw_key(info, name)
    return FieldInfo.from_field(
        info.default if own else default,
        default_factory=info.default_factory if own else None,
        alias=key,
        validation_alias=key,
        description=info.description,
    )


def _flat_fields(
    param_name: str,
    model_class: type[BaseModel],
    instance: BaseModel | None,
) -> dict[str, tuple[Any, FieldInfo]]:
    """The flag model's fields for a Flat parameter, one per field of its model, keyed `<param>__<field>`."""
    # a plain parameter may share the field's name and still have another flag, through an alias
    return {
        f"{param_name}__{name}": (
            info.annotation,
            _inlined(info, name, ... if instance is None else getattr(instance, name)),
        )
        for name, info in model_class.model_fields.items()
    }


def _check_flag_names(owners: list[tuple[str, str]]) -> None:
    """Raise when two parameters or Flat fields give the same top-level flag."""
    seen: dict[str, str] = {}
    for flag, owner in owners:
        if flag in seen:
            raise ValueError(f"flag `--{flag}` comes from {seen[flag]} and {owner}")
        seen[flag] = owner


def _build_spec(fn: Callable[..., Any], hints: SafetyHints) -> CommandSpec:
    # the command name comes from __name__, which partials and callable instances lack
    fn_name = getattr(fn, "__name__", None)
    if fn_name is None:
        raise TypeError(f"a command must be a named function, got {fn!r}")
    signature = inspect.signature(fn, eval_str=True)
    summary, param_descriptions = parse_docstring(inspect.getdoc(fn) or "")
    fields: dict[str, Any] = {}
    flag_fields: dict[str, Any] = {}
    owners: list[tuple[str, str]] = []
    model_params: dict[str, _ModelParam] = {}
    flat: dict[str, frozenset[str]] = {}
    for param_name, param in signature.parameters.items():
        default = ... if param.default is param.empty else param.default
        annotation = param.annotation
        model_class = _model_class(annotation)
        is_flat = _is_flat(annotation)
        if is_flat and model_class is None:
            raise TypeError(
                f"Flat needs a pydantic model, got {get_args(annotation)[0]!r} for parameter '{param_name}'"
            )
        # a `Field(...)` default holds the field's settings, as it does in a pydantic model
        field = default if isinstance(default, FieldInfo) else FieldInfo.from_field(default)
        # the default and the alias may also sit in a Field in the annotation
        declared = FieldInfo.from_annotated_attribute(annotation, field)
        if _model_class(annotation, optional=True) is not None:
            model_params[param_name] = _ModelParam(
                empty_when_unset=model_class is not None and declared.is_required(),
                declared=declared,
            )
        # Field(description=...) in the annotation or the default wins over the docstring
        described = FieldInfo.from_annotation(annotation).description or field.description
        if not described and param_name in param_descriptions:
            annotation = Annotated[annotation, Field(description=param_descriptions[param_name])]
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
    )


class _Parser(argparse.ArgumentParser):
    """An ArgumentParser that raises its errors instead of printing usage and exiting."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # argparse joins the paragraphs of a description into one by default
        kwargs.setdefault("formatter_class", argparse.RawDescriptionHelpFormatter)
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> NoReturn:
        raise InputRejected(message)

    def _check_value(self, action: argparse.Action, value: Any) -> None:
        # argparse reports an unknown command only as text, so raise the structured error before it does
        if isinstance(action, argparse._SubParsersAction) and value not in action.choices:
            raise InputRejected.command_not_found(self.prog, list(action.choices), value)
        super()._check_value(action, value)


def _flags(parser: argparse.ArgumentParser) -> list[str]:
    """Every flag spelling a leaf accepts, except help."""
    # argparse has no public way to list a parser's flags
    return [
        option
        for action in parser._actions
        if not isinstance(action, argparse._HelpAction)
        for option in action.option_strings
    ]


@dataclass(frozen=True)
class _Leaf:
    """What a run needs from the subparser argparse picked."""

    spec: CommandSpec
    source: CliSettingsSource[Any]
    flags: list[str]


class App:
    """A CLI: a named tree of commands that runs from an argv list.

    Args:
        name: the program name in usage lines and errors. For a mounted App, also the token that selects it on the
            command line.
        description: the help text. Its first line is the summary in the parent's `--help`.
    """

    def __init__(self, name: str, *, description: str | None = None) -> None:
        self.name = name
        # help prints the description as written, so a triple-quoted one loses its indentation here
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
        # allow_abbrev=False stops argparse expanding a prefix like --ti to --title
        parser = _Parser(prog=self.name, description=self.description, allow_abbrev=False)
        self._add_children(parser)
        return parser

    def _add_children(self, parser: argparse.ArgumentParser) -> None:
        # each group on the path overwrites these, so a missing command is reported at the deepest one. A tuple,
        # because pydantic-settings parses every list in argparse's result as input
        parser.set_defaults(_level=parser.prog, _choices=tuple(self._children))
        # not required=True: argparse would then reject a missing command with its own text, not COMMAND_NOT_FOUND
        subparsers = parser.add_subparsers(dest="_command_name")
        for name, child in self._children.items():
            # argparse 3.14.0 builds a default prog with colour codes, and error messages print the prog
            prog = f"{parser.prog} {name}"
            # argparse %-formats help text, so a literal % is doubled
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
            subparser.set_defaults(_leaf=_Leaf(child, source, _flags(subparser)))

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
    def _inputs(leaf: _Leaf, parsed_args: argparse.Namespace) -> dict[str, Any]:
        """The raw values from the flags, with the model parameter defaults applied."""
        raw = leaf.source(parsed_args=parsed_args)()
        fields = leaf.spec.model.model_fields
        # every group comes out before any goes back, since a Flat parameter may share its name with a field of
        # another Flat model
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
        leaf: _Leaf = parsed_args._leaf
        spec = leaf.spec
        flat = frozenset(spec.flat)
        try:
            command_inputs = spec.model(**self._inputs(leaf, parsed_args))
        except (ValidationError, SettingsError) as error:
            raise InputRejected.from_parse(spec.model, leftovers, leaf.flags, error, flat) from None
        if leftovers:
            raise InputRejected.from_parse(spec.model, leftovers, leaf.flags, flat=flat)
        result = spec.fn(**dict(command_inputs))
        if result is None:
            return None
        return json.dumps(spec.output.dump_python(result, mode="json"))

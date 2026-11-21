import argparse
import inspect
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, NoReturn, TypeVar, overload

from pydantic import Field, TypeAdapter, ValidationError, create_model
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    CliApp,
    CliSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    SettingsError,
)

from argdantic.docstrings import parse_docstring
from argdantic.errors import ExitCode, InputRejected, fail

F = TypeVar("F", bound=Callable[..., Any])


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
class CommandSpec:
    """Everything argdantic knows about one command, built once at registration."""

    name: str
    fn: Callable[..., Any]
    model: type[InputModel]
    output: TypeAdapter[Any]
    hints: SafetyHints
    summary: str


def _kebab_case(name: str) -> str:
    return name.replace("_", "-")


def _pascal_case(name: str) -> str:
    return name.title().replace("_", "")


def _build_spec(fn: Callable[..., Any], hints: SafetyHints) -> CommandSpec:
    # the command name comes from __name__, which partials and callable instances lack
    fn_name = getattr(fn, "__name__", None)
    if fn_name is None:
        raise TypeError(f"a command must be a named function, got {fn!r}")
    signature = inspect.signature(fn, eval_str=True)
    summary, param_descriptions = parse_docstring(inspect.getdoc(fn) or "")
    fields: dict[str, Any] = {}
    for param_name, param in signature.parameters.items():
        default = ... if param.default is param.empty else param.default
        # a `Field(...)` default holds the field's settings, as it does in a pydantic model
        field = default if isinstance(default, FieldInfo) else Field(default)
        annotation = param.annotation
        # Field(description=...) in the annotation or the default wins over the docstring
        described = FieldInfo.from_annotation(annotation).description or field.description
        if not described and param_name in param_descriptions:
            annotation = Annotated[annotation, Field(description=param_descriptions[param_name])]
        fields[param_name] = (annotation, field)
    model = create_model(
        _pascal_case(fn_name),
        __base__=InputModel,
        __doc__=summary,
        **fields,
    )
    return CommandSpec(
        name=_kebab_case(fn_name),
        fn=fn,
        model=model,
        output=TypeAdapter(signature.return_annotation),
        hints=hints,
        summary=summary,
    )


class _Parser(argparse.ArgumentParser):
    """An ArgumentParser that raises its errors instead of printing usage and exiting."""

    def error(self, message: str) -> NoReturn:
        raise InputRejected(message)


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
    """A CLI: a named tree of commands that runs from an argv list."""

    def __init__(self, name: str, *, description: str | None = None) -> None:
        self.name = name
        self.description = description
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
        return parse_docstring(inspect.cleandoc(self.description or ""))[0]

    def _parser(self) -> argparse.ArgumentParser:
        # allow_abbrev=False stops argparse expanding a prefix like --ti to --title
        parser = _Parser(prog=self.name, description=self.description, allow_abbrev=False)
        self._add_children(parser)
        return parser

    def _add_children(self, parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(dest="_command_name", required=True)
        for name, child in self._children.items():
            if isinstance(child, App):
                subparser = subparsers.add_parser(
                    name,
                    help=child._summary,
                    description=child.description,
                    allow_abbrev=False,
                )
                child._add_children(subparser)
                continue
            subparser = subparsers.add_parser(
                name,
                help=child.summary,
                description=child.summary,
                allow_abbrev=False,
            )
            source = CliSettingsSource(child.model, root_parser=subparser)
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

    def _run(self, argv: Sequence[str] | None) -> str | None:
        """The rendered result, or None when there is nothing to print."""
        argv = sys.argv[1:] if argv is None else list(argv)
        self._check_command_path(argv)
        parsed_args, leftovers = self._parser().parse_known_args(argv)
        leaf: _Leaf = parsed_args._leaf
        spec = leaf.spec
        try:
            command_inputs = CliApp.run(spec.model, cli_args=parsed_args, cli_settings_source=leaf.source)
        except (ValidationError, SettingsError) as error:
            raise InputRejected.from_parse(spec.model, leftovers, leaf.flags, error) from None
        if leftovers:
            raise InputRejected.from_parse(spec.model, leftovers, leaf.flags)
        result = spec.fn(**dict(command_inputs))
        if result is None:
            return None
        return json.dumps(spec.output.dump_python(result, mode="json"))

    def _check_command_path(self, argv: Sequence[str]) -> None:
        """Walk argv down the tree to a command, so a wrong or missing name gets its choices, not argparse's text."""
        app, path = self, [self.name]
        for token in argv:
            if token in ("-h", "--help"):
                return
            if token.startswith("-"):
                # a flag where a command name should be: the name is missing, not unknown
                break
            child = app._children.get(token)
            if child is None:
                raise InputRejected.command_not_found(path, list(app._children), token)
            if isinstance(child, CommandSpec):
                return
            app, path = child, [*path, token]
        raise InputRejected.command_not_found(path, list(app._children))

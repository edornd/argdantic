import argparse
import inspect
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar, overload

from pydantic import Field, TypeAdapter, ValidationError, create_model
from pydantic_settings import (
    BaseSettings,
    CliApp,
    CliSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from argdantic.docstrings import parse_docstring

F = TypeVar("F", bound=Callable[..., Any])


class Command(BaseSettings):
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
        # No env input: CliApp.run puts the CLI source in front of these, and defaults fill the rest.
        return (init_settings,)


@dataclass(frozen=True)
class SafetyHints:
    """MCP-style tool annotations. Stored only; they take effect in M3."""

    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
    open_world: bool = False


@dataclass(frozen=True)
class CommandSpec:
    """Everything argdantic knows about one command, built once at registration."""

    name: str
    fn: Callable[..., Any]
    model: type[Command]
    output: TypeAdapter[Any]
    hints: SafetyHints
    summary: str


def _kebab_case(name: str) -> str:
    return name.replace("_", "-")


def _build_spec(fn: Callable[..., Any], hints: SafetyHints) -> CommandSpec:
    # Any callable fits the type, but the command name comes from __name__, which partials and instances lack.
    fn_name = getattr(fn, "__name__", None)
    if fn_name is None:
        raise TypeError(f"a command must be a named function, got {fn!r}")
    signature = inspect.signature(fn, eval_str=True)
    summary, param_descriptions = parse_docstring(inspect.getdoc(fn) or "")
    fields: dict[str, Any] = {}
    for param_name, param in signature.parameters.items():
        default = ... if param.default is param.empty else param.default
        # A Field(description=...) in the annotation wins over the docstring, so only pass one when the
        # docstring has it: an explicit description=None would override the annotation.
        description = param_descriptions.get(param_name)
        field = Field(default) if description is None else Field(default, description=description)
        fields[param_name] = (param.annotation, field)
    model = create_model(
        fn_name.title().replace("_", ""),
        __base__=Command,
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


class App:
    """A CLI: a named tree of commands that runs from an argv list."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._commands: dict[str, CommandSpec] = {}

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
            self._add(_build_spec(fn, hints))
            return fn

        return register if fn is None else register(fn)

    def _add(self, spec: CommandSpec) -> None:
        self._commands[spec.name] = spec

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog=self.name)
        subparsers = parser.add_subparsers(dest="_command_name", required=True)
        for spec in self._commands.values():
            subparser = subparsers.add_parser(
                spec.name,
                help=spec.summary,
                description=spec.summary,
            )
            subparser.set_defaults(
                _command_spec=spec,
                _cli_source=CliSettingsSource(spec.model, root_parser=subparser),
            )
        return parser

    def __call__(self, argv: Sequence[str] | None = None) -> None:
        # argparse reads sys.argv[1:] when argv is None.
        parsed_args = self._parser().parse_args(argv)
        spec: CommandSpec = parsed_args._command_spec
        try:
            command_inputs = CliApp.run(
                spec.model,
                cli_args=parsed_args,
                cli_settings_source=parsed_args._cli_source,
            )
        except ValidationError as error:
            # Plain text until structured errors land (ticket 02).
            print(error, file=sys.stderr)
            raise SystemExit(2) from None
        result = spec.fn(**{name: getattr(command_inputs, name) for name in type(command_inputs).model_fields})
        if result is not None:
            print(json.dumps(spec.output.dump_python(result, mode="json")))
        raise SystemExit(0)

import argparse
import inspect
from typing import Any, Callable, List, Optional, Sequence, Type

from pydantic import BaseModel, create_model
from pydantic.utils import lenient_issubclass

from argdantic.arguments import Argument
from argdantic.convert import args_to_dict_tree, model_to_args


class Command:
    def __init__(
        self,
        callback: Callable,
        arguments: Sequence[Argument],
        model_class: Type[BaseModel],
        name: str = None,
        description: str = None,
        delimiter: str = "__",
    ) -> None:
        assert callback is not None, "Callback must be a callable object"
        self.name = name
        self.description = description
        self.callback = callback
        self.model_class = model_class
        self.delimiter = delimiter
        self.arguments = arguments or []

    def __repr__(self) -> str:
        return f"<Command {self.name}>"

    def __call__(self, args: List[Any] = None) -> Any:
        parser = self.build()
        kwargs = vars(parser.parse_args(args))
        raw_data = args_to_dict_tree(kwargs, self.delimiter)
        validated = self.model_class(**raw_data)
        desctructured = {k: getattr(validated, k) for k in validated.__fields__.keys()}
        return self.callback(**desctructured)

    def build(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog=self.name,
            description=self.description,
        )
        for argument in self.arguments:
            argument.build(parser=parser)
        return parser


class ArgParser:
    def __init__(self, name: str = None) -> None:
        self.name = name
        self.entrypoint = None
        self.commands = []

    def __repr__(self) -> str:
        name = f" '{self.name}'" if self.name else ""
        return f"<Parser{name}(commands={self.commands})>"

    def __call__(self) -> Any:
        if self.entrypoint is None:
            self._build_entrypoint()
        return self.entrypoint()

    def _build_entrypoint(self) -> Callable:
        self.entrypoint = self.commands[0]
        return self.entrypoint

    def command(
        self,
        name: Optional[str] = None,
        help: Optional[str] = None,
        delimiter: str = ".",
        internal_delimiter: str = "__",
    ) -> Callable:
        assert (
            internal_delimiter.isidentifier()
        ), f"The internal delimiter {internal_delimiter} is not a valid identifier"

        def decorator(f: Callable) -> Command:
            # create a name or use the provided one
            command_name = name or f.__name__.lower().replace("_", "-")
            command_help = help or inspect.getdoc(f)
            # extract function parameters and prepare list of click params
            # assign the same function as callback for empty commands
            func_params = list(inspect.signature(f).parameters.items())
            # if we have a configuration parse it, otherwise handle empty commands
            # wrap everything into a wrapper model, so that multiple inputs can be provided
            arguments = None
            wrapped_fields = dict()
            if func_params:
                for param_name, param in func_params:
                    assert param.annotation is not inspect.Parameter.empty, f"Field '{name}' lacks annotations"
                    default_value = param.default if param.default is not inspect.Parameter.empty else Ellipsis
                    wrapped_fields[param_name] = (param.annotation, default_value)

            cfg_class = create_model("WrapperModel", **wrapped_fields)
            assert lenient_issubclass(cfg_class, BaseModel), "Configuration must be a pydantic model"
            arguments = model_to_args(cfg_class, delimiter, internal_delimiter)

            command = Command(
                callback=f,
                arguments=arguments,
                model_class=cfg_class,
                name=command_name,
                description=command_help,
                delimiter=internal_delimiter,
            )
            # add command to current CLI list and return it
            self.commands.append(command)
            return command

        return decorator

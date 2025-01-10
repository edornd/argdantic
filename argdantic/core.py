import inspect
from argparse import ArgumentParser, Namespace, _SubParsersAction
from typing import Any, Callable, Dict, Generic, Iterable, List, Optional, Sequence, Type, TypeVar, cast, get_type_hints

from pydantic import BaseModel, ValidationError, create_model
from pydantic.v1.utils import lenient_issubclass
from pydantic_settings import BaseSettings
from pydantic_settings.sources import PydanticBaseSettingsSource

from argdantic.convert import args_to_dict_tree, model_to_args
from argdantic.parsing import Argument
from argdantic.parsing.arguments import ActionTracker
from argdantic.stores import SettingsStoreCallable

SettingSourceCallable = Callable[[Type[BaseSettings]], PydanticBaseSettingsSource]
ParserType = TypeVar("ParserType", bound="ArgParser")


class Command:
    """
    A command represents a single function that can be invoked from the command line.
    It is composed of a callback function, a list of arguments, and a pydantic model
    that is used to validate the arguments.
    """

    def __init__(
        self,
        callback: Callable,
        arguments: Iterable[Argument],
        model_class: Type[BaseModel],
        name: str,
        description: Optional[str] = None,
        singleton: bool = False,
        stores: Optional[List[SettingsStoreCallable]] = None,
        delimiter: str = "__",
    ) -> None:
        assert callback is not None, "Callback must be a callable object"
        self.name = name
        self.description = description
        self.singleton = singleton
        self.callback = callback
        self.model_class = model_class
        self.delimiter = delimiter
        self.arguments = arguments or []
        self.stores = stores or []
        self.trackers: Dict[str, ActionTracker] = {}

    def __repr__(self) -> str:
        return f"<Command {self.name}>"

    def __call__(self, args: Namespace) -> Any:
        """
        Invoke the command with the arguments already parsed by argparse,
        and return the result, which is the return value of the callback.
        Arguments are converted into a dictionary and passed to the pydantic model
        for validation. The validated model is then passed to the callback.

        Args:
            args (Namespace): parsed arguments provided by argparse.

        Returns:
            Any: return value of the callback.
        """
        # transform the arguments into a dictionary tree for validation
        kwargs = vars(args)
        raw_data = args_to_dict_tree(
            kwargs,
            internal_delimiter=self.delimiter,
            remove_helpers=True,
            cli_trackers=self.trackers,
        )
        # validate the arguments against the pydantic model
        validated = self.model_class(**raw_data)
        # store the validated arguments in the settings stores
        for store in self.stores:
            store(validated)
        # invoke the callback with the validated arguments
        # if the command is a singleton, pass the model as a single argument
        if self.singleton:
            return self.callback(validated)
        destructured = {k: getattr(validated, k) for k in validated.model_fields.keys()}
        return self.callback(**destructured)

    def build(self, parser: ArgumentParser) -> None:
        """
        Build the command by adding all arguments to the parser.

        Args:
            parser (ArgumentParser): parser to add the arguments to.
        """
        for argument in self.arguments:
            tracker = argument.build(parser=parser)
            self.trackers[argument.identifier] = tracker
        parser.set_defaults(__func__=self)


class ArgParser(Generic[ParserType]):
    """
    A parser is a collection of commands and subparsers.
    It is responsible for building the entrypoint for the command line interface,
    and invoking the correct command by constructing the parser hierarchy.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        force_group: bool = False,
        delimiter: str = ".",
        internal_delimiter: str = "__",
        subcommand_meta: str = "<command>",
    ) -> None:
        self.entrypoint: Optional[ArgumentParser] = None
        self.name = name
        self.description = description
        self.force_group = force_group
        self.commands: List[Command] = []
        self.groups: List[ParserType] = []
        # internal variables
        assert internal_delimiter.isidentifier(), (
            f"The internal delimiter {internal_delimiter} is not a valid identifier"
        )

        self._delimiter = delimiter
        self._internal_delimiter = internal_delimiter
        self._subcommand_meta = subcommand_meta
        # keeping a reference to subparser is necessary to add subparsers
        # Each cli level can only have one subparser.
        self._subparser: Optional[_SubParsersAction] = None

    def __repr__(self) -> str:
        name = f" '{self.name}'" if self.name else ""
        return f"<Parser{name}(commands={self.commands})>"

    def __call__(self, args: Optional[Namespace] = None) -> Any:
        """
        Invoke the parser by building the entrypoint and parsing the arguments.
        The result is the return value of the callback of the invoked command.

        Args:
            args (Sequence[Any], optional): arguments to parse. Defaults to None.

        Returns:
            Any: return value of the callback.
        """
        if self.entrypoint is None:
            self.entrypoint = self._build_entrypoint()
        try:
            args = self.entrypoint.parse_args(cast(Sequence[str], args))
            return args.__func__(args)
        except ValidationError as e:
            self.entrypoint.error(self._format_validation_error(e))

    def _format_validation_error(self, exception: ValidationError) -> str:
        """
        Format a validation error into a string, providinf a more human-readable representation.

        Args:
            exception (ValidationError): validation error raised by pydantic.

        Returns:
            str: formatted string.
        """
        errors = exception.errors()
        num_errors = len(errors)
        intro = f"{num_errors} validation {'error' if num_errors == 1 else 'errors'} while parsing arguments\n"
        body = []
        max_len = 0
        for error in errors:
            location = " -> ".join(str(e) for e in error["loc"])
            max_len = max(max_len, len(location))
            body.append((location, error["msg"]))
        body_str = "\n".join(f"{location:<{max_len}}: {msg}" for location, msg in body)
        return f"{intro}{body_str}"

    def _get_subparser(
        self,
        parser: ArgumentParser,
        *,
        destination: str = "group",
    ) -> _SubParsersAction:
        """
        Get the subparser for the current parser. If it does not exist, create it.

        Args:
            destination (str, optional): destination of the subparser. Defaults to "group".

        Returns:
            _SubParsersAction: subparser.
        """
        if self._subparser is None:
            self._subparser = parser.add_subparsers(dest=destination, required=True, metavar=self._subcommand_meta)
        return self._subparser

    def _build_entrypoint(self, parser: Optional[ArgumentParser] = None, level: int = 0) -> ArgumentParser:
        """
        Construct the entrypoint for the command line interface. This is a recursive
        function that builds the entrypoint for the current parser and all subparsers.

        Args:
            parser (ArgumentParser, optional): Current parser to pass around. Defaults to None.

        Returns:
            Callable: the main parser to be invoked as root.
        """
        assert self.commands or self.groups, "Parser must have at least one command or group of commands"
        # if the root parser is not provided, create a new one
        # else, create a subparser for the current parser
        if parser is None:
            parser = ArgumentParser(prog=self.name, description=self.description)

        # then build the entrypoint for the current parser
        if len(self.commands) == 1 and not self.groups and not self.force_group:
            parser.description = self.commands[0].description
            self.commands[0].build(parser=parser)
        else:
            subparsers = self._get_subparser(parser, destination=f"__group{level}__")
            for command in self.commands:
                subparser = subparsers.add_parser(command.name, help=command.description)
                command.build(parser=subparser)

        # last, build the entrypoint for all subparsers
        for group in self.groups:
            sublevel = level + 1
            subparser = self._get_subparser(parser, destination=f"__group{sublevel}__")
            group._build_entrypoint(
                parser=subparser.add_parser(group.name, help=group.description),
                level=sublevel,
            )
        return parser

    def command(
        self,
        name: Optional[str] = None,
        help: Optional[str] = None,
        sources: Optional[List[SettingSourceCallable]] = None,
        stores: Optional[List[SettingsStoreCallable]] = None,
        singleton: bool = False,
    ) -> Callable:
        """Decorator to register a function as a command.

        Args:
            name (str, optional): Name of the command. Defaults to the function name when not provided.
            help (str, optional): Help text for the command. Defaults to the function docstring when not provided.
            delimiter (str, optional): Custom delimiter character. Defaults to ".".
            internal_delimiter (str, optional): Custom internal delimiter. Defaults to "__".

        Returns:
            Callable: The same function, promoted to a command.
        """
        assert sources is None or isinstance(sources, list), "Sources must be a list of callables"
        assert stores is None or isinstance(stores, list), "Stores must be a list of callables"

        def decorator(f: Callable) -> Command:
            # create a name or use the provided one
            command_name = name or f.__name__.lower().replace("_", "-")
            command_help = help or inspect.getdoc(f)
            # extract function parameters and prepare list of click params
            # assign the same function as callback for empty commands
            f.__annotations__ = get_type_hints(f)
            func_params = list(inspect.signature(f).parameters.items())
            # if we have a configuration parse it, otherwise handle empty commands
            # wrap everything into a wrapper model, so that multiple inputs can be provided
            arguments = None
            model_class = None
            wrapped_fields = dict()
            if func_params:
                # if the function expects a single argument, we do not wrap it
                # otherwise, we prepare the fields for the wrapper model
                if singleton:
                    assert len(func_params) == 1, (
                        f"The command '{command_name}' expects a single argument, but {len(func_params)} were provided"
                    )
                    param_name, param = func_params[0]
                    assert lenient_issubclass(param.annotation, BaseModel), (
                        f"The singleton argument '{param_name}' must be a pydantic model"
                    )
                    model_class = param.annotation

                else:
                    for param_name, param in func_params:
                        assert param.annotation is not inspect.Parameter.empty, (
                            f"Field '{param_name}' lacks type annotations"
                        )
                        default_value = param.default if param.default is not inspect.Parameter.empty else Ellipsis
                        wrapped_fields[param_name] = (param.annotation, default_value)

            # set the base Model and Config class
            if sources:

                class StaticSourceSettings(BaseSettings):
                    # patch the config class so that pydantic functionality remains
                    # the same, but the sources are properly initialized

                    @classmethod
                    def settings_customise_sources(
                        cls,
                        settings_cls: Type[BaseSettings],
                        init_settings: PydanticBaseSettingsSource,
                        env_settings: PydanticBaseSettingsSource,
                        dotenv_settings: PydanticBaseSettingsSource,
                        file_secret_settings: PydanticBaseSettingsSource,
                    ):
                        # cheeky way to harmonize the sources inside the config class:
                        # this is needed to make sure that the config class is properly
                        # initialized with the sources declared by the user on CLI init.
                        # Env and file sources are discarded, the user must provide them explicitly.
                        source_list = cast(List[SettingSourceCallable], sources)
                        callables = [source(settings_cls) for source in source_list]
                        return (init_settings, *callables)

                model_class = StaticSourceSettings if model_class is None else (model_class, StaticSourceSettings)

            cfg_class = create_model(  # type: ignore
                "WrapperModel",
                **wrapped_fields,
                __base__=model_class,
            )
            arguments = model_to_args(cfg_class, self._delimiter, self._internal_delimiter)

            command = Command(
                callback=f,
                arguments=arguments,
                model_class=cfg_class,
                name=command_name,
                description=command_help,
                singleton=singleton,
                stores=stores,
                delimiter=self._internal_delimiter,
            )
            # add command to current CLI list and return it
            self.commands.append(command)
            return command

        return decorator

    def add_parser(self, parser: ParserType, name: Optional[str] = None) -> None:
        """
        Add a subparser to the current parser.

        Args:
            parser (ArgParser): subparser to add.
        """
        assert parser.name or name, "The given subparser must have a name"
        if name:
            parser.name = name
        self.groups.append(parser)

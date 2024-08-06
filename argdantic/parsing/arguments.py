import json
from abc import ABC, abstractmethod
from argparse import ArgumentParser, ArgumentTypeError
from collections import abc, deque
from enum import Enum
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
    get_args,
    get_origin,
)

from argdantic.parsing.actions import (
    Action,
    AppendAction,
    StoreAction,
    StoreFalseAction,
    StoreTrueAction,
)
from argdantic.registry import Registry
from argdantic.utils import is_container, type_name

registry = Registry()

cli_types: Dict[str, Tuple[Any, str]] = {
    "bool": (bool, "BOOL"),
    "int": (int, "INT"),
    "float": (float, "FLOAT"),
    "complex": (complex, "COMPLEX"),
    "bytes": (str.encode, "BYTES"),
    "str": (str, "TEXT"),
    "dict": (dict, "JSON"),
    "datetime": (str, "DATETIME"),
    "date": (str, "DATE"),
    "time": (str, "TIME"),
    "timedelta": (str, "TIMEDELTA"),
    "path": (str, "PATH"),
    "email": (str, "EMAIL"),
}
cli_default = (str, "TEXT")


class ActionTracker:
    """
    Action tracker for argparse actions. This class is used to track if an action has been
    specified or not. This is useful for determining if an argument has been set or not using the CLI.
    """

    def __init__(self, action_class: Type[Action]) -> None:
        self.action_class = action_class
        self.action: Optional[Action] = None

    def __call__(self, option_strings: Sequence[str], dest: str, **kwargs) -> Any:
        self.action = self.action_class(option_strings, dest, **kwargs)
        return self.action

    def is_set(self) -> bool:
        return self.action is not None and self.action.specified  # type: ignore


class MultiActionTracker(ActionTracker):
    """
    Multi action tracker for argparse actions. This class is used to track if an action has been
    specified or not. Compared to the ActionTracker, this class is used for actions that can be
    specified multiple times.
    """

    def __init__(self, trackers: List[ActionTracker]) -> None:
        self.trackers = trackers

    def is_set(self) -> bool:
        return any(tracker.is_set() for tracker in self.trackers)


class Argument(ABC):
    """
    Base class for all argument types. This class is not meant to be used directly, but rather
    subclassed to create new argument types.
    """

    def __init__(
        self,
        *field_names: str,
        identifier: str,
        field_type: Type[Any],
        default: Any = None,
        required: bool = True,
        description: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.identifier = identifier
        self.field_names = field_names
        self.field_type = field_type
        self.default = default
        self.required = required
        self.description = description

    @abstractmethod
    def build(self, parser: ArgumentParser) -> ActionTracker:
        raise NotImplementedError  # pragma: no cover

    def build_internal(self, parser: ArgumentParser, *, action: Type[Action], **optional_fields: Any) -> ActionTracker:
        tracker = ActionTracker(action)
        parser.add_argument(
            *self.field_names,
            dest=self.identifier,
            default=self.default,
            required=self.required,
            help=self.description,
            action=tracker,  # type: ignore
            **optional_fields,
        )
        return tracker


class PrimitiveArgument(Argument):
    """
    Argument for primitive types, assigned as default argument type
    """

    def build(self, parser: ArgumentParser) -> ActionTracker:
        cli_type, cli_metavar = cli_types.get(type_name(self.field_type), cli_default)
        return super().build_internal(
            parser,
            action=StoreAction,
            type=cli_type,
            metavar=cli_metavar,
        )


@registry.register(bool)
class FlagArgument(Argument):
    """
    Argument for a boolean flag. If the flag is present, the value is True, otherwise False
    """

    def build(self, parser: ArgumentParser) -> ActionTracker:
        # create a group with two mutually exclusive arguments
        group = parser.add_mutually_exclusive_group(required=self.required)
        # create a tracker for each argument, then create a multi-tracker to track both
        tracker_true = ActionTracker(StoreTrueAction)
        tracker_false = ActionTracker(StoreFalseAction)
        tracker = MultiActionTracker([tracker_true, tracker_false])
        # add the arguments to the group and set the default value, if any
        negative_field_names = [f"--no-{name.lstrip('-')}" for name in self.field_names]
        group.add_argument(
            *self.field_names,
            dest=self.identifier,
            action=cast(Type[Action], tracker_true),
            help=self.description,
        )  # type: ignore
        group.add_argument(
            *negative_field_names,
            dest=self.identifier,
            action=cast(Type[Action], tracker_false),
        )  # type: ignore
        default = self.default if self.default is not None else False
        parser.set_defaults(**{self.identifier: default})
        # return the multi-tracker
        return tracker


@registry.register(
    list,
    tuple,
    set,
    frozenset,
    range,
    deque,
    abc.Sequence,
    abc.Iterable,
)
class MultipleArgument(Argument):
    """
    Argument that accepts multiple values.
    When the field type is a container, the inner type is used to determine the type of the argument.
    For example, a field type of List[int] will result in an argument that accepts multiple integers.
    """

    def _type_and_count(self) -> Tuple[Type[Any], Union[str, int], Any]:
        inner_type = str
        arg_count: Union[str, int] = "+" if self.required else "*"
        metavar: Union[tuple, str] = cli_types[type_name(inner_type)]
        if is_container(self.field_type):
            # A non-composite type has a single argument, such as 'List[int]'
            # A composite type has a tuple of arguments, like 'Tuple[str, int, int]'.
            args = get_args(self.field_type)
            if len(args) == 1 or (len(args) == 2 and args[1] is Ellipsis):
                inner_type, metavar = cli_types.get(type_name(args[0]), cli_default)
            elif len(args) >= 2:
                arg_count = len(args)
                metavar = tuple([cli_types.get(type_name(arg), cli_default)[1] for arg in args])
        return inner_type, arg_count, metavar

    def build(self, parser: ArgumentParser) -> ActionTracker:
        field_type, nargs, metavar = self._type_and_count()
        return super().build_internal(
            parser,
            action=AppendAction,
            type=field_type,
            nargs=nargs,
            metavar=metavar,
        )


@registry.register(
    Literal,
    Enum,
)
class ChoiceArgument(Argument):
    """
    ChoiceArgument is a special case of MultipleArgument that has a fixed number of choices.
    It supports both Enum and Literal types. Overriding the *contains* and *iter* methods allows
    to use the very same class as a custom choices argument for argparse.
    """

    def __contains__(self, item: Any) -> bool:
        # The control is done after the `convert` method,
        # so the item is already a value or an Enum member.
        item_set = {i.value for i in self.field_type}
        key = item if self.value_only else item.value
        return key in item_set

    def __iter__(self) -> Iterator:
        return iter(self.field_type)  # type: ignore

    def __next__(self) -> Any:
        return next(iter(self.field_type))  # type: ignore

    def __len__(self) -> int:
        return len(self.field_type)  # type: ignore

    def __repr__(self) -> str:
        str_choices = [str(i.value) if self.value_only else i.name for i in self.field_type]
        return f"[{'|'.join(str_choices)}]"

    def convert(self, name: Any) -> Any:
        try:
            item = self.field_type[name]
        except KeyError:
            raise ArgumentTypeError(f"invalid choice: {name} (choose from {repr(self)})")
        if self.value_only:
            return item.value
        return item

    def build(self, parser: ArgumentParser) -> ActionTracker:
        self.value_only = False
        if get_origin(self.field_type) is Literal:
            self.field_type = Enum(self.identifier, {str(v): v for v in get_args(self.field_type)})  # type: ignore
            self.value_only = True
        return super().build_internal(
            parser,
            action=StoreAction,
            type=self.convert,
            metavar=repr(self),
            choices=self,
        )


@registry.register(
    dict,
    Dict,
    Mapping,
)
class DictArgument(Argument):
    """
    Argument for a dictionary type. The value is a JSON string.
    """

    def build(self, parser: ArgumentParser) -> ActionTracker:
        _, metavar = cli_types[type_name(dict)]
        return super().build_internal(
            parser,
            action=StoreAction,
            type=json.loads,
            metavar=metavar,
        )

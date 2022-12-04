import json
import typing as t
from abc import ABC
from argparse import ArgumentParser
from collections import abc, deque
from enum import Enum

from argdantic.registry import Registry
from argdantic.utils import is_container

registry = Registry()


class Argument(ABC):
    """Base class for all argument types. This class is not meant to be used directly, but rather
    subclassed to create new argument types.
    """

    NAMES = {
        bool: "BOOL",
        int: "INT",
        float: "FLOAT",
        complex: "COMPLEX",
        bytes: "BYTES",
        str: "TEXT",
        dict: "JSON",
    }

    def __init__(
        self,
        *field_names: t.Sequence[str],
        identifier: str,
        field_type: t.Type[t.Any],
        default: t.Any = None,
        required: bool = True,
        description: str = None,
        action: str = "store",
        **kwargs,
    ) -> None:
        super().__init__()
        self.identifier = identifier
        self.field_names = field_names
        self.field_type = field_type
        self.default = default
        self.required = required
        self.description = description
        self.action = action

    def build(self, parser: ArgumentParser, **optional_fields: dict) -> ArgumentParser:
        parser.add_argument(
            *self.field_names,
            dest=self.identifier,
            default=self.default,
            required=self.required,
            help=self.description,
            **optional_fields,
        )
        return parser


class PrimitiveArgument(Argument):
    """Argument for primitive types, assigned as default argument type"""

    def build(self, parser: ArgumentParser) -> ArgumentParser:
        # metavar=self.field_type.__name__.upper()
        optional_fields = dict(type=self.field_type, metavar=self.NAMES[self.field_type])
        return super().build(parser, **optional_fields)


@registry.register(bytes)
class BytesArgument(Argument):
    """Argument for bytes type"""

    def build(self, parser: ArgumentParser) -> ArgumentParser:
        optional_fields = dict(type=str.encode, metavar=self.NAMES[self.field_type])
        return super().build(parser, **optional_fields)


@registry.register(bool)
class FlagArgument(Argument):
    """Argument for a boolean flag. If the flag is present, the value is True, otherwise False"""

    def build(self, parser: ArgumentParser) -> ArgumentParser:
        group = parser.add_mutually_exclusive_group(required=self.required)
        negative_field_names = [f"--no-{name.lstrip('-')}" for name in self.field_names]
        group.add_argument(*self.field_names, dest=self.identifier, action="store_true")
        group.add_argument(*negative_field_names, dest=self.identifier, action="store_false")
        default = self.default if self.default is not None else False
        parser.set_defaults(**{self.identifier: default})
        return parser


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
    """Argument that accepts multiple values.
    When the field type is a container, the inner type is used to determine the type of the argument.
    For example, a field type of List[int] will result in an argument that accepts multiple integers.
    """

    def _type_and_count(self) -> bool:
        inner_type = str
        arg_count = "+" if self.required else "*"
        metavar = self.NAMES[inner_type]
        if is_container(self.field_type):
            # A non-composite type has a single argument, such as 'List[int]'
            # A composite type has a tuple of arguments, like 'Tuple[str, int, int]'.
            args = t.get_args(self.field_type)
            if len(args) == 1 or (len(args) == 2 and args[1] is Ellipsis):
                inner_type = args[0]
                metavar = self.NAMES[inner_type]
            elif len(args) >= 2:
                arg_count = len(args)
                metavar = tuple([self.NAMES[arg] for arg in args])
        return inner_type, arg_count, metavar

    def build(self, parser: ArgumentParser) -> ArgumentParser:
        field_type, nargs, metavar = self._type_and_count()
        optional_fields = dict(type=field_type, nargs=nargs, metavar=metavar)
        return super().build(parser, **optional_fields)


@registry.register(
    t.Literal,
    Enum,
)
class ChoiceArgument(Argument):
    """ChoiceArgument is a special case of MultipleArgument that has a fixed number of choices.
    It supports both Enum and Literal types. Overriding the *contains* and *iter* methods allows
    to use the very same class as a custom choices argument for argparse.
    """

    def __contains__(self, item: t.Any) -> bool:
        key = item if self.value_only else item.name
        return key in self.choices

    def convert(self, value: t.Any) -> t.Any:
        item = self.field_type[value]
        if self.value_only:
            return item.value
        return item

    def build(self, parser: ArgumentParser, **optional_fields: dict) -> ArgumentParser:
        self.value_only = False
        if t.get_origin(self.field_type) is t.Literal:
            self.field_type = Enum(self.identifier, {v: v for v in t.get_args(self.field_type)})
            self.value_only = True
        self.choices = [v.name for v in self.field_type]
        metavar = f"[{', '.join(self.choices)}]"
        optional_fields = dict(
            type=self.convert,
            metavar=metavar,
            choices=self,
        )
        return super().build(parser, **optional_fields)


@registry.register(
    dict,
    t.Dict,
    t.Mapping,
)
class DictArgument(Argument):
    def build(self, parser: ArgumentParser, **optional_fields: dict) -> ArgumentParser:
        optional_fields = dict(type=json.loads, metavar=self.NAMES[dict])
        return super().build(parser, **optional_fields)

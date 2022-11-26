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
    def build(self, parser: ArgumentParser) -> ArgumentParser:
        # metavar=self.field_type.__name__.upper()
        optional_fields = dict(type=self.field_type, metavar=self.NAMES[self.field_type])
        return super().build(parser, **optional_fields)


@registry.register(bool)
class FlagArgument(Argument):
    def build(self, parser: ArgumentParser) -> ArgumentParser:
        optional_fields = dict(action="store_true")
        return super().build(parser, **optional_fields)


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
    def build(self, parser: ArgumentParser, **optional_fields: dict) -> ArgumentParser:
        choices = [v.name for v in self.field_type]
        metavar = f"[{', '.join(choices)}]"
        optional_fields = dict(
            type=self.convert,
            metavar=metavar,
            choices=choices,
        )
        return super().build(parser, **optional_fields)

    def convert(self, value: t.Any) -> t.Any:
        return self.field_type[value]


@registry.register(
    dict,
    t.Dict,
    t.Mapping,
)
class DictArgument(Argument):
    def build(self, parser: ArgumentParser, **optional_fields: dict) -> ArgumentParser:
        optional_fields = dict(type=json.loads, metavar=self.NAMES[dict])
        return super().build(parser, **optional_fields)

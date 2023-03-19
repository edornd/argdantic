import logging
from collections import deque
from typing import Deque, Dict, FrozenSet, List, Literal, Sequence, Set, Tuple

import pytest
from pytest import CaptureFixture

from argdantic import ArgParser
from argdantic.parsing.actions import (
    AppendAction,
    StoreAction,
    StoreFalseAction,
    StoreTrueAction,
)
from argdantic.testing import CLIRunner

LOG = logging.getLogger(__name__)


def test_store_action_init():
    action = StoreAction(["--a"], dest="a", metavar="A", help="help")
    assert action.option_strings == ["--a"]
    assert action.dest == "a"
    assert action.nargs is None
    assert action.const is None
    assert action.default is None
    assert action.type is None
    assert action.choices is None
    assert action.required is False
    assert action.metavar == "A"
    assert action.help == "help"


def test_store_true_action_init():
    action = StoreTrueAction(["--a"], dest="a", metavar="A", help="help")
    assert action.option_strings == ["--a"]
    assert action.dest == "a"
    assert action.nargs == 0
    assert action.const is True
    assert action.type is None
    assert action.choices is None
    assert action.required is False
    assert action.metavar == "A"
    assert action.help == "help"


def test_store_false_action_init():
    action = StoreFalseAction(["--a"], dest="a", metavar="A", help="help")
    assert action.option_strings == ["--a"]
    assert action.dest == "a"
    assert action.nargs == 0
    assert action.const is False
    assert action.type is None
    assert action.choices is None
    assert action.required is False
    assert action.metavar == "A"
    assert action.help == "help"


def test_append_action_exceptions():
    with pytest.raises(ValueError):
        AppendAction(["--a"], dest="a", nargs=0)
    with pytest.raises(ValueError):
        AppendAction(["--a"], dest="a", nargs="+", const=1)


def test_primitives(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def primitives(
        a: int = 1,
        b: float = 1.0,
        c: str = "hello",
        d: bool = True,
        e: bytes = b"hello",
    ):
        print(a, b, c, d, e)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "1 1.0 hello True b'hello'"


def test_sequences(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def sequences(
        a: list = [],
        b: List[int] = [1, 2, 3],
        c: tuple = (1, 2, 3),
        d: Tuple[int, float, str, bool] = (1, 1.0, "hello", True),
        e: set = {"a"},
        f: Set[bytes] = {b"a"},
        g: FrozenSet[int] = frozenset({1, 2, 3}),
        h: Sequence[int] = [1, 2, 3],
        i: Deque[int] = deque([1, 2, 3]),
    ):
        return a, b, c, d, e, f, g, h, i

    result = runner.invoke(parser, [])
    assert result.return_value == (
        [],
        [1, 2, 3],
        (1, 2, 3),
        (1, 1.0, "hello", True),
        {"a"},
        {b"a"},
        frozenset({1, 2, 3}),
        [1, 2, 3],
        deque([1, 2, 3]),
    )


def test_mappings(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()
    runner = CLIRunner(catch_exceptions=False)

    @parser.command()
    def mappings(
        a: dict = {},
        b: Dict[str, float] = {"a": 1.0, "b": 2.0},
        c: Dict[str, List[Set[int]]] = {"a": [{1, 2}, {3, 4}]},
    ):
        print(a, b, c)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.out.rstrip() == "{} {'a': 1.0, 'b': 2.0} {'a': [{1, 2}, {3, 4}]}"


def test_enums(runner: CLIRunner, capsys: CaptureFixture):
    from enum import Enum

    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3

    parser = ArgParser()

    @parser.command()
    def enums(a: Literal["yellow", "purple"] = "yellow", b: Color = Color.RED):
        print(a, b)

    result = runner.invoke(parser, ["--a=purple", "--b=GREEN"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert result.exception is None
    assert output.out.rstrip() == "purple Color.GREEN"


def test_primitives_help(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def primitives(
        a: int = 1,
        b: float = 1.0,
        c: str = "hello",
        d: bool = True,
        e: bytes = b"hello",
    ):
        print(a, b, c, d, e)

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output.out)
    stripped_out = output.out.rstrip()
    assert "usage" in stripped_out
    assert "--a INT" in stripped_out
    assert "--b FLOAT" in stripped_out
    assert "--c TEXT" in stripped_out
    assert "--d" in stripped_out
    assert "--no-d" in stripped_out
    assert "--e BYTES" in stripped_out
    assert "-h, --help" in stripped_out
    assert "show this help message and exit" in stripped_out


def test_sequences_help(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def sequences(
        a: list = [],
        b: List[int] = [1, 2, 3],
        c: tuple = (1, 2, 3),
        d: Tuple[int, float, str, bool] = (1, 1.0, "hello", True),
        e: set = {"a"},
        f: Set[bytes] = {b"a"},
        g: FrozenSet[int] = {1, 2, 3},
        h: Sequence[int] = [1, 2, 3],
        i: Deque[int] = [1, 2, 3],
    ):
        print(a, b, c, d, e, f, g, h, i)

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output.out)
    stripped_out = output.out.rstrip()
    assert "usage" in stripped_out
    assert "--a" in stripped_out
    assert "--b" in stripped_out
    assert "--c" in stripped_out
    assert "--d INT FLOAT TEXT BOOL" in stripped_out
    assert "--e" in stripped_out
    assert "--f" in stripped_out
    assert "--g" in stripped_out
    assert "--h" in stripped_out
    assert "--i" in stripped_out
    assert "-h, --help" in stripped_out
    assert "show this help message and exit" in stripped_out


def test_mappings_help(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def mappings(
        a: dict = {},
        b: Dict[str, float] = {"a": 1.0, "b": 2.0},
        c: Dict[str, List[Set[int]]] = {"a": [{1, 2}, {3, 4}]},
    ):
        print(a, b, c)

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output.out)
    stripped_out = output.out.rstrip()
    assert "usage" in stripped_out
    assert "--a JSON" in stripped_out
    assert "--b JSON" in stripped_out
    assert "--c JSON" in stripped_out
    assert "-h, --help" in stripped_out
    assert "show this help message and exit" in stripped_out


def test_enums_help(runner: CLIRunner, capsys: CaptureFixture):
    from enum import Enum

    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3

    parser = ArgParser()

    @parser.command()
    def enums(a: Literal["yellow", "purple"] = "yellow", b: Color = Color.RED):
        print(a, b)

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output.out)
    stripped_out = output.out.rstrip()
    assert "usage" in stripped_out
    assert "--a [yellow|purple]" in stripped_out
    assert "--b [RED|GREEN|BLUE]" in stripped_out
    assert "-h, --help" in stripped_out
    assert "show this help message and exit" in stripped_out

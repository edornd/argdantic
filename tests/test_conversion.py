import logging
from typing import Deque, Dict, FrozenSet, List, Sequence, Set, Tuple

from pytest import CaptureFixture

from argdantic import Parser
from argdantic.testing import CLIRunner

LOG = logging.getLogger(__name__)


def test_primitives(runner: CLIRunner, capsys: CaptureFixture):
    parser = Parser()

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
    parser = Parser()

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

    runner.invoke(parser, [])
    output = capsys.readouterr()
    assert (
        output.out.rstrip() == "[] [1, 2, 3] (1, 2, 3) (1, 1.0, 'hello', True) "
        "{'a'} {b'a'} frozenset({1, 2, 3}) [1, 2, 3] deque([1, 2, 3])"
    )


def test_mappings(runner: CLIRunner, capsys: CaptureFixture):
    parser = Parser()

    @parser.command()
    def mappings(
        a: dict = {},
        b: Dict[str, float] = {"a": 1.0, "b": 2.0},
        c: Dict[str, List[Set[int]]] = {"a": [{1, 2}, {3, 4}]},
    ):
        print(a, b, c)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    assert output.out.rstrip() == "{} {'a': 1.0, 'b': 2.0} {'a': [{1, 2}, {3, 4}]}"


def test_primitives_help(runner: CLIRunner, capsys: CaptureFixture):
    parser = Parser()

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
    assert "usage: primitives [-h] [--a INT] [--b FLOAT] [--c TEXT] [--d] [--e BYTES]" in stripped_out
    assert "optional arguments:" in stripped_out
    assert "--a INT" in stripped_out
    assert "--b FLOAT" in stripped_out
    assert "--c TEXT" in stripped_out
    assert "--d" in stripped_out
    assert "--e BYTES" in stripped_out
    assert "-h, --help" in stripped_out
    assert "show this help message and exit" in stripped_out

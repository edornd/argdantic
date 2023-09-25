import logging
from typing import Union

import pytest
from pytest import CaptureFixture

from argdantic import ArgParser
from argdantic.testing import CLIRunner

LOG = logging.getLogger(__name__)


def test_numerical_types_required_error(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def numerical_types_required_error(a: int, b: float):
        print(a, b)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    "error: the following arguments are required: --a, --b" in output.err.rstrip()
    assert output.out.rstrip() == ""


def test_numerical_types_default_values(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def numerical_types_default_values(a: int = 1, b: float = 1.0):
        print(a, b)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "1 1.0"


def test_numerical_types(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def numerical_types(a: int = 1, b: float = 1.0):
        print(a, b)

    runner.invoke(parser, ["--a", "2", "--b", "2.0"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "2 2.0"


def test_numerical_types_help(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def numerical_types_help(a: int = 1, b: float = 1.0):
        print(a, b)

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert "usage" in output.out.rstrip()
    assert "[-h] [--a INT] [--b FLOAT]" in output.out.rstrip()


def test_boolean_types_required_error(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def boolean_types_required_error(a: bool, b: bool):
        print(a, b)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    "error: the following arguments are required: --a, --b" in output.err.rstrip()
    assert output.out.rstrip() == ""


def test_boolean_types_default_values(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def boolean_types_default_values(a: bool = True, b: bool = False):
        print(a, b)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "True False"


def test_boolean_types(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def boolean_types(a: bool, b: bool):
        print(a, b)

    runner.invoke(parser, ["--no-a", "--b"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "False True"


def test_boolean_types_help(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def boolean_types_help(a: bool, b: bool):
        print(a, b)

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert "usage" in output.out.rstrip()
    assert "[-h] (--a | --no-a) (--b | --no-b)" in output.out.rstrip()


def test_string_types_required_error(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def string_types_required_error(a: str, b: str):
        print(a, b)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    "error: the following arguments are required: --a, --b" in output.err.rstrip()
    assert output.out.rstrip() == ""


def test_string_types_default_values(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def string_types_default_values(a: str = "a", b: str = "b"):
        print(a, b)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "a b"


def test_string_types(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def string_types(a: str = "a", b: str = "b"):
        print(a, b)

    runner.invoke(parser, ["--a", "aa", "--b", "bb"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "aa bb"


def test_string_types_help(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def string_types_help(a: str = "a", b: str = "b"):
        print(a, b)

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert "usage:" in output.out.rstrip()
    assert "[-h] [--a TEXT] [--b TEXT]" in output.out.rstrip()


def test_bytes_types_required_error(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def bytes_types_required_error(a: bytes, b: bytes):
        print(a, b)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    "error: the following arguments are required: --a, --b" in output.err.rstrip()
    assert output.out.rstrip() == ""


def test_bytes_types_default_values(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def bytes_types_default_values(a: bytes = b"a", b: bytes = b"b"):
        print(a, b)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "b'a' b'b'"


def test_bytes_types(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def bytes_types(a: bytes = b"a", b: bytes = b"b"):
        print(a, b)

    runner.invoke(parser, ["--a", "aa", "--b", "bb"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "b'aa' b'bb'"


def test_bytes_types_help(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def bytes_types_help(a: bytes = b"a", b: bytes = b"b"):
        print(a, b)

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert "usage:" in output.out.rstrip()
    assert "[-h] [--a BYTES] [--b BYTES]" in output.out.rstrip()


def test_value_error_on_union(capsys: CaptureFixture):
    parser = ArgParser()
    runner = CLIRunner(catch_exceptions=False)

    @parser.command()
    def value_error_on_union(a: Union[int, str]):
        print(a)

    with pytest.raises(ValueError):
        runner.invoke(parser, ["--a", "aa"])

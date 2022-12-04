import logging

import pytest
from pytest import CaptureFixture

from argdantic import Parser
from argdantic.core import Command
from argdantic.testing import CLIRunner

LOG = logging.getLogger(__name__)


def test_empty(runner: CLIRunner, capsys: CaptureFixture):
    parser = Parser()

    @parser.command()
    def empty():
        print("Hello world")

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "Hello world"


def test_repr():
    cli = Parser()

    @cli.command()
    def command1():
        pass

    @cli.command()
    def command2():
        pass

    LOG.debug(str(command1))
    LOG.debug(str(command2))
    LOG.debug(str(cli))
    assert cli.entrypoint is None
    assert isinstance(cli.commands, list)
    assert len(cli.commands) == 2
    assert repr(command1) == "<Command command1>"
    assert repr(command2) == "<Command command2>"
    assert repr(cli) == "<Parser(commands=[<Command command1>, <Command command2>])>"


def test_repr_named():
    cli = Parser(name="cli")

    @cli.command(name="cmd1")
    def command1():
        pass

    @cli.command(name="cmd2")
    def command2():
        pass

    LOG.debug(str(command1))
    LOG.debug(str(command2))
    LOG.debug(str(cli))
    assert cli.entrypoint is None
    assert isinstance(cli.commands, list)
    assert len(cli.commands) == 2
    assert repr(command1) == "<Command cmd1>"
    assert repr(command2) == "<Command cmd2>"
    assert repr(cli) == "<Parser 'cli'(commands=[<Command cmd1>, <Command cmd2>])>"


def test_empty_help(runner: CLIRunner, capsys: CaptureFixture):
    parser = Parser()

    @parser.command()
    def empty():
        print("Hello world")

    runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert "usage: empty [-h]" in output.out.rstrip()


def test_missing_annotation(runner: CLIRunner, capsys: CaptureFixture):
    parser = Parser()

    with pytest.raises(AssertionError):

        @parser.command()
        def empty(a):
            print(f"Hello {a}")


def test_build_entrypoint(runner: CLIRunner, capsys: CaptureFixture):
    parser = Parser()

    @parser.command()
    def empty():
        print("Hello world")

    try:
        parser()
    except SystemExit:
        pass
    assert parser.entrypoint is not None
    assert parser.entrypoint.name == "empty"
    assert isinstance(parser.entrypoint, Command)

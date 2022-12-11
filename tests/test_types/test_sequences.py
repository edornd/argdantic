import logging

from pytest import CaptureFixture

from argdantic import ArgParser
from argdantic.testing import CLIRunner

LOG = logging.getLogger(__name__)


def test_list_type_required_error(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def list_type_required_error(a: list):
        print(a)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    "error: the following arguments are required: --a" in output.err.rstrip()
    assert output.out.rstrip() == ""


def test_list_type_wrong_arg(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def list_type_wrong_arg(a: list):
        print(a)

    runner.invoke(parser, ["--a"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert "argument --a: expected at least one argument" in output.err.rstrip()
    assert output.out.rstrip() == ""


def test_list_type(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def list_type(a: list):
        print(a)

    runner.invoke(parser, ["--a", "1", "2", "3"])
    output = capsys.readouterr()
    LOG.debug(output)
    assert output.err.rstrip() == ""
    assert output.out.rstrip() == "['1', '2', '3']"

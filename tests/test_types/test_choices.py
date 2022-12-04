import logging
from typing import Literal

from pytest import CaptureFixture

from argdantic import ArgParser
from argdantic.testing import CLIRunner

LOG = logging.getLogger(__name__)


def test_literal_types_required_error(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def literal_types_required_error(a: Literal["a", "b", "c"]):
        print(a)

    runner.invoke(parser, [])
    output = capsys.readouterr()
    LOG.debug(output)
    "error: the following arguments are required: --a" in output.err.rstrip()
    assert output.out.rstrip() == ""


def test_literal_types_wrong_arg(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def literal_types_wrong_arg(a: Literal["a", "b", "c"]):
        print(a)

    runner.invoke(parser, ["--a", "d"])
    output = capsys.readouterr()
    LOG.debug(output)
    "error: argument --a: invalid choice: 'd' (choose from 'a', 'b', 'c')" in output.err.rstrip()
    assert output.out.rstrip() == ""

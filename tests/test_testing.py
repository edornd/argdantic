import logging

import pytest
from pytest import CaptureFixture

from argdantic import ArgParser
from argdantic.testing import CLIRunner

LOG = logging.getLogger(__name__)


def test_cli_runner_no_catch_exceptions(capsys: CaptureFixture):
    parser = ArgParser()
    runner = CLIRunner(catch_exceptions=False)

    @parser.command()
    def cli_runner_no_catch_exceptions():
        raise ValueError("hello")

    with pytest.raises(ValueError):
        runner.invoke(parser, [])


def test_cli_runner_exception_result(capsys: CaptureFixture):
    parser = ArgParser()
    runner = CLIRunner(catch_exceptions=True)

    @parser.command()
    def cli_runner_exception_result():
        raise ValueError("hello")

    result = runner.invoke(parser, [])
    assert result.exception
    assert result.exception.args[0] == "hello"


def test_cli_runner_invoke_params(capsys: CaptureFixture):
    parser = ArgParser()
    runner = CLIRunner(catch_exceptions=True)

    @parser.command()
    def cli_runner_invoke_params(a: int, b: int):
        print(a, b)
        return a + b

    result = runner.invoke(parser, ["--a", "1", "--b", "2"])
    assert result.return_value == 3
    assert result.exception is None
    assert result.exc_info is None

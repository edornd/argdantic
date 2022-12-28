import argparse
import logging
from enum import Enum
from typing import Iterable, Literal

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


def test_choice_iterable(runner: CLIRunner, capsys: CaptureFixture):
    parser = ArgParser()

    @parser.command()
    def choice_iterable(a: Literal["a", "b", "c"]):
        print(a)

    choice = list(choice_iterable.arguments)[0]
    choice.build(argparse.ArgumentParser())
    assert issubclass(choice.field_type, Enum)
    assert len(choice) == 3
    assert "a" in choice
    assert next(choice) == choice.field_type.a
    assert isinstance(iter(choice), Iterable)

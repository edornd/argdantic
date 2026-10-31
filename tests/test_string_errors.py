import pytest
from conftest import Run, RunRaising

import argdantic
import argdantic.errors
from argdantic import App, CommandError


@pytest.fixture(autouse=True)
def string_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(argdantic.errors, "_string_errors", True)


def test_string_errors_print_pydantic_and_argparse_text(notes_app: App, run: Run) -> None:
    result = run(notes_app, ["add", "--priority", "abc", "--bogus", "1"])

    assert result.code == 2
    assert result.out.startswith("unrecognized arguments: --bogus 1\n1 validation error for Add\npriority\n")
    assert "Input should be a valid integer" in result.out


def test_string_errors_print_the_argparse_message(notes_app: App, run: Run) -> None:
    assert run(notes_app, ["add", "--title"]) == (2, "argument --title: expected one argument\n", "")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (CommandError("NOTE_EXISTS", "note a already exists", exit_code=3), (3, "note a already exists\n", "")),
        (RuntimeError("disk full"), (1, "disk full\n", "")),
    ],
)
def test_string_errors_print_the_exception_text(
    error: Exception, expected: tuple[int, str, str], run_raising: RunRaising
) -> None:
    assert run_raising(error) == expected


def test_string_errors_switch_is_private(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.undo()

    assert argdantic.errors._string_errors is False
    assert "_string_errors" not in argdantic.__all__
    assert not hasattr(argdantic, "_string_errors")

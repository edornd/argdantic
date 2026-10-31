import pytest
from conftest import Run, RunRaising

from argdantic import App, CommandError


def test_command_error_renders_its_own_code_and_exit_code(run_raising: RunRaising) -> None:
    error = CommandError("NOTE_EXISTS", "note a already exists", hint="pass a new --title")

    result = run_raising(error)

    assert result.code == 1
    assert result.json() == {
        "code": "NOTE_EXISTS",
        "message": "note a already exists",
        "retryable": False,
        "hint": "pass a new --title",
    }


def test_command_error_options_override_the_defaults(run_raising: RunRaising) -> None:
    error = CommandError("STORE_LOCKED", "the note store is locked", retryable=True, exit_code=3)

    result = run_raising(error)

    assert result.code == 3
    assert result.json() == {"code": "STORE_LOCKED", "message": "the note store is locked", "retryable": True}


def test_error_message_keeps_only_its_first_line(run_raising: RunRaising) -> None:
    error = CommandError("NOTE_EXISTS", "note a already exists\nsee notes/a.md for details")

    assert run_raising(error).json()["message"] == "note a already exists"


@pytest.mark.parametrize("code", ["note_exists", "NoteExists", "NOTE-EXISTS", "", "_NOTE"])
def test_command_error_code_must_be_screaming_case(code: str) -> None:
    with pytest.raises(ValueError, match="SCREAMING_CASE"):
        CommandError(code, "message")


@pytest.mark.parametrize("exit_code", [0, 2])
def test_command_error_cannot_use_a_reserved_exit_code(exit_code: int) -> None:
    with pytest.raises(ValueError, match="reserved"):
        CommandError("NOTE_EXISTS", "message", exit_code=exit_code)


def test_uncaught_exception_is_unknown_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch, run_raising: RunRaising
) -> None:
    monkeypatch.delenv("ARGD_DEBUG", raising=False)

    result = run_raising(RuntimeError("disk full\nwhile writing notes/a.md"))

    assert result.code == 1
    assert result.json() == {"code": "UNKNOWN", "message": "disk full", "retryable": False}
    assert result.err == ""


def test_exception_without_text_falls_back_to_its_type_name(run_raising: RunRaising) -> None:
    class QuotaExceeded(Exception):
        pass

    result = run_raising(QuotaExceeded())

    assert result.code == 1
    assert result.json() == {"code": "UNKNOWN", "message": "QuotaExceeded", "retryable": False}


def test_result_that_cannot_be_serialised_is_unknown(run: Run) -> None:
    app = App("calc")

    @app.command
    def broken() -> int:
        return object()  # ty: ignore[invalid-return-type]

    result = run(app, ["broken"])

    assert result.code == 1
    assert result.json()["code"] == "UNKNOWN"


@pytest.mark.parametrize(
    ("value", "shows_traceback"),
    [("1", True), ("true", True), ("on", True), ("0", False), ("off", False), ("", False), ("verbose", False)],
)
def test_argd_debug_sends_the_traceback_to_stderr(
    value: str, shows_traceback: bool, monkeypatch: pytest.MonkeyPatch, run_raising: RunRaising
) -> None:
    monkeypatch.setenv("ARGD_DEBUG", value)

    result = run_raising(RuntimeError("disk full"))

    assert (result.code, result.json()["code"]) == (1, "UNKNOWN")
    assert ("Traceback" in result.err and "RuntimeError: disk full" in result.err) is shows_traceback
    if not shows_traceback:
        assert result.err == ""


def test_keyboard_interrupt_is_not_turned_into_an_error() -> None:
    app = App("notes")

    @app.command
    def wait() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        app(["wait"])

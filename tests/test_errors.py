import enum
import json
from typing import Annotated, Any, Literal

import pytest
from pydantic import BaseModel, Field, SecretBytes, SecretStr

import argdantic._errors
from argdantic import App, CommandError


def run(app: App, argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    with pytest.raises(SystemExit) as exc:
        app(argv)
    code = exc.value.code
    assert isinstance(code, int)
    return code, json.loads(capsys.readouterr().out)


def test_validation_failure_gives_one_field_error_per_pydantic_error(capsys: pytest.CaptureFixture[str]) -> None:
    app = App("trainctl")
    calls = []

    @app.command
    def train(epochs: int, learning_rate: Annotated[float, Field(gt=0)] = 0.1) -> None:
        calls.append(epochs)

    code, error = run(app, ["train", "--learning-rate", "-1"], capsys)

    assert code == 2
    assert calls == []
    assert error == {
        "code": "VALIDATION_ERROR",
        "message": "invalid input",
        "retryable": False,
        "fieldErrors": [
            {
                "path": "epochs",
                "code": "missing",
                "message": "Field required",
            },
            {
                "path": "learning_rate",
                "code": "greater_than",
                "message": "Input should be greater than 0",
                "received": "-1",
                "source": "flag",
            },
        ],
    }


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class Optim(BaseModel):
    name: Literal["adamw", "sgd"] = "adamw"


DEFAULT_OPTIM = Optim()


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--fmt", "csv"], {"path": "fmt", "code": "literal_error", "allowed": ["parquet", "webdataset"]}),
        (["--color", "green"], {"path": "color", "code": "enum", "allowed": ["red", "blue"]}),
        (["--size", "xl"], {"path": "size", "code": "literal_error", "allowed": ["s", "m"]}),
        (["--optim.name", "adam"], {"path": "optim.name", "code": "literal_error", "allowed": ["adamw", "sgd"]}),
    ],
)
def test_choice_errors_list_the_allowed_values(
    argv: list[str], expected: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    app = App("dataprep")

    @app.command
    def convert(
        fmt: Literal["parquet", "webdataset"] = "parquet",
        color: Color = Color.RED,
        size: Annotated[Literal["s", "m"], Field(description="shard size")] | None = None,
        optim: Optim = DEFAULT_OPTIM,
    ) -> None: ...

    code, error = run(app, ["convert", *argv], capsys)

    assert code == 2
    [field_error] = error["fieldErrors"]
    assert {key: field_error[key] for key in expected} == expected
    assert field_error["source"] == "flag"
    assert field_error["received"] == argv[1]
    assert field_error["expected"] == " or ".join(repr(choice) for choice in expected["allowed"])


def make_train_app(calls: list[int]) -> App:
    app = App("trainctl")

    @app.command
    def train(epochs: int = 1, learning_rate: float = 0.1, use_slurm: bool = False) -> None:
        calls.append(epochs)

    return app


TRAIN_FLAGS = ["--epochs", "--learning-rate", "--use-slurm", "--no-use-slurm"]


@pytest.mark.parametrize(
    ("argv", "path", "received"),
    [
        (["--epoch", "3"], "epoch", "--epoch"),
        (["--learnin-rate=3"], "learnin_rate", "--learnin-rate"),
        # argparse would expand an unambiguous prefix to --epochs; argdantic turns that off.
        (["--epo", "3"], "epo", "--epo"),
        (["--optim.lrr", "3"], "optim.lrr", "--optim.lrr"),
    ],
)
def test_unknown_flag_lists_the_valid_flags(
    argv: list[str], path: str, received: str, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[int] = []

    code, error = run(make_train_app(calls), ["train", *argv], capsys)

    assert code == 2
    assert calls == []
    assert error["code"] == "VALIDATION_ERROR"
    assert error["fieldErrors"] == [
        {
            "path": path,
            "code": "unknown_flag",
            "message": f"unknown flag {received}",
            "received": received,
            "allowed": TRAIN_FLAGS,
            "source": "flag",
        }
    ]


def test_stray_token_is_an_unexpected_argument(capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[int] = []

    code, error = run(make_train_app(calls), ["train", "extra"], capsys)

    assert code == 2
    assert calls == []
    assert error["fieldErrors"] == [
        {
            "path": "",
            "code": "unexpected_argument",
            "message": "unexpected argument extra",
            "received": "extra",
            "source": "flag",
        }
    ]


def test_unknown_flags_come_before_validation_errors(capsys: pytest.CaptureFixture[str]) -> None:
    code, error = run(make_train_app([]), ["train", "--epochs", "abc", "--bogus"], capsys)

    assert code == 2
    assert [(item["path"], item["code"]) for item in error["fieldErrors"]] == [
        ("bogus", "unknown_flag"),
        ("epochs", "int_parsing"),
    ]


def test_argparse_usage_error_is_a_validation_error(capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[int] = []

    with pytest.raises(SystemExit) as exc:
        make_train_app(calls)(["train", "--epochs"])
    captured = capsys.readouterr()

    assert exc.value.code == 2
    assert calls == []
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "code": "VALIDATION_ERROR",
        "message": "argument --epochs: expected one argument",
        "retryable": False,
    }


def run_failing(error: Exception, capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    app = App("trainctl")

    @app.command
    def train() -> None:
        raise error

    return run(app, ["train"], capsys)


def test_command_error_renders_its_own_code_and_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    error = CommandError("RUN_EXISTS", "run a already exists", hint="pass a new --run-id")

    assert run_failing(error, capsys) == (
        1,
        {"code": "RUN_EXISTS", "message": "run a already exists", "retryable": False, "hint": "pass a new --run-id"},
    )


def test_command_error_options_override_the_defaults(capsys: pytest.CaptureFixture[str]) -> None:
    error = CommandError("QUEUE_FULL", "the queue is full", retryable=True, exit_code=3)

    assert run_failing(error, capsys) == (3, {"code": "QUEUE_FULL", "message": "the queue is full", "retryable": True})


def test_error_message_keeps_only_its_first_line(capsys: pytest.CaptureFixture[str]) -> None:
    error = CommandError("RUN_EXISTS", "run a already exists\nsee runs/a for details")

    _, rendered = run_failing(error, capsys)

    assert rendered["message"] == "run a already exists"


@pytest.mark.parametrize("code", ["run_exists", "RunExists", "RUN-EXISTS", "", "_RUN"])
def test_command_error_code_must_be_screaming_case(code: str) -> None:
    with pytest.raises(ValueError, match="SCREAMING_CASE"):
        CommandError(code, "message")


def test_uncaught_exception_is_unknown_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("ARGD_DEBUG", raising=False)
    app = App("trainctl")

    @app.command
    def train() -> None:
        raise RuntimeError("disk full\nwhile writing runs/a")

    with pytest.raises(SystemExit) as exc:
        app(["train"])
    captured = capsys.readouterr()

    assert exc.value.code == 1
    assert json.loads(captured.out) == {"code": "UNKNOWN", "message": "disk full", "retryable": False}
    assert captured.err == ""


def test_exception_without_text_falls_back_to_its_type_name(capsys: pytest.CaptureFixture[str]) -> None:
    class QuotaExceeded(Exception):
        pass

    assert run_failing(QuotaExceeded(), capsys) == (
        1,
        {"code": "UNKNOWN", "message": "QuotaExceeded", "retryable": False},
    )


def test_result_that_cannot_be_serialised_is_unknown(capsys: pytest.CaptureFixture[str]) -> None:
    app = App("tool")

    @app.command
    def broken() -> int:
        return object()  # ty: ignore[invalid-return-type]

    code, error = run(app, ["broken"], capsys)

    assert code == 1
    assert error["code"] == "UNKNOWN"


@pytest.mark.parametrize(
    ("value", "shows_traceback"),
    [("1", True), ("true", True), ("on", True), ("0", False), ("off", False), ("", False), ("verbose", False)],
)
def test_argd_debug_sends_the_traceback_to_stderr(
    value: str, shows_traceback: bool, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ARGD_DEBUG", value)
    app = App("trainctl")

    @app.command
    def train() -> None:
        raise RuntimeError("disk full")

    with pytest.raises(SystemExit) as exc:
        app(["train"])
    out, err = capsys.readouterr()

    assert (exc.value.code, json.loads(out)["code"]) == (1, "UNKNOWN")
    assert ("Traceback" in err and "RuntimeError: disk full" in err) is shows_traceback
    if not shows_traceback:
        assert err == ""


def test_keyboard_interrupt_is_not_turned_into_an_error() -> None:
    app = App("tool")

    @app.command
    def wait() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        app(["wait"])


class Credentials(BaseModel):
    api_key: Annotated[SecretBytes, Field(min_length=8)]


DEFAULT_CREDENTIALS = Credentials(api_key=SecretBytes(b"a-long-enough-key"))
DEFAULT_TOKEN = SecretStr("a-long-enough-token")


@pytest.mark.parametrize(
    ("argv", "path"),
    [
        (["--token", "abc"], "token"),
        (["--maybe-token", "abc"], "maybe_token"),
        (["--creds.api-key", "abc"], "creds.api_key"),
    ],
)
def test_secret_fields_never_echo_the_received_value(
    argv: list[str], path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    app = App("admin")

    @app.command
    def login(
        token: Annotated[SecretStr, Field(min_length=8)] = DEFAULT_TOKEN,
        maybe_token: Annotated[SecretStr, Field(min_length=8)] | None = None,
        creds: Credentials = DEFAULT_CREDENTIALS,
    ) -> None: ...

    code, error = run(app, ["login", *argv], capsys)

    assert code == 2
    [field_error] = error["fieldErrors"]
    assert field_error["path"] == path
    assert "received" not in field_error
    assert "abc" not in json.dumps(error)


@pytest.fixture
def string_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(argdantic._errors, "_string_errors", True)


def run_text(app: App, argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    with pytest.raises(SystemExit) as exc:
        app(argv)
    code = exc.value.code
    assert isinstance(code, int)
    return code, capsys.readouterr().out


@pytest.mark.usefixtures("string_errors")
def test_string_errors_print_pydantic_and_argparse_text(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run_text(make_train_app([]), ["train", "--epochs", "abc", "--bogus", "1"], capsys)

    assert code == 2
    assert out.startswith("unrecognized arguments: --bogus 1\n1 validation error for Train\nepochs\n")
    assert "Input should be a valid integer" in out


@pytest.mark.usefixtures("string_errors")
def test_string_errors_print_the_argparse_message(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_text(make_train_app([]), ["train", "--epochs"], capsys) == (
        2,
        "argument --epochs: expected one argument\n",
    )


@pytest.mark.usefixtures("string_errors")
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (CommandError("RUN_EXISTS", "run a already exists", exit_code=3), (3, "run a already exists\n")),
        (RuntimeError("disk full"), (1, "disk full\n")),
    ],
)
def test_string_errors_print_the_exception_text(
    error: Exception, expected: tuple[int, str], capsys: pytest.CaptureFixture[str]
) -> None:
    app = App("trainctl")

    @app.command
    def train() -> None:
        raise error

    assert run_text(app, ["train"], capsys) == expected


def test_string_errors_switch_is_private() -> None:
    assert argdantic._errors._string_errors is False
    assert not any("string" in name for name in argdantic.__all__)
    assert not hasattr(argdantic, "_string_errors")

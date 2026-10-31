import enum
import json
from typing import Annotated, Any, Literal

import pytest
from conftest import Run
from pydantic import BaseModel, Field, SecretBytes, SecretStr

from argdantic import App

NOTES_FLAGS = ["--title", "--priority", "--pinned", "--no-pinned"]


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class Style(BaseModel):
    font: Literal["serif", "mono"] = "serif"


class Credentials(BaseModel):
    api_key: Annotated[SecretBytes, Field(min_length=8)]


DEFAULT_STYLE = Style()
DEFAULT_CREDENTIALS = Credentials(api_key=SecretBytes(b"a-long-enough-key"))
DEFAULT_TOKEN = SecretStr("a-long-enough-token")


def test_parameter_without_default_is_a_required_flag(run: Run) -> None:
    app = App("calc")
    calls = []

    @app.command
    def double(value: int) -> int:
        calls.append(value)
        return value * 2

    result = run(app, ["double"])

    assert result.code == 2
    assert result.json()["fieldErrors"][0]["code"] == "missing"
    assert calls == []


def test_validation_failure_gives_one_field_error_per_pydantic_error(run: Run) -> None:
    app = App("notes")
    calls = []

    @app.command
    def add(title: str, priority: Annotated[int, Field(gt=0)] = 1) -> None:
        calls.append(title)

    result = run(app, ["add", "--priority", "-1"])

    assert result.code == 2
    assert calls == []
    assert result.json() == {
        "code": "VALIDATION_ERROR",
        "message": "invalid input",
        "retryable": False,
        "fieldErrors": [
            {
                "path": "title",
                "code": "missing",
                "message": "Field required",
            },
            {
                "path": "priority",
                "code": "greater_than",
                "message": "Input should be greater than 0",
                "received": "-1",
                "source": "flag",
            },
        ],
    }


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--fmt", "html"], {"path": "fmt", "code": "literal_error", "allowed": ["markdown", "text"]}),
        (["--color", "green"], {"path": "color", "code": "enum", "allowed": ["red", "blue"]}),
        (["--size", "xl"], {"path": "size", "code": "literal_error", "allowed": ["s", "m"]}),
        (["--style.font", "sans"], {"path": "style.font", "code": "literal_error", "allowed": ["serif", "mono"]}),
    ],
)
def test_choice_errors_list_the_allowed_values(argv: list[str], expected: dict[str, Any], run: Run) -> None:
    app = App("notes")

    @app.command
    def export(
        fmt: Literal["markdown", "text"] = "markdown",
        color: Color = Color.RED,
        size: Annotated[Literal["s", "m"], Field(description="page size")] | None = None,
        style: Style = DEFAULT_STYLE,
    ) -> None: ...

    result = run(app, ["export", *argv])

    assert result.code == 2
    [field_error] = result.json()["fieldErrors"]
    assert {key: field_error[key] for key in expected} == expected
    assert field_error["source"] == "flag"
    assert field_error["received"] == argv[1]
    assert field_error["expected"] == " or ".join(repr(choice) for choice in expected["allowed"])


@pytest.mark.parametrize(
    ("argv", "path", "received"),
    [
        (["--titel", "a"], "titel", "--titel"),
        (["--priorty=3"], "priorty", "--priorty"),
        # argparse would expand an unambiguous prefix to --title, argdantic turns that off
        (["--ti", "a"], "ti", "--ti"),
        (["--style.fnt", "mono"], "style.fnt", "--style.fnt"),
    ],
)
def test_unknown_flag_lists_the_valid_flags(
    argv: list[str], path: str, received: str, notes_app: App, calls: list[str], run: Run
) -> None:
    result = run(notes_app, ["add", *argv])

    assert result.code == 2
    assert calls == []
    assert result.json()["code"] == "VALIDATION_ERROR"
    assert result.json()["fieldErrors"] == [
        {
            "path": path,
            "code": "unknown_flag",
            "message": f"unknown flag {received}",
            "received": received,
            "allowed": NOTES_FLAGS,
            "source": "flag",
        }
    ]


def test_stray_token_is_an_unexpected_argument(notes_app: App, calls: list[str], run: Run) -> None:
    result = run(notes_app, ["add", "extra"])

    assert result.code == 2
    assert calls == []
    assert result.json()["fieldErrors"] == [
        {
            "path": "",
            "code": "unexpected_argument",
            "message": "unexpected argument extra",
            "received": "extra",
            "source": "flag",
        }
    ]


@pytest.mark.parametrize(
    ("argv", "tokens"),
    [(["--", "extra"], ["--", "extra"]), (["-.5"], ["-.5"]), (["-1e3"], ["-1e3"]), (["-"], ["-"])],
)
def test_separator_and_negative_numbers_are_not_flags(
    argv: list[str], tokens: list[str], notes_app: App, run: Run
) -> None:
    result = run(notes_app, ["add", *argv])

    assert result.code == 2
    assert [(item["code"], item["received"]) for item in result.json()["fieldErrors"]] == [
        ("unexpected_argument", token) for token in tokens
    ]


def test_unknown_flags_come_before_validation_errors(notes_app: App, run: Run) -> None:
    result = run(notes_app, ["add", "--priority", "abc", "--bogus"])

    assert result.code == 2
    assert [(item["path"], item["code"]) for item in result.json()["fieldErrors"]] == [
        ("bogus", "unknown_flag"),
        ("priority", "int_parsing"),
    ]


def test_argparse_usage_error_is_a_validation_error(notes_app: App, calls: list[str], run: Run) -> None:
    result = run(notes_app, ["add", "--title"])

    assert result.code == 2
    assert calls == []
    assert result.err == ""
    assert result.json() == {
        "code": "VALIDATION_ERROR",
        "message": "argument --title: expected one argument",
        "retryable": False,
    }


@pytest.mark.parametrize(
    ("argv", "field"),
    [(["--tags", "[1,"], "tags"), (["--style", "{bad"], "style"), (["--counts", "{bad"], "counts")],
)
def test_malformed_structured_value_is_a_validation_error(argv: list[str], field: str, run: Run) -> None:
    app = App("notes")
    calls = []

    @app.command
    def add(
        tags: list[str] | None = None,
        style: Style = DEFAULT_STYLE,
        counts: dict[str, int] | None = None,
    ) -> None:
        calls.append(tags)

    result = run(app, ["add", *argv])

    assert result.code == 2
    assert calls == []
    assert result.json()["code"] == "VALIDATION_ERROR"
    assert field in result.json()["message"]
    assert "fieldErrors" not in result.json()


@pytest.mark.parametrize(
    ("argv", "path"),
    [
        (["--token", "abc"], "token"),
        (["--maybe-token", "abc"], "maybe_token"),
        (["--creds.api-key", "abc"], "creds.api_key"),
    ],
)
def test_secret_fields_never_echo_the_received_value(argv: list[str], path: str, run: Run) -> None:
    app = App("notes")

    @app.command
    def login(
        token: Annotated[SecretStr, Field(min_length=8)] = DEFAULT_TOKEN,
        maybe_token: Annotated[SecretStr, Field(min_length=8)] | None = None,
        creds: Credentials = DEFAULT_CREDENTIALS,
    ) -> None: ...

    result = run(app, ["login", *argv])

    assert result.code == 2
    [field_error] = result.json()["fieldErrors"]
    assert field_error["path"] == path
    assert "received" not in field_error
    assert "abc" not in json.dumps(result.json())

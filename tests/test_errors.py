import enum
import json
from typing import Annotated, Any, Literal

import pytest
from pydantic import BaseModel, Field

from argdantic import App


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

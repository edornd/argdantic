import json
from datetime import date
from pathlib import Path
from typing import Annotated

import pytest
from pydantic import BaseModel, Field

from argdantic import App


def run(app: App, argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    with pytest.raises(SystemExit) as exc:
        app(argv)
    code = exc.value.code
    assert isinstance(code, int)
    return code, capsys.readouterr().out


def test_command_prints_result_as_json(capsys: pytest.CaptureFixture[str]) -> None:
    app = App("calc")

    @app.command
    def add_numbers(first_value: int, second_value: int = 10) -> dict[str, int]:
        return {"sum": first_value + second_value}

    code, out = run(app, ["add-numbers", "--first-value", "3", "--second-value", "4"], capsys)

    assert code == 0
    assert json.loads(out) == {"sum": 7}


def test_parameter_without_default_is_a_required_flag(capsys: pytest.CaptureFixture[str]) -> None:
    app = App("calc")
    calls = []

    @app.command
    def double(value: int) -> int:
        calls.append(value)
        return value * 2

    code, out = run(app, ["double"], capsys)

    assert code == 2
    assert out == ""
    assert calls == []


@pytest.mark.parametrize(
    ("argv", "expected"),
    [([], False), (["--dry-mode"], True), (["--dry-mode", "--no-dry-mode"], False)],
)
def test_bool_parameter_gets_on_and_off_flags(
    argv: list[str], expected: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    app = App("tool")

    @app.command
    def show(dry_mode: bool = False) -> bool:
        return dry_mode

    code, out = run(app, ["show", *argv], capsys)

    assert code == 0
    assert json.loads(out) is expected


def test_none_result_prints_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    app = App("tool")
    calls = []

    @app.command
    def ping() -> None:
        calls.append("ping")

    code, out = run(app, ["ping"], capsys)

    assert code == 0
    assert out == ""
    assert calls == ["ping"]


class RunInfo(BaseModel):
    run_id: str
    started: date
    out_dir: Path


class RunInfoWithSecret(RunInfo):
    token: str


def test_result_is_dumped_through_the_return_annotation(capsys: pytest.CaptureFixture[str]) -> None:
    app = App("trainctl")

    @app.command
    def train(run_id: str) -> RunInfo:
        return RunInfoWithSecret(
            run_id=run_id,
            started=date(2025, 1, 2),
            out_dir=Path("runs/a"),
            token="s3cret",
        )

    code, out = run(app, ["train", "--run-id", "a"], capsys)

    assert code == 0
    assert json.loads(out) == {"run_id": "a", "started": "2025-01-02", "out_dir": "runs/a"}


def test_env_var_with_a_field_name_is_ignored(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TARGET_NAME", "from-env")
    monkeypatch.setenv("target_name", "from-env")
    app = App("tool")

    @app.command
    def greet(target_name: str = "world") -> str:
        return f"hello {target_name}"

    code, out = run(app, ["greet"], capsys)

    assert code == 0
    assert json.loads(out) == "hello world"


def test_command_with_parentheses_and_safety_hints_registers(capsys: pytest.CaptureFixture[str]) -> None:
    app = App("admin")

    @app.command()
    def list_users() -> list[str]:
        return ["ada"]

    @app.command(
        read_only=False,
        destructive=True,
        idempotent=True,
        open_world=False,
    )
    def delete_user(user_name: str) -> str:
        return f"deleted {user_name}"

    assert run(app, ["list-users"], capsys) == (0, '["ada"]\n')
    assert run(app, ["delete-user", "--user-name", "ada"], capsys) == (0, '"deleted ada"\n')


def test_help_shows_docstring_and_field_descriptions(capsys: pytest.CaptureFixture[str]) -> None:
    app = App("trainctl")

    @app.command
    def train(
        epochs: int,
        learning_rate: Annotated[float, Field(description="peak learning rate")] = 3e-4,
        use_slurm: bool = False,
    ) -> None:
        """
        Launch a training run.

        Runs locally unless told otherwise.

        Args:
            epochs: number of passes over the dataset.
            use_slurm: submit through sbatch
                instead of running locally.
        """

    code, out = run(app, ["train", "--help"], capsys)

    assert code == 0
    assert "Launch a training run." in out
    assert "Runs locally" not in out
    assert "number of passes over the dataset." in out
    assert "peak learning rate" in out
    assert "submit through sbatch instead of running locally." in " ".join(out.split())


def test_root_help_lists_commands_with_their_summary(capsys: pytest.CaptureFixture[str]) -> None:
    app = App("trainctl")

    @app.command
    def train() -> None:
        """Launch a training run."""

    code, out = run(app, ["--help"], capsys)

    assert code == 0
    assert "train" in out
    assert "Launch a training run." in out

import pytest
from conftest import Run
from pydantic import BaseModel, ConfigDict, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from argdantic import App


class Optim(BaseModel):
    lr: float = Field(0.1, gt=0, description="learning rate")


class TrainConfig(BaseModel):
    optim: Optim = Optim()
    epochs: int = 3


class Sized(BaseModel):
    size: int
    epochs: int = 3


class Keyed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: SecretStr
    epochs: int = 3

    @computed_field
    @property
    def double(self) -> int:
        return self.epochs * 2


FIVE_EPOCHS = TrainConfig(epochs=5)
KEYED = Keyed(key=SecretStr("a-long-key"))


class Env(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRAIN_")

    epochs: int = 3


def test_model_parameter_gives_nested_flags(run: Run) -> None:
    app = App("ml")
    received: list[type] = []

    @app.command
    def train(cfg: TrainConfig) -> TrainConfig:
        received.extend([type(cfg), type(cfg.optim)])
        return cfg

    result = run(app, ["train", "--cfg.optim.lr", "0.5", "--cfg.epochs", "4"])

    assert result.json() == {"optim": {"lr": 0.5}, "epochs": 4}
    assert received == [TrainConfig, Optim]


def test_all_default_model_parameter_is_optional(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: TrainConfig) -> TrainConfig:
        return cfg

    result = run(app, ["train"])

    assert result.code == 0
    assert result.json() == {"optim": {"lr": 0.1}, "epochs": 3}


def test_required_model_field_reports_its_own_path(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Sized) -> Sized:
        return cfg

    result = run(app, ["train"])

    assert [(e["path"], e["code"]) for e in result.json()["field_errors"]] == [("cfg.size", "missing")]


def test_default_instance_keeps_its_other_values(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: TrainConfig = FIVE_EPOCHS) -> TrainConfig:
        return cfg

    result = run(app, ["train", "--cfg.optim.lr", "0.5"])

    assert result.json() == {"optim": {"lr": 0.5}, "epochs": 5}


def test_default_instance_with_computed_and_secret_fields_merges(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Keyed = KEYED) -> str:
        return cfg.key.get_secret_value()

    result = run(app, ["train", "--cfg.epochs", "4"])

    assert result.code == 0
    assert result.json() == "a-long-key"


@pytest.mark.parametrize(("argv", "expected"), [([], 7), (["--env.epochs", "9"], 9)])
def test_settings_parameter_reads_its_env_and_a_flag_wins(
    argv: list[str],
    expected: int,
    monkeypatch: pytest.MonkeyPatch,
    run: Run,
) -> None:
    monkeypatch.setenv("TRAIN_EPOCHS", "7")
    app = App("ml")

    @app.command
    def train(env: Env) -> Env:
        return env

    result = run(app, ["train", *argv])

    assert result.json() == {"epochs": expected}


def test_plain_model_parameter_ignores_env(monkeypatch: pytest.MonkeyPatch, run: Run) -> None:
    for name in ("EPOCHS", "CFG__EPOCHS", "CFG_EPOCHS"):
        monkeypatch.setenv(name, "7")
    app = App("ml")

    @app.command
    def train(cfg: TrainConfig) -> TrainConfig:
        return cfg

    result = run(app, ["train"])

    assert result.json()["epochs"] == 3

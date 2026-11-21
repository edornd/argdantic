from typing import Annotated, Any, Literal

import pytest
from conftest import Run
from pydantic import BaseModel, ConfigDict, Field, SecretStr, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from argdantic import App, Flat


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


class Steps(BaseModel):
    steps: int

    @field_validator("steps", mode="before")
    @classmethod
    def expand_k(cls, value: Any) -> Any:
        return int(value[:-1]) * 1000 if isinstance(value, str) and value.endswith("k") else value


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    epochs: int = 3


class Sched(BaseModel):
    lr: float = 0.1


class Kind(BaseModel):
    kind: Literal["adam", "sgd"] = "adam"


class Secret(BaseModel):
    key: Annotated[SecretStr, Field(min_length=8)]


class Checked(BaseModel):
    epochs: int = 3

    @model_validator(mode="after")
    def reject(self) -> "Checked":
        raise ValueError("bad")


class Aliased(BaseModel):
    max_steps: int = Field(10, alias="steps")


class Warmup(BaseModel):
    warm: int = Field(2, validation_alias="warmup_steps")


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


def test_flat_parameter_drops_the_prefix(run: Run) -> None:
    app = App("ml")
    received: list[Any] = []

    @app.command
    def train(cfg: Flat[TrainConfig], slurm: bool = False) -> TrainConfig:
        received.extend([type(cfg), type(cfg.optim), cfg.optim.lr, slurm])
        return cfg

    result = run(app, ["train", "--optim.lr", "0.5", "--epochs", "4", "--slurm"])

    assert result.json() == {"optim": {"lr": 0.5}, "epochs": 4}
    assert received == [TrainConfig, Optim, 0.5, True]


def test_flat_model_before_validator_sees_the_raw_string(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[Steps]) -> Steps:
        return cfg

    result = run(app, ["train", "--steps", "2k"])

    assert result.json() == {"steps": 2000}


def test_flat_model_config_does_not_apply_to_other_parameters(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[Frozen], tags: list[str] | None = None) -> list[str]:
        tags = tags or []
        tags.append("x")
        return tags

    result = run(app, ["train", "--tags", '["a"]'])

    assert result.json() == ["a", "x"]


def _flat_pair(optim: Flat[Optim], sched: Flat[Sched]) -> None: ...


def _flat_and_plain(optim: Flat[Optim], lr: float = 1.0) -> None: ...


def _alias_and_plain(cfg: Flat[Aliased], steps: int = 1) -> None: ...


@pytest.mark.parametrize(
    ("fn", "match"),
    [
        (_flat_pair, "`--lr` comes from `optim: Flat\\[Optim\\]` and `sched: Flat\\[Sched\\]`"),
        (_flat_and_plain, "`--lr` comes from `optim: Flat\\[Optim\\]` and `lr`"),
        (_alias_and_plain, "`--steps` comes from `cfg: Flat\\[Aliased\\]` and `steps`"),
    ],
)
def test_flag_name_clash_raises_at_definition(fn: Any, match: str) -> None:
    app = App("ml")

    with pytest.raises(ValueError, match=match):
        app.command(fn)


def test_prefixed_field_and_plain_parameter_may_share_a_name(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Optim, lr: float = 1.0) -> list[float]:
        return [cfg.lr, lr]

    result = run(app, ["train", "--cfg.lr", "0.5", "--lr", "2"])

    assert result.code == 0
    assert result.json() == [0.5, 2.0]


def test_flat_on_a_non_model_raises() -> None:
    app = App("ml")

    with pytest.raises(TypeError, match="Flat needs a pydantic model, got <class 'int'> for parameter 'cfg'"):

        @app.command
        def train(cfg: Flat[int]) -> None: ...


def test_required_flat_field_reports_its_own_name(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[Sized]) -> Sized:
        return cfg

    result = run(app, ["train"])

    assert [(e["path"], e["code"]) for e in result.json()["field_errors"]] == [("size", "missing")]


def test_flat_default_instance_keeps_its_other_values(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[TrainConfig] = FIVE_EPOCHS) -> TrainConfig:
        return cfg

    result = run(app, ["train", "--optim.lr", "0.5"])

    assert result.json() == {"optim": {"lr": 0.5}, "epochs": 5}


@pytest.mark.parametrize(("argv", "expected"), [([], 7), (["--epochs", "9"], 9)])
def test_flat_settings_parameter_reads_its_env_and_a_flag_wins(
    argv: list[str],
    expected: int,
    monkeypatch: pytest.MonkeyPatch,
    run: Run,
) -> None:
    monkeypatch.setenv("TRAIN_EPOCHS", "7")
    app = App("ml")

    @app.command
    def train(env: Flat[Env]) -> Env:
        return env

    result = run(app, ["train", *argv])

    assert result.json() == {"epochs": expected}


def test_flat_field_error_path_has_no_parameter_name(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[TrainConfig]) -> None: ...

    result = run(app, ["train", "--optim.lr", "-1"])

    assert result.json()["field_errors"][0]["path"] == "optim.lr"


def test_flat_literal_error_lists_allowed(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[Kind]) -> None: ...

    result = run(app, ["train", "--kind", "rms"])

    field_error = result.json()["field_errors"][0]
    assert field_error["path"] == "kind"
    assert field_error["allowed"] == ["adam", "sgd"]


def test_flat_secret_is_hidden(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[Secret]) -> None: ...

    result = run(app, ["train", "--key", "abc"])

    assert result.json()["field_errors"][0]["path"] == "key"
    assert "abc" not in result.out


def test_flat_model_validator_error_has_an_empty_path(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[Checked]) -> None: ...

    result = run(app, ["train"])

    assert result.json()["field_errors"][0]["path"] == ""


def test_flat_field_alias_is_its_flag(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[Aliased]) -> int:
        return cfg.max_steps

    result = run(app, ["train", "--steps", "4"])

    assert result.json() == 4


def test_flat_field_and_aliased_plain_parameter_may_share_a_name(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(optim: Flat[Optim], lr: float = Field(1.0, alias="rate")) -> list[float]:
        return [optim.lr, lr]

    result = run(app, ["train", "--lr", "0.5", "--rate", "2"])

    assert result.json() == [0.5, 2.0]


def test_flat_field_validation_alias_is_its_flag(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[Warmup]) -> int:
        return cfg.warm

    result = run(app, ["train", "--warmup-steps", "9"])

    assert result.json() == 9


def test_flat_malformed_json_is_a_validation_error(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[TrainConfig]) -> None: ...

    result = run(app, ["train", "--optim", "{bad"])

    assert result.code == 2
    assert result.json()["code"] == "VALIDATION_ERROR"


def test_unknown_flag_lists_the_flat_flags(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[TrainConfig]) -> None: ...

    result = run(app, ["train", "--nope", "1"])

    field_error = result.json()["field_errors"][0]
    assert "--optim.lr" in field_error["allowed"]
    assert "--epochs" in field_error["allowed"]


def test_help_shows_flat_fields_with_descriptions_and_instance_defaults(run: Run) -> None:
    app = App("ml")

    @app.command
    def train(cfg: Flat[TrainConfig] = FIVE_EPOCHS) -> None: ...

    result = run(app, ["train", "--help"])

    assert "--epochs int" in result.out
    assert "(default: 5)" in result.out
    assert "optim options" in result.out
    assert "learning rate" in result.out

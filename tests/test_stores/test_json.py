import json
from pathlib import Path
from typing import Any, Dict, List, Set

from pydantic_settings import BaseSettings

from argdantic.stores import JsonSettingsStore
from argdantic.testing import CLIRunner


def test_json_store_repr(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    store = JsonSettingsStore(path)
    assert store.path == path
    assert repr(store) == f"<JsonSettingsStore path={path}>"


def test_json_store_call(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    store = JsonSettingsStore(path)
    assert store.path == path

    class Settings(BaseSettings):
        foo: str = "baz"
        bar: int = 42

    store(Settings())
    assert "".join(path.read_text().split(" ")) == '{"foo":"baz","bar":42}'

    class Settings(BaseSettings):
        foo: str = "baz"
        bar: int = 42
        baz: List[str] = ["foo", "bar"]

    store(Settings())
    assert "".join(path.read_text().split(" ")) == '{"foo":"baz","bar":42,"baz":["foo","bar"]}'

    class Settings(BaseSettings):
        foo: str = "baz"
        bar: int = 42
        baz: List[str] = ["foo", "bar"]
        qux: Set[str] = {"foo", "bar"}

    store(Settings())
    text = path.read_text()
    data = json.loads(text)
    assert data["foo"] == "baz"
    assert data["bar"] == 42
    assert all(item in data["baz"] for item in ["foo", "bar"])
    assert all(item in data["qux"] for item in ["foo", "bar"])

    class Settings(BaseSettings):
        foo: str = "baz"
        bar: int = 42
        baz: List[str] = ["foo", "bar"]
        qux: Set[str] = {"foo", "bar"}
        quux: Dict[str, Any] = {"foo": "bar"}

    store(Settings())
    text = path.read_text()
    data = json.loads(text)
    assert data["foo"] == "baz"
    assert data["bar"] == 42
    assert all(item in data["baz"] for item in ["foo", "bar"])
    assert all(item in data["qux"] for item in ["foo", "bar"])
    assert data["quux"] == {"foo": "bar"}


def test_parser_using_json_store(tmp_path: Path, runner: CLIRunner) -> None:
    from argdantic import ArgParser

    cli = ArgParser()
    path = tmp_path / "settings.json"

    @cli.command(stores=[JsonSettingsStore(path)])
    def main(foo: str = "baz", bar: int = 42) -> None:
        return foo, bar

    result = runner.invoke(cli, [])
    assert result.exception is None
    assert result.return_value == ("baz", 42)


def test_parser_using_json_store_complex_data(tmp_path: Path, runner: CLIRunner) -> None:
    from pathlib import Path

    from argdantic import ArgParser

    cli = ArgParser()
    path = tmp_path / "settings.json"

    @cli.command(stores=[JsonSettingsStore(path)])
    def main(foo: Path = "baz", bar: int = 42) -> None:
        return foo, bar

    result = runner.invoke(cli, [])
    assert result.exception is None
    assert result.return_value == ("baz", 42)

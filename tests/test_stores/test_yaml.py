from pathlib import Path

import mock
import pytest
from pydantic_settings import BaseSettings

from argdantic.testing import CLIRunner


def test_yaml_store_import_error(tmp_path: Path) -> None:
    from argdantic.stores.yaml import YamlSettingsStore

    class Settings(BaseSettings):
        foo: str = "baz"
        bar: int = 42

    with mock.patch.dict("sys.modules", {"yaml": None}):
        store = YamlSettingsStore(tmp_path / "settings.yaml")
        assert repr(store) == f"<YamlSettingsStore path={store.path}>"
        assert isinstance(store, YamlSettingsStore)
        with pytest.raises(Exception):
            data = Settings()
            store(data)


def test_yaml_store_repr(tmp_path: Path) -> None:
    from argdantic.stores.yaml import YamlSettingsStore

    path = tmp_path / "settings.yaml"
    store = YamlSettingsStore(path)
    assert store.path == path
    assert repr(store) == f"<YamlSettingsStore path={path}>"


def test_yaml_store_call(tmp_path: Path) -> None:
    from argdantic.stores.yaml import YamlSettingsStore

    path = tmp_path / "settings.yaml"
    store = YamlSettingsStore(path)
    assert store.path == path

    class Settings(BaseSettings):
        foo: str = "baz"
        bar: int = 42

    store(Settings())
    # read data, remove trailing newline and trailing whitespace
    data = path.read_text().strip().replace("\n", " ")
    assert data == "bar: 42 foo: baz"


def test_parser_using_yaml_store(tmp_path: Path, runner: CLIRunner) -> None:
    from argdantic import ArgParser
    from argdantic.stores.yaml import YamlSettingsStore

    path = tmp_path / "settings.yaml"
    parser = ArgParser()

    @parser.command(stores=[YamlSettingsStore(path)])
    def main(foo: str = "baz", bar: int = 42) -> None:
        return foo, bar

    result = runner.invoke(parser, [])
    assert result.exception is None
    assert result.return_value == ("baz", 42)

    result = runner.invoke(parser, ["--foo", "qux"])
    assert result.exception is None
    assert result.return_value == ("qux", 42)
    assert result.return_value == ("qux", 42)


def test_parser_using_yaml_store_complex_data(tmp_path: Path, runner: CLIRunner) -> None:
    from argdantic import ArgParser
    from argdantic.stores.yaml import YamlSettingsStore

    path = tmp_path / "settings.yaml"
    parser = ArgParser()

    @parser.command(stores=[YamlSettingsStore(path, mode="json")])
    def main(foo: Path = "baz", bar: int = 42) -> None:
        return str(foo), bar

    result = runner.invoke(parser, [])
    assert result.exception is None
    assert result.return_value == ("baz", 42)

    result = runner.invoke(parser, ["--foo", "qux", "--bar", "24"])
    assert result.exception is None
    print(result.return_value)
    assert result.return_value == ("qux", 24)

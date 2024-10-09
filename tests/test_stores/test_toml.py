from pathlib import Path

import mock
import pytest
from pydantic_settings import BaseSettings

from argdantic.testing import CLIRunner


def test_toml_store_repr(tmp_path: Path) -> None:
    from argdantic.stores.toml import TomlSettingsStore

    path = tmp_path / "settings.toml"
    store = TomlSettingsStore(path)
    assert store.path == path
    assert repr(store) == f"<TomlSettingsStore path={path}>"


def test_toml_store_import_error(tmp_path: Path) -> None:
    from argdantic.stores.toml import TomlSettingsStore

    class Settings(BaseSettings):
        foo: str = "baz"
        bar: int = 42

    with mock.patch.dict("sys.modules", {"toml": None}):
        store = TomlSettingsStore(tmp_path / "settings.toml")
        assert repr(store) == f"<TomlSettingsStore path={store.path}>"
        with pytest.raises(ImportError):
            store(Settings())


def test_toml_store_call(tmp_path: Path) -> None:
    from argdantic.stores.toml import TomlSettingsStore

    path = tmp_path / "settings.toml"
    store = TomlSettingsStore(path)
    assert store.path == path

    class Settings(BaseSettings):
        foo: str = "baz"
        bar: int = 42

    store(Settings())
    # read data, remove trailing newline and trailing whitespace
    data = path.read_text().strip().replace("\n", " ")
    assert data == 'foo = "baz" bar = 42'


def test_parser_using_toml_store(tmp_path: Path, runner: CLIRunner) -> None:
    from argdantic import ArgParser
    from argdantic.stores.toml import TomlSettingsStore

    path = tmp_path / "settings.toml"
    parser = ArgParser()

    @parser.command(stores=[TomlSettingsStore(path)])
    def main(foo: str = "baz", bar: int = 42) -> None:
        return foo, bar

    result = runner.invoke(parser, [])
    assert result.exception is None
    assert result.return_value == ("baz", 42)


def test_parser_using_toml_store_complex_data(tmp_path: Path, runner: CLIRunner) -> None:
    from argdantic import ArgParser
    from argdantic.stores.toml import TomlSettingsStore

    path = tmp_path / "settings.toml"
    parser = ArgParser()

    @parser.command(stores=[TomlSettingsStore(path, mode="json")])
    def main(foo: Path = "baz", bar: int = 42) -> None:
        return foo, bar

    result = runner.invoke(parser, [])
    assert result.exception is None
    assert result.return_value == ("baz", 42)

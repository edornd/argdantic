from pathlib import Path
from typing import Any, Dict

import mock
import pytest
from pydantic_settings import BaseSettings

from argdantic.sources.base import FileSettingsSource
from argdantic.testing import CLIRunner


def create_toml_file(data: Dict[str, Any], path: Path) -> Path:
    import tomli_w

    path.write_text(tomli_w.dumps(data))
    return path


class TestConfig(BaseSettings):
    __test__ = False
    foo: str
    bar: int


def test_toml_import_error(tmp_path: Path) -> None:
    from argdantic.sources.toml import TomlSettingsSource

    with mock.patch.dict("sys.modules", {"tomli": None}):
        path = create_toml_file({"foo": "baz", "bar": 42}, tmp_path / "settings.toml")
        source_spawner = TomlSettingsSource(path)
        assert repr(source_spawner) == f"<TomlSettingsSource path={path}>"
        assert isinstance(source_spawner, FileSettingsSource)
        with pytest.raises(ImportError):
            source_spawner(TestConfig)()


def test_toml_source(tmp_path: Path) -> None:
    from argdantic.sources.toml import TomlSettingsSource

    path = create_toml_file({"foo": "baz", "bar": 42}, tmp_path / "settings.toml")
    source_spawner = TomlSettingsSource(path)
    assert repr(source_spawner) == f"<TomlSettingsSource path={path}>"
    assert isinstance(source_spawner, FileSettingsSource)
    assert source_spawner(TestConfig)() == {"foo": "baz", "bar": 42}


def test_parser_using_toml_source(tmp_path: Path, runner: CLIRunner) -> None:
    from argdantic import ArgParser
    from argdantic.sources import TomlSettingsSource

    path = create_toml_file({"foo": "baz", "bar": 42}, tmp_path / "settings.toml")
    parser = ArgParser()

    @parser.command(sources=[TomlSettingsSource(path)])
    def main(foo: str = None, bar: int = None) -> None:
        return foo, bar

    result = runner.invoke(parser, [])
    assert result.exception is None
    assert result.return_value == ("baz", 42)

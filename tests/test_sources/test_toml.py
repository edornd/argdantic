from pathlib import Path
from typing import Any, Dict

import mock
import pytest
from pydantic import BaseModel

from argdantic.sources.base import FileSettingsSourceBuilder
from argdantic.testing import CLIRunner


def create_toml_file(data: Dict[str, Any], path: Path) -> Path:
    import tomli_w

    path.write_text(tomli_w.dumps(data))
    return path


class TestConfig(BaseModel):
    __test__ = False
    foo: str
    bar: int


def test_toml_import_error(tmp_path: Path) -> None:
    from argdantic.sources.toml import TomlSettingsSource

    with mock.patch.dict("sys.modules", {"tomli": None}):
        path = create_toml_file({"foo": "baz", "bar": 42}, tmp_path / "settings.toml")
        source_spawner = TomlSettingsSource(path)
        assert repr(source_spawner) == f"<TomlSettingsSource path={path}>"
        assert isinstance(source_spawner, FileSettingsSourceBuilder)
        with pytest.raises(ImportError):
            source_spawner(TestConfig)()


def test_toml_source(tmp_path: Path) -> None:
    from argdantic.sources.toml import TomlSettingsSource

    path = create_toml_file({"foo": "baz", "bar": 42}, tmp_path / "settings.toml")
    source_spawner = TomlSettingsSource(path)
    assert repr(source_spawner) == f"<TomlSettingsSource path={path}>"
    assert isinstance(source_spawner, FileSettingsSourceBuilder)
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


def test_dynamic_toml_source(tmp_path: Path, runner: CLIRunner, capsys: pytest.CaptureFixture) -> None:
    from argdantic import ArgParser
    from argdantic.sources import TomlFileLoader, from_file

    path = create_toml_file({"foo": "baz", "bar": 42}, tmp_path / "settings.toml")
    parser = ArgParser()

    @from_file(loader=TomlFileLoader)
    class TestModel(BaseModel):
        foo: str = "default"
        bar: int = 0

    @parser.command()
    def main(model: TestModel) -> None:
        return model.model_dump()

    # check if the cli requires the model argument
    result = runner.invoke(parser, [])
    output = capsys.readouterr()

    assert result.exception is None
    assert not output.out
    assert "error: the following arguments are required: --model" in output.err.rstrip()

    # check if the help message contains 'model', together with 'model.foo' and 'model.bar'
    result = runner.invoke(parser, ["--help"])
    output = capsys.readouterr()
    assert "--model " in output.out
    assert "--model.foo" in output.out
    assert "--model.bar" in output.out

    # check that the model is populated with the values from the JSON file
    result = runner.invoke(parser, ["--model", str(path)])
    assert result.exception is None
    assert result.return_value == {"foo": "baz", "bar": 42}

    # check that the CLI argument overrides the JSON file
    result = runner.invoke(parser, ["--model", str(path), "--model.foo", "overridden"])
    assert result.exception is None
    assert result.return_value == {"foo": "overridden", "bar": 42}

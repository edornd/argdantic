import json
from pathlib import Path
from typing import Any, Dict

import mock
from pydantic_settings import BaseSettings
from pytest import CaptureFixture

from argdantic.sources.base import FileSettingsSourceBuilder
from argdantic.testing import CLIRunner


def create_json_file(data: Dict[str, Any], path: Path) -> Path:
    path.write_text(json.dumps(data))
    return path


class TestConfig(BaseSettings):
    __test__ = False
    foo: str
    bar: int


def test_json_no_import_error(tmp_path: Path) -> None:
    from argdantic.sources.json import JsonSettingsSource

    with mock.patch.dict("sys.modules", {"orjson": None}):
        path = create_json_file({"foo": "baz", "bar": 42}, tmp_path / "settings.json")
        source_spawner = JsonSettingsSource(path)
        assert isinstance(source_spawner, FileSettingsSourceBuilder)
        assert source_spawner(TestConfig)() == {"foo": "baz", "bar": 42}
        assert repr(source_spawner) == f"<JsonSettingsSource path={path}>"


def test_json_source(tmp_path: Path) -> None:
    from argdantic.sources.json import JsonSettingsSource

    path = create_json_file({"foo": "baz", "bar": 42}, tmp_path / "settings.json")
    source_spawner = JsonSettingsSource(path)
    assert isinstance(source_spawner, FileSettingsSourceBuilder)
    assert source_spawner(TestConfig)() == {"foo": "baz", "bar": 42}
    assert repr(source_spawner) == f"<JsonSettingsSource path={path}>"


def test_parser_using_json_source(tmp_path: Path, runner: CLIRunner) -> None:
    from argdantic import ArgParser
    from argdantic.sources.json import JsonSettingsSource

    path = create_json_file({"foo": "baz", "bar": 42}, tmp_path / "settings.json")
    parser = ArgParser()

    @parser.command(sources=[JsonSettingsSource(path)])
    def main(foo: str = None, bar: int = None) -> None:
        return foo, bar

    result = runner.invoke(parser, [])
    assert result.exception is None
    assert result.return_value == ("baz", 42)


def test_json_sourced_model(tmp_path: Path, runner: CLIRunner, capsys: CaptureFixture) -> None:
    from argdantic import ArgParser
    from argdantic.sources import JsonModel

    path = create_json_file({"foo": "baz", "bar": 42}, tmp_path / "settings.json")
    parser = ArgParser()

    class TestModel(JsonModel):
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

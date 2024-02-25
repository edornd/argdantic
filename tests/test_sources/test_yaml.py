from pathlib import Path
from typing import Any, Dict

import mock
import pytest
from pydantic_settings import BaseSettings

from argdantic.sources.base import FileSettingsSource
from argdantic.testing import CLIRunner


def create_yaml_file(data: Dict[str, Any], path: Path) -> Path:
    import yaml

    path.write_text(yaml.dump(data))
    return path


class TestConfig(BaseSettings):
    __test__ = False
    foo: str
    bar: int


def test_yaml_import_error(tmp_path: Path) -> None:
    from argdantic.sources.yaml import YamlSettingsSource

    path = create_yaml_file({"foo": "baz", "bar": 42}, tmp_path / "settings.yaml")
    with mock.patch.dict("sys.modules", {"yaml": None}):
        source_spawner = YamlSettingsSource(path)
        assert repr(source_spawner) == f"<YamlSettingsSource path={path}>"
        assert isinstance(source_spawner, FileSettingsSource)
        with pytest.raises(ImportError):
            source_spawner(TestConfig)()


def test_yaml_source(tmp_path: Path) -> None:
    from argdantic.sources.yaml import YamlSettingsSource

    path = create_yaml_file({"foo": "baz", "bar": 42}, tmp_path / "settings.yaml")
    source = YamlSettingsSource(path)
    assert repr(source) == f"<YamlSettingsSource path={path}>"
    assert isinstance(source, FileSettingsSource)
    assert source(TestConfig)() == {"foo": "baz", "bar": 42}


def test_parser_using_yaml_source(tmp_path: Path, runner: CLIRunner) -> None:
    from argdantic import ArgParser
    from argdantic.sources.yaml import YamlSettingsSource

    path = create_yaml_file({"foo": "baz", "bar": 42}, tmp_path / "settings.yaml")
    parser = ArgParser()

    @parser.command(sources=[YamlSettingsSource(path)])
    def main(foo: str = None, bar: int = None) -> None:
        return foo, bar

    result = runner.invoke(parser, [])
    assert result.exception is None
    assert result.return_value == ("baz", 42)


def test_yaml_sourced_model(tmp_path: Path, runner: CLIRunner, capsys: pytest.CaptureFixture) -> None:
    from argdantic import ArgParser
    from argdantic.sources import YamlModel

    path = create_yaml_file({"foo": "baz", "bar": 42}, tmp_path / "settings.yaml")
    parser = ArgParser()

    class TestModel(YamlModel):
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

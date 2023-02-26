from pathlib import Path

import mock

from argdantic import ArgParser
from argdantic.sources.base import EnvSettingsSource, SecretsSettingsSource
from argdantic.testing import CLIRunner


def test_env_settings_source(runner: CLIRunner) -> None:
    source = EnvSettingsSource(env_file=".env", env_file_encoding="utf-8", env_prefix="ARGDANTIC_")
    assert "EnvSettingsSource" in repr(source)
    assert isinstance(source, EnvSettingsSource)

    parser = ArgParser()

    @parser.command(sources=[source])
    def main(foo: str = None, bar: int = None) -> None:
        return foo, bar

    with mock.patch.dict("os.environ", {"ARGDANTIC_FOO": "baz", "ARGDANTIC_BAR": "42"}):
        result = runner.invoke(parser, [])
        assert result.exception is None
        assert result.return_value == ("baz", 42)


def test_secrets_setting_source(runner: CLIRunner, tmp_path: Path) -> None:
    source = SecretsSettingsSource(secrets_dir=tmp_path)
    assert "SecretsSettingsSource" in repr(source)
    assert isinstance(source, SecretsSettingsSource)

    parser = ArgParser()

    @parser.command(sources=[source])
    def main(foo: str = None, bar: int = None) -> None:
        return foo, bar

    # just check that it still runs properly
    result = runner.invoke(parser, [])
    assert result.exception is None
    assert result.return_value == (None, None)

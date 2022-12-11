from typing import Any, Dict

from pydantic import BaseSettings

from argdantic.sources.base import FileSettingsSource


class TomlSettingsSource(FileSettingsSource):
    """
    A TOML file settings source reads settings from a TOML file.
    """

    def __call__(self, settings: BaseSettings = None) -> Dict[str, Any]:
        try:
            import tomli
        except ImportError:
            raise ImportError(
                "You need to install TOML libraries to use the TOML source. "
                "You can do so by running `pip install argdantic[toml]`."
            )
        with open(self.path, mode="rb") as f:
            return tomli.load(f)

    def __repr__(self) -> str:
        return f"<TomlSettingsSource path={self.path}>"

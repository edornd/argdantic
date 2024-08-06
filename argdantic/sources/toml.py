from typing import Any, Dict, Tuple, Type

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from argdantic.sources.base import FileBaseSettingsSource, FileSettingsSourceBuilder


class TomlFileLoader(FileBaseSettingsSource):
    """
    Class internal to pydantic-settings that reads settings from a TOML file.
    This gets spawned by the TomlSettingsSource class.
    """

    def get_field_value(self, field: FieldInfo, field_name: str) -> Tuple[Any, str, bool]:
        return None, field_name, False  # pragma: no cover

    def __call__(self) -> Dict[str, Any]:
        try:
            import tomli
        except ImportError:
            raise ImportError(
                "You need to install TOML libraries to use the TOML source. "
                "You can do so by running `pip install argdantic[toml]`."
            )
        with open(self.path, mode="rb") as f:
            return tomli.load(f)


class TomlSettingsSource(FileSettingsSourceBuilder):
    """
    A TOML file settings source reads settings from a TOML file.
    """

    def __call__(self, settings: Type[BaseSettings]) -> PydanticBaseSettingsSource:
        return TomlFileLoader(settings, self.path)

    def __repr__(self) -> str:
        return f"<TomlSettingsSource path={self.path}>"

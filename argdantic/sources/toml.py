from pathlib import Path
from typing import Any, Dict, Tuple, Type, Union

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from argdantic.sources.base import FileSettingsSource


class PydanticTomlSource(PydanticBaseSettingsSource):
    """
    Class internal to pydantic-settings that reads settings from a TOML file.
    This gets spawned by the TomlSettingsSource class.
    """

    def __init__(self, settings_cls: Type[BaseSettings], path: Union[str, Path]):
        super().__init__(settings_cls)
        self.path = Path(path)

    def get_field_value(self, *args) -> Tuple[Any, str, bool]:
        # see json source
        pass  # pragma: no cover

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


class TomlSettingsSource(FileSettingsSource):
    """
    A TOML file settings source reads settings from a TOML file.
    """

    def __call__(self, settings: BaseSettings = None) -> PydanticBaseSettingsSource:
        return PydanticTomlSource(settings, self.path)

    def __repr__(self) -> str:
        return f"<TomlSettingsSource path={self.path}>"

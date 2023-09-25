from pathlib import Path
from typing import Any, Dict, Tuple, Type, Union

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from argdantic.sources.base import FileSettingsSource


class PydanticJsonSource(PydanticBaseSettingsSource):
    """
    Class internal to pydantic-settings that reads settings from a JSON file.
    This gets spawned by the JsonSettingsSource class.
    """

    def __init__(self, settings_cls: Type[BaseSettings], path: Union[str, Path]):
        super().__init__(settings_cls)
        self.path = Path(path)

    def get_field_value(self, *args) -> Tuple[Any, str, bool]:
        # Until I get a better understanding of how this works, I'm just going to
        # load the settings from a JSON file and return them as a dictionary.
        pass  # pragma: no cover

    def __call__(self) -> Dict[str, Any]:
        try:
            import orjson as json

            return json.loads(self.path.read_bytes())
        except ImportError:
            import json

            return json.load(self.path.open())


class JsonSettingsSource(FileSettingsSource):
    """
    A JSON file settings source reads settings from a JSON file.
    Orjson is used if available, otherwise the standard json module is used.
    """

    def __call__(self, settings: BaseSettings = None) -> PydanticBaseSettingsSource:
        return PydanticJsonSource(settings, self.path)

    def __repr__(self) -> str:
        return f"<JsonSettingsSource path={self.path}>"

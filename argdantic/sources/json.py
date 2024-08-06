from typing import Any, Dict, Tuple, Type

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from argdantic.sources.base import FileBaseSettingsSource, FileSettingsSourceBuilder


class JsonFileLoader(FileBaseSettingsSource):
    """
    Class internal to pydantic-settings that reads settings from a JSON file.
    This gets spawned by the JsonSettingsSource class.
    """

    def get_field_value(self, field: FieldInfo, field_name: str) -> Tuple[Any, str, bool]:
        return None, field_name, False  # pragma: no cover

    def __call__(self) -> Dict[str, Any]:
        try:
            import orjson as json

            return json.loads(self.path.read_bytes())
        except ImportError:
            import json  # type: ignore

            return json.load(self.path.open())  # type: ignore


class JsonSettingsSource(FileSettingsSourceBuilder):
    """
    A JSON file settings source reads settings from a JSON file.
    Orjson is used if available, otherwise the standard json module is used.
    """

    def __call__(self, settings: Type[BaseSettings]) -> PydanticBaseSettingsSource:
        return JsonFileLoader(settings, self.path)

    def __repr__(self) -> str:
        return f"<JsonSettingsSource path={self.path}>"

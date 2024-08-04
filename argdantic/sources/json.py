from pathlib import Path
from typing import Any, Dict, Tuple, Type

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from argdantic.sources.base import FileBaseSettingsSource, FileSettingsSourceBuilder, SourceBaseModel


class PydanticJsonSource(FileBaseSettingsSource):
    """
    Class internal to pydantic-settings that reads settings from a JSON file.
    This gets spawned by the JsonSettingsSource class.
    """

    def get_field_value(self, field: FieldInfo, field_name: str) -> Tuple[Any, str, bool]:
        return None, field_name, False

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
        return PydanticJsonSource(settings, self.path)

    def __repr__(self) -> str:
        return f"<JsonSettingsSource path={self.path}>"


class JsonModel(SourceBaseModel):
    """
    A base model that reads additional settings from a JSON file.
    """

    def __init__(self, _source: Path, **data) -> None:
        super().__init__(_source, PydanticJsonSource, **data)

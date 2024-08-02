from pathlib import Path
from typing import Any, Dict, Type, Union

from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from argdantic.sources.base import FileSettingsSource, SourceBaseModel


class PydanticJsonSource(PydanticBaseSettingsSource):
    """
    Class internal to pydantic-settings that reads settings from a JSON file.
    This gets spawned by the JsonSettingsSource class.
    """

    def __init__(self, settings_cls: Type[BaseSettings], path: Union[str, Path]):
        super().__init__(settings_cls)
        self.path = Path(path)

    def __call__(self) -> Dict[str, Any]:
        try:
            import orjson as json

            return json.loads(self.path.read_bytes())
        except ImportError:
            import json  # type: ignore

            return json.load(self.path.open())  # type: ignore


class JsonSettingsSource(FileSettingsSource):
    """
    A JSON file settings source reads settings from a JSON file.
    Orjson is used if available, otherwise the standard json module is used.
    """

    def __call__(self, settings: BaseModel) -> Dict[str, Any]:
        return PydanticJsonSource(settings, self.path)

    def __repr__(self) -> str:
        return f"<JsonSettingsSource path={self.path}>"


class JsonModel(SourceBaseModel):
    """
    A base model that reads additional settings from a JSON file.
    """

    def __init__(self, _source: Path = None, **data) -> None:
        super().__init__(_source, PydanticJsonSource, **data)

from typing import Any, Dict

from pydantic import BaseSettings

from argdantic.sources.base import FileSettingsSource


class JsonSettingsSource(FileSettingsSource):
    """
    A JSON file settings source reads settings from a JSON file.
    Orjson is used if available, otherwise the standard json module is used.
    """

    def __call__(self, settings: BaseSettings = None) -> Dict[str, Any]:
        try:
            import orjson as json

            return json.loads(self.path.read_bytes())
        except ImportError:
            import json

            return json.load(self.path.open())

    def __repr__(self) -> str:
        return f"<JsonSettingsSource path={self.path}>"

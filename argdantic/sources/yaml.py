from pathlib import Path
from typing import Any, Dict, Tuple, Type

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from argdantic.sources.base import FileBaseSettingsSource, FileSettingsSourceBuilder, SourceBaseModel


class PydanticYamlSource(FileBaseSettingsSource):
    """
    Class internal to pydantic-settings that reads settings from a YAML file.
    This gets spawned by the YamlSettingsSource class.
    """

    def get_field_value(self, field: FieldInfo, field_name: str) -> Tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "You need to install YAML dependencies to use the YAML source. "
                "You can do so by running `pip install argdantic[yaml]`."
            )
        return yaml.safe_load(self.path.read_text())


class YamlSettingsSource(FileSettingsSourceBuilder):
    """
    A YAML file settings source reads settings from a YAML file.
    If the PyYAML library is not installed, an error is raised.
    """

    def __call__(self, settings: Type[BaseSettings]) -> PydanticBaseSettingsSource:
        return PydanticYamlSource(settings, self.path)

    def __repr__(self) -> str:
        return f"<YamlSettingsSource path={self.path}>"


class YamlModel(SourceBaseModel):
    """
    A base model that reads additional settings from a YAML file.
    """

    def __init__(self, _source: Path, **data) -> None:
        super().__init__(_source, PydanticYamlSource, **data)

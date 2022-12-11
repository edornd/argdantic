from typing import Any, Dict

from pydantic import BaseSettings

from argdantic.sources.base import FileSettingsSource


class YamlSettingsSource(FileSettingsSource):
    """
    A YAML file settings source reads settings from a YAML file.
    If the PyYAML library is not installed, an error is raised.
    """

    def __call__(self, settings: BaseSettings = None) -> Dict[str, Any]:
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "You need to install YAML dependencies to use the YAML source. "
                "You can do so by running `pip install argdantic[yaml]`."
            )
        return yaml.safe_load(self.path.read_text())

    def __repr__(self) -> str:
        return f"<YamlSettingsSource path={self.path}>"

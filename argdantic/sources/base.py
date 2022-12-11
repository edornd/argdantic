from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Union

from pydantic.env_settings import BaseSettings, DotenvType
from pydantic.env_settings import EnvSettingsSource as PydanticEnvSource
from pydantic.env_settings import SecretsSettingsSource as PydanticSecretsSource


class FileSettingsSource(ABC):
    """
    A file settings source is a callable object that takes an input file path
    to read settings from, and returns a dictionary of settings that can be
    passed to a pydantic model.
    """

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)

    @abstractmethod
    def __call__(self, settings: BaseSettings) -> Dict[str, Any]:
        raise NotImplementedError  # pragma: no cover

    def inject(self, config_class: BaseSettings.Config) -> BaseSettings.Config:
        """
        Monkey patch to make sure that the pydantic config class has the right attributes.
        """
        return config_class


class EnvSettingsSource(PydanticEnvSource):
    """
    Reads settings from environment variables.
    This class inherits from the pydantic EnvSettingsSource class to fully customize input sources.
    """

    def __init__(
        self,
        env_file: Optional[DotenvType],
        env_file_encoding: Optional[str] = "utf-8",
        env_nested_delimiter: Optional[str] = "__",
        env_prefix: str = "",
        env_case_sensitive: bool = False,
    ):
        super().__init__(env_file, env_file_encoding, env_nested_delimiter, len(env_prefix))
        self.env_prefix = env_prefix
        self.case_sensitive = env_case_sensitive

    def __call__(self, settings: BaseSettings) -> Dict[str, Any]:
        return super().__call__(settings)

    def inject(self, config_class: BaseSettings.Config) -> BaseSettings.Config:
        config_class.env_file = self.env_file
        config_class.env_file_encoding = self.env_file_encoding
        config_class.env_nested_delimiter = self.env_nested_delimiter
        config_class.env_prefix = self.env_prefix
        config_class.case_sensitive = self.case_sensitive
        return config_class


class SecretsSettingsSource(PydanticSecretsSource):
    """Reads secrets from the given directory.
    This class inherits from the pydantic SecretsSettingsSource class to fully customize input sources.
    """

    def __init__(self, secrets_dir: Optional[Union[str, Path]]):
        return super().__init__(secrets_dir)

    def inject(self, config_class: BaseSettings.Config) -> BaseSettings.Config:
        config_class.secrets_dir = self.secrets_dir
        return config_class

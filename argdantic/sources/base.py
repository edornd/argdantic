import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Type, Union

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from pydantic_settings.sources import DotEnvSettingsSource as PydanticEnvSource
from pydantic_settings.sources import DotenvType
from pydantic_settings.sources import SecretsSettingsSource as PydanticSecretsSource


class ArgdanticSource(ABC):
    """
    An argdantic source is a callable object that takes an input settings object
    and returns a dictionary of settings that can be passed to an argument parser.
    """

    @abstractmethod
    def __call__(self, settings_cls: Type[BaseSettings]) -> PydanticBaseSettingsSource:
        raise NotImplementedError  # pragma: no cover


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


class PydanticMultiEnvSource(PydanticEnvSource):
    """
    A pydantic settings source that loads settings from multiple environment sources.
    This loads from both the environment variables and the dotenv file.
    """

    def _load_env_vars(self) -> Mapping[str, Union[str, None]]:
        if self.case_sensitive:
            env_vars = os.environ
        else:
            self.env_prefix = self.env_prefix.lower()
            env_vars = {k.lower(): v for k, v in os.environ.items()}
        # filter out env vars that are not fields in the settings class
        valid_vars = {}
        for field_name in self.settings_cls.model_fields:
            expected = f"{self.env_prefix}{field_name}"
            # keep them with the prefix, it will be removed later
            if expected in env_vars:
                valid_vars[expected] = env_vars[expected]
        add_vars = super()._load_env_vars()
        valid_vars.update(add_vars)
        return valid_vars


class EnvSettingsSource(ArgdanticSource):
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
        self.env_file = env_file
        self.env_file_encoding = env_file_encoding
        self.env_nested_delimiter = env_nested_delimiter
        self.env_prefix = env_prefix
        self.env_case_sensitive = env_case_sensitive

    def __call__(self, settings_cls: Type[BaseSettings]) -> PydanticBaseSettingsSource:
        return PydanticMultiEnvSource(
            settings_cls=settings_cls,
            env_file=self.env_file,
            env_file_encoding=self.env_file_encoding,
            case_sensitive=self.env_case_sensitive,
            env_prefix=self.env_prefix,
            env_nested_delimiter=self.env_nested_delimiter,
        )


class SecretsSettingsSource(ArgdanticSource):
    """Reads secrets from the given directory.
    This class inherits from the pydantic SecretsSettingsSource class to fully customize input sources.
    """

    def __init__(self, secrets_dir: Optional[Union[str, Path]], case_sensitive: bool = False, env_prefix: str = ""):
        self.secrets_dir = secrets_dir
        self.case_sensitive = case_sensitive
        self.env_prefix = env_prefix

    def __call__(self, settings_cls: Type[BaseSettings]) -> PydanticBaseSettingsSource:
        return PydanticSecretsSource(
            settings_cls=settings_cls,
            secrets_dir=self.secrets_dir,
            case_sensitive=self.case_sensitive,
            env_prefix=self.env_prefix,
        )

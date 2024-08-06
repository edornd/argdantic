from pathlib import Path
from typing import Any, Optional, Tuple, Type, cast

from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, InitSettingsSource, PydanticBaseSettingsSource

from argdantic.sources.base import FileBaseSettingsSource

DEFAULT_SOURCE_FIELD = "_source"


class DynamicFileSource(PydanticBaseSettingsSource):
    """
    Source class for loading values provided during settings class initialization.
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        source_cls: type[FileBaseSettingsSource],
        init_kwargs: dict[str, Any],
        required: bool,
        field_name: Optional[str] = None,
    ):
        super().__init__(settings_cls)
        self.init_kwargs = init_kwargs
        self.field_name = field_name or DEFAULT_SOURCE_FIELD
        if self.field_name not in init_kwargs:
            if required:
                raise ValueError("Missing required source")
            self.source = None
        else:
            self.source = source_cls(settings_cls, init_kwargs[self.field_name])

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        # Nothing to do here. Only implement the return statement to make mypy happy
        return None, "", False  # pragma: no cover

    def __call__(self) -> dict[str, Any]:
        if self.source is not None:
            main_kwargs = self.source()
            main_kwargs.update(self.init_kwargs)
            # remove the source field if it is the default one
            if self.field_name == DEFAULT_SOURCE_FIELD:
                main_kwargs.pop(self.field_name)
            return main_kwargs
        return self.init_kwargs

    def __repr__(self) -> str:
        return f"DynamicFileSource(source={self.source!r})"


def from_file(
    loader: Type[FileBaseSettingsSource],
    use_field: Optional[str] = None,
    required: bool = True,
):
    def decorator(cls):
        if not issubclass(cls, BaseModel):
            raise TypeError("@from_file can only be applied to Pydantic models")
        if use_field is not None:
            if use_field not in cls.model_fields:
                raise ValueError(f"Field {use_field} not found in model {cls.__name__}")
            field_annotation = cls.model_fields[use_field].annotation
            if not issubclass(field_annotation, (str, Path)):
                raise ValueError(f"Field {use_field} must be a string or Path to be used as file source")

        class DynamicSourceSettings(cls, BaseSettings):
            # required to eventually add a cli argument to the model
            # if cli_field is None, an additional argument will be added
            __arg_source_field__ = use_field
            __arg_source_required__ = required
            model_config = ConfigDict(extra="ignore")

            @classmethod
            def settings_customise_sources(
                cls,
                settings_cls: Type[BaseSettings],
                init_settings: PydanticBaseSettingsSource,
                env_settings: PydanticBaseSettingsSource,
                dotenv_settings: PydanticBaseSettingsSource,
                file_secret_settings: PydanticBaseSettingsSource,
            ) -> Tuple[PydanticBaseSettingsSource, ...]:
                source = DynamicFileSource(
                    settings_cls,
                    loader,
                    cast(InitSettingsSource, init_settings).init_kwargs,
                    required,
                    use_field,
                )
                return (source,)

        return DynamicSourceSettings

    return decorator

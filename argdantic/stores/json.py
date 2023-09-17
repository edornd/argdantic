from pydantic_settings import BaseSettings

from argdantic.stores.base import BaseSettingsStore


class JsonSettingsStore(BaseSettingsStore):
    """
    A JSON file settings store writes settings to a JSON file.
    Orjson is used if available, otherwise the standard json module is used.
    """

    def __call__(self, settings: BaseSettings) -> None:
        with self.path.open("wb") as f:
            text = settings.model_dump_json(
                include=self.include,
                exclude=self.exclude,
                by_alias=self.by_alias,
                exclude_defaults=self.exclude_defaults,
                exclude_unset=self.exclude_unset,
                exclude_none=self.exclude_none,
            )
            f.write(text.encode(self.encoding))

    def __repr__(self) -> str:
        return f"<JsonSettingsStore path={self.path}>"

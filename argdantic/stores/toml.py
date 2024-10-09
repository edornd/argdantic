from pydantic_settings import BaseSettings

from argdantic.stores.base import BaseSettingsStore


class TomlSettingsStore(BaseSettingsStore):
    """
    A TOML file settings store writes settings to a TOML file.
    Tomli is used if available, otherwise the standard toml module is used.
    """

    def __call__(self, settings: BaseSettings) -> None:
        try:
            import toml
        except ImportError:
            raise ImportError(
                "You need to install TOML dependencies to use the TOML source. "
                "You can do so by running `pip install argdantic[toml]`."
            )

        with self.path.open("wb") as f:
            text = toml.dumps(
                settings.model_dump(
                    mode=self.mode,
                    include=self.include,
                    exclude=self.exclude,
                    by_alias=self.by_alias,
                    exclude_defaults=self.exclude_defaults,
                    exclude_unset=self.exclude_unset,
                    exclude_none=self.exclude_none,
                )
            )
            f.write(text.encode(self.encoding))

    def __repr__(self) -> str:
        return f"<TomlSettingsStore path={self.path}>"

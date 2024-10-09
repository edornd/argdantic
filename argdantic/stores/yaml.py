from pydantic_settings import BaseSettings

from argdantic.stores.base import BaseSettingsStore


class YamlSettingsStore(BaseSettingsStore):
    """
    A YAML file settings store writes settings to a YAML file.
    PyYAML is used if available, otherwise the standard yaml module is used.
    """

    def __call__(self, settings: BaseSettings) -> None:
        try:
            import yaml
        # exception actually tested, but coverage does not detect it
        except ImportError:  # pragma: no cover
            raise ImportError(
                "You need to install YAML dependencies to use the YAML store. "
                "You can do so by running `pip install argdantic[yaml]`."
            )

        with self.path.open("w") as f:
            data = settings.model_dump(
                mode=self.mode,
                include=self.include,
                exclude=self.exclude,
                by_alias=self.by_alias,
                exclude_defaults=self.exclude_defaults,
                exclude_unset=self.exclude_unset,
                exclude_none=self.exclude_none,
            )
            yaml.safe_dump(data, f, encoding="utf-8", allow_unicode=True)

    def __repr__(self) -> str:
        return f"<YamlSettingsStore path={self.path}>"

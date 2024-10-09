from pathlib import Path
from typing import Optional, Set, Union

from pydantic_settings import BaseSettings

from argdantic.stores.base import BaseSettingsStore


class JsonSettingsStore(BaseSettingsStore):
    """
    A JSON file settings store writes settings to a JSON file.
    Orjson is used if available, otherwise the standard json module is used.
    """

    def __init__(
        self,
        path: Union[str, Path],
        *,
        encoding: str = "utf-8",
        include: Optional[Set[str]] = None,
        exclude: Optional[Set[str]] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> None:
        super().__init__(
            path,
            mode="json",
            encoding=encoding,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

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

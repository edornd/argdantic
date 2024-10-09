from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Literal, Optional, Set, Union

from pydantic import BaseModel
from pydantic_settings import BaseSettings

SettingsStoreCallable = Callable[[Union[BaseSettings, BaseModel]], None]


class BaseSettingsStore(ABC):
    """
    A settings store is a callable object that takes an input file path
    and stores settings to it in a specific format, given by the implementation.
    """

    def __init__(
        self,
        path: Union[str, Path],
        *,
        mode: Literal["python", "json"] = "python",
        encoding: str = "utf-8",
        include: Optional[Set[str]] = None,
        exclude: Optional[Set[str]] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> None:
        self.path = Path(path)
        self.mode = mode
        self.encoding = encoding
        self.include = include
        self.exclude = exclude
        self.by_alias = by_alias
        self.exclude_unset = exclude_unset
        self.exclude_defaults = exclude_defaults
        self.exclude_none = exclude_none

    @abstractmethod
    def __call__(self, settings: BaseSettings) -> None:
        raise NotImplementedError  # pragma: no cover

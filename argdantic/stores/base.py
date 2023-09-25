from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Set, Union

from pydantic_settings import BaseSettings

SettingsStoreCallable = Callable[["BaseSettings"], None]


class BaseSettingsStore(ABC):
    """
    A settings store is a callable object that takes an input file path
    and stores settings to it in a specific format, given by the implementation.
    """

    def __init__(
        self,
        path: Union[str, Path],
        *,
        encoding: str = "utf-8",
        include: Set[str] = None,
        exclude: Set[str] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> None:
        self.path = Path(path)
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

from collections.abc import MutableMapping
from typing import Any, Dict, Iterator, Type, Union, get_origin


class Registry(MutableMapping):
    """Simple class registry for mapping types and their argument handlers."""

    def __init__(self) -> None:
        self.store: Dict[type, Any] = dict()

    def __getitem__(self, key: type) -> Any:
        # do not allow Union types (unless they are Optional, handled in conversion)
        if get_origin(key) is Union:
            raise ValueError("Union types are not supported, please specify a single type.")
        try:
            hierarchy = key.mro()[:-1]
        # avoid look-up errors for non-classes (Literals, etc.)
        except AttributeError:
            origin = get_origin(key)
            hierarchy = [origin] if origin else [key]
        for type_class in hierarchy:
            if type_class in self.store:
                return self.store[type_class]

    def __setitem__(self, key: type, value: Any) -> None:
        return self.store.__setitem__(key, value)

    def __delitem__(self, key: type) -> None:
        return self.store.__delitem__(key)

    def __iter__(self) -> Iterator[Any]:
        return self.store.__iter__()

    def __len__(self) -> int:
        return self.store.__len__()

    def get(self, key: type, default: Any = None) -> Any:
        value = self[key] or default
        return value

    def register(self, *keys: Any):
        assert keys is not None and len(keys) > 0, "Keys required!"

        def decorator(cls: Type[Any]):
            for key in keys:
                self.store[key] = cls
            return cls

        return decorator

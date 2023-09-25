import typing as types
from collections.abc import MutableMapping


class Registry(MutableMapping):
    """Simple class registry for mapping types and their argument handlers."""

    def __init__(self) -> None:
        self.store = dict()

    def __getitem__(self, key: type) -> types.Any:
        # do not allow Union types (unless they are Optional, handled in conversion)
        if types.get_origin(key) is types.Union:
            raise ValueError("Union types are not supported, please specify a single type.")
        try:
            hierarchy = key.mro()[:-1]
        # avoid look-up errors for non-classes (Literals, etc.)
        except AttributeError:
            origin = types.get_origin(key)
            hierarchy = [origin] if origin else [key]
        for type_class in hierarchy:
            if type_class in self.store:
                return self.store[type_class]

    def __setitem__(self, key: type, value: types.Any) -> None:
        return self.store.__setitem__(key, value)

    def __delitem__(self, key: type) -> None:
        return self.store.__delitem__(key)

    def __iter__(self) -> types.Iterator[types.Any]:
        return self.store.__iter__()

    def __len__(self) -> int:
        return self.store.__len__()

    def get(self, key: type, default: types.Any = None) -> types.Any:
        value = self[key] or default
        return value

    def register(self, *keys: types.Any):
        assert keys is not None and len(keys) > 0, "Keys required!"

        def decorator(cls: types.Type[types.Any]):
            for key in keys:
                self.store[key] = cls
            return cls

        return decorator

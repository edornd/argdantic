import typing as t
from argparse import OPTIONAL, Action, ArgumentParser, Namespace, _copy_items


class StoreAction(Action):
    """
    Store action for argparse. This class is used to store the value of an argument.
    This thin wrapper around the argparse Action is used to track if a field has been explicitly set or not.
    """

    def __init__(self, option_strings: t.Sequence[str], dest: str, nargs: t.Union[int, str] = None, **kwargs) -> None:
        super().__init__(option_strings=option_strings, dest=dest, nargs=nargs, **kwargs)
        self._specified = False

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: t.Union[str, t.Sequence[t.Any]],
        option_string: str = None,
    ) -> None:
        setattr(namespace, self.dest, values)
        self._specified = True

    @property
    def specified(self) -> bool:
        return self._specified


class StoreConstAction(StoreAction):
    def __init__(
        self,
        option_strings: t.Sequence[str],
        dest: str,
        const: t.Any,
        nargs: t.Union[int, str] = 0,
        **kwargs: dict,
    ) -> None:
        nargs = 0
        super().__init__(option_strings, dest, nargs=nargs, const=const, **kwargs)

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: t.Union[str, t.Sequence[t.Any]],
        option_string: str = ...,
    ) -> None:
        return super().__call__(parser, namespace, self.const, option_string)


class StoreTrueAction(StoreConstAction):
    def __init__(self, option_strings: t.Sequence[str], dest: str, **kwargs: dict) -> None:
        super().__init__(
            option_strings,
            dest,
            const=True,
            **kwargs,
        )


class StoreFalseAction(StoreConstAction):
    def __init__(self, option_strings: t.Sequence[str], dest: str, **kwargs: dict) -> None:
        super().__init__(
            option_strings,
            dest,
            const=False,
            **kwargs,
        )


class AppendAction(StoreAction):
    def __init__(
        self,
        option_strings: t.Sequence[str],
        dest: str,
        nargs: t.Union[int, str, None],
        const: t.Any = None,
        **kargs: dict,
    ) -> None:
        if nargs == 0:
            raise ValueError("nargs for append actions must be > 0; if arg is optional, use const")
        if const is not None and nargs != OPTIONAL:
            raise ValueError("nargs must be %r to supply const" % OPTIONAL)
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            **kargs,
        )

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: t.Union[str, t.Sequence[t.Any]],
        option_string: str = ...,
    ) -> None:
        items = getattr(namespace, self.dest, None)
        items = list(_copy_items(items))
        items.extend(values)
        super().__call__(parser, namespace, items, option_string)

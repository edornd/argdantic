import sys
from typing import Any, List, Optional

from argdantic import Parser


class Result:
    def __init__(
        self,
        return_value: Any,
        exception: Optional[Exception],
        exc_info: Optional[Any],
    ) -> None:
        self.return_value = return_value
        self.exception = exception
        self.exc_info = exc_info


class CLIRunner:
    def __init__(self, catch_exceptions: bool = True) -> None:
        self.catch_exceptions = catch_exceptions

    def invoke(self, cli: Parser, args: List[Any]) -> Any:
        command = cli._build_entrypoint()
        exception = None
        exc_info = None
        try:
            command(args=args)
        # avoid early exit on help invocation
        except SystemExit:
            pass
        # avoid early exit on exceptions
        except Exception as e:
            if not self.catch_exceptions:
                raise e
            exception = e
            exc_info = sys.exc_info()
        return Result(
            return_value=None,
            exception=exception,
            exc_info=exc_info,
        )

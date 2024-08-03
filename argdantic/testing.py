import sys
from argparse import Namespace
from typing import Any, Optional

from argdantic import ArgParser


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

    def invoke(self, cli: ArgParser, args: Optional[Namespace]) -> Any:
        exception = None
        exc_info = None
        result = None
        try:
            result = cli(args=args)
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
            return_value=result,
            exception=exception,
            exc_info=exc_info,
        )

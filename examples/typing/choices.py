from enum import Enum, IntEnum
from typing import Literal

from argdantic import ArgParser

cli = ArgParser()


class ToolEnum(Enum):
    hammer = "Hammer"
    screwdriver = "Screwdriver"


class HTTPEnum(IntEnum):
    ok = 200
    not_found = 404
    internal_error = 500


@cli.command()
def run(
    a: Literal["one", "two"] = "two",
    b: Literal[1, 2] = 2,
    c: Literal[True, False] = True,
    d: ToolEnum = ToolEnum.hammer,
    e: HTTPEnum = HTTPEnum.not_found,
):
    print(f"a: {a}")
    print(f"b: {b}")
    print(f"c: {c}")
    print(f"d: {d}")
    print(f"e: {e}")


if __name__ == "__main__":
    cli()

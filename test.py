from enum import Enum
from typing import Deque, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

from pydantic import BaseModel

from argdantic import Parser


class Animals(Enum):
    dog = 1
    cat = 2
    duck = 3


class Submodule(BaseModel):
    name: str
    surname: str


class Config(BaseModel):
    simple_list: list = None
    list_of_ints: List[int] = None

    simple_tuple: tuple = None
    tuple_of_different_types: Tuple[int, float, str, bool] = None

    simple_dict: dict = None
    dict_str_float: Dict[str, float] = None

    simple_set: set = None
    set_bytes: Set[bytes] = None
    frozen_set: FrozenSet[int] = None
    none_or_str: Optional[str] = None
    sequence_of_ints: Sequence[int] = None
    # compound: Dict[str, List[Set[int]]] = None
    deque: Deque[int] = None
    animal: Animals = Animals.cat


cli = Parser()


@cli.command()
def hello(cfg: Config = Config(), a: int = 1, b: int = 2):
    print(cfg)
    print(a, b)


if __name__ == "__main__":
    cli()

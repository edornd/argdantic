from typing import Deque, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

from argdantic import ArgParser

cli = ArgParser()


@cli.command()
def run(
    simple_list: list,
    list_of_ints: List[int],
    simple_tuple: tuple,
    multi_typed_tuple: Tuple[int, float, str, bool],
    simple_dict: dict,
    dict_str_float: Dict[str, float],
    simple_set: set,
    set_bytes: Set[bytes],
    frozen_set: FrozenSet[int],
    none_or_str: Optional[str],
    sequence_of_ints: Sequence[int],
    compound: Dict[str, List[Set[int]]],
    deque: Deque[int],
):
    print(f"simple_list: {simple_list}")
    print(f"list_of_ints: {list_of_ints}")
    print(f"simple_tuple: {simple_tuple}")
    print(f"multi_typed_tuple: {multi_typed_tuple}")
    print(f"simple_dict: {simple_dict}")
    print(f"dict_str_float: {dict_str_float}")
    print(f"simple_set: {simple_set}")
    print(f"set_bytes: {set_bytes}")
    print(f"frozen_set: {frozen_set}")
    print(f"none_or_str: {none_or_str}")
    print(f"sequence_of_ints: {sequence_of_ints}")
    print(f"compound: {compound}")
    print(f"deque: {deque}")


if __name__ == "__main__":
    cli()

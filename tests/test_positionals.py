from typing import Any

import pytest
from conftest import Run
from pydantic import BaseModel

from argdantic import App, Arg


class Optim(BaseModel):
    lr: float = 0.1


def test_required_positional_reaches_the_command(run: Run) -> None:
    app = App("cli")

    @app.command
    def copy(src: Arg[str], force: bool = False) -> str:
        return src

    result = run(app, ["copy", "a.txt"])

    assert result.code == 0
    assert result.json() == "a.txt"


def test_positional_with_default_is_optional(run: Run) -> None:
    app = App("cli")

    @app.command
    def show(name: Arg[str] = "all") -> str:
        return name

    result = run(app, ["show"])

    assert result.code == 0
    assert result.json() == "all"


@pytest.mark.parametrize("values", [["a"], ["a", "b", "c"]])
def test_list_positional_takes_one_or_more(run: Run, values: list[str]) -> None:
    app = App("cli")

    @app.command
    def cat(paths: Arg[list[str]]) -> list[str]:
        return paths

    result = run(app, ["cat", *values])

    assert result.code == 0
    assert result.json() == values


def test_list_positional_with_empty_default_takes_none(run: Run) -> None:
    app = App("cli")

    @app.command
    def cat(paths: Arg[list[str]] = []) -> list[str]:  # noqa: B006
        return paths

    result = run(app, ["cat"])

    assert result.code == 0
    assert result.json() == []


@pytest.mark.parametrize(
    "argv",
    [
        ["convert", "a", "b", "--out", "z"],
        ["convert", "--out", "z", "a", "b"],
        ["convert", "a", "--out", "z", "b"],
    ],
)
def test_positionals_and_flags_mix(run: Run, argv: list[str]) -> None:
    app = App("cli")

    @app.command
    def convert(src: Arg[str], dst: Arg[str], out: str) -> list[str]:
        return [src, dst, out]

    result = run(app, argv)

    assert result.code == 0
    assert result.json() == ["a", "b", "z"]


def test_missing_positional_is_a_missing_field_error(run: Run) -> None:
    app = App("cli")

    @app.command
    def copy(src_dir: Arg[str]) -> None:
        pass

    result = run(app, ["copy"])

    assert result.code == 2
    assert result.json()["field_errors"] == [{"path": "src_dir", "code": "missing", "message": "Field required"}]


def test_two_missing_positionals_come_in_one_rejection(run: Run) -> None:
    app = App("cli")

    @app.command
    def convert(src: Arg[str], paths: Arg[list[str]]) -> None:
        pass

    result = run(app, ["convert"])

    assert result.code == 2
    assert [error["path"] for error in result.json()["field_errors"]] == ["src", "paths"]


def test_invalid_positional_has_source_positional(run: Run) -> None:
    app = App("cli")

    @app.command
    def repeat(times: Arg[int]) -> None:
        pass

    result = run(app, ["repeat", "many"])

    error = result.json()["field_errors"][0]
    assert result.code == 2
    assert (error["path"], error["code"], error["received"], error["source"]) == (
        "times",
        "int_parsing",
        "many",
        "positional",
    )


def test_negative_number_reaches_a_positional(run: Run) -> None:
    app = App("cli")

    @app.command
    def shift(by: Arg[int]) -> int:
        return by

    result = run(app, ["shift", "-3"])

    assert result.code == 0
    assert result.json() == -3


def test_double_dash_passes_a_flag_like_value(run: Run) -> None:
    app = App("cli")

    @app.command
    def echo(text: Arg[str]) -> str:
        return text

    result = run(app, ["echo", "--", "-weird"])

    assert result.code == 0
    assert result.json() == "-weird"


def test_help_shows_positionals_with_descriptions(run: Run) -> None:
    app = App("cli")

    @app.command
    def copy(src_dir: Arg[str]) -> None:
        """
        Copy a folder.

        Args:
            src_dir: the folder to copy.
        """

    result = run(app, ["copy", "--help"])

    assert result.code == 0
    assert "SRC-DIR" in result.out
    assert "the folder to copy." in result.out


def test_positional_after_list_positional_raises() -> None:
    app = App("cli")

    with pytest.raises(ValueError, match="'paths'"):

        @app.command
        def convert(paths: Arg[list[str]], out: Arg[str]) -> None:
            pass


def test_model_positional_raises() -> None:
    app = App("cli")

    with pytest.raises(TypeError, match="'cfg'"):

        @app.command
        def train(cfg: Arg[Optim]) -> None:
            pass


def test_positional_only_parameter_is_passed_by_place(run: Run) -> None:
    app = App("cli")

    @app.command
    def move(src: str, dst: str, /, force: bool = False) -> list[Any]:
        return [src, dst, force]

    result = run(app, ["move", "a", "b", "--force"])

    assert result.code == 0
    assert result.json() == ["a", "b", True]


def test_star_args_are_unpacked(run: Run) -> None:
    app = App("cli")

    @app.command
    def cat(*paths: str) -> list[str]:
        return list(paths)

    result = run(app, ["cat", "a", "b"])

    assert result.code == 0
    assert result.json() == ["a", "b"]


def test_star_args_need_one_value(run: Run) -> None:
    app = App("cli")

    @app.command
    def cat(*paths: str) -> None:
        pass

    result = run(app, ["cat"])

    assert result.code == 2
    assert result.json()["field_errors"] == [{"path": "paths", "code": "missing", "message": "Field required"}]


def test_optional_positional_only_before_star_args(run: Run) -> None:
    app = App("cli")

    @app.command
    def pack(mode: str = "fast", /, *paths: str) -> list[Any]:
        return [mode, list(paths)]

    result = run(app, ["pack", "a", "b"])

    assert result.code == 0
    assert result.json() == ["a", ["b"]]


def test_star_args_docstring_entry_shows_in_help(run: Run) -> None:
    app = App("cli")

    @app.command
    def cat(*paths: str) -> None:
        """
        Print files.

        Args:
            *paths: the files to read.
        """

    result = run(app, ["cat", "--help"])

    assert result.code == 0
    assert "PATHS" in result.out
    assert "the files to read." in result.out


def test_positional_only_list_before_star_args_raises() -> None:
    app = App("cli")

    with pytest.raises(ValueError, match="'paths'"):

        @app.command
        def bad(paths: Arg[list[str]], /, *rest: str) -> None:
            pass

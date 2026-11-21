import functools
from datetime import date
from pathlib import Path
from typing import Annotated, Any

import pytest
from conftest import Run
from pydantic import BaseModel, Field

from argdantic import App
from argdantic.app import CommandSpec, SafetyHints


class Note(BaseModel):
    title: str
    created: date
    path: Path


class NoteWithOwner(Note):
    owner: str


def test_command_prints_result_as_json(run: Run) -> None:
    app = App("calc")

    @app.command
    def add_numbers(first_value: int, second_value: int = 10) -> dict[str, int]:
        return {"sum": first_value + second_value}

    result = run(app, ["add-numbers", "--first-value", "3", "--second-value", "4"])

    assert result.code == 0
    assert result.json() == {"sum": 7}


@pytest.mark.parametrize(
    ("argv", "expected"),
    [([], False), (["--dry-run"], True), (["--dry-run", "--no-dry-run"], False)],
)
def test_bool_parameter_gets_on_and_off_flags(argv: list[str], expected: bool, run: Run) -> None:
    app = App("notes")

    @app.command
    def delete(dry_run: bool = False) -> bool:
        return dry_run

    result = run(app, ["delete", *argv])

    assert result.code == 0
    assert result.json() is expected


def test_none_result_prints_nothing(run: Run) -> None:
    app = App("notes")
    calls = []

    @app.command
    def sync() -> None:
        calls.append("sync")

    assert run(app, ["sync"]) == (0, "", "")
    assert calls == ["sync"]


def test_missing_return_annotation_prints_result_as_any(run: Run) -> None:
    app = App("notes")

    @app.command
    def sync():
        pass

    @app.command
    def count():
        return {"notes": 3}

    assert run(app, ["sync"]) == (0, "", "")
    assert run(app, ["count"]).json() == {"notes": 3}


def test_result_is_dumped_through_the_return_annotation(run: Run) -> None:
    app = App("notes")

    @app.command
    def show(title: str) -> Note:
        return NoteWithOwner(title=title, created=date(2025, 1, 2), path=Path("notes/a.md"), owner="ada")

    result = run(app, ["show", "--title", "a"])

    assert result.code == 0
    assert result.json() == {"title": "a", "created": "2025-01-02", "path": "notes/a.md"}


def test_env_var_with_a_field_name_is_ignored(monkeypatch: pytest.MonkeyPatch, run: Run) -> None:
    monkeypatch.setenv("TITLE", "from-env")
    monkeypatch.setenv("title", "from-env")
    app = App("notes")

    @app.command
    def add(title: str = "untitled") -> str:
        return title

    result = run(app, ["add"])

    assert result.code == 0
    assert result.json() == "untitled"


def test_command_with_parentheses_stores_its_safety_hints(run: Run) -> None:
    app = App("notes")

    @app.command()
    def list_notes() -> list[str]:
        return ["a"]

    @app.command(destructive=True, idempotent=True)
    def delete_note(title: str) -> str:
        return f"deleted {title}"

    assert run(app, ["list-notes"]) == (0, '["a"]\n', "")
    assert run(app, ["delete-note", "--title", "a"]) == (0, '"deleted a"\n', "")
    hints = {name: spec.hints for name, spec in app._children.items() if isinstance(spec, CommandSpec)}
    assert hints == {"list-notes": SafetyHints(), "delete-note": SafetyHints(destructive=True, idempotent=True)}


def test_nameless_callable_cannot_be_a_command() -> None:
    app = App("calc")

    def add(first: int, second: int) -> int:
        return first + second

    with pytest.raises(TypeError, match="named function"):
        app.command(functools.partial(add, 1))


def test_help_shows_docstring_and_field_descriptions(run: Run) -> None:
    app = App("notes")

    @app.command
    def add(
        title: str,
        priority: Annotated[int, Field(description="higher comes first")] = 1,
        pinned: bool = False,
    ) -> None:
        """
        Add a note.

        Notes are unpinned unless told otherwise.

        Args:
            title: the note's title.
            pinned: keep the note
                at the top of the list.
        """

    result = run(app, ["add", "--help"])

    assert result.code == 0
    assert "Add a note." in result.out
    assert "unpinned" not in result.out
    assert "the note's title." in result.out
    assert "higher comes first" in result.out
    assert "keep the note at the top of the list." in " ".join(result.out.split())


def test_field_description_wins_over_docstring(run: Run) -> None:
    app = App("notes")

    @app.command
    def add(priority: Annotated[int, Field(description="from the field")] = 1) -> None:
        """
        Add a note.

        Args:
            priority: from the docstring.
        """

    result = run(app, ["add", "--help"])

    assert "from the field" in result.out
    assert "from the docstring" not in result.out


def _field_default_app() -> App:
    app = App("notes")

    @app.command
    def show(title: str = Field(min_length=1), count: int = Field(1, ge=0)) -> dict[str, Any]:
        return {"title": title, "count": count}

    return app


def test_field_default_gives_its_default_value(run: Run) -> None:
    result = run(_field_default_app(), ["show", "--title", "milk"])

    assert result.code == 0
    assert result.json() == {"title": "milk", "count": 1}


@pytest.mark.parametrize(
    ("argv", "path", "code"),
    [
        (["show", "--title", "milk", "--count", "-5"], "count", "greater_than_equal"),
        (["show", "--title", ""], "title", "string_too_short"),
        (["show"], "title", "missing"),
    ],
)
def test_field_default_applies_its_constraints(argv: list[str], path: str, code: str, run: Run) -> None:
    result = run(_field_default_app(), argv)

    assert result.code == 2
    assert [(item["path"], item["code"]) for item in result.json()["field_errors"]] == [(path, code)]


def test_field_default_description_wins_over_docstring(run: Run) -> None:
    app = App("notes")

    @app.command
    def add(priority: int = Field(1, description="from the field"), limit: int = Field(10, ge=1)) -> None:
        """
        Add a note.

        Args:
            priority: from the docstring.
            limit: most notes to keep.
        """

    result = run(app, ["add", "--help"])

    assert "from the field" in result.out
    assert "from the docstring" not in result.out
    assert "most notes to keep." in result.out

import re

import pytest
from conftest import Run

from argdantic import App


def test_command_in_a_group_runs_at_any_depth(cli_app: App, calls: list[str], run: Run) -> None:
    added = run(cli_app, ["notes", "add", "--title", "milk"])
    renamed = run(cli_app, ["notes", "tags", "rename", "--old", "a", "--new", "b"])

    assert (added.code, added.json(), calls) == (0, "milk", ["milk"])
    assert (renamed.code, renamed.json()) == (0, "b")


def test_mounted_app_runs_alone(run: Run) -> None:
    notes = App("notes")

    @notes.command
    def add(title: str) -> str:
        return title

    App("cli").add(notes)

    result = run(notes, ["add", "--title", "milk"])

    assert (result.code, result.json()) == (0, "milk")


def test_command_registered_after_add_is_reachable(run: Run) -> None:
    cli = App("cli")
    notes = App("notes")
    cli.add(notes)

    @notes.command
    def list_notes() -> list[str]:
        return ["milk"]

    result = run(cli, ["notes", "list-notes"])

    assert (result.code, result.json()) == (0, ["milk"])


def test_app_mounted_under_two_parents_runs_through_both(run: Run) -> None:
    tags = App("tags")

    @tags.command
    def rename(old: str, new: str) -> str:
        return new

    notes = App("notes")
    notes.add(tags)
    cli = App("cli")
    cli.add(notes)
    cli.add(tags)

    direct = run(cli, ["tags", "rename", "--old", "a", "--new", "b"])
    nested = run(cli, ["notes", "tags", "rename", "--old", "a", "--new", "c"])

    assert (direct.code, direct.json()) == (0, "b")
    assert (nested.code, nested.json()) == (0, "c")


def test_root_help_lists_commands_and_groups_with_their_summaries(cli_app: App, run: Run) -> None:
    result = run(cli_app, ["--help"])

    assert result.code == 0
    for text in ("Manage notes.", "notes", "Work with notes.", "sync", "Sync everything."):
        assert text in result.out
    assert "Notes are plain text." not in result.out


def test_triple_quoted_group_description_gives_a_summary(run: Run) -> None:
    notes = App(
        "notes",
        description="""
        Work with notes.

        Notes are plain text.
        """,
    )
    cli = App("cli")
    cli.add(notes)

    result = run(cli, ["--help"])

    assert result.code == 0
    assert re.search(r"^\s+notes\s+Work with notes\.$", result.out, re.MULTILINE)


def test_group_help_lists_its_commands_and_groups(cli_app: App, run: Run) -> None:
    result = run(cli_app, ["notes", "--help"])

    assert result.code == 0
    for text in ("cli notes", "Notes are plain text.", "add", "Add a note.", "tags", "Manage tags."):
        assert text in result.out
    assert "Sync everything." not in result.out


def test_command_help_works_inside_a_group(cli_app: App, run: Run) -> None:
    result = run(cli_app, ["notes", "add", "--help"])

    assert result.code == 0
    assert "Add a note." in result.out
    assert "--title" in result.out


def test_unknown_flag_in_a_group_lists_the_command_flags(cli_app: App, calls: list[str], run: Run) -> None:
    result = run(cli_app, ["notes", "add", "--title", "x", "--colour", "red"])

    assert result.code == 2
    assert calls == []
    assert result.json()["field_errors"] == [
        {
            "path": "colour",
            "code": "unknown_flag",
            "message": "unknown flag --colour",
            "received": "--colour",
            "allowed": ["--title"],
            "source": "flag",
        }
    ]


def test_duplicate_command_name_raises() -> None:
    app = App("notes")

    def add() -> None: ...

    app.command(add)

    with pytest.raises(ValueError, match="'add'"):
        app.command(add)


@pytest.mark.parametrize("group_first", [True, False])
def test_command_and_group_with_one_name_raise_in_either_order(group_first: bool) -> None:
    cli = App("cli")

    def notes() -> None: ...

    mount_group, register_command = (lambda: cli.add(App("notes"))), (lambda: cli.command(notes))
    first, second = (mount_group, register_command) if group_first else (register_command, mount_group)
    first()

    with pytest.raises(ValueError, match="'notes'"):
        second()


def test_mounting_an_app_on_itself_raises() -> None:
    cli = App("cli")

    with pytest.raises(ValueError, match="cycle"):
        cli.add(cli)


def test_indirect_cycle_raises() -> None:
    cli, notes, tags = App("cli"), App("notes"), App("tags")
    cli.add(notes)
    notes.add(tags)

    with pytest.raises(ValueError, match="cycle"):
        tags.add(cli)


def test_add_with_a_function_raises_type_error() -> None:
    cli = App("cli")

    def sync() -> None: ...

    with pytest.raises(TypeError, match=r"@app\.command"):
        cli.add(sync)  # ty: ignore[invalid-argument-type]


def test_same_command_name_in_two_groups_is_allowed(run: Run) -> None:
    cli, notes, runs = App("cli"), App("notes"), App("runs")
    for group in (notes, runs):

        @group.command
        def add() -> None: ...

        cli.add(group)

    assert run(cli, ["notes", "add"]).code == 0
    assert run(cli, ["runs", "add"]).code == 0

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

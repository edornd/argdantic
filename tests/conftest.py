import json
from collections.abc import Callable
from typing import Any, NamedTuple

import pytest

from argdantic import App


class Outcome(NamedTuple):
    code: int
    out: str
    err: str

    def json(self) -> Any:
        return json.loads(self.out)


Run = Callable[[App, list[str]], Outcome]
RunRaising = Callable[[BaseException], Outcome]


@pytest.fixture
def run(capsys: pytest.CaptureFixture[str]) -> Run:
    """Run an app on argv and capture its exit code and output."""

    def run_app(app: App, argv: list[str]) -> Outcome:
        with pytest.raises(SystemExit) as exc:
            app(argv)
        code = exc.value.code
        assert isinstance(code, int)
        out, err = capsys.readouterr()
        return Outcome(code, out, err)

    return run_app


@pytest.fixture
def calls() -> list[str]:
    return []


@pytest.fixture
def notes_app(calls: list[str]) -> App:
    """A one-command app whose `add` records each call's title in `calls`."""
    app = App("notes")

    @app.command
    def add(title: str = "untitled", priority: int = 1, pinned: bool = False) -> None:
        calls.append(title)

    return app


@pytest.fixture
def run_raising(run: Run) -> RunRaising:
    """Run a one-command app whose `add` raises the given exception."""

    def run_with(error: BaseException) -> Outcome:
        app = App("notes")

        @app.command
        def add() -> None:
            raise error

        return run(app, ["add"])

    return run_with


@pytest.fixture
def cli_app(calls: list[str]) -> App:
    """`cli` with a group `notes` (command `add`, nested group `tags`) and a root command `sync`."""
    tags = App("tags", description="Manage tags.")

    @tags.command
    def rename(old: str, new: str) -> str:
        """Rename a tag."""
        return new

    notes = App("notes", description="Work with notes.\n\nNotes are plain text.")

    @notes.command
    def add(title: str) -> str:
        """Add a note."""
        calls.append(title)
        return title

    notes.add(tags)
    cli = App("cli", description="Manage notes.")
    cli.add(notes)

    @cli.command
    def sync() -> None:
        """Sync everything."""

    return cli

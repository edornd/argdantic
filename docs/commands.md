# Commands

`@app.command` registers a function as a command. The command name is the function name in kebab case, so `add_note` is called as `add-note`.

## Parameters become flags

Each parameter becomes a flag named after it in kebab case: `max_items` becomes `--max-items`. A one-letter parameter gets a short flag: `n` becomes `-n`. pydantic validates every value against the parameter's type hint. Scalar types such as `int`, `Path`, `date`, `Literal` and enums work as flags.

- A parameter without a default is required.
- A parameter with a default is optional.
- A `bool` parameter gets a pair of flags, `--pinned` and `--no-pinned`.

pydantic's `Field` adds constraints and a description. Put it in an `Annotated` type hint or use it as the default, as in a pydantic model:

```python
@app.command
def add(
    title: Annotated[str, Field(min_length=1)],
    priority: int = Field(1, ge=0, description="higher comes first"),
) -> None:
    """Add a note."""
```

Flags must be spelled in full. argdantic does not expand a prefix such as `--ti` to `--title`.

Input comes only from flags and the defaults in code. argdantic does not read environment variables or `.env` files.

## Help text

The first line of the docstring is the command's summary, shown in `--help` for the CLI and for the command. Parameter descriptions come from the `Args:` section of a Google-style docstring, or from `Field(description=...)`. When both are set, the `Field` wins.

## Groups

A group is an `App` mounted on another `App` with `add`. The group's name is the word that selects it on the command line.

```python
from argdantic import App

notes = App("notes", description="Work with notes.")


@notes.command
def add(title: str) -> str:
    """Add a note."""
    return title


cli = App("cli", description="Manage notes.")
cli.add(notes)

if __name__ == "__main__":
    cli()
```

```console
$ python cli.py notes add --title milk
"milk"
```

- Groups nest to any depth. Mount one group on another with `add`.
- A mounted `App` still runs alone, so `notes(["add", "--title", "milk"])` works, and a group can live in its own module.
- `add` mounts the `App` itself, not a copy. A command registered on `notes` after `cli.add(notes)` is still available through `cli`.
- `description` is the help text of an `App`. `python cli.py --help` shows the description of `cli`, then each command and group with its summary. The summary of a group is the first line of its description. `python cli.py notes --help` shows the full description of `notes`.
- The names at one level are unique. Two commands with the same name, a command and a group with the same name, or an `App` mounted below itself raise an error when the module is imported.

## Results

The return type hint decides how the result is serialised. With no return type hint, argdantic treats the result as `Any`. A pydantic model, a dataclass, a dict or a plain value prints as one JSON document on stdout. A command that returns `None` prints nothing. Exit code 0 means success.

## Safety hints

`@app.command` takes four optional hints that describe what a command does: `read_only`, `destructive`, `idempotent` and `open_world`. They follow the tool annotations of the Model Context Protocol.

```python
@app.command(destructive=True)
def remove(title: str) -> None:
    """Remove notes by title."""
```

argdantic stores the hints but does not act on them yet.

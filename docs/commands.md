# Commands

`@app.command` registers a function as a command. The command name is the function name in kebab case, so `add_note` is called as `add-note`.

## Parameters become flags

Each parameter becomes a flag named after it in kebab case: `max_items` becomes `--max-items`. A one-letter parameter gets a short flag: `n` becomes `-n`. pydantic validates every value against the parameter's type hint. Scalar types such as `int`, `Path`, `date`, `Literal` and enums work as flags.

- A parameter without a default is required.
- A parameter with a default is optional.
- A `bool` parameter gets a pair of flags, `--pinned` and `--no-pinned`.

Flags must be spelled in full. argdantic does not expand a prefix such as `--ti` to `--title`.

Input comes only from flags and the defaults in code. argdantic does not read environment variables or `.env` files.

## Help text

The first line of the docstring is the command's summary, shown in `--help` for the CLI and for the command. Parameter descriptions come from the `Args:` section of a Google-style docstring, or from `Field(description=...)` in an `Annotated` type hint.

## Results

The return type hint decides how the result is serialised. A pydantic model, a dataclass, a dict or a plain value prints as one JSON document on stdout. A command that returns `None` prints nothing. Exit code 0 means success.

## Safety hints

`@app.command` takes four optional hints that describe what a command does: `read_only`, `destructive`, `idempotent` and `open_world`. They follow the tool annotations of the Model Context Protocol.

```python
@app.command(destructive=True)
def remove(title: str) -> None:
    """Remove notes by title."""
```

argdantic stores the hints but does not act on them yet.

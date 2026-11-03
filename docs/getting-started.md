# Getting started

A CLI is an `App` with one or more commands. Save this as `notes.py`:

```python
from pydantic import BaseModel

from argdantic import App

app = App("notes")


class Note(BaseModel):
    title: str
    priority: int


@app.command
def add(title: str, priority: int = 1) -> Note:
    """Add a note.

    Args:
        title: what the note says.
        priority: higher comes first.
    """
    return Note(title=title, priority=priority)


if __name__ == "__main__":
    app()
```

Run the command by name. The result is the function's return value, printed as JSON on stdout:

```console
$ python notes.py add --title milk --priority 2
{"title": "milk", "priority": 2}
```

The docstring becomes the help text:

```console
$ python notes.py add --help
usage: notes add [-h] [--title str] [--priority int]

Add a note.

options:
  -h, --help      show this help message and exit
  --title str     what the note says. (required)
  --priority int  higher comes first. (default: 1)
```

A wrong value prints an error instead of a result, and exits with code 2:

```console
$ python notes.py add --title milk --priority high
{"code": "VALIDATION_ERROR", "message": "invalid input", "retryable": false, "fieldErrors": [{"path": "priority", "code": "int_parsing", "message": "Input should be a valid integer, unable to parse string as an integer", "received": "high", "source": "flag"}]}
```

`app()` reads `sys.argv`. To run it on a fixed list, pass it in: `app(["add", "--title", "milk"])`. Either way, `app()` exits the process with the run's exit code.

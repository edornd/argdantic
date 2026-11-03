# argdantic

argdantic builds a command line interface from typed Python functions. You write one function with type hints, and argdantic turns its parameters into flags, validates the input with pydantic, and prints the return value as JSON. People at a terminal and programs, including AI agents, call the same command.

When a call fails, the output is a structured error with a stable code, the field that was wrong and the values it accepts, and the exit code tells success and failure apart. A program can fix its call from the error alone.

!!! warning "Pre-alpha"
    This documents argdantic 2, which is under development on the `v2` branch. The API can change between commits. For argdantic 1.x, see the [PyPI release](https://pypi.org/project/argdantic/).

## Install

argdantic 2 needs Python 3.11 or later and is not on PyPI yet. Install it from the `v2` branch:

```bash
uv add "argdantic @ git+https://github.com/edornd/argdantic@v2"
```

## Next

- [Getting started](getting-started.md) builds a first CLI.
- [Commands](commands.md) shows how parameters become flags.
- [Errors and exit codes](errors.md) describes what a failed call prints.

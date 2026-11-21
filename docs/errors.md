# Errors and exit codes

A run prints exactly one JSON document on stdout: the result when it succeeds, an error when it fails. The exit code tells the two apart.

| Exit code | Meaning |
| --- | --- |
| 0 | The command ran and printed its result. |
| 1 | The command failed while running. |
| 2 | argdantic rejected the input, and the command did not run. |

## The error object

| Key | Type | Meaning |
| --- | --- | --- |
| `code` | string | A stable SCREAMING_CASE name that programs match on. |
| `message` | string | One line for the reader. The wording may change; do not match on it. |
| `retryable` | bool | Whether the same call may succeed if tried again. |
| `hint` | string, optional | What the caller can do about it. |
| `field_errors` | list, optional | One entry per problem with an input value or a command name. |

Each field error has these keys:

| Key | Type | Meaning |
| --- | --- | --- |
| `path` | string | The dotted name of the input, such as `priority`, or `command` for a command name. |
| `code` | string | The error type: pydantic's own (`missing`, `int_parsing`, `literal_error`), or `unknown_flag`, `unexpected_argument` and `unknown_command`. |
| `message` | string | One line for the reader. |
| `expected` | string, optional | What the input should look like. |
| `received` | any, optional | The value given. Omitted when the value is or holds a secret, see [Secrets](#secrets). |
| `allowed` | list, optional | The accepted values: the choices of a `Literal` or an enum, the valid flags for an unknown flag, or the commands and groups for a command name. |
| `source` | string, optional | Where the value came from. Currently always `flag`. |

## Rejected input

Invalid input gives `VALIDATION_ERROR` and exit code 2, with every problem listed at once. An unknown flag lists the flags the command accepts:

```console
$ python notes.py add --title milk --colour red
{"code": "VALIDATION_ERROR", "message": "invalid input", "retryable": false, "field_errors": [{"path": "colour", "code": "unknown_flag", "message": "unknown flag --colour", "received": "--colour", "allowed": ["--title", "--priority"], "source": "flag"}]}
```

A value outside a `Literal` lists the accepted values:

```console
$ python notes.py remove --title milk --scope everyone
{"code": "VALIDATION_ERROR", "message": "invalid input", "retryable": false, "field_errors": [{"path": "scope", "code": "literal_error", "message": "Input should be 'mine' or 'all'", "expected": "'mine' or 'all'", "received": "everyone", "allowed": ["mine", "all"], "source": "flag"}]}
```

## Unknown commands

A command name that does not exist gives `COMMAND_NOT_FOUND` and exit code 2. The field error lists the commands and groups at that level of the CLI in `allowed`:

```console
$ python cli.py notes ad
{"code": "COMMAND_NOT_FOUND", "message": "unknown command 'ad' in 'cli notes'", "retryable": false, "field_errors": [{"path": "command", "code": "unknown_command", "message": "unknown command ad", "received": "ad", "allowed": ["add"], "source": "flag"}]}
```

A missing command name gives the same error, with the field error code `missing` and no `received`. The `cli.py` above is the example in [Groups](commands.md#groups).

## Secrets

A field error has no `received` when the rejected value is or holds a `SecretStr`, `SecretBytes` or `Secret`, subclasses included. A model with a password field whose own validator fails has no `received`, because it would echo the password.

argdantic also omits `received` when it can't trace the rejected value to a type, such as a field inside a discriminated union.

A custom type that validates as a secret through `__get_pydantic_core_schema__` is not detected. Subclass `SecretStr` or `Secret` instead.

## Failures in a command

A command reports an expected failure by raising `CommandError` with its own code:

```python
from argdantic import CommandError


@app.command
def remove(title: str) -> None:
    """Remove notes by title."""
    raise CommandError("NOTE_NOT_FOUND", f"no note titled {title!r}", hint="list notes to see the titles")
```

```console
$ python notes.py remove --title milk
{"code": "NOTE_NOT_FOUND", "message": "no note titled 'milk'", "retryable": false, "hint": "list notes to see the titles"}
```

The code must be SCREAMING_CASE. The exit code defaults to 1 and can be set with `exit_code=`, except to 0 or 2, which are reserved for success and rejected input.

Any other exception gives `UNKNOWN` with exit code 1. Set `ARGD_DEBUG=1` to also print its traceback on stderr.

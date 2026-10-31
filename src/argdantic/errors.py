"""Error objects, exit codes and their rendering. Only `CommandError` is exported from `argdantic`."""

import enum
import json
import os
import re
import sys
import traceback
import types
from typing import Annotated, Any, Literal, NoReturn, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, SecretBytes, SecretStr, TypeAdapter, ValidationError, field_validator

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REJECTED = 2

# Bench-only switch for the structured-vs-string errors ablation. Not public API. When True, errors print as the
# plain text pydantic and argparse produce on their own (or the exception text), with the same exit codes.
_string_errors = False

_SCREAMING_CASE = re.compile(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)*")


class FieldError(BaseModel):
    """One problem with one input value."""

    model_config = ConfigDict(frozen=True)

    path: str
    code: str
    message: str
    expected: str | None = None
    received: Any = None
    allowed: list[Any] | None = None
    source: str | None = None


class ErrorReport(BaseModel):
    """A failed run: the error object plus the exit code that goes with it."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    retryable: bool = False
    hint: str | None = None
    field_errors: list[FieldError] | None = Field(default=None, serialization_alias="fieldErrors")
    exit_code: int = Field(exclude=True)
    # What pydantic or argparse would print on their own. Only the string-errors ablation shows it.
    native_text: str | None = Field(default=None, exclude=True)

    @field_validator("message")
    @classmethod
    def _first_line(cls, message: str) -> str:
        return message.strip().partition("\n")[0]


class CommandError(Exception):
    """A failure the command reports on purpose, rendered with its own code instead of UNKNOWN.

    Args:
        code: a stable SCREAMING_CASE name that programs match on.
        message: one short line for the reader. Only the first line is shown.
        retryable: whether the same call may succeed if tried again.
        hint: what the caller can do about it.
        exit_code: the process exit code.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        hint: str | None = None,
        exit_code: int = EXIT_FAILED,
    ) -> None:
        if not _SCREAMING_CASE.fullmatch(code):
            raise ValueError(f"error code must be SCREAMING_CASE, got {code!r}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.hint = hint
        self.exit_code = exit_code

    @property
    def report(self) -> ErrorReport:
        return ErrorReport(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            hint=self.hint,
            exit_code=self.exit_code,
        )


class InputRejected(Exception):
    """Raised inside a run when the input is rejected, before the command is called."""

    def __init__(
        self,
        message: str,
        field_errors: list[FieldError] | None = None,
        native_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.report = ErrorReport(
            code="VALIDATION_ERROR",
            message=message,
            field_errors=field_errors or None,
            exit_code=EXIT_REJECTED,
            native_text=native_text,
        )


def rejected_input(
    model: type[BaseModel],
    leftovers: list[str],
    valid_flags: list[str],
    error: ValidationError | None = None,
) -> InputRejected:
    """Every problem with a command's input as one rejection: leftover tokens first, then pydantic's errors."""
    field_errors = _leftover_errors(leftovers, valid_flags)
    native_texts = [f"unrecognized arguments: {' '.join(leftovers)}"] if leftovers else []
    if error is not None:
        field_errors += [_field_error(model, item) for item in error.errors()]
        native_texts.append(str(error))
    return InputRejected("invalid input", field_errors, "\n".join(native_texts))


def _field_error(model: type[BaseModel], error: Any) -> FieldError:
    loc = error["loc"]
    if error["type"] == "missing":
        # pydantic puts the whole parent input in `input` here, and no value came from any source.
        return FieldError(path=_dotted(loc), code="missing", message=error["msg"])
    annotation = _annotation_at(model, loc)
    return FieldError(
        path=_dotted(loc),
        code=error["type"],
        message=error["msg"],
        expected=error.get("ctx", {}).get("expected"),
        received=None if _is_secret(annotation) else error["input"],
        allowed=_choices(annotation) or None,
        source="flag",
    )


def _dotted(loc: tuple[int | str, ...]) -> str:
    return ".".join(str(part) for part in loc)


def _unwrap_annotated(annotation: Any) -> Any:
    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    return annotation


def _annotation_at(model: type[BaseModel], loc: tuple[int | str, ...]) -> Any:
    """The annotation of the input at `loc`, or None when the path leaves the declared types."""
    annotation: Any = model
    for part in loc:
        annotation = _unwrap_annotated(annotation)
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            field_info = annotation.model_fields.get(str(part))
            if field_info is None:
                return None
            annotation = field_info.annotation
        elif get_origin(annotation) in (list, tuple, set, frozenset) and get_args(annotation):
            annotation = get_args(annotation)[0]
        elif get_origin(annotation) is dict and get_args(annotation):
            annotation = get_args(annotation)[1]
        else:
            return None
    return annotation


def _choices(annotation: Any) -> list[Any]:
    """The `Literal` values and enum member values an annotation accepts, through `Annotated` and unions."""
    annotation = _unwrap_annotated(annotation)
    if get_origin(annotation) is Literal:
        return [value.value if isinstance(value, enum.Enum) else value for value in get_args(annotation)]
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return [member.value for member in annotation]
    if get_origin(annotation) in (Union, types.UnionType):
        return [choice for member in get_args(annotation) for choice in _choices(member)]
    return []


def _is_secret(annotation: Any) -> bool:
    annotation = _unwrap_annotated(annotation)
    if get_origin(annotation) in (Union, types.UnionType):
        return any(_is_secret(member) for member in get_args(annotation))
    return isinstance(annotation, type) and issubclass(annotation, SecretStr | SecretBytes)


def _looks_like_flag(token: str) -> bool:
    # "-1" is a negative number, "-" conventionally means stdin.
    return token.startswith("-") and len(token) > 1 and not token[1].isdigit()


def _leftover_errors(tokens: list[str], valid_flags: list[str]) -> list[FieldError]:
    """Field errors for the tokens argparse could not place.

    A non-flag token right after an unknown flag is taken as that flag's value and not reported again.
    """
    errors: list[FieldError] = []
    previous_was_bare_flag = False
    for token in tokens:
        if _looks_like_flag(token):
            flag, has_value, _ = token.partition("=")
            errors.append(
                FieldError(
                    path=flag.lstrip("-").replace("-", "_"),
                    code="unknown_flag",
                    message=f"unknown flag {flag}",
                    received=flag,
                    allowed=valid_flags,
                    source="flag",
                )
            )
            previous_was_bare_flag = not has_value
            continue
        if not previous_was_bare_flag:
            errors.append(
                FieldError(
                    path="",
                    code="unexpected_argument",
                    message=f"unexpected argument {token}",
                    received=token,
                    source="flag",
                )
            )
        previous_was_bare_flag = False
    return errors


def fail(error: Exception) -> NoReturn:
    """Print the error object for `error` on stdout and exit with its code.

    `InputRejected` and `CommandError` carry their own report. Anything else is UNKNOWN, and its traceback goes to
    stderr when ARGD_DEBUG is on.
    """
    match error:
        case InputRejected() | CommandError():
            report = error.report
        case _:
            if _debug_enabled():
                traceback.print_exception(error, file=sys.stderr)
            message = str(error).strip() or type(error).__name__
            report = ErrorReport(code="UNKNOWN", message=message, exit_code=EXIT_FAILED)
    if _string_errors:
        print(report.native_text or report.message)
    else:
        print(json.dumps(report.model_dump(mode="json", by_alias=True, exclude_none=True)))
    raise SystemExit(report.exit_code)


def _debug_enabled() -> bool:
    # Read outside the app's env isolation. pydantic's bool parsing decides; an unreadable value counts as off.
    try:
        return TypeAdapter(bool).validate_python(os.environ.get("ARGD_DEBUG", ""))
    except ValidationError:
        return False

import enum
import json
import os
import re
import sys
import traceback
import types
from typing import Annotated, Any, Literal, NoReturn, Self, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, SecretBytes, SecretStr, TypeAdapter, ValidationError, field_validator
from pydantic.fields import FieldInfo
from pydantic_core import ErrorDetails
from pydantic_settings import SettingsError

_NEGATIVE_NUMBER = re.compile(r"-\.?\d")


class ExitCode(enum.IntEnum):
    OK = 0
    FAILED = 1
    REJECTED = 2


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

    code: str = Field(pattern=r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")
    message: str
    retryable: bool = False
    hint: str | None = None
    field_errors: list[FieldError] | None = None
    exit_code: int = Field(exclude=True)

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
        exit_code: the process exit code. 0 and 2 are reserved for success and rejected input.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        hint: str | None = None,
        exit_code: int = ExitCode.FAILED,
    ) -> None:
        if exit_code in (ExitCode.OK, ExitCode.REJECTED):
            raise ValueError(f"exit code {exit_code} is reserved for success and rejected input")
        super().__init__(message)
        self.report = ErrorReport(code=code, message=message, retryable=retryable, hint=hint, exit_code=exit_code)


class InputRejected(Exception):
    """Raised inside a run when the input is rejected, before the command is called."""

    def __init__(self, message: str, field_errors: list[FieldError] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field_errors = field_errors or None

    @classmethod
    def from_parse(
        cls,
        model: type[BaseModel],
        leftovers: list[str],
        valid_flags: list[str],
        error: ValidationError | SettingsError | None = None,
    ) -> Self:
        """Every problem with a command's input as one rejection: leftover tokens first, then pydantic's errors."""
        field_errors = _leftover_errors(leftovers, valid_flags)
        if isinstance(error, SettingsError):
            # malformed JSON in a structured flag, pydantic-settings names the field only in its message
            return cls(str(error), field_errors)
        if error is not None:
            field_errors += [_field_error(model, item) for item in error.errors()]
        return cls("invalid input", field_errors)

    @property
    def report(self) -> ErrorReport:
        return ErrorReport(
            code="VALIDATION_ERROR",
            message=self.message,
            field_errors=self.field_errors,
            exit_code=ExitCode.REJECTED,
        )


def _field_error(model: type[BaseModel], error: ErrorDetails) -> FieldError:
    loc = error["loc"]
    if error["type"] == "missing":
        # `input` holds the whole parent input here, not a value for this field
        return FieldError(path=_dotted(loc), code="missing", message=error["msg"])
    annotation = _annotation_at(model, loc)
    return FieldError(
        path=_dotted(loc),
        code=error["type"],
        message=error["msg"],
        expected=error.get("ctx", {}).get("expected"),
        # an unresolved path counts as secret, so a type the walk does not understand can't leak its value
        received=None if annotation is None or _is_secret(annotation) else error["input"],
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
    """The annotation of the input at `loc`, or None when the walk can't resolve it. Callers treat None as secret."""
    annotation: Any = model
    for part in loc:
        annotation = _unwrap_optional(annotation)
        origin, args = get_origin(annotation), get_args(annotation)
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            field_info = _model_field(annotation, str(part))
            annotation = field_info.annotation if field_info else None
        elif origin is tuple and len(args) == 2 and args[1] is Ellipsis:
            annotation = args[0]
        elif origin is tuple and isinstance(part, int) and 0 <= part < len(args):
            annotation = args[part]
        elif origin in (list, set, frozenset) and args:
            annotation = args[0]
        elif origin is dict and args:
            annotation = args[1]
        else:
            return None
        if annotation is None:
            return None
    return annotation


def _unwrap_optional(annotation: Any) -> Any:
    """`X | None` and `Annotated` stripped down to `X`. Pydantic puts no member tag in `loc` for them."""
    while True:
        annotation = _unwrap_annotated(annotation)
        members = [member for member in get_args(annotation) if member is not type(None)]
        if get_origin(annotation) not in (Union, types.UnionType) or len(members) != 1:
            return annotation
        annotation = members[0]


def _model_field(model: type[BaseModel], part: str) -> FieldInfo | None:
    """The field `loc` names with `part`: pydantic reports the alias when there is one."""
    for name, field_info in model.model_fields.items():
        if part in (field_info.alias, field_info.validation_alias, name):
            return field_info
    return None


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
    # "-1" and "-.5" are numbers, "-" means stdin and "--" ends the flags
    return token.startswith("-") and token not in ("-", "--") and not _NEGATIVE_NUMBER.match(token)


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
            report = ErrorReport(code="UNKNOWN", message=message, exit_code=ExitCode.FAILED)
    print(json.dumps(report.model_dump(mode="json", exclude_none=True)))
    raise SystemExit(report.exit_code)


def _debug_enabled() -> bool:
    # an unparseable value counts as off
    try:
        return TypeAdapter(bool).validate_python(os.environ.get("ARGD_DEBUG", ""))
    except ValidationError:
        return False

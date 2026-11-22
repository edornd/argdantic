import dataclasses
import enum
import json
import os
import re
import sys
import traceback
import typing
from collections.abc import Collection, Mapping
from types import NoneType
from typing import Any, ForwardRef, NoReturn, Self, get_args, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    Secret,
    SecretBytes,
    SecretStr,
    TypeAdapter,
    ValidationError,
    field_validator,
)
from pydantic_core import ErrorDetails
from pydantic_settings import SettingsError
from typing_extensions import is_typeddict
from typing_inspection import typing_objects
from typing_inspection.introspection import AnnotationSource, get_literal_values, inspect_annotation, is_union_origin

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

    def __init__(
        self,
        message: str,
        field_errors: list[FieldError] | None = None,
        *,
        code: str = "VALIDATION_ERROR",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field_errors = field_errors or None
        self.code = code

    @classmethod
    def command_not_found(cls, level: str, allowed: list[str], token: str | None = None) -> Self:
        """An unknown command `token`, or a missing one when it is None, in the group `level`, such as "cli notes"."""
        code, message, field_message = (
            ("missing", f"a command is required in '{level}'", "a command is required")
            if token is None
            else ("unknown_command", f"unknown command '{token}' in '{level}'", f"unknown command {token}")
        )
        field_error = FieldError(
            path="command",
            code=code,
            message=field_message,
            received=token,
            allowed=allowed,
            source="flag",
        )
        return cls(message, [field_error], code="COMMAND_NOT_FOUND")

    @classmethod
    def missing_value(cls, path: str, flag: str) -> Self:
        """A value flag given with no value, such as a bare `--title`."""
        field_error = FieldError(
            path=path,
            code="missing_value",
            message="a value is required",
            received=flag,
            source="flag",
        )
        return cls(f"{flag} needs a value", [field_error])

    @classmethod
    def from_parse(
        cls,
        model: type[BaseModel],
        leftovers: list[str],
        valid_flags: list[str],
        error: ValidationError | SettingsError | None = None,
        flat: frozenset[str] = frozenset(),
    ) -> Self:
        """Every problem with a command's input as one rejection: leftover tokens first, then pydantic's errors.

        Args:
            flat: the Flat parameters, whose name the error paths leave out.
        """
        field_errors = _leftover_errors(leftovers, valid_flags)
        if isinstance(error, SettingsError):
            # malformed JSON in a structured flag, pydantic-settings names the field only in its message
            return cls(str(error), field_errors)
        if error is not None:
            field_errors += [_field_error(model, item, flat) for item in error.errors()]
        return cls("invalid input", field_errors)

    @property
    def report(self) -> ErrorReport:
        return ErrorReport(
            code=self.code,
            message=self.message,
            field_errors=self.field_errors,
            exit_code=ExitCode.REJECTED,
        )


def _field_error(model: type[BaseModel], error: ErrorDetails, flat: frozenset[str]) -> FieldError:
    loc = error["loc"]
    # a Flat parameter has no flag, so the path starts at its field
    path = _dotted(loc[1:] if loc and loc[0] in flat else loc)
    if error["type"] == "missing":
        # `input` holds the whole parent input here, not a value for this field
        return FieldError(path=path, code="missing", message=error["msg"])
    annotations = _annotations_at(model, loc)
    # an unresolved path counts as secret, so a type the walk does not understand can't leak its value
    hidden = any(annotation is None or _holds_secret(annotation) for annotation in annotations)
    allowed = [choice for annotation in annotations if annotation is not None for choice in _choices(annotation)]
    return FieldError(
        path=path,
        code=error["type"],
        message=error["msg"],
        expected=error.get("ctx", {}).get("expected"),
        received=None if hidden else error["input"],
        allowed=allowed or None,
        source="flag",
    )


def _dotted(loc: tuple[int | str, ...]) -> str:
    return ".".join(str(part) for part in loc)


def _bare(annotation: Any) -> Any:
    """The type an annotation names, without `Annotated`, type aliases, qualifiers or a root model wrapper."""
    inspected = inspect_annotation(annotation, annotation_source=AnnotationSource.ANY, unpack_type_aliases="eager")
    annotation = inspected.type
    if isinstance(annotation, type) and issubclass(annotation, RootModel):
        # a root model's `loc` skips `root`
        return _bare(annotation.model_fields["root"].annotation)
    return annotation


def _annotations_at(annotation: Any, loc: tuple[int | str, ...]) -> list[Any]:
    """Every annotation the input at `loc` can have. None marks a step the walk can't follow: callers hide it."""
    annotation = _bare(annotation)
    origin, args = get_origin(annotation), get_args(annotation)
    if is_union_origin(origin):
        members = [member for member in args if member is not NoneType]
        if len(members) == 1:
            # `X | None` puts no member tag in `loc`
            return _annotations_at(members[0], loc)
        if loc:
            # other unions put a member tag first: a model's class name, or a name only pydantic-core knows (a
            # discriminator value, `list[int]`). A tag that names no member makes the walk follow every member.
            named = [member for member in members if getattr(_bare(member), "__name__", None) == loc[0]]
            return [found for member in named or members for found in _annotations_at(member, loc[1:])]
    if not loc:
        return [annotation]
    part, rest = loc[0], loc[1:]
    if (fields := _fields(annotation)) is not None:
        child = fields.get(part)
    elif origin is tuple and args[-1:] == (Ellipsis,):
        child = args[0]
    elif origin is tuple:
        child = args[part] if isinstance(part, int) and 0 <= part < len(args) else None
    elif isinstance(origin, type) and issubclass(origin, Mapping) and len(args) == 2:
        child = args[1]
    elif isinstance(origin, type) and issubclass(origin, Collection) and len(args) == 1:
        child = args[0]
    else:
        child = None
    return [None] if child is None else _annotations_at(child, rest)


def _fields(annotation: Any) -> dict[int | str, Any] | None:
    """The annotation behind each key `loc` can use in a model, dataclass, TypedDict or NamedTuple; None otherwise."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        by_name: dict[int | str, Any] = {name: field.annotation for name, field in annotation.model_fields.items()}
        # pydantic reports the alias, so an alias beats a field of the same name
        return by_name | {
            field.validation_alias: field.annotation
            for field in annotation.model_fields.values()
            if isinstance(field.validation_alias, str)
        }
    if dataclasses.is_dataclass(annotation) or is_typeddict(annotation):
        return {**typing.get_type_hints(annotation, include_extras=True)}
    if typing_objects.is_namedtuple(annotation):
        hints: dict[int | str, Any] = {**typing.get_type_hints(annotation, include_extras=True)}
        # `loc` names a NamedTuple field by name or by position, depending on the input
        return hints | dict(enumerate(hints.values()))
    return None


def _choices(annotation: Any) -> list[Any]:
    """The `Literal` values and enum member values an annotation accepts, through unions."""
    annotation = _bare(annotation)
    if typing_objects.is_literal(get_origin(annotation)):
        values = get_literal_values(annotation, unpack_type_aliases="eager")
        return [value.value if isinstance(value, enum.Enum) else value for value in values]
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return [member.value for member in annotation]
    if is_union_origin(get_origin(annotation)):
        return [choice for member in get_args(annotation) for choice in _choices(member)]
    return []


def _holds_secret(annotation: Any, seen: frozenset[int] = frozenset()) -> bool:
    """Whether a value of this type is or contains a secret, since an error on a container echoes all of it."""
    if id(annotation) in seen:
        # a recursive type: the outer call already checks everything it holds
        return False
    seen |= {id(annotation)}
    annotation = _bare(annotation)
    if typing_objects.is_literal(get_origin(annotation)):
        # its arguments are values, and a string value is not a forward reference
        return False
    if isinstance(annotation, str | ForwardRef) or typing_objects.is_typealiastype(annotation):
        # a forward reference the walk can't evaluate could name a secret
        return True
    if isinstance(annotation, type) and issubclass(annotation, SecretStr | SecretBytes | Secret):
        return True
    if get_origin(annotation) is Secret:
        return True
    if (fields := _fields(annotation)) is not None:
        return any(_holds_secret(field, seen) for field in fields.values())
    return any(_holds_secret(arg, seen) for arg in get_args(annotation))


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

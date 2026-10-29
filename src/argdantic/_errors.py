"""Error objects, exit codes and their rendering. Only `CommandError` is public."""

import enum
import json
import types
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal, NoReturn, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REJECTED = 2


@dataclass(frozen=True)
class FieldError:
    """One problem with one input value."""

    path: str
    code: str
    message: str
    expected: str | None = None
    received: Any = None
    allowed: list[Any] | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"path": self.path, "code": self.code, "message": self.message}
        optional = {
            "expected": self.expected,
            "received": self.received,
            "allowed": self.allowed,
            "source": self.source,
        }
        data.update({key: value for key, value in optional.items() if value is not None})
        return data


@dataclass(frozen=True)
class ErrorReport:
    """A failed run: the error object plus the exit code that goes with it."""

    code: str
    message: str
    exit_code: int
    retryable: bool = False
    hint: str | None = None
    field_errors: list[FieldError] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"code": self.code, "message": self.message, "retryable": self.retryable}
        if self.hint is not None:
            data["hint"] = self.hint
        if self.field_errors:
            data["fieldErrors"] = [error.to_dict() for error in self.field_errors]
        return data


def _dotted(loc: tuple[int | str, ...]) -> str:
    return ".".join(str(part) for part in loc)


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


def _unwrap_annotated(annotation: Any) -> Any:
    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
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


def _field_error(model: type[BaseModel], error: Any) -> FieldError:
    loc = error["loc"]
    if error["type"] == "missing":
        # pydantic puts the whole parent input in `input` here, and no value came from any source.
        return FieldError(path=_dotted(loc), code="missing", message=error["msg"])
    return FieldError(
        path=_dotted(loc),
        code=error["type"],
        message=error["msg"],
        received=error["input"],
        allowed=_choices(_annotation_at(model, loc)) or None,
        source="flag",
    )


def validation_errors(model: type[BaseModel], error: ValidationError) -> list[FieldError]:
    return [_field_error(model, item) for item in error.errors()]


def _looks_like_flag(token: str) -> bool:
    # "-1" is a negative number, "-" conventionally means stdin.
    return token.startswith("-") and len(token) > 1 and not token[1].isdigit()


def leftover_errors(tokens: list[str], valid_flags: list[str]) -> list[FieldError]:
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


def invalid_input(field_errors: list[FieldError]) -> ErrorReport:
    return ErrorReport(
        code="VALIDATION_ERROR",
        message="invalid input",
        exit_code=EXIT_REJECTED,
        field_errors=field_errors,
    )


def usage_report(message: str) -> ErrorReport:
    """An input error argparse found on its own, such as a flag without its value."""
    return ErrorReport(code="VALIDATION_ERROR", message=message, exit_code=EXIT_REJECTED)


def emit(report: ErrorReport) -> NoReturn:
    """Print the error object on stdout and exit with its code."""
    print(json.dumps(report.to_dict()))
    raise SystemExit(report.exit_code)

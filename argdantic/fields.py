from typing import Any, Optional, Sequence

from pydantic import Field


def ArgField(
    *names: Optional[Sequence[str]],
    default: Optional[Any] = ...,
    description: Optional[str] = None,
    **extra: Any,
) -> Any:
    """Create a FieldInfo object with the given arguments.

    This is a convenience function for creating a FieldInfo object
    with the given arguments. It is used to create the default
    FieldInfo object for each field in a model.

    Args:
        *names (str, optional): Additional optional names for the current field.
        default (Any, optional): The default value of the argument, empty by default.
        description: The description of the argument.
        **extra: Extra keyword arguments, see the pydantic Field function for more info.

    Returns:
        A FieldInfo object with the given arguments.
    """
    json_schema_extra = extra.pop("json_schema_extra", {})
    json_schema_extra["names"] = names
    return Field(default, description=description, json_schema_extra=json_schema_extra, **extra)

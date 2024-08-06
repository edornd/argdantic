from typing import Any, Container, Mapping, Optional, Sequence, Type, Union, get_args, get_origin

from pydantic.v1.utils import lenient_issubclass


def type_name(field_type: Type[Any]) -> str:
    """Returns the name of the type, or the name of the type's origin, if the type is a
    typing construct.
    Args:
        field_type (type): pydantic field type
    Returns:
        str: name of the type
    """
    origin = get_origin(field_type)
    if origin is not None:
        name = origin.__name__
    else:
        name = field_type.__name__
    return name.lower()


def is_multiple(field_type: Type[Any]) -> bool:
    """Checks whether the current type is a container type ('contains' other types), like
    lists and tuples.
    Args:
        field_type (type): pydantic field type
    # Returns:
        bool: true if a container, false otherwise
    """
    # do not consider strings or byte arrays as containers
    if field_type in (str, bytes):
        return False
    # Early out for standard containers: list, tuple, range
    if lenient_issubclass(field_type, Sequence):
        return True
    origin = get_origin(field_type)
    # Early out for non-typing objects
    if origin is None:
        return False
    return lenient_issubclass(origin, Sequence)


def is_mapping(field_type: Type[Any]) -> bool:
    """Checks whether this field represents a dictionary or JSON object.
    Args:
        field_type (type): pydantic type
    Returns:
        bool: true when the field is a dict-like object, false otherwise.
    """
    # Early out for standard containers.
    if lenient_issubclass(field_type, Mapping):
        return True
    # for everything else or when the typing is more complex, check its origin
    origin = get_origin(field_type)
    if origin is None:
        return False
    return lenient_issubclass(origin, Mapping)


def is_container(field_type: Type[Any]) -> bool:
    """Checks whether the current type is a container type ('contains' other types), like
    lists and tuples.
    Args:
        field_type (type): pydantic field type
    Returns:
        bool: true if a container, false otherwise
    """
    # do not consider strings or byte arrays as containers
    if field_type in (str, bytes):
        return False
    # Early out for standard containers: list, tuple, range
    if lenient_issubclass(field_type, Container):
        return True
    origin = get_origin(field_type)
    # Early out for non-typing objects
    if origin is not None:
        return lenient_issubclass(origin, Container)
    return False


def is_typing(field_type: Type[Any]) -> bool:
    """Checks whether the current type is a module-like type.
    Args:
        field_type (type): pydantic field type
    Returns:
        bool: true if the type is itself a type
    """
    raw = get_origin(field_type)
    if raw is None:
        return False
    return raw is type or raw is Type


def is_optional(field_type: Optional[Type[Any]]) -> bool:
    """Checks whether the current type is an optional type.
    Args:
        field_type (type): pydantic field type
    Returns:
        bool: true if the type is optional, false otherwise
    """
    return get_origin(field_type) is Union and type(None) in get_args(field_type)


def get_optional_type(field_type: Optional[Type[Any]]) -> Type[Any]:
    """Returns the type of the optional field.
    Args:
        field_type (type): pydantic field type
    Returns:
        Type[Any]: the type of the field
    """
    return get_args(field_type)[0]

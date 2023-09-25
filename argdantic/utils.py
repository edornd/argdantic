import typing as types

from pydantic.v1.utils import lenient_issubclass


def type_name(field_type: type) -> str:
    """Returns the name of the type, or the name of the type's origin, if the type is a
    typing construct.
    Args:
        field_type (type): pydantic field type
    Returns:
        str: name of the type
    """
    origin = types.get_origin(field_type)
    if origin is not None:
        name = origin.__name__
    else:
        name = field_type.__name__
    return name.lower()


def is_multiple(field_type: type) -> bool:
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
    if lenient_issubclass(field_type, types.Sequence):
        return True
    origin = types.get_origin(field_type)
    # Early out for non-typing objects
    if origin is None:
        return False
    return lenient_issubclass(origin, types.Sequence)


def is_mapping(field_type: type) -> bool:
    """Checks whether this field represents a dictionary or JSON object.
    Args:
        field_type (type): pydantic type
    Returns:
        bool: true when the field is a dict-like object, false otherwise.
    """
    # Early out for standard containers.
    if lenient_issubclass(field_type, types.Mapping):
        return True
    # for everything else or when the typing is more complex, check its origin
    origin = types.get_origin(field_type)
    if origin is None:
        return False
    return lenient_issubclass(origin, types.Mapping)


def is_container(field_type: type) -> bool:
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
    if lenient_issubclass(field_type, types.Container):
        return True
    origin = types.get_origin(field_type)
    # Early out for non-typing objects
    if origin is not None:
        return lenient_issubclass(origin, types.Container)
    return False


def is_typing(field_type: type) -> bool:
    """Checks whether the current type is a module-like type.
    Args:
        field_type (type): pydantic field type
    Returns:
        bool: true if the type is itself a type
    """
    raw = types.get_origin(field_type)
    if raw is None:
        return False
    return raw is type or raw is types.Type


def is_optional(field_type: type) -> bool:
    """Checks whether the current type is an optional type.
    Args:
        field_type (type): pydantic field type
    Returns:
        bool: true if the type is optional, false otherwise
    """
    return types.get_origin(field_type) is types.Union and type(None) in types.get_args(field_type)

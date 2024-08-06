import argparse
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Tuple, Type, cast, get_args

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic.v1.utils import lenient_issubclass
from pydantic_core import PydanticUndefined

from argdantic.parsing import ActionTracker, Argument, PrimitiveArgument, registry
from argdantic.sources import DEFAULT_SOURCE_FIELD
from argdantic.utils import get_optional_type, is_optional


def format_description(description: Optional[str], has_default: bool, is_required: bool) -> str:
    """Formats the field description, adding additional info about defaults and if it is required.

    Args:
        description (str): The description.
        has_default (bool): If the field has a default value.
        is_required (bool): If the field is required.

    Returns:
        str: The formatted description.
    """
    suffix = None
    # if it already has a default, it is not required
    if is_required:
        suffix = "(required)"
    elif has_default:
        suffix = "(default: %(default)s)"
    # handle cases:
    # - when there is no prefix, return the description as is (also handles None)
    # - when there is no description, return the prefix as is (also handles None)
    # - when there is both, return the prefix and description
    if suffix is None:
        return description or ""
    if description is None:
        return suffix
    return f"{description} {suffix}"


def argument_from_field(
    field_info: FieldInfo,
    kebab_name: str,
    delimiter: str,
    internal_delimiter: str,
    parent_path: Tuple[str, ...],
    custom_identifier: Optional[str] = None,
) -> Argument:
    """Converts a pydantic field to a single argument.

    Args:
        field (Field): The field to convert.
        kebab_name (str): The kebab case name of the field.
        delimiter (str): The delimiter to use for the argument names.
        internal_delimiter (str): The delimiter to use for the internal names.
        parent_path (Tuple[str, ...]): The parent path of the field.

    Returns:
        Argument: The argument.
    """
    # this function should only deal with non-pydantic objects
    assert not lenient_issubclass(field_info.annotation, BaseModel)
    base_option_name = delimiter.join(parent_path + (kebab_name,))
    full_option_name = f"--{base_option_name}"
    extra_fields: Dict[str, Any] = (
        field_info.json_schema_extra or {} if isinstance(field_info.json_schema_extra, dict) else {}
    )
    extra_names = extra_fields.get("names", ())

    # example.test-attribute -> example__test_attribute
    identifier = custom_identifier or base_option_name.replace(delimiter, internal_delimiter).replace("-", "_")
    # handle optional types, the only case where we currently support Unions
    field_type: Type[Any] = field_info.annotation  # type: ignore
    if is_optional(field_info.annotation):
        field_type = get_args(field_info.annotation)[0]

    field_names = (full_option_name, *extra_names)
    has_default = field_info.default is not PydanticUndefined and field_info.default is not None
    field_default = field_info.default if has_default else argparse.SUPPRESS
    description = format_description(field_info.description, has_default, field_info.is_required())

    arg_class = registry.get(field_type, PrimitiveArgument)
    return arg_class(
        *field_names,
        identifier=identifier,
        field_type=field_type,
        default=field_default,
        required=field_info.is_required(),
        description=description,
    )


def model_to_args(
    model: Type[BaseModel],
    delimiter: str,
    internal_delimiter: str,
    parent_path: Tuple[str, ...] = tuple(),
) -> Generator[Argument, None, None]:
    """Converts a pydantic model to a list of arguments.

    Args:
        model (Type[BaseModel]): The model to convert.
        delimiter (str): The delimiter to use for the argument names.
        internal_delimiter (str): The delimiter to use for the internal names.
        parent_path (Tuple[str, ...], optional): The parent path. Defaults to tuple().

    Returns:
        ArgumentParser: The argument parser.
    """
    # iterate over fields in the settings
    for field_name, field_info in model.model_fields.items():
        # checks on delimiters to be done
        kebab_name = field_name.replace("_", "-")
        assert internal_delimiter not in kebab_name

        annotation = (
            field_info.annotation
            if not is_optional(field_info.annotation)
            else get_optional_type(field_info.annotation)
        )
        if lenient_issubclass(annotation, BaseModel):
            yield from model_to_args(
                cast(Type[BaseModel], annotation),
                delimiter,
                internal_delimiter,
                parent_path=parent_path + (kebab_name,),
            )
            # if the model requires a file source, we add an extra argument
            # whose name is the same as the model's name (yes I'm not gonna bother with mypy here)
            if hasattr(annotation, "__arg_source_field__") and annotation.__arg_source_field__ is None:  # type: ignore
                default = PydanticUndefined if annotation.__arg_source_required__ else None  # type: ignore
                info = FieldInfo(
                    annotation=Path,
                    alias=field_info.alias,
                    title=field_info.title,
                    description=field_info.description,
                    default=default,
                    json_schema_extra=field_info.json_schema_extra,
                )
                base_name = delimiter.join(parent_path + (kebab_name,))
                internal_name = base_name.replace(delimiter, internal_delimiter).replace("-", "_")
                custom_identifier = f"{internal_name}{internal_delimiter}{DEFAULT_SOURCE_FIELD}"
                yield argument_from_field(
                    field_info=info,
                    kebab_name=kebab_name,
                    delimiter=delimiter,
                    internal_delimiter=internal_delimiter,
                    parent_path=parent_path,
                    custom_identifier=custom_identifier,
                )
            continue
        # simple fields
        yield argument_from_field(
            field_info=field_info,
            kebab_name=kebab_name,
            delimiter=delimiter,
            internal_delimiter=internal_delimiter,
            parent_path=parent_path,
        )


def args_to_dict_tree(
    kwargs: Dict[str, Any],
    internal_delimiter: str,
    remove_helpers: bool = True,
    cli_trackers: Optional[Dict[str, ActionTracker]] = None,
) -> Dict[str, Any]:
    """Transforms a flat dictionary of identifiers and values back into a complex object made of nested dictionaries.
    E.g. the following input: `animal__type='dog', animal__name='roger', animal__owner__name='Mark'`
    becomes: `{animal: {name: 'roger', type: 'dog'}, owner: {name: 'Mark'}}`

    Args:
        kwargs (Dict[str, Any]): flat dictionary of available fields
        internal_delimiter (str): delimiter required to split fields
        remove_helpers (bool, optional): whether to remove helper fields (e.g., __func__). Defaults to True.
        cli_trackers (Dict[str, ActionTracker], optional): dictionary of action trackers. Defaults to None.

    Returns:
        Dict[str, Any]: nested dictionary of properties to be converted into pydantic models
    """
    cli_trackers = cli_trackers or {}
    result: Dict[str, Any] = dict()
    for name, value in kwargs.items():
        if remove_helpers and name.startswith("__"):
            continue
        if tracker := cli_trackers.get(name):
            if not tracker.is_set():
                continue
        # split full name into parts
        parts = name.split(internal_delimiter)
        # create nested dicts corresponding to each part
        # test__inner__value -> {test: {inner: value}}
        nested = result
        for part in parts[:-1]:
            if part not in nested:
                nested[part] = dict()
            nested = nested[part]
        nested[parts[-1]] = value
    return dict(result)

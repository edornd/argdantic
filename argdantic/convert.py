import argparse
from argparse import ArgumentParser
from typing import Any, Dict, Tuple, Type

from pydantic import BaseModel, Field
from pydantic.utils import lenient_issubclass

from argdantic.arguments import PrimitiveArgument, registry


def argument_from_field(
    field: Field,
    kebab_name: str,
    delimiter: str,
    internal_delimiter: str,
    parent_path: Tuple[str, ...],
) -> None:
    # this function should only deal with non-pydantic objects
    assert not lenient_issubclass(field.outer_type_, BaseModel)
    base_option_name = delimiter.join(parent_path + (kebab_name,))
    full_option_name = f"--{base_option_name}"
    extra_names = field.field_info.extra.get("names", ())

    # example.test-attribute -> example__test_attribute
    identifier = base_option_name.replace(delimiter, internal_delimiter).replace("-", "_")
    field_type = field.outer_type_
    field_names = (full_option_name, *extra_names)
    field_default = field.default if field.default is not None else argparse.SUPPRESS

    arg_class = registry.get(field_type, PrimitiveArgument)
    return arg_class(
        *field_names,
        identifier=identifier,
        field_type=field_type,
        default=field_default,
        required=field.required,
        description=field.field_info.description,
    )


def model_to_args(
    model: Type[BaseModel],
    delimiter: str,
    internal_delimiter: str,
    parent_path: Tuple[str, ...] = tuple(),
) -> ArgumentParser:
    # iterate over fields in the settings
    for field in model.__fields__.values():
        # checks on delimiters to be done
        kebab_name = field.name.replace("_", "-")
        assert internal_delimiter not in kebab_name
        if lenient_issubclass(field.outer_type_, BaseModel):
            yield from model_to_args(
                field.outer_type_,
                delimiter,
                internal_delimiter,
                parent_path=parent_path + (kebab_name,),
            )
            continue
        # simple fields
        yield argument_from_field(
            field=field,
            kebab_name=kebab_name,
            delimiter=delimiter,
            internal_delimiter=internal_delimiter,
            parent_path=parent_path,
        )


def args_to_dict_tree(kwargs: Dict[str, Any], internal_delimiter: str) -> Dict[str, Any]:
    """Transforms a flat dictionary of identifiers and values back into a complex object made of nested dictionaries.
    E.g. the following input: `animal__type='dog', animal__name='roger', animal__owner__name='Mark'`
    becomes: `{animal: {name: 'roger', type: 'dog'}, owner: {name: 'Mark'}}`
    Args:
        kwargs (Dict[str, Any]): flat dictionary of available fields
        internal_delimiter (str): delimiter required to split fields
    Returns:
        Dict[str, Any]: nested dictionary of properties to be converted into pydantic models
    """
    result: Dict[str, Any] = dict()
    for name, value in kwargs.items():
        # skip when not set
        if value is None:
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

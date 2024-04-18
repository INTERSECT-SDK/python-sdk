"""This is a particular implementation of Pydantic's 'GenerateJsonSchema' class.

See: https://docs.pydantic.dev/latest/api/json_schema/#pydantic.json_schema.GenerateJsonSchema
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
)

from jsonschema import Draft202012Validator as SchemaValidator
from jsonschema import ValidationError as SchemaValidationError
from jsonschema.validators import validator_for
from pydantic import PydanticInvalidForJsonSchema, PydanticSchemaGenerationError, TypeAdapter
from pydantic.json_schema import (
    GenerateJsonSchema,
    JsonSchemaMode,
    JsonSchemaValue,
)
from pydantic.type_adapter import _type_has_config
from pydantic_core import PydanticSerializationError, to_jsonable_python

if TYPE_CHECKING:
    from pydantic_core import CoreSchema, core_schema


# build nested dictionary from list of keys. i.e. if keys = ['one', 'two', 'three']
def build_nested_dict(keys: list[str], val: Any) -> dict[str, Any]:
    """Build nested dictionary from list of keys.

    i.e. if keys = ['one', 'two', 'three'], return:
    {
        "one": {
            "two": {
                "three": val
            }
        }
    }

    This function is fairly generic, but not really useful outside of a specific use-case in the Pydantic JSON schema generator.
    """
    nested_dict: dict[str, Any] = {}
    pointer = nested_dict
    for part in keys[:-1]:
        pointer[part] = {}
        pointer = pointer[part]
    pointer[keys[-1]] = val
    return nested_dict


def validate_against_schema(
    json_schema: Any,
    value: Any,
) -> None:
    """Validates "value" (a python object) against "json_schema" (a python object).

    We also validate default values against a few predefined formats - see https://python-jsonschema.readthedocs.io/en/stable/validate/#validating-formats
    for a complete reference.

    NOTE: While the JSON schema specification *does not* require defaults validate against the schema, we *do*.
    However, we *do not* validate examples against the schema.
    This is because examples are only used for autocomplete assistance in UIs, while defaults are used in actual API calls.

    Raises jsonschema.ValidationError if it fails to validate
    """
    SchemaValidator(
        json_schema,
        format_checker=SchemaValidator.FORMAT_CHECKER,
    ).validate(value)


def validate_schema(json_schema: Any) -> list[str]:
    """Checks that json_schema is itself a valid JSON schema - specifically, against draft 2020-12.

    Returns a list of error strings. If list is empty, there were no errors.
    """
    # custom impl. of check_schema() , gather all errors instead of throwing on first error
    validator_cls = validator_for(SchemaValidator.META_SCHEMA, default=SchemaValidator)
    metavalidator: SchemaValidator = validator_cls(
        SchemaValidator.META_SCHEMA, format_checker=SchemaValidator.FORMAT_CHECKER
    )
    return [
        f'{error.json_path} : {error.message}' for error in metavalidator.iter_errors(json_schema)
    ]


class GenerateTypedJsonSchema(GenerateJsonSchema):
    """This extends Pydantic's default JSON schema generation class.

    With any type which returns an empty dictionary or missing types, we want to invalidate these schemas.
    We can't construct a meaningful schema from these types.
    """

    def generate(self, schema: CoreSchema, mode: JsonSchemaMode = 'validation') -> JsonSchemaValue:
        """This is the main 'entrypoint' for generating one json schema.

        It would be foolish to attempt to override Pydantic's default implementation, but we need to validate defaults before we return the schema.
        We initialize the "intersect_postgeneration_defaults" list on the instance, and perform post-defs validation later on.
        """
        self.intersect_sdk_postgeneration_defaults: list[tuple[Any, dict[str, Any]]] = []
        """
        This is a custom item we store for postvalidation of some defaults after the entire json schema has been generated.
        We need to validate EACH default (tuple item 0) against its ref (tuple item 1)
        """

        json_schema = super().generate(schema, mode)

        # 1) Check that the user's own JSON schema is a valid JSON schema.
        # Pydantic can check most things, but not the pydantic "WithJsonSchema" wrapper, json_schema_extra (from Field or ConfigDict), or any of __get_pydantic_json_schema__ / __get_pydantic_core_schema__ implementations
        # Note that this does NOT check that the user's JSON schema would validate against their Pydantic model,
        # but if they're explicitly using any of the aforementioned methods or the "SkipJsonSchema" wrapper (which will almost always be a horrid mistake), we have to trust they know what they are doing.
        json_schema_errors = validate_schema(json_schema)
        if json_schema_errors:
            error_str = '\n    '.join(json_schema_errors)
            msg = f'Invalid JSON schema generated for INTERSECT - make sure any JSON schema you custom write is valid under Draft 2020-12.\n{error_str}'
            raise PydanticInvalidForJsonSchema(msg)

        # 2): check that all default ref values are valid (it's easier to analyze non-ref'd defaults as we're analyzing the Pydantic core schema)
        # Note that we do NOT check 'examples', though these are only useful for giving form hints for non-enumerated values
        if self.intersect_sdk_postgeneration_defaults:
            tmp_schema = json_schema.copy()
            defs = tmp_schema.pop('$defs')  # this SHOULD ALWAYS exist if we have values in our list
            # ref_template should always start with "#" and end with "{model}"
            ref_parts = self.ref_template.split('/')[1:-1]
            defs_schema = build_nested_dict(ref_parts, defs)

            for default, inner_schema in self.intersect_sdk_postgeneration_defaults:
                final_schema = {**defs_schema, **inner_schema}
                try:
                    validate_against_schema(final_schema, default)
                except SchemaValidationError as e:
                    err_msg = f'Invalid nested validation regarding defaults: {e.message}'
                    raise PydanticInvalidForJsonSchema(err_msg) from e

        return json_schema

    def any_schema(self, schema: core_schema.AnySchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches any value.

        OVERRIDE: We get no type hints from this schema, so we need to invalidate this.
        The two big annotations to watch out for are 'object' and "typing.Any".
        This will handle 'object' in _most_ other types (i.e. List[object]), but NOT i.e. List[Any].

        It will not handle Tuples or classes in all cases; it will catch invalid types, but not missing types.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.handle_invalid_for_json_schema(
            schema, 'Any or object : dynamic typing is not allowed for INTERSECT schemas'
        )

    def is_subclass_schema(self, schema: core_schema.IsSubclassSchema) -> JsonSchemaValue:
        """Generates a JSON schema that checks if a value is a subclass of a class, equivalent to Python's `issubclass` method.

        OVERRIDE: Pydantic v2 returned an empty dictionary to maintain backwards compat. with v1, but we don't need this.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        return self.handle_invalid_for_json_schema(
            schema, f'core_schema.IsSubclassSchema ({schema["cls"]})'
        )

    def list_schema(self, schema: core_schema.ListSchema) -> JsonSchemaValue:
        """Returns a schema that matches a list schema.

        OVERRIDES: we need to make sure we have an items schema, defer to Pydantic's implementation otherwise

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        if not schema.get('items_schema'):
            return self.handle_invalid_for_json_schema(
                schema, 'list subtyping may not be dynamic in INTERSECT'
            )
        return super().list_schema(schema)

    def tuple_schema(self, schema: core_schema.TupleSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a tuple schema e.g. `Tuple[int,str, bool]` or `Tuple[int, ...]`.

        OVERRIDE: disallow bare tuple typing, Tuple[()], and tuple[()] types, otherwise defer to Pydantic's handling

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema = super().tuple_schema(schema)
        if not json_schema.get('items') and not json_schema.get('prefixItems'):
            return self.handle_invalid_for_json_schema(
                schema,
                'core_schema.TupleSchema: Tuple must have non-empty types and not use () as a type for INTERSECT',
            )
        return json_schema

    def set_schema(self, schema: core_schema.SetSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a set schema.

        OVERRIDES: we need to make sure we have an items schema, defer to Pydantic's implementation otherwise

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        if not schema.get('items_schema'):
            return self.handle_invalid_for_json_schema(
                schema, 'set subtyping may not be dynamic in INTERSECT'
            )
        return super().set_schema(schema)

    def frozenset_schema(self, schema: core_schema.FrozenSetSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a frozenset schema.

        OVERRIDES: we need to make sure we have an items schema, defer to Pydantic's implementation otherwise

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        if not schema.get('items_schema'):
            return self.handle_invalid_for_json_schema(
                schema, 'frozenset subtyping may not be dynamic in INTERSECT'
            )
        return super().frozenset_schema(schema)

    def generator_schema(self, schema: core_schema.GeneratorSchema) -> JsonSchemaValue:
        """Returns a JSON schema that represents the provided GeneratorSchema.

        OVERRIDES: we need to make sure we have an items schema, defer to Pydantic's implementation otherwise
        NOTE: at time of writing (pydantic v2.5.3), this never seems to execute when there's an error, but the superclass function
        suggests that it should. This function is kept in for backwards compatibility purposes.

        Args:
            schema: The schema.

        Returns:
            The generated JSON schema.
        """
        if not schema.get('items_schema'):
            return self.handle_invalid_for_json_schema(
                schema, 'generator yield subtyping (first argument) may not be dynamic in INTERSECT'
            )
        json_schema = super().generator_schema(schema)
        if not json_schema.get('items'):
            return self.handle_invalid_for_json_schema(
                schema, 'generator yield subtyping (first argument) may not be dynamic in INTERSECT'
            )
        return json_schema

    def dict_schema(self, schema: core_schema.DictSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a dict schema.

        OVERRIDE: This is a reimplementation of Pydantic's handling, because we need to check two things:
        1) We need to make sure that "additionalProperties" has typing information (don't allow "Any" or "object" as the Value type)
        2) In JSON, mapping "keys" must always be strings, so check that the Key type is either "str" or integer/float.
        With integer/float, we can generate a "patternProperties" schema for the key automatically.

        NOTE: if you are using integer/float as the dictionary type, you CANNOT set strict_validation=True on the @intersect_message handler.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        if 'keys_schema' not in schema:
            return self.handle_invalid_for_json_schema(
                schema,
                "dict or mapping: key type needs to be 'str', 'int', or 'float' for INTERSECT. You may use typing_extensions.Annotated in conjunction with Pydantic.Field to specify a string pattern if desired.",
            )
        if 'values_schema' not in schema:
            return self.handle_invalid_for_json_schema(
                schema, 'dict or mapping: value type cannot be Any/object for INTERSECT'
            )
        keys_schema = self.generate_inner(schema['keys_schema']).copy()
        values_schema = self.generate_inner(schema['values_schema']).copy()
        values_schema.pop('title', None)  # don't give a title to the additionalProperties

        # this is actually the Python type, not the jsonschema type.
        # Only strings are valid JSON keys, but integers/floats are still useful for many use-cases.
        # Other key types should be discouraged due to how their implementation would be obfuscated.
        keys_type = schema['keys_schema']['type']

        json_schema: JsonSchemaValue = {'type': 'object'}
        if keys_type == 'int':
            json_schema['patternProperties'] = {'^-?[0-9]+$': values_schema}
        elif keys_type == 'float':
            # this regex disallows '1237.', which can be handled by Python but not every programming language
            json_schema['patternProperties'] = {
                '^-?[0-9]*\\.?[0-9]+([eE]-?[0-9]+)?$': values_schema
            }
        elif keys_type == 'str':
            keys_pattern = keys_schema.pop('pattern', None)
            if keys_pattern is None:
                json_schema['additionalProperties'] = values_schema
            else:
                json_schema['patternProperties'] = {keys_pattern: values_schema}
        else:
            return self.handle_invalid_for_json_schema(
                schema,
                "dict or mapping: key type needs to be 'str', 'int', or 'float' for INTERSECT. You may use typing_extensions.Annotated in conjunction with Pydantic.Field to specify a string pattern if desired.",
            )
        self.update_with_validations(json_schema, schema, self.ValidationsMapping.object)
        return json_schema

    def default_schema(self, schema: core_schema.WithDefaultSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema with a default value.

        Mostly follows Pydantic's implementation, but we need to override because we actually do schema validation here.

        One way we could do this use "validate_default" in Pydantic's ConfigDict, but this has too many problems.
        First, we can't specify a ConfigDict on the TypeAdapter if the type is a pydantic.BaseModel, a dataclass, or a TypedDict; and our TypeAdapter handles ALL generic types.
        See https://docs.pydantic.dev/2.6/errors/usage_errors/#type-adapter-config-unused
        You also would ideally leave this as "False" anyways, because it is a performance cost every time the object is validated.
        Since user types are never actually created until reacting to a userspace message, we check their schema instead.

        We only want to do the validation step once, during configuration. Additionally, we only care if the default SCHEMA
        value doesn't validate against the rest of the SCHEMA - otherwise, user defaults are fine.

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema = self.generate_inner(schema['schema'])

        # Skip verification if there's not actually a default value
        # Users are free to use pydantic.Field's 'default_factory' if they want, but those values generally shouldn't be represented in schema
        # and we ideally don't want to call a function (which we would need to do for default_factory).
        if 'default' not in schema:
            return json_schema
        default = schema['default']

        try:
            encoded_default = self.encode_default(default)
        except PydanticSerializationError:
            # normally, Pydantic would only emit a warning here, but we'll error out.
            self.handle_invalid_for_json_schema(
                schema,
                f"Default value '{default}' is not JSON serializable; use pydantic.Field's 'default_factory' argument for this.",
            )

        if '$ref' in json_schema:
            # TODO - not best way to handle this
            # validate this default later, when all $refs have been resolved
            # IMPORTANT!!! You must send the "json_schema" object itself, it will be modified later internally by Pydantic
            self.intersect_sdk_postgeneration_defaults.append((encoded_default, json_schema))
            # Since reference schemas do not support child keys, we wrap the reference schema in a single-case allOf:
            return {'allOf': [json_schema], 'default': encoded_default}

        # if this schema does not have a $ref, we should instead validate immediately
        try:
            validate_against_schema(json_schema, encoded_default)
        except SchemaValidationError as e:
            err_msg = f"Default value '{default}' does not validate against schema\n{e}"
            raise PydanticInvalidForJsonSchema(err_msg) from e

        json_schema['default'] = encoded_default
        return json_schema

    def encode_default(self, dft: Any) -> Any:
        """Encode a default value to a JSON-serializable value.

        This is used to encode default values for fields in the generated JSON schema.

        OVERRIDE: overriding because Pydantic's implementation currently has an error when handling regular dataclass defaults.
        (This is a temporary fix, see https://github.com/pydantic/pydantic/issues/9253 to track this.)

        Args:
            dft: The default value to encode.

        Returns:
            The encoded default value.
        """
        config = self._config
        try:
            default = (
                dft
                if _type_has_config(type(dft))
                else TypeAdapter(type(dft), config=config.config_dict).dump_python(dft, mode='json')
            )
        except PydanticSchemaGenerationError as e:
            msg = f'Unable to encode default value {dft}'
            raise PydanticSerializationError(msg) from e

        return to_jsonable_python(
            default,
            timedelta_mode=config.ser_json_timedelta,
            bytes_mode=config.ser_json_bytes,
        )

    def typed_dict_schema(self, schema: core_schema.TypedDictSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a typed dict.

        OVERRIDE: make sure TypedDict class has at least one property, otherwise defer to Pydantic's handling

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema = super().typed_dict_schema(schema)
        if not json_schema.get('properties'):
            return self.handle_invalid_for_json_schema(
                schema, 'TypedDict (empty TypedDict not allowed in INTERSECT)'
            )
        return json_schema

    def model_schema(self, schema: core_schema.ModelSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a model.

        OVERRIDE: make sure BaseModel class has at least one property, otherwise defer to Pydantic's handling

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema = super().model_schema(schema)
        if not json_schema.get('properties'):
            return self.handle_invalid_for_json_schema(
                schema,
                f'pydantic.BaseModel "{schema["cls"].__name__}" (needs at least one property for INTERSECT)',
            )
        return json_schema

    def dataclass_schema(self, schema: core_schema.DataclassSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a dataclass.

        OVERRIDE: make sure dataclass has at least one property, otherwise defer to Pydantic's handling

        Args:
            schema: The core schema.

        Returns:
            The generated JSON schema.
        """
        json_schema = super().dataclass_schema(schema)
        if not json_schema.get('properties'):
            return self.handle_invalid_for_json_schema(
                schema,
                f'dataclass "{schema["cls"].__name__}" (needs at least one property for INTERSECT)',
            )
        return json_schema

    def kw_arguments_schema(
        self,
        arguments: list[core_schema.ArgumentsParameter],
        var_kwargs_schema: CoreSchema | None,
    ) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a function's keyword arguments.

        OVERRIDE: Make sure at least one argument is present, otherwise defer to Pydantic's handling. (This is done to ensure future compatibility, but it currently doesn't appear to be used by Pydantic.)

        Args:
            arguments: The core schema.
            var_kwargs_schema: The JSON schema for the function keyword arguments.

        Returns:
            The generated JSON schema.
        """
        if not arguments:
            err_msg = 'Cannot generate a JsonSchema for core_schema.ArgumentsSchema (missing keyword arguments, needed for INTERSECT)'
            raise PydanticInvalidForJsonSchema(err_msg)
        return super().kw_arguments_schema(arguments, var_kwargs_schema)

    def p_arguments_schema(
        self, arguments: list[core_schema.ArgumentsParameter], var_args_schema: CoreSchema | None
    ) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema that defines a function's positional arguments.

        OVERRIDE: Make sure at least one argument is present, otherwise defer to Pydantic's handling. This is used for NamedTuples.

        Args:
            arguments: The core schema.
            var_args_schema: The JSON schema for the function positional arguments.

        Returns:
            The generated JSON schema.
        """
        if not arguments:
            err_msg = 'Cannot generate a JsonSchema for core_schema.ArgumentsSchema (missing arguments, needed for INTERSECT - are you using a NamedTuple class with no properties?)'
            raise PydanticInvalidForJsonSchema(err_msg)
        return super().p_arguments_schema(arguments, var_args_schema)

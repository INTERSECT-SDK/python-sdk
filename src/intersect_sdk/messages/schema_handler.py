from jsonschema import ValidationError, validate, Validator

class SchemaHandler:
    def __init__(self, schema, schemaValidator = None) -> None:
        SchemaHandler.schema = schema
        SchemaHandler.validator = schemaValidator if schemaValidator is not None else Validator

    def check_schema():
        SchemaHandler.validator.check_schema(SchemaHandler.schema)
    
    def is_valid(arguments):
        SchemaHandler.validator(arguments, SchemaHandler.schema)
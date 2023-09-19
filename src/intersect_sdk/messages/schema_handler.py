import json
from jsonschema import ValidationError, validate, Validator

class SchemaHandler:
    def load_schema(schema, schemaValidator = None):
        SchemaHandler.schema = schema
        SchemaHandler.validator = schemaValidator if schemaValidator is not None else Validator

    def check_schema():
        SchemaHandler.validator.check_schema(SchemaHandler.schema)
    
    def is_valid(arguments):
        try:
            SchemaHandler.validator(arguments, SchemaHandler.schema)
            return True
        except ValidationError:
            return False
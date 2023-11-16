from jsonschema import validators


class SchemaHandler:
    def __init__(self, schema, schemaValidator=None, screen=None) -> None:
        self.schema = schema
        self.validator = schemaValidator if schemaValidator is not None else validators
        self.screen = screen

    def is_valid(self, arguments):
        self.validator.validate(arguments, self.schema)

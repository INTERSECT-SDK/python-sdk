import json
import pathlib

import jsonschema
import pytest
from intersect_sdk.messages import schema_handler

with open(pathlib.Path(__file__).parent / 'schema_examples/schema_example.json') as schemaf:
    goodSchema = json.loads('\n'.join(schemaf.readlines()))


def test_check_is_valid_bad_msg():
    bad_system_status_msg = {
        'SystemStatus': {
            'Header': {
                'SystemID': {'UUID': 'lmnop'},
                'Timestamp': '2023-08-15T20:20:39+00:00',
                'SchemaVersion': '1',
            },
            'MessageState': 'NEWs',
            'MessageData': {'SystemID': {'UUID': 'abc123'}, 'SystemState': 'OPERATIONAL'},
        }
    }
    schemaHandler = schema_handler.SchemaHandler(goodSchema)
    with pytest.raises(jsonschema.exceptions.ValidationError):
        schemaHandler.is_valid(bad_system_status_msg)


def test_check_is_valid_good_msg():
    good_system_status_msg = {
        'SystemStatus': {
            'Header': {
                'SystemID': {'UUID': 'lmnop'},
                'Timestamp': '2023-08-15T20:20:39+00:00',
                'SchemaVersion': '1',
            },
            'MessageState': 'NEW',
            'MessageData': {'SystemID': {'UUID': 'abc123'}, 'SystemState': 'OPERATIONAL'},
        }
    }
    schemaHandler = schema_handler.SchemaHandler(goodSchema)
    schemaHandler.is_valid(good_system_status_msg)

"""
UserspaceMessage validation testing
"""

import datetime
import uuid

import pytest
from intersect_sdk import IntersectDataHandler, IntersectMimeType, version_string
from intersect_sdk._internal.messages.userspace import (
    create_userspace_message,
    deserialize_and_validate_userspace_message,
)
from pydantic import ValidationError


def test_valid_userspace_message_deserializes():
    serialized = b'{"messageId":"cc88a2c9-7e47-409f-82c5-ef49914ae140","operationId":"operation","contentType":"application/json","payload":"payload","headers":{"source":"source","destination":"destination","sdk_version":"0.5.0","created_at":"2024-01-19T20:21:14.045591Z","data_handler":0}}'
    deserialized = deserialize_and_validate_userspace_message(serialized)
    assert deserialized['headers']['data_handler'] == IntersectDataHandler.MESSAGE
    assert deserialized['contentType'] == IntersectMimeType.JSON
    assert deserialized['headers']['has_error'] is False


def test_unusual_userspace_message_deserializes():
    serialized = b'{"messageId":"cc88a2c9-7e47-409f-82c5-ef49914ae140","operationId":"operation","contentType":"application/json","payload":"payload","headers":{"source":"source.one","destination":"destination.two","sdk_version":"0.5.0","created_at":"2024","data_handler":0}}'
    deserialized = deserialize_and_validate_userspace_message(serialized)
    assert deserialized['headers']['data_handler'] == IntersectDataHandler.MESSAGE
    assert deserialized['contentType'] == IntersectMimeType.JSON
    assert deserialized['headers']['has_error'] is False
    # even on strict mode, Pydantic can validate an integer as a string type, i.e. '"2024"' - it parses this as number of seconds since the Unix epoch
    assert deserialized['headers']['created_at'].year == 1970


def test_missing_does_not_deserialize():
    serialized = b'{}'
    with pytest.raises(ValidationError) as err:
        deserialize_and_validate_userspace_message(serialized)
    errors = err.value.errors()
    assert len(errors) == 4
    assert all(e['type'] == 'missing' for e in errors)
    locations = [e['loc'] for e in errors]
    assert ('messageId',) in locations
    assert ('payload',) in locations
    assert ('headers',) in locations
    assert ('operationId',) in locations


def test_missing_headers_properties_does_not_deserialize():
    serialized = b'{"messageId":"cc88a2c9-7e47-409f-82c5-ef49914ae140","operationId":"operation","contentType":"application/json","payload":"payload","headers":{}}'
    with pytest.raises(ValidationError) as err:
        deserialize_and_validate_userspace_message(serialized)
    errors = err.value.errors()
    assert len(errors) == 4
    assert all(e['type'] == 'missing' for e in errors)
    locations = [e['loc'] for e in errors]
    assert ('headers', 'source') in locations
    assert ('headers', 'destination') in locations
    assert ('headers', 'created_at') in locations
    assert ('headers', 'sdk_version') in locations


def test_invalid_does_not_deserialize():
    serialized = b'{"messageId":"notauuid","operationId":1,"contentType":"doesnotexist","payload":"payload","headers":{"source":"/","destination":"/","sdk_version":"1.0.0+20130313144700","created_at":"2024-01-19T20:21:14.045591","data_handler":-1}}'
    with pytest.raises(ValidationError) as err:
        deserialize_and_validate_userspace_message(serialized)
    errors = [{'type': e['type'], 'loc': e['loc']} for e in err.value.errors()]
    assert len(errors) == 8
    # value we have is a string, but not a UUID
    assert {'type': 'uuid_parsing', 'loc': ('messageId',)} in errors
    assert {'type': 'string_type', 'loc': ('operationId',)} in errors
    # '/' is not a valid character in a source string or destination string
    assert {'type': 'string_pattern_mismatch', 'loc': ('headers', 'source')} in errors
    assert {'type': 'string_pattern_mismatch', 'loc': ('headers', 'destination')} in errors
    # The datetime in the sample data is ALMOST valid, but lacks zone information!
    assert {'type': 'timezone_aware', 'loc': ('headers', 'created_at')} in errors
    # the sample versions here have build metadata or alpha release data in their strings, this is not valid for INTERSECT
    assert {'type': 'string_pattern_mismatch', 'loc': ('headers', 'sdk_version')} in errors
    # can't transpose these values into the enumerations
    assert {'type': 'enum', 'loc': ('headers', 'data_handler')} in errors
    assert {'type': 'enum', 'loc': ('contentType',)} in errors


def test_create_userspace_message():
    msg = create_userspace_message(
        source='source',
        destination='destination',
        operation_id='operation',
        content_type=IntersectMimeType.JSON,
        data_handler=IntersectDataHandler.MESSAGE,
        payload=[1, 2, 3],
    )
    assert isinstance(msg['messageId'], uuid.UUID)
    # rule of UUID-4 generation
    assert str(msg['messageId'])[14] == '4'
    assert msg['operationId'] == 'operation'
    assert msg['contentType'] == IntersectMimeType.JSON
    assert msg['payload'] == [1, 2, 3]
    assert isinstance(msg['headers']['created_at'], datetime.datetime)
    # enforce UTC
    assert msg['headers']['created_at'].tzinfo == datetime.timezone.utc
    assert msg['headers']['data_handler'] == IntersectDataHandler.MESSAGE
    assert msg['headers']['sdk_version'] == version_string
    assert msg['headers']['source'] == 'source'
    assert msg['headers']['destination'] == 'destination'

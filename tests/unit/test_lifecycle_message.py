"""
LifecycleMessage validation testing
"""

import datetime
import uuid

import pytest
from intersect_sdk import version_string
from intersect_sdk._internal.messages.lifecycle import (
    LifecycleType,
    create_lifecycle_message,
    deserialize_and_validate_lifecycle_message,
)
from pydantic import ValidationError


def test_valid_lifecycle_message_deserializes():
    serialized = b'{"messageId":"cc88a2c9-7e47-409f-82c5-ef49914ae140","contentType":"application/json","payload":"payload","headers":{"source":"source","destination":"destination","sdk_version":"0.5.0","created_at":"2024-01-19T20:21:14.045591Z","lifecycle_type":0}}'
    deserialized = deserialize_and_validate_lifecycle_message(serialized)
    assert deserialized['headers']['lifecycle_type'] == LifecycleType.STARTUP
    assert deserialized['contentType'] == 'application/json'


def test_unusual_lifecycle_message_deserializes():
    serialized = b'{"messageId":"cc88a2c9-7e47-409f-82c5-ef49914ae140","contentType":"application/json","payload":"payload","headers":{"source":"source.one","destination":"destination.two","sdk_version":"0.5.0","created_at":"2024","lifecycle_type":0}}'
    deserialized = deserialize_and_validate_lifecycle_message(serialized)
    assert deserialized['headers']['lifecycle_type'] == LifecycleType.STARTUP
    assert deserialized['contentType'] == 'application/json'
    # even on strict mode, Pydantic can validate an integer as a string type, i.e. '"2024"' - it parses this as number of seconds since the Unix epoch
    assert deserialized['headers']['created_at'].year == 1970


def test_missing_does_not_deserialize():
    serialized = b'{}'
    with pytest.raises(ValidationError) as err:
        deserialize_and_validate_lifecycle_message(serialized)
    errors = err.value.errors()
    assert len(errors) == 3
    assert all(e['type'] == 'missing' for e in errors)
    locations = [e['loc'] for e in errors]
    assert ('messageId',) in locations
    assert ('payload',) in locations
    assert ('headers',) in locations


def test_missing_headers_properties_does_not_deserialize():
    serialized = b'{"messageId":"cc88a2c9-7e47-409f-82c5-ef49914ae140","contentType":"application/json","payload":"payload","headers":{}}'
    with pytest.raises(ValidationError) as err:
        deserialize_and_validate_lifecycle_message(serialized)
    errors = err.value.errors()
    assert len(errors) == 5
    assert all(e['type'] == 'missing' for e in errors)
    locations = [e['loc'] for e in errors]
    assert ('headers', 'source') in locations
    assert ('headers', 'destination') in locations
    assert ('headers', 'created_at') in locations
    assert ('headers', 'sdk_version') in locations
    assert ('headers', 'lifecycle_type') in locations


def test_invalid_does_not_deserialize():
    serialized = b'{"messageId":"notauuid","contentType":"doesnotexist","payload":"payload","headers":{"source":"/","destination":"/","sdk_version":"1.0.0+20130313144700","created_at":"2024-01-19T20:21:14.045591","lifecycle_type":-1}}'
    with pytest.raises(ValidationError) as err:
        deserialize_and_validate_lifecycle_message(serialized)
    errors = [{'type': e['type'], 'loc': e['loc']} for e in err.value.errors()]
    assert len(errors) == 7
    # value we have is a string, but not a UUID
    assert {'type': 'uuid_parsing', 'loc': ('messageId',)} in errors
    # '/' is not a valid character in a source string or destination string
    assert {'type': 'string_pattern_mismatch', 'loc': ('headers', 'source')} in errors
    assert {'type': 'string_pattern_mismatch', 'loc': ('headers', 'destination')} in errors
    # The datetime in the sample data is ALMOST valid, but lacks zone information!
    assert {'type': 'timezone_aware', 'loc': ('headers', 'created_at')} in errors
    # the sample versions here have build metadata or alpha release data in their strings, this is not valid for INTERSECT
    assert {'type': 'string_pattern_mismatch', 'loc': ('headers', 'sdk_version')} in errors
    # can't transpose these values into the enumerations
    assert {'type': 'enum', 'loc': ('headers', 'lifecycle_type')} in errors
    assert {'type': 'literal_error', 'loc': ('contentType',)} in errors


def test_create_lifecycle_message():
    msg = create_lifecycle_message(
        source='source',
        destination='destination',
        lifecycle_type=LifecycleType.SHUTDOWN,
        payload=[1, 2, 3],
    )
    assert isinstance(msg['messageId'], uuid.UUID)
    # rule of UUID-4 generation
    assert str(msg['messageId'])[14] == '4'
    assert msg['contentType'] == 'application/json'
    assert msg['payload'] == [1, 2, 3]
    assert isinstance(msg['headers']['created_at'], datetime.datetime)
    # enforce UTC
    assert msg['headers']['created_at'].tzinfo == datetime.timezone.utc
    assert msg['headers']['lifecycle_type'] == LifecycleType.SHUTDOWN
    assert msg['headers']['sdk_version'] == version_string
    assert msg['headers']['source'] == 'source'
    assert msg['headers']['destination'] == 'destination'

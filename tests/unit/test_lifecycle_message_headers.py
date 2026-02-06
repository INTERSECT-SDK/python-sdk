"""
lifecycle message header validation testing
"""

import datetime
import uuid

import pytest
from pydantic import ValidationError

from intersect_sdk import version_string
from intersect_sdk._internal.messages.lifecycle import (
    create_lifecycle_message_headers,
    validate_lifecycle_message_headers,
)


def test_valid_lifecycle_message_deserializes() -> None:
    raw_headers = {
        'message_id': 'cc88a2c9-7e47-409f-82c5-ef49914ae140',
        'source': 'source',
        'sdk_version': '0.5.0',
        'created_at': '2024-01-19T20:21:14.045591Z',
        'lifecycle_type': 'LCT_STARTUP',
    }
    headers = validate_lifecycle_message_headers(raw_headers)
    assert isinstance(headers.message_id, uuid.UUID)
    assert isinstance(headers.created_at, datetime.datetime)
    assert headers.created_at.year == 2024


def test_unusual_lifecycle_message_deserializes() -> None:
    raw_headers = {
        'message_id': 'cc88a2c9-7e47-409f-82c5-ef49914ae140',
        'source': 'source.one',
        'sdk_version': '0.5.0',
        'created_at': '2024',
        'lifecycle_type': 'LCT_STARTUP',
    }
    headers = validate_lifecycle_message_headers(raw_headers)
    # even on strict mode, Pydantic can validate an integer as a string type, i.e. '"2024"' - it parses this as number of seconds since the Unix epoch
    assert headers.created_at.year == 1970


def test_missing_does_not_deserialize() -> None:
    raw_headers: dict[str, str] = {}
    with pytest.raises(ValidationError) as err:
        validate_lifecycle_message_headers(raw_headers)
    errors = err.value.errors()
    assert len(errors) == 5
    assert all(e['type'] == 'missing' for e in errors)
    locations = [e['loc'] for e in errors]
    assert ('message_id',) in locations
    assert ('source',) in locations
    assert ('lifecycle_type',) in locations
    assert ('sdk_version',) in locations
    assert ('created_at',) in locations


def test_invalid_does_not_deserialize() -> None:
    raw_headers = {
        'message_id': 'not_a_uuid',
        'source': '/',
        'sdk_version': '1.0.0+20130313144700',
        'created_at': '2024-01-19T20:21:14.045591',
        'lifecycle_type': 'NOT_A_LIFECYCLE_TYPE',
    }
    with pytest.raises(ValidationError) as err:
        validate_lifecycle_message_headers(raw_headers)
    errors = [{'type': e['type'], 'loc': e['loc']} for e in err.value.errors()]
    assert len(errors) == 5
    # value we have is a string, but not a UUID
    assert {'type': 'uuid_parsing', 'loc': ('message_id',)} in errors
    # '/' is not a valid character in a source string
    assert {'type': 'string_pattern_mismatch', 'loc': ('source',)} in errors
    # The datetime in the sample data is ALMOST valid, but lacks zone information!
    assert {'type': 'timezone_aware', 'loc': ('created_at',)} in errors
    # the sample versions here have build metadata or alpha release data in their strings, this is not valid for INTERSECT
    assert {'type': 'string_pattern_mismatch', 'loc': ('sdk_version',)} in errors
    # can't transpose these values into the enumerations
    assert {'type': 'literal_error', 'loc': ('lifecycle_type',)} in errors


def test_create_lifecycle_message() -> None:
    msg = create_lifecycle_message_headers(
        source='source',
        lifecycle_type='LCT_SHUTDOWN',
    )

    # make sure all values are serialized as strings, this is necessary for some protocols i.e. MQTT5 Properties
    for value in msg.values():
        assert isinstance(value, str)

    # rule of UUID-4 generation
    assert msg['message_id'][14] == '4'
    assert len(msg['message_id']) == 36
    # enforce UTC
    assert msg['created_at'][-6:] == '+00:00'
    assert msg['lifecycle_type'] == 'LCT_SHUTDOWN'
    assert msg['sdk_version'] == version_string
    assert msg['source'] == 'source'

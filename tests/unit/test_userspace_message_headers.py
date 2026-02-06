"""
userspace message header validation testing
"""

import datetime
import uuid

import pytest
from pydantic import ValidationError

from intersect_sdk import IntersectDataHandler, version_string
from intersect_sdk._internal.messages.userspace import (
    create_userspace_message_headers,
    validate_userspace_message_headers,
)


def test_valid_userspace_message_deserializes() -> None:
    raw_headers = {
        'message_id': 'cc88a2c9-7e47-409f-82c5-ef49914ae140',
        'campaign_id': 'dd88a2c9-7e47-409f-82c5-ef49914ae141',
        'request_id': 'ee88a2c9-7e47-409f-82c5-ef49914ae142',
        'operation_id': 'operation',
        'source': 'source',
        'destination': 'destination',
        'sdk_version': '0.5.0',
        'created_at': '2024-01-19T20:21:14.045591Z',
    }
    headers = validate_userspace_message_headers(raw_headers)
    # check defaults
    assert headers.data_handler == IntersectDataHandler.MESSAGE
    assert headers.has_error is False
    # check type serializations
    assert isinstance(headers.message_id, uuid.UUID)
    assert isinstance(headers.created_at, datetime.datetime)
    assert headers.created_at.year == 2024


def test_unusual_userspace_message_deserializes() -> None:
    raw_headers = {
        'message_id': 'cc88a2c9-7e47-409f-82c5-ef49914ae140',
        'campaign_id': 'dd88a2c9-7e47-409f-82c5-ef49914ae141',
        'request_id': 'ee88a2c9-7e47-409f-82c5-ef49914ae142',
        'operation_id': 'operation',
        'source': 'source.one',
        'destination': 'destination.two',
        'sdk_version': '0.5.0',
        'created_at': '2024',
        'data_handler': 'MINIO',
        'has_error': 'true',
    }
    headers = validate_userspace_message_headers(raw_headers)
    assert headers.data_handler == IntersectDataHandler.MINIO
    assert headers.has_error is True
    # even on strict mode, Pydantic can validate an integer as a string type, i.e. '"2024"' - it parses this as number of seconds since the Unix epoch
    assert headers.created_at.year == 1970


def test_missing_does_not_deserialize() -> None:
    raw_headers: dict[str, str] = {}
    with pytest.raises(ValidationError) as err:
        validate_userspace_message_headers(raw_headers)
    errors = err.value.errors()
    assert len(errors) == 8
    assert all(e['type'] == 'missing' for e in errors)
    locations = [e['loc'] for e in errors]
    assert ('message_id',) in locations
    assert ('campaign_id',) in locations
    assert ('request_id',) in locations
    assert ('operation_id',) in locations
    assert ('source',) in locations
    assert ('destination',) in locations
    assert ('sdk_version',) in locations
    assert ('created_at',) in locations


def test_invalid_does_not_deserialize() -> None:
    raw_headers = {
        'message_id': 'not_a_uuid',
        'campaign_id': 'also_not_a_uuid',
        'request_id': 'definitely_not_a_uuid',
        'operation_id': 1,
        'source': '/',
        'destination': '/',
        'sdk_version': '1.0.0+20130313144700',
        'created_at': '2024-01-19T20:21:14.045591',
        'data_handler': 'COBOL',
        'has_error': 'I_AM_NOT_A_BOOLEAN',
    }
    with pytest.raises(ValidationError) as err:
        validate_userspace_message_headers(raw_headers)
    errors = [{'type': e['type'], 'loc': e['loc']} for e in err.value.errors()]
    assert len(errors) == 10
    # value we have is a string, but not a UUID
    assert {'type': 'uuid_parsing', 'loc': ('message_id',)} in errors
    assert {'type': 'uuid_parsing', 'loc': ('request_id',)} in errors
    assert {'type': 'uuid_parsing', 'loc': ('campaign_id',)} in errors
    assert {'type': 'string_type', 'loc': ('operation_id',)} in errors
    # '/' is not a valid character in a source string or destination string
    assert {'type': 'string_pattern_mismatch', 'loc': ('source',)} in errors
    assert {'type': 'string_pattern_mismatch', 'loc': ('destination',)} in errors
    # The datetime in the sample data is ALMOST valid, but lacks zone information!
    assert {'type': 'timezone_aware', 'loc': ('created_at',)} in errors
    # the sample versions here have build metadata or alpha release data in their strings, this is not valid for INTERSECT
    assert {'type': 'string_pattern_mismatch', 'loc': ('sdk_version',)} in errors
    # can't transpose these values into the enumerations
    assert {'type': 'enum', 'loc': ('data_handler',)} in errors


def test_create_userspace_message() -> None:
    msg = create_userspace_message_headers(
        source='source',
        destination='destination',
        operation_id='operation',
        data_handler=IntersectDataHandler.MESSAGE,
        request_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
    )

    # make sure all values are serialized as strings, this is necessary for some protocols i.e. MQTT5 Properties
    for value in msg.values():
        assert isinstance(value, str)

    # rule of UUID-4 generation
    assert str(msg['message_id'])[14] == '4'
    assert len(msg['message_id']) == 36
    assert str(msg['request_id'])[14] == '4'
    assert len(msg['request_id']) == 36
    assert str(msg['campaign_id'])[14] == '4'
    assert len(msg['campaign_id']) == 36
    # enforce UTC
    assert msg['created_at'][-6:] == '+00:00'
    # this should be lowercase for maximum language capability
    assert msg['has_error'] == 'false'
    assert msg['operation_id'] == 'operation'
    assert msg['data_handler'] == 'MESSAGE'
    assert msg['sdk_version'] == version_string
    assert msg['source'] == 'source'
    assert msg['destination'] == 'destination'

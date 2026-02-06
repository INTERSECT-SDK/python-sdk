"""
Integration tests with one service; the ControlPlaneManager is used to mock responses.

To run the integration tests, you will need a connection to the broker and MINIO.

NOTE: do NOT write assert statements in the callbacks; if the assert fails, the test will hang
instead, initialize an array with one value in it, then change the value inside the callback
"""

import json
import time
from uuid import uuid4

from intersect_sdk import (
    ControlPlaneConfig,
    DataStoreConfig,
    DataStoreConfigMap,
    IntersectDataHandler,
    IntersectService,
    IntersectServiceConfig,
)
from intersect_sdk._internal.control_plane.control_plane_manager import ControlPlaneManager
from intersect_sdk._internal.data_plane.minio_utils import MinioPayload, get_minio_object
from intersect_sdk._internal.messages.lifecycle import (
    validate_lifecycle_message_headers,
)
from intersect_sdk._internal.messages.userspace import (
    create_userspace_message_headers,
    validate_userspace_message_headers,
)
from tests.fixtures.example_schema import FAKE_HIERARCHY_CONFIG, DummyCapabilityImplementation

# HELPERS #############################


def make_intersect_service() -> IntersectService:
    return IntersectService(
        [DummyCapabilityImplementation()],
        IntersectServiceConfig(
            hierarchy=FAKE_HIERARCHY_CONFIG,
            data_stores=DataStoreConfigMap(
                minio=[
                    DataStoreConfig(
                        username='AKIAIOSFODNN7EXAMPLE',
                        password='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                        port=9000,
                    )
                ]
            ),
            brokers=[
                ControlPlaneConfig(
                    username='intersect_username',
                    password='intersect_password',
                    port=1883,
                    protocol='mqtt5.0',
                ),
            ],
            status_interval=30.0,
        ),
    )


def make_message_interceptor() -> ControlPlaneManager:
    return ControlPlaneManager(
        [
            ControlPlaneConfig(
                username='intersect_username',
                password='intersect_password',
                port=1883,
                protocol='mqtt5.0',
            )
        ],
    )


# TESTS ################


def test_control_plane_connections() -> None:
    intersect_service = make_intersect_service()
    # make sure to wait a bit between each startup/shutdown call
    assert intersect_service.is_connected() is False
    intersect_service.startup()
    time.sleep(1.0)
    assert intersect_service.is_connected() is True
    intersect_service.shutdown()
    time.sleep(1.0)
    assert intersect_service.is_connected() is False

    channels = intersect_service._control_plane_manager.get_subscription_channels()
    # we have two channels (even if we're disconnected) ...
    assert len(channels) == 2
    # ... and one callback function for each channel
    channel_keys = []
    for channel_key in iter(channels):
        channel_keys.append(channel_key)
        assert len(channels[channel_key].callbacks) == 1

    for channel_key in channel_keys:
        intersect_service._control_plane_manager.remove_subscription_channel(channel_key)
    assert len(intersect_service._control_plane_manager.get_subscription_channels()) == 0


# normal test that the user function can be called
def test_call_user_function() -> None:
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None, None, None]

    campaign_id = uuid4()
    request_id = uuid4()

    def userspace_msg_callback(
        payload: bytes, content_type: str, raw_headers: dict[str, str]
    ) -> None:
        msg[0] = payload
        msg[1] = content_type
        msg[2] = validate_userspace_message_headers(raw_headers)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        b'[4,6]',
        'application/json',
        create_userspace_message_headers(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.calculate_fibonacci',
            campaign_id=campaign_id,
            request_id=request_id,
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    assert msg[0] == b'[5,8,13]'
    # make sure header IDs were not modified
    assert msg[2]['request_id'] == request_id
    assert msg[2]['campaign_id'] == campaign_id


# call a @staticmethod user function, which should work as normal
def test_call_static_user_function() -> None:
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None, None, None]

    def userspace_msg_callback(
        payload: bytes, content_type: str, raw_headers: dict[str, str]
    ) -> None:
        msg[0] = payload
        msg[1] = content_type
        msg[2] = validate_userspace_message_headers(raw_headers)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        b'"res"',
        'application/json',
        create_userspace_message_headers(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.test_generator',
            campaign_id=uuid4(),
            request_id=uuid4(),
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    assert msg[0] == b'[114,215,330,101,216,115]'


def test_call_user_function_with_default_and_empty_payload() -> None:
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None, None, None]

    def userspace_msg_callback(
        payload: bytes, content_type: str, raw_headers: dict[str, str]
    ) -> None:
        msg[0] = payload
        msg[1] = content_type
        msg[2] = validate_userspace_message_headers(raw_headers)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        b'null',  # the SDK will call the function's default value if "null" is passed as an argument
        'application/json',
        create_userspace_message_headers(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.valid_default_argument',
            campaign_id=uuid4(),
            request_id=uuid4(),
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    assert msg[0] == b'8'


# call a user function with invalid parameters (so Pydantic will catch the error and pass it to the message interceptor)
def test_call_user_function_with_invalid_payload() -> None:
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None, None, None]

    def userspace_msg_callback(
        payload: bytes, content_type: str, raw_headers: dict[str, str]
    ) -> None:
        msg[0] = payload
        msg[1] = content_type
        msg[2] = validate_userspace_message_headers(raw_headers)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        b'[2]',
        'application/json',
        create_userspace_message_headers(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.calculate_fibonacci',
            campaign_id=uuid4(),
            request_id=uuid4(),
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    assert msg[2].has_error is True
    assert b'Bad arguments to application' in msg[0]
    assert b'validation error for tuple[int, int]' in msg[0]


# try to call an operation which doesn't exist - we'll get an error message back
def test_call_nonexistent_user_function() -> None:
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None, None, None]

    # in this case, the message payload will be a Pydantic error (as our payload was invalid, but the operation was valid)
    def userspace_msg_callback(
        payload: bytes, content_type: str, raw_headers: dict[str, str]
    ) -> None:
        msg[0] = payload
        msg[1] = content_type
        msg[2] = validate_userspace_message_headers(raw_headers)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        b'null',
        'application/json',
        create_userspace_message_headers(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.THIS_FUNCTION_DOES_NOT_EXIST',
            campaign_id=uuid4(),
            request_id=uuid4(),
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    assert msg[2].has_error is True
    assert b'Tried to call non-existent operation' in msg[0]


# make sure that exceptions propagate appropriately, based on whether or not IntersectCapabilityException is explicitly thrown
def test_exception_propagation() -> None:
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = []

    def userspace_msg_callback(
        payload: bytes, content_type: str, raw_headers: dict[str, str]
    ) -> None:
        msg.append((payload, content_type, validate_userspace_message_headers(raw_headers)))

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    # divide by zero message which does NOT propagate
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        b'-1',
        'application/json',
        create_userspace_message_headers(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.divide_by_zero_exceptions',
            campaign_id=uuid4(),
            request_id=uuid4(),
        ),
        True,
    )
    # divide by zero message which DOES propagate
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        b'1',
        'application/json',
        create_userspace_message_headers(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.divide_by_zero_exceptions',
            campaign_id=uuid4(),
            request_id=uuid4(),
        ),
        True,
    )
    # sanity check for message propagation without param
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        b'null',
        'application/json',
        create_userspace_message_headers(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.raise_exception_no_param',
            campaign_id=uuid4(),
            request_id=uuid4(),
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    assert msg[0][2].has_error is True
    assert msg[0][0] == b'Service domain logic threw exception.'
    assert msg[1][2].has_error is True
    assert msg[1][0] == b'Service domain logic threw explicit exception:\ndivision by zero'
    assert msg[2][2].has_error is True
    assert (
        msg[2][0]
        == b'Service domain logic threw explicit exception:\nI should not exist in production!'
    )


# this function is just here to ensure the MINIO workflow is correct
def test_call_minio_user_function() -> None:
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None, None, None]

    def userspace_msg_callback(
        payload: bytes, content_type: str, raw_headers: dict[str, str]
    ) -> None:
        msg[0] = payload
        msg[1] = content_type
        msg[2] = validate_userspace_message_headers(raw_headers)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        b'"1970-01-01T00:00:00Z"',
        'application/json',
        create_userspace_message_headers(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.test_datetime',
            campaign_id=uuid4(),
            request_id=uuid4(),
        ),
        True,
    )
    time.sleep(5.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    minio_payload: MinioPayload = json.loads(msg[0])
    assert msg[2].data_handler == IntersectDataHandler.MINIO
    actual_data_str = get_minio_object(
        intersect_service._data_plane_manager._minio_providers[0], minio_payload
    ).decode()
    assert 'since 1970-01-01 00:00:00+00:00' in actual_data_str


# Listen for "startup" and "shutdown" lifecycle messages, as well as a status update message and a polling
#
# NOTE: this test deliberately takes over a minute to run, due to how POLLING works.
#
# NOTE: we are NOT listening for FUNCTIONS_ALLOWED or FUNCTIONS_BLOCKED messages here because that API is subject to change
def test_lifecycle_messages() -> None:
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    messages = []

    def lifecycle_msg_callback(
        payload: bytes, content_type: str, raw_headers: dict[str, str]
    ) -> None:
        messages.append(
            (json.loads(payload), content_type, validate_lifecycle_message_headers(raw_headers))
        )

    message_interceptor.add_subscription_channel(
        'test/test/test/test/test/lifecycle', {lifecycle_msg_callback}, False
    )
    # we do not really care about the userspace message response, but we'll listen to it to consume it
    message_interceptor.add_subscription_channel('msg/msg/msg/msg/msg/response', set(), False)
    message_interceptor.connect()
    # sleep a moment to make sure message_interceptor catches the startup message
    time.sleep(1.0)
    intersect_service.startup()
    # startup message should include a "default state" for the status, make sure we get it before we publish our message
    time.sleep(3.0)
    # send a message to make sure the next status update will be different (just the way the example service's domain works, not intrinsic)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        b'{"1.2":"one point two"}',
        'application/json',
        create_userspace_message_headers(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.verify_float_dict',
            # note that the dict key MUST be a string, even though the input wants a float key
            campaign_id=uuid4(),
            request_id=uuid4(),
        ),
        True,
    )
    # sleep a bit over 60 seconds to make sure we get the polling message with the new status
    time.sleep(62.0)

    intersect_service.shutdown('I want to shutdown')
    # sleep to get the shutdown message
    time.sleep(1.0)
    message_interceptor.disconnect()

    assert len(messages) == 3

    assert messages[0][2].lifecycle_type == 'LCT_STARTUP'
    assert 'schema' in messages[0][0]

    assert messages[1][2].lifecycle_type == 'LCT_POLLING'
    assert 'schema' in messages[1][0]

    assert messages[2][2].lifecycle_type == 'LCT_SHUTDOWN'
    assert 'I want to shutdown' in messages[2][0]

    # make sure both the universal capability and the test capability show up in the first two messages
    for i in range(2):
        assert list(messages[i][0]['status'].keys()) == ['intersect_sdk', 'DummyCapability']

    # check the status values of the DummyCapability (the INTERSECT-SDK capability's status values are too variable)
    assert messages[0][0]['status']['DummyCapability'] == {
        'functions_called': 0,
        'last_function_called': '',
    }
    assert messages[1][0]['status']['DummyCapability'] == {
        'functions_called': 1,
        'last_function_called': 'verify_float_dict',
    }

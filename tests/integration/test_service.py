"""
Integration tests with one service; the ControlPlaneManager is used to mock responses.

To run the integration tests, you will need a connection to the broker and MINIO.

NOTE: do NOT write assert statements in the callbacks; if the assert fails, the test will hang
instead, initialize an array with one value in it, then change the value inside the callback
"""

import time
from typing import List

from intersect_sdk import (
    ControlPlaneConfig,
    DataStoreConfig,
    DataStoreConfigMap,
    IntersectDataHandler,
    IntersectMimeType,
    IntersectService,
    IntersectServiceConfig,
)
from intersect_sdk._internal.control_plane.control_plane_manager import ControlPlaneManager
from intersect_sdk._internal.data_plane.minio_utils import MinioPayload, get_minio_object
from intersect_sdk._internal.messages.lifecycle import (
    LifecycleMessage,
    LifecycleType,
    deserialize_and_validate_lifecycle_message,
)
from intersect_sdk._internal.messages.userspace import (
    UserspaceMessage,
    create_userspace_message,
    deserialize_and_validate_userspace_message,
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
                    protocol='mqtt3.1.1',
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
                protocol='mqtt3.1.1',
            )
        ],
    )


# TESTS ################


def test_control_plane_connections():
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
def test_call_user_function():
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None]

    def userspace_msg_callback(payload: bytes) -> None:
        msg[0] = deserialize_and_validate_userspace_message(payload)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        create_userspace_message(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            content_type=IntersectMimeType.JSON,
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.calculate_fibonacci',
            payload=b'[4,6]',
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    msg: UserspaceMessage = msg[0]
    assert msg['payload'] == b'[5,8,13]'


# call a @staticmethod user function, which should work as normal
def test_call_static_user_function():
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None]

    def userspace_msg_callback(payload: bytes) -> None:
        msg[0] = deserialize_and_validate_userspace_message(payload)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        create_userspace_message(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            content_type=IntersectMimeType.JSON,
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.test_generator',
            payload=b'"res"',
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    msg: UserspaceMessage = msg[0]
    assert msg['payload'] == b'[114,215,330,101,216,115]'


def test_call_user_function_with_default_and_empty_payload():
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None]

    def userspace_msg_callback(payload: bytes) -> None:
        msg[0] = deserialize_and_validate_userspace_message(payload)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        create_userspace_message(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            content_type=IntersectMimeType.JSON,
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.valid_default_argument',
            payload=b'null',  # if sending null as the payload, the SDK will call the function's default value
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    msg: UserspaceMessage = msg[0]
    assert msg['payload'] == b'8'


# call a user function with invalid parameters (so Pydantic will catch the error and pass it to the message interceptor)
def test_call_user_function_with_invalid_payload():
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None]

    def userspace_msg_callback(payload: bytes) -> None:
        msg[0] = deserialize_and_validate_userspace_message(payload)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        create_userspace_message(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            content_type=IntersectMimeType.JSON,
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.calculate_fibonacci',
            # calculate_fibonacci takes in a tuple of two integers but we'll just send it one
            payload=b'[2]',
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    msg: UserspaceMessage = msg[0]
    assert msg['headers']['has_error'] is True
    assert b'Bad arguments to application' in msg['payload']
    assert b'validation error for tuple[int, int]' in msg['payload']


# try to call an operation which doesn't exist - we'll get an error message back
def test_call_nonexistent_user_function():
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None]

    # in this case, the message payload will be a Pydantic error (as our payload was invalid, but the operation was valid)
    def userspace_msg_callback(payload: bytes) -> None:
        msg[0] = deserialize_and_validate_userspace_message(payload)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        create_userspace_message(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            content_type=IntersectMimeType.JSON,
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.THIS_FUNCTION_DOES_NOT_EXIST',
            payload=b'null',
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    msg: UserspaceMessage = msg[0]
    assert msg['headers']['has_error'] is True
    assert b'Tried to call non-existent operation' in msg['payload']


# this function is just here to ensure the MINIO workflow is correct
def test_call_minio_user_function():
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    msg = [None]

    def userspace_msg_callback(payload: bytes) -> None:
        msg[0] = deserialize_and_validate_userspace_message(payload)

    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {userspace_msg_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        create_userspace_message(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            content_type=IntersectMimeType.JSON,
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.test_datetime',
            payload=b'"1970-01-01T00:00:00Z"',
        ),
        True,
    )
    time.sleep(5.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    msg: UserspaceMessage = msg[0]
    minio_payload: MinioPayload = msg['payload']
    assert msg['headers']['data_handler'] == IntersectDataHandler.MINIO
    actual_data_str = get_minio_object(
        intersect_service._data_plane_manager._minio_providers[0], minio_payload
    ).decode()
    assert 'since 1970-01-01 00:00:00+00:00' in actual_data_str


# Listen for "startup" and "shutdown" lifecycle messages, as well as a status update message and a polling
#
# NOTE: this test deliberately takes over a minute to run, due to how POLLING works.
#
# NOTE: we are NOT listening for FUNCTIONS_ALLOWED or FUNCTIONS_BLOCKED messages here because that API is subject to change
def test_lifecycle_messages():
    intersect_service = make_intersect_service()
    message_interceptor = make_message_interceptor()
    messages: List[LifecycleMessage] = []

    def lifecycle_msg_callback(payload: bytes) -> None:
        messages.append(deserialize_and_validate_lifecycle_message(payload))

    message_interceptor.add_subscription_channel(
        'test/test/test/test/test/lifecycle', {lifecycle_msg_callback}, False
    )
    # we do not really care about the userspace message response, but we'll listen to it to consume it
    message_interceptor.add_subscription_channel('msg/msg/msg/msg/msg/response', set(), False)
    message_interceptor.connect()
    # sleep a moment to make sure message_interceptor catches the startup message
    time.sleep(1.0)
    intersect_service.startup()
    # sleep a bit over 60 seconds to make sure we get the polling message
    time.sleep(62.0)

    # send a message to trigger a status update (just the way the example service's domain works, not intrinsic)
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        create_userspace_message(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            content_type=IntersectMimeType.JSON,
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.verify_float_dict',
            # note that the dict key MUST be a string, even though the input wants a float key
            payload=b'{"1.2":"one point two"}',
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown('I want to shutdown')
    # sleep to get the shutdown message
    time.sleep(1.0)
    message_interceptor.disconnect()

    assert len(messages) == 4

    assert messages[0]['headers']['lifecycle_type'] == LifecycleType.STARTUP
    assert 'schema' in messages[0]['payload']

    assert messages[1]['headers']['lifecycle_type'] == LifecycleType.POLLING
    assert 'schema' in messages[1]['payload']

    assert messages[2]['headers']['lifecycle_type'] == LifecycleType.STATUS_UPDATE
    assert 'schema' in messages[2]['payload']

    assert messages[3]['headers']['lifecycle_type'] == LifecycleType.SHUTDOWN
    assert 'I want to shutdown' in messages[3]['payload']

    assert messages[0]['payload']['status'] == messages[1]['payload']['status']
    assert messages[0]['payload']['status'] != messages[2]['payload']['status']

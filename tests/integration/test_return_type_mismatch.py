"""
Integration tests with one service; the ControlPlaneManager is used to mock responses.

To run the integration tests, you will need a connection to the broker and MINIO.

NOTE: do NOT write assert statements in the callbacks; if the assert fails, the test will hang
instead, initialize an array with one value in it, then change the value inside the callback
"""

import time

from intersect_sdk import (
    ControlPlaneConfig,
    DataStoreConfig,
    DataStoreConfigMap,
    IntersectBaseCapabilityImplementation,
    IntersectDataHandler,
    IntersectMimeType,
    IntersectService,
    IntersectServiceConfig,
    intersect_message,
)
from intersect_sdk._internal.control_plane.control_plane_manager import (
    ControlPlaneManager,
)
from intersect_sdk._internal.messages.userspace import (
    UserspaceMessage,
    create_userspace_message,
    deserialize_and_validate_userspace_message,
)

from tests.fixtures.example_schema import FAKE_HIERARCHY_CONFIG

# FIXTURE #############################


class ReturnTypeMismatchCapabilityImplementation(IntersectBaseCapabilityImplementation):
    intersect_sdk_capability_name = 'ReturnTypeMismatchCapability'

    @intersect_message()
    def wrong_return_annotation(self, param: int) -> int:
        return 'this is not an integer!'


# HELPERS #############################


def make_intersect_service() -> IntersectService:
    capability = ReturnTypeMismatchCapabilityImplementation()
    return IntersectService(
        [capability],
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


# the service is not fulfilling its schema contract in the return value, so we get an error message back
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
            operation_id='ReturnTypeMismatchCapability.wrong_return_annotation',
            # calculate_fibonacci takes in a tuple of two integers but we'll just send it one
            payload=b'2',
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    msg: UserspaceMessage = msg[0]
    assert msg['headers']['has_error'] is True
    assert b'Service domain logic threw exception.' in msg['payload']

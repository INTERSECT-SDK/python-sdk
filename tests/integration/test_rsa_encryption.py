"""
Integration tests for RSA encryption between service and client.

These tests verify end-to-end RSA encryption functionality including:
- Service-to-client encrypted responses
- Client-to-service encrypted requests
- Public key exchange mechanism
- Decryption of encrypted messages

To run these integration tests, you will need a connection to the broker and MINIO.

NOTE: do NOT write assert statements in the callbacks; if the assert fails, the test will hang
instead, initialize an array with one value in it, then change the value inside the callback
"""

import time
from uuid import uuid4

from pydantic import BaseModel

from intersect_sdk import (
    ControlPlaneConfig,
    DataStoreConfig,
    DataStoreConfigMap,
    IntersectClient,
    IntersectDataHandler,
    IntersectService,
    IntersectServiceConfig,
)
from intersect_sdk._internal.control_plane.control_plane_manager import ControlPlaneManager
from intersect_sdk._internal.messages.userspace import (
    create_userspace_message_headers,
    validate_userspace_message_headers,
)
from tests.fixtures.example_schema import FAKE_HIERARCHY_CONFIG, DummyCapabilityImplementation
from cryptography.hazmat.primitives import serialization

# HELPERS #############################

def make_intersect_service_with_rsa() -> IntersectService:
    """Create an IntersectService with RSA encryption enabled.
    
    Note: RSA keys are automatically generated internally by the service.
    """
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


def make_intersect_client_with_rsa() -> IntersectClient:
    """Create an IntersectClient with RSA encryption enabled.
    
    Note: RSA keys are automatically generated internally by the client.
    """
    return IntersectClient(
        FAKE_HIERARCHY_CONFIG,
        config=IntersectServiceConfig(
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


def test_service_responds_with_rsa_encryption() -> None:
    """Test that service can respond to requests using RSA encryption."""
    intersect_service = make_intersect_service_with_rsa()
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
    
    # Send a message requesting RSA encryption
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
            encryption_scheme='RSA',
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    # Verify response was received
    assert msg[0] is not None
    assert msg[2] is not None
    # Verify encryption scheme was RSA
    assert msg[2]['encryption_scheme'] == 'RSA'
    # Verify header IDs were not modified
    assert msg[2]['request_id'] == request_id
    assert msg[2]['campaign_id'] == campaign_id


def test_service_fetches_client_public_key_for_rsa_response() -> None:
    """Test that service fetches client's public key before sending encrypted response."""
    intersect_service = make_intersect_service_with_rsa()
    message_interceptor = make_message_interceptor()
    
    public_key_request_received = [False]
    response_msg = [None, None, None]

    def public_key_request_callback(
        payload: bytes, content_type: str, raw_headers: dict[str, str]
    ) -> None:
        headers = validate_userspace_message_headers(raw_headers)
        if headers['operation_id'] == 'intersect_sdk.get_public_key':
            public_key_request_received[0] = True
            # Respond with a public key
            public_key_pem = intersect_service._private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()
            
            message_interceptor.publish_message(
                'msg/msg/msg/msg/msg/response',
                f'{{"public_key": "{public_key_pem}"}}'.encode(),
                'application/json',
                create_userspace_message_headers(
                    source='test.test.test.test.test',
                    destination='msg.msg.msg.msg.msg',
                    data_handler=IntersectDataHandler.MESSAGE,
                    operation_id='intersect_sdk.get_public_key',
                    campaign_id=headers['campaign_id'],
                    request_id=headers['request_id'],
                    encryption_scheme='NONE',
                ),
                True,
            )

    def response_callback(
        payload: bytes, content_type: str, raw_headers: dict[str, str]
    ) -> None:
        headers = validate_userspace_message_headers(raw_headers)
        if headers['operation_id'] == 'DummyCapability.calculate_fibonacci':
            response_msg[0] = payload
            response_msg[1] = content_type
            response_msg[2] = headers

    # Subscribe to both the request channel (to intercept public key requests) and response channel
    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/request', {public_key_request_callback}, False
    )
    message_interceptor.add_subscription_channel(
        'msg/msg/msg/msg/msg/response', {response_callback}, False
    )
    message_interceptor.connect()
    intersect_service.startup()
    time.sleep(1.0)
    
    # Send a message requesting RSA encryption
    message_interceptor.publish_message(
        intersect_service._service_channel_name,
        b'[4,6]',
        'application/json',
        create_userspace_message_headers(
            source='msg.msg.msg.msg.msg',
            destination='test.test.test.test.test',
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id='DummyCapability.calculate_fibonacci',
            campaign_id=uuid4(),
            request_id=uuid4(),
            encryption_scheme='RSA',
        ),
        True,
    )
    time.sleep(3.0)
    intersect_service.shutdown()
    message_interceptor.disconnect()

    # Verify that the service requested the client's public key
    assert public_key_request_received[0] is True
    # Verify that a response was sent
    assert response_msg[0] is not None


def test_client_sends_rsa_encrypted_message() -> None:
    """Test that client can send RSA encrypted messages to service."""
    intersect_service = make_intersect_service_with_rsa()
    intersect_client = make_intersect_client_with_rsa()
    
    response_received = [None]

    def user_callback(source: str, operation: str, has_error: bool, payload: dict) -> None:
        response_received[0] = payload

    intersect_service.startup()
    time.sleep(1.0)
    
    intersect_client.startup(user_callback=user_callback)
    time.sleep(1.0)
    
    # Send encrypted message from client to service
    from intersect_sdk.shared_callback_definitions import IntersectDirectMessageParams
    
    params = IntersectDirectMessageParams(
        destination='test.test.test.test.test',
        operation='DummyCapability.calculate_fibonacci',
        payload=(4, 6),
        content_type='application/json',
        encryption_scheme='RSA',
    )
    
    intersect_client.send_message(params)
    time.sleep(3.0)
    
    intersect_client.shutdown()
    intersect_service.shutdown()

    # Verify response was received
    assert response_received[0] is not None
    # Verify the decrypted response is correct
    assert response_received[0] == [5, 8, 13]


def test_client_receives_rsa_encrypted_response() -> None:
    """Test that client can receive and decrypt RSA encrypted responses from service."""
    intersect_service = make_intersect_service_with_rsa()
    intersect_client = make_intersect_client_with_rsa()
    
    response_received = [None]
    encryption_scheme_used = [None]

    def user_callback(source: str, operation: str, has_error: bool, payload: dict) -> None:
        response_received[0] = payload
        # Note: we can't directly check encryption_scheme here as it's not passed to callback
        # but we can verify the payload was properly decrypted

    intersect_service.startup()
    time.sleep(1.0)
    
    intersect_client.startup(user_callback=user_callback)
    time.sleep(1.0)
    
    # Send request with RSA encryption (service should respond with RSA)
    from intersect_sdk.shared_callback_definitions import IntersectDirectMessageParams
    
    params = IntersectDirectMessageParams(
        destination='test.test.test.test.test',
        operation='DummyCapability.calculate_fibonacci',
        payload=(10, 12),
        content_type='application/json',
        encryption_scheme='RSA',
    )
    
    intersect_client.send_message(params)
    time.sleep(3.0)
    
    intersect_client.shutdown()
    intersect_service.shutdown()

    # Verify response was received and properly decrypted
    assert response_received[0] is not None
    assert response_received[0] == [89, 144, 233]


def test_bidirectional_rsa_encryption() -> None:
    """Test that both client and service can exchange RSA encrypted messages."""
    intersect_service = make_intersect_service_with_rsa()
    intersect_client = make_intersect_client_with_rsa()
    
    responses = []

    def user_callback(source: str, operation: str, has_error: bool, payload: dict) -> None:
        responses.append({
            'source': source,
            'operation': operation,
            'payload': payload,
            'has_error': has_error,
        })

    intersect_service.startup()
    time.sleep(1.0)
    
    intersect_client.startup(user_callback=user_callback)
    time.sleep(1.0)
    
    from intersect_sdk.shared_callback_definitions import IntersectDirectMessageParams
    
    # Send multiple encrypted messages
    test_cases = [
        (4, 6, [5, 8, 13]),
        (0, 2, [1, 2, 3]),
        (10, 15, [89, 144, 233, 377, 610, 987]),
    ]
    
    for start, end, expected in test_cases:
        params = IntersectDirectMessageParams(
            destination='test.test.test.test.test',
            operation='DummyCapability.calculate_fibonacci',
            payload=(start, end),
            content_type='application/json',
            encryption_scheme='RSA',
        )
        intersect_client.send_message(params)
        time.sleep(2.0)
    
    intersect_client.shutdown()
    intersect_service.shutdown()

    # Verify all responses were received and properly decrypted
    assert len(responses) == 3
    for idx, (start, end, expected) in enumerate(test_cases):
        assert responses[idx]['payload'] == expected
        assert responses[idx]['has_error'] is False
        assert responses[idx]['operation'] == 'DummyCapability.calculate_fibonacci'

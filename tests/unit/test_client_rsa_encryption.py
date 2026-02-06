"""
Unit tests for RSA encryption in IntersectClient

Tests cover the client-side RSA encryption flow where a client:
1. Fetches the service's public key before sending encrypted messages
2. Encrypts outgoing messages using the service's public key
3. Decrypts incoming messages using its own private key
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from intersect_sdk._internal.encryption import (
    intersect_payload_decrypt,
    intersect_payload_encrypt,
)
from intersect_sdk._internal.encryption.models import IntersectEncryptedPayload
from intersect_sdk._internal.messages.userspace import create_userspace_message_headers
from intersect_sdk._internal.encryption.models import IntersectEncryptionPublicKey
from intersect_sdk.client import IntersectClient
from intersect_sdk.core_definitions import IntersectDataHandler
from intersect_sdk.shared_callback_definitions import IntersectDirectMessageParams


class SampleMessage(BaseModel):
    """Simple test message for encryption/decryption testing"""
    result: str = ""


@pytest.fixture
def rsa_keypair():
    """Generate RSA key pair for testing"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture
def public_key_pem(rsa_keypair):
    """Get PEM encoded public key"""
    _, public_key = rsa_keypair
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return public_pem


@pytest.fixture
def mock_client(rsa_keypair):
    """Create a mock IntersectClient for testing"""
    mock_cli = MagicMock(spec=IntersectClient)
    private_key, _ = rsa_keypair
    mock_cli._private_key = private_key
    mock_cli._hierarchy = MagicMock()
    mock_cli._hierarchy.hierarchy_string.return_value = "test.org-fac.sys-client"
    mock_cli._hierarchy.hierarchy_string.side_effect = lambda sep='.': "test.org-fac.sys-client".replace('.', sep) if sep != '.' else "test.org-fac.sys-client"
    mock_cli._terminate_after_initial_messages = False
    mock_cli._campaign_id = uuid4()
    mock_cli._user_callback = MagicMock()

    # Mock data plane manager
    mock_cli._data_plane_manager = MagicMock()

    # Mock control plane manager
    mock_cli._control_plane_manager = MagicMock()

    return mock_cli


def test_send_message_encryption_scheme_none_skips_encryption(mock_client):
    """Test that encryption_scheme='NONE' skips encryption for outgoing messages"""
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-service",
        operation="test_op",
        payload='{"test": "data"}',
        content_type="application/json",
        encryption_scheme="NONE",
    )

    mock_client._data_plane_manager.outgoing_message_data_handler.return_value = (
        b"serialized_data"
    )

    # Call the send method
    IntersectClient._send_userspace_message(mock_client, params)

    # Verify publish_message was called
    assert mock_client._control_plane_manager.publish_message.called
    call_args = mock_client._control_plane_manager.publish_message.call_args
    # The payload should not be encrypted (not an IntersectEncryptedPayload instance)
    payload = call_args[0][1]
    assert payload == b"serialized_data"

def test_send_message_rsa_fetches_public_key(mock_client, public_key_pem):
    """Test that RSA encryption fetches the public key before encrypting"""
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-service",
        operation="test_op",
        payload='{"test": "data"}',
        content_type="application/json",
        encryption_scheme="RSA",
    )

    # Mock the public key fetch to return the service's public key
    mock_client._fetch_service_public_key = MagicMock(return_value=public_key_pem)
    mock_client._data_plane_manager.outgoing_message_data_handler.return_value = (
        b"encrypted_payload"
    )

    # Call the send method
    IntersectClient._send_userspace_message(mock_client, params)

    # Verify that public key was fetched
    mock_client._fetch_service_public_key.assert_called_once_with("test.org-fac.sys-service")

def test_send_message_rsa_encryption_payload_structure(mock_client, public_key_pem):
    """Test that encrypted payload has the expected structure"""
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-service",
        operation="test_op",
        payload='{"message": "hello", "value": 42}',
        content_type="application/json",
        encryption_scheme="RSA",
    )

    mock_client._fetch_service_public_key = MagicMock(return_value=public_key_pem)
    
    captured_data = None
    def capture_handler(data, content_type, handler):
        nonlocal captured_data
        captured_data = data
        return b"encrypted_to_broker"

    mock_client._data_plane_manager.outgoing_message_data_handler = capture_handler

    # Call the send method
    IntersectClient._send_userspace_message(mock_client, params)

    # Verify the payload structure
    assert isinstance(captured_data, IntersectEncryptedPayload)
    assert captured_data.key
    assert captured_data.initial_vector
    assert captured_data.data

def test_send_message_rsa_encryption_fails_without_public_key(mock_client):
    """Test that sending fails if public key cannot be fetched"""
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-service",
        operation="test_op",
        payload='{"test": "data"}',
        content_type="application/json",
        encryption_scheme="RSA",
    )

    # Mock the public key fetch to return None (failure)
    mock_client._fetch_service_public_key = MagicMock(return_value=None)

    # Call the send method
    IntersectClient._send_userspace_message(mock_client, params)

    # Verify that outgoing_message_data_handler was NOT called (message sending failed)
    assert not mock_client._data_plane_manager.outgoing_message_data_handler.called

def test_receive_message_encryption_scheme_none_skips_decryption(mock_client):
    """Test that encryption_scheme='NONE' skips decryption for incoming messages"""
    # Create message headers for an unencrypted message
    headers = create_userspace_message_headers(
        source="test.org-fac.sys-service",
        destination=mock_client._hierarchy.hierarchy_string('.'),
        data_handler=IntersectDataHandler.MESSAGE,
        operation_id="test_op",
        campaign_id=uuid4(),
        request_id=uuid4(),
        encryption_scheme="NONE",
    )

    payload = b'{"test": "data"}'
    mock_client._data_plane_manager.incoming_message_data_handler.return_value = payload
    mock_client._user_callback = MagicMock()

    # Call the handle method
    IntersectClient._handle_userspace_message(
        mock_client, payload, "application/json", headers
    )

    # Verify that incoming_message_data_handler was called
    assert mock_client._data_plane_manager.incoming_message_data_handler.called

def test_receive_message_rsa_decryption_uses_private_key(mock_client, rsa_keypair):
    """Test that RSA decryption uses the client's private key for incoming messages"""
    private_key, _ = rsa_keypair
    mock_client._private_key = private_key

    # Create a simple message to encrypt
    # The client expects a wrapper model with 'data' field containing the JSON string
    test_message_json = '{"data": "{\\"result\\": \\"data from service\\"}"}'
    key_payload = IntersectEncryptionPublicKey(
        public_key=private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
    )
    
    encrypted_payload = intersect_payload_encrypt(
        key_payload=key_payload,
        unencrypted_model=test_message_json,
    )

    # Create message headers for an encrypted message
    headers = create_userspace_message_headers(
        source="test.org-fac.sys-service",
        destination=mock_client._hierarchy.hierarchy_string('.'),
        data_handler=IntersectDataHandler.MESSAGE,
        operation_id="test_op",
        campaign_id=uuid4(),
        request_id=uuid4(),
        encryption_scheme="RSA",
    )

    # Mock the incoming handler to return the encrypted payload
    mock_client._data_plane_manager.incoming_message_data_handler.return_value = (
        encrypted_payload
    )
    mock_client._user_callback = MagicMock()

    # Call the handle method
    IntersectClient._handle_userspace_message(
        mock_client, b"ignored_payload", "application/json", headers
    )

    # Verify that incoming_message_data_handler was called
    assert mock_client._data_plane_manager.incoming_message_data_handler.called

def test_receive_public_key_response_stores_in_cache(mock_client):
    """Test that public key responses are cached for use in key fetching"""
    request_id = uuid4()
    public_key_data = {"public_key": "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----\n"}
    
    # Create message headers for a public key response
    headers = create_userspace_message_headers(
        source="test.org-fac.sys-service",
        destination=mock_client._hierarchy.hierarchy_string('.'),
        data_handler=IntersectDataHandler.MESSAGE,
        operation_id="intersect_sdk.get_public_key",
        campaign_id=uuid4(),
        request_id=request_id,
        encryption_scheme="NONE",
    )

    payload = b'{"public_key": "test_key"}'
    mock_client._data_plane_manager.incoming_message_data_handler.return_value = public_key_data

    # Call the handle method
    IntersectClient._handle_userspace_message(
        mock_client, payload, "application/json", headers
    )

    # Verify that the response was cached using message_id as key
    assert hasattr(mock_client, '_public_key_responses')
    message_id = headers['message_id']  # Extract from the headers dict
    assert message_id in mock_client._public_key_responses
    assert mock_client._public_key_responses[message_id] == public_key_data

def test_send_message_rsa_encryption_roundtrip(mock_client, rsa_keypair, public_key_pem):
    """Test that encrypted message can be decrypted"""
    private_key, _ = rsa_keypair
    class LocalMessage(BaseModel):
        text: str
        
    original_message = LocalMessage(text="Test message from client")
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-service",
        operation="test_op",
        payload=original_message,
        content_type="application/json",
        encryption_scheme="RSA",
    )

    mock_client._fetch_service_public_key = MagicMock(return_value=public_key_pem)
    
    captured_data = None
    def capture_handler(data, content_type, handler):
        nonlocal captured_data
        captured_data = data
        return b"encrypted_to_broker"

    mock_client._data_plane_manager.outgoing_message_data_handler = capture_handler

    # Send the message (which encrypts it)
    IntersectClient._send_userspace_message(mock_client, params)

    # Decrypt it to verify correctness
    decrypted = intersect_payload_decrypt(
        rsa_private_key=private_key,
        encrypted_payload=captured_data,
        model=LocalMessage,
    )

    # The decrypted payload should match the original
    assert decrypted.model.text == original_message.text

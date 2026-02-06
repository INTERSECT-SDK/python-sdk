"""
Unit tests for RSA encryption in IntersectService._send_client_message

Tests cover the service-to-service RSA encryption flow where a service:
1. Fetches the public key from the destination service
2. Encrypts the payload using that public key
3. Sends the encrypted payload
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from intersect_sdk._internal.encryption import intersect_payload_decrypt
from intersect_sdk._internal.encryption.models import IntersectEncryptedPayload
from intersect_sdk.shared_callback_definitions import IntersectDirectMessageParams
from intersect_sdk.service import IntersectService


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
def mock_service():
    """Create a mock IntersectService for testing"""
    mock_svc = MagicMock(spec=IntersectService)
    mock_svc._hierarchy = MagicMock()
    mock_svc._hierarchy.hierarchy_string.return_value = "test.org-fac.sys-service"
    mock_svc._campaign_id = uuid4()
    mock_svc._private_key = MagicMock()
    mock_svc._external_requests = {}
    mock_svc._external_request_ctr = 0

    # Mock data plane manager
    mock_svc._data_plane_manager = MagicMock()

    # Mock control plane manager
    mock_svc._control_plane_manager = MagicMock()

    return mock_svc



def test_encryption_scheme_none_skips_encryption(mock_service):
    """Test that encryption_scheme='NONE' skips the encryption logic"""
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-other",
        operation="test_op",
        payload={"test": "data"},
        encryption_scheme="NONE",
    )

    mock_service._data_plane_manager.outgoing_message_data_handler.return_value = (
        b"test_payload"
    )

    # Call the actual method with mocked service
    result = IntersectService._send_client_message(mock_service, uuid4(), params)

    assert result is True
    # Verify that publish_message was called
    assert mock_service._control_plane_manager.publish_message.called

def test_rsa_encryption_fetches_public_key(mock_service, public_key_pem):
    """Test that RSA encryption requests the public key from destination service"""
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-service",
        operation="test_op",
        payload='{"test": "data"}',  # JSON string
        content_type="application/json",
        encryption_scheme="RSA",
    )

    # Mock the external request mechanism
    public_key_request_id = uuid4()
    requests_created = []

    def mock_create_external_request(request, response_handler=None, timeout=None):
        """Mock external request creation"""
        requests_created.append(request)
        if request.operation == "intersect_sdk.get_public_key":
            return public_key_request_id
        return uuid4()

    def mock_get_external_request(req_id):
        """Mock getting external request status"""
        if req_id == public_key_request_id:
            # Return a mock request with received state and public key response
            mock_extreq = MagicMock()
            mock_extreq.request_state = "received"
            mock_extreq.response_payload = {
                "public_key": public_key_pem
            }
            return mock_extreq
        return None

    mock_service.create_external_request = mock_create_external_request
    mock_service._get_external_request = mock_get_external_request
    mock_service._data_plane_manager.outgoing_message_data_handler.return_value = (
        b"encrypted_payload"
    )

    # Call the method
    result = IntersectService._send_client_message(mock_service, uuid4(), params)

    assert result is True
    # Verify that the public key request was created
    assert len(requests_created) >= 1
    assert any(r.operation == "intersect_sdk.get_public_key" for r in requests_created)

def test_rsa_encryption_timeout_returns_false(mock_service):
    """Test that RSA encryption returns False when public key fetch times out"""
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-service",
        operation="test_op",
        payload={"test": "data"},
        content_type="application/json",
        encryption_scheme="RSA",
    )

    public_key_request_id = uuid4()

    def mock_create_external_request(request, response_handler=None, timeout=None):
        return public_key_request_id

    def mock_get_external_request(req_id):
        """Return a request that never receives a response"""
        if req_id == public_key_request_id:
            mock_extreq = MagicMock()
            mock_extreq.request_state = "sent"  # Never transitions to 'received'
            return mock_extreq
        return None

    mock_service.create_external_request = mock_create_external_request
    mock_service._get_external_request = mock_get_external_request

    # Patch time.time to control the timeout
    # We need to return enough values since time.time is called multiple times
    with patch("intersect_sdk.service.time.time") as mock_time:
        # Return values that will trigger the timeout condition
        # First call at 0, then subsequent calls will progress past 30
        time_values = [0] + [31] * 100  # Start at 0, then always return 31 (exceeds timeout)
        mock_time.side_effect = time_values

        result = IntersectService._send_client_message(mock_service, uuid4(), params)

        assert result is False
        # Verify publish was NOT called due to timeout
        assert not mock_service._control_plane_manager.publish_message.called

def test_rsa_encryption_payload_structure(mock_service, public_key_pem):
    """Test that the encrypted payload has the expected structure"""
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-service",
        operation="test_op",
        payload='{"message": "hello", "value": 42}',
        content_type="application/json",
        encryption_scheme="RSA",
    )

    public_key_request_id = uuid4()
    received_encrypted_payload = None

    def mock_create_external_request(request, response_handler=None, timeout=None):
        return public_key_request_id

    def mock_get_external_request(req_id):
        if req_id == public_key_request_id:
            mock_extreq = MagicMock()
            mock_extreq.request_state = "received"
            mock_extreq.response_payload = {
                "public_key": public_key_pem
            }
            return mock_extreq
        return None

    def mock_outgoing_handler(data, content_type, handler):
        nonlocal received_encrypted_payload
        received_encrypted_payload = data
        return b"encrypted_data_to_broker"

    mock_service.create_external_request = mock_create_external_request
    mock_service._get_external_request = mock_get_external_request
    mock_service._data_plane_manager.outgoing_message_data_handler = mock_outgoing_handler

    result = IntersectService._send_client_message(mock_service, uuid4(), params)

    assert result is True
    # Verify that the data passed to outgoing_handler is an IntersectEncryptedPayload
    assert isinstance(received_encrypted_payload, IntersectEncryptedPayload)
    assert received_encrypted_payload.key  # Should have encrypted AES key
    assert received_encrypted_payload.initial_vector  # Should have IV
    assert received_encrypted_payload.data  # Should have encrypted data

def test_rsa_encryption_roundtrip(mock_service, public_key_pem, rsa_keypair):
    """Test that encrypted payload can be decrypted with the correct private key"""
    from pydantic import BaseModel
    
    private_key, _ = rsa_keypair

    # Create a simple model to use in roundtrip
    class TestMessage(BaseModel):
        text: str
        
    original_message = TestMessage(text="Test message for encryption")
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-service",
        operation="test_op",
        payload=original_message,  # JSON serializable model
        content_type="application/json",
        encryption_scheme="RSA",
    )

    public_key_request_id = uuid4()
    received_encrypted_payload = None

    def mock_create_external_request(request, response_handler=None, timeout=None):
        return public_key_request_id

    def mock_get_external_request(req_id):
        if req_id == public_key_request_id:
            mock_extreq = MagicMock()
            mock_extreq.request_state = "received"
            mock_extreq.response_payload = {
                "public_key": public_key_pem
            }
            return mock_extreq
        return None

    def mock_outgoing_handler(data, content_type, handler):
        nonlocal received_encrypted_payload
        received_encrypted_payload = data
        return b"encrypted_data_to_broker"

    mock_service.create_external_request = mock_create_external_request
    mock_service._get_external_request = mock_get_external_request
    mock_service._data_plane_manager.outgoing_message_data_handler = mock_outgoing_handler

    # Send the message (which encrypts it)
    result = IntersectService._send_client_message(mock_service, uuid4(), params)
    assert result is True

    # Now decrypt it to verify correctness
    decrypted = intersect_payload_decrypt(
        rsa_private_key=private_key,
        encrypted_payload=received_encrypted_payload,
        model=TestMessage,
    )

    # The decrypted payload should match the original
    assert decrypted.model.text == original_message.text

def test_rsa_encryption_with_dict_response(mock_service, public_key_pem):
    """Test that RSA encryption handles dict response from get_public_key"""
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-service",
        operation="test_op",
        payload='{"test": "data"}',
        content_type="application/json",
        encryption_scheme="RSA",
    )

    public_key_request_id = uuid4()

    def mock_create_external_request(request, response_handler=None, timeout=None):
        return public_key_request_id

    def mock_get_external_request(req_id):
        if req_id == public_key_request_id:
            mock_extreq = MagicMock()
            mock_extreq.request_state = "received"
            # Return response as a dict (as it would come from JSON deserialization)
            mock_extreq.response_payload = {
                "public_key": public_key_pem
            }
            return mock_extreq
        return None

    mock_service.create_external_request = mock_create_external_request
    mock_service._get_external_request = mock_get_external_request
    mock_service._data_plane_manager.outgoing_message_data_handler.return_value = (
        b"encrypted_payload"
    )

    result = IntersectService._send_client_message(mock_service, uuid4(), params)

    assert result is True
    # Verify that publish_message was called (indicating successful encryption)
    assert mock_service._control_plane_manager.publish_message.called

def test_rsa_encryption_invalid_public_key_response(mock_service):
    """Test error handling when public key response is invalid"""
    from pydantic_core import ValidationError
    
    params = IntersectDirectMessageParams(
        destination="test.org-fac.sys-service",
        operation="test_op",
        payload='{"test": "data"}',
        content_type="application/json",
        encryption_scheme="RSA",
    )

    public_key_request_id = uuid4()

    def mock_create_external_request(request, response_handler=None, timeout=None):
        return public_key_request_id

    def mock_get_external_request(req_id):
        if req_id == public_key_request_id:
            mock_extreq = MagicMock()
            mock_extreq.request_state = "received"
            # Return invalid response (missing public_key field)
            mock_extreq.response_payload = {"invalid": "response"}
            return mock_extreq
        return None

    mock_service.create_external_request = mock_create_external_request
    mock_service._get_external_request = mock_get_external_request

    # Should raise a ValidationError due to invalid public key response
    with pytest.raises((ValidationError, KeyError, TypeError, AttributeError)):
        IntersectService._send_client_message(mock_service, uuid4(), params)

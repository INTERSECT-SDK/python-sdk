"""
Unit tests for intersect_sdk._internal.encryption module
Tests cover AESCipher, client encryption, and service decryption functionality
"""
import base64
import json
import os
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from pydantic import BaseModel

from intersect_sdk._internal.encryption import (
    AESCipher,
    intersect_client_encryption,
    intersect_service_decryption,
)
from intersect_sdk._internal.encryption.models import (
    IntersectEncryptedPayload,
    IntersectEncryptionPublicKey,
    IntersectDecryptedPayload,
)


# Sample Models for Testing
class SampleModel(BaseModel):
    """Simple sample model for encryption/decryption"""
    message: str
    value: int


class ComplexSampleModel(BaseModel):
    """More complex sample model"""
    name: str
    data: dict
    items: list


# Fixtures
@pytest.fixture
def aes_key():
    """Generate a 256-bit AES key"""
    return os.urandom(32)


@pytest.fixture
def aes_iv():
    """Generate a 128-bit initialization vector"""
    return os.urandom(16)


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


# AESCipher Tests
def test_cipher_initialization_valid_key(aes_key, aes_iv):
    """Test that AESCipher initializes with valid 256-bit key"""
    cipher = AESCipher(aes_key, aes_iv)
    assert cipher is not None
    assert cipher._key == aes_key
    assert cipher._initial_vector == aes_iv

def test_cipher_initialization_invalid_key_size(aes_iv):
    """Test that AESCipher raises ValueError for invalid key size"""
    invalid_key = os.urandom(16)  # 128-bit instead of 256-bit
    with pytest.raises(ValueError, match="Invalid key size"):
        AESCipher(invalid_key, aes_iv)

def test_cipher_encrypt_decrypt_roundtrip(aes_key, aes_iv):
    """Test encryption and decryption roundtrip"""
    cipher = AESCipher(aes_key, aes_iv)
    plaintext = b"Hello, World!"

    encrypted = cipher.encrypt(plaintext)
    decrypted = cipher.decrypt(encrypted)

    assert decrypted == plaintext

def test_cipher_encrypt_returns_base64(aes_key, aes_iv):
    """Test that encrypt returns base64 encoded data"""
    cipher = AESCipher(aes_key, aes_iv)
    plaintext = b"test data"
    encrypted = cipher.encrypt(plaintext)

    # Should be valid base64
    decoded = base64.b64decode(encrypted)
    assert decoded != plaintext  # Should be encrypted

def test_cipher_decrypt_accepts_base64(aes_key, aes_iv):
    """Test that decrypt accepts base64 encoded data"""
    cipher = AESCipher(aes_key, aes_iv)
    plaintext = b"test data"
    encrypted = cipher.encrypt(plaintext)
    assert isinstance(encrypted, bytes)

    decrypted = cipher.decrypt(encrypted)
    assert decrypted == plaintext

def test_cipher_encrypt_empty_plaintext(aes_key, aes_iv):
    """Test encryption of empty plaintext"""
    cipher = AESCipher(aes_key, aes_iv)
    plaintext = b""

    encrypted = cipher.encrypt(plaintext)
    decrypted = cipher.decrypt(encrypted)

    assert decrypted == plaintext

def test_cipher_encrypt_long_plaintext(aes_key, aes_iv):
    """Test encryption of longer plaintext"""
    cipher = AESCipher(aes_key, aes_iv)
    plaintext = b"a" * 10000

    encrypted = cipher.encrypt(plaintext)
    decrypted = cipher.decrypt(encrypted)

    assert decrypted == plaintext

def test_cipher_different_keys_different_results(aes_iv):
    """Test that different keys produce different ciphertexts"""
    key1 = os.urandom(32)
    key2 = os.urandom(32)

    cipher1 = AESCipher(key1, aes_iv)
    cipher2 = AESCipher(key2, aes_iv)

    plaintext = b"test data"
    encrypted1 = cipher1.encrypt(plaintext)
    encrypted2 = cipher2.encrypt(plaintext)

    assert encrypted1 != encrypted2

def test_cipher_same_plaintext_different_ivs(aes_key):
    """Test that same plaintext with different IVs produces different ciphertexts"""
    iv1 = os.urandom(16)
    iv2 = os.urandom(16)

    cipher1 = AESCipher(aes_key, iv1)
    cipher2 = AESCipher(aes_key, iv2)

    plaintext = b"test data"
    encrypted1 = cipher1.encrypt(plaintext)
    encrypted2 = cipher2.encrypt(plaintext)

    assert encrypted1 != encrypted2


# Client Encryption Tests
def test_client_encryption_basic(public_key_pem):
    """Test basic client encryption"""
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)
    model_data = SampleModel(message="hello", value=42)
    unencrypted_json = model_data.model_dump_json()

    result = intersect_client_encryption(key_payload, unencrypted_json)

    assert isinstance(result, IntersectEncryptedPayload)
    assert result.key  # Encrypted AES key
    assert result.initial_vector  # IV
    assert result.data  # Encrypted data

def test_client_encryption_produces_base64(public_key_pem):
    """Test that client encryption produces base64 encoded outputs"""
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)
    unencrypted_json = '{"test": "data"}'

    result = intersect_client_encryption(key_payload, unencrypted_json)

    # All fields should be valid base64
    base64.b64decode(result.key.encode())
    base64.b64decode(result.initial_vector.encode())
    base64.b64decode(result.data.encode())

def test_client_encryption_different_plaintext(public_key_pem):
    """Test that different plaintext produces different ciphertexts"""
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)

    result1 = intersect_client_encryption(key_payload, '{"text": "first"}')
    result2 = intersect_client_encryption(key_payload, '{"text": "second"}')

    # Data should be different
    assert result1.data != result2.data

def test_client_encryption_same_plaintext_different_outputs(public_key_pem):
    """Test that encrypting same plaintext produces different outputs (due to random AES key/IV)"""
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)
    plaintext = '{"test": "data"}'

    result1 = intersect_client_encryption(key_payload, plaintext)
    result2 = intersect_client_encryption(key_payload, plaintext)

    # Due to random key and IV generation, outputs should differ
    assert result1.key != result2.key
    assert result1.initial_vector != result2.initial_vector

def test_client_encryption_complex_model(public_key_pem):
    """Test client encryption with complex model"""
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)
    model_data = ComplexSampleModel(
        name="test",
        data={"nested": {"key": "value"}},
        items=[1, 2, 3],
    )
    unencrypted_json = model_data.model_dump_json()

    result = intersect_client_encryption(key_payload, unencrypted_json)

    assert isinstance(result, IntersectEncryptedPayload)
    assert result.key and result.initial_vector and result.data

def test_client_encryption_large_payload(public_key_pem):
    """Test client encryption with large payload"""
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)
    large_data = {"data": "x" * 100000}
    unencrypted_json = json.dumps(large_data)

    result = intersect_client_encryption(key_payload, unencrypted_json)

    assert isinstance(result, IntersectEncryptedPayload)
    assert result.key and result.initial_vector and result.data


# Service Decryption Tests
def test_service_decryption_basic(rsa_keypair, public_key_pem):
    """Test basic service decryption"""
    private_key, _ = rsa_keypair
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)
    model_data = SampleModel(message="hello", value=42)
    unencrypted_json = model_data.model_dump_json()

    # Encrypt with client
    encrypted = intersect_client_encryption(key_payload, unencrypted_json)

    # Decrypt with service
    result = intersect_service_decryption(private_key, encrypted, SampleModel)

    assert isinstance(result, IntersectDecryptedPayload)
    assert isinstance(result.model, SampleModel)
    assert result.model.message == "hello"
    assert result.model.value == 42

def test_service_decryption_returns_aes_key_and_iv(rsa_keypair, public_key_pem):
    """Test that service decryption returns AES key and IV"""
    private_key, _ = rsa_keypair
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)
    unencrypted_json = '{"message": "test", "value": 10}'

    encrypted = intersect_client_encryption(key_payload, unencrypted_json)
    result = intersect_service_decryption(private_key, encrypted, SampleModel)

    assert result.aes_key is not None
    assert result.aes_initialization_vector is not None
    assert isinstance(result.aes_key, bytes)
    assert isinstance(result.aes_initialization_vector, bytes)

def test_service_decryption_complex_model(rsa_keypair, public_key_pem):
    """Test service decryption with complex model"""
    private_key, _ = rsa_keypair
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)
    model_data = ComplexSampleModel(
        name="complex",
        data={"key": "value", "nested": {"deep": "data"}},
        items=[1, 2, 3, 4, 5],
    )
    unencrypted_json = model_data.model_dump_json()

    encrypted = intersect_client_encryption(key_payload, unencrypted_json)
    result = intersect_service_decryption(private_key, encrypted, ComplexSampleModel)

    assert isinstance(result.model, ComplexSampleModel)
    assert result.model.name == "complex"
    assert result.model.data["key"] == "value"
    assert result.model.items == [1, 2, 3, 4, 5]

def test_service_decryption_wrong_private_key_fails(rsa_keypair):
    """Test that decryption fails with wrong private key"""
    private_key1, public_key1 = rsa_keypair
    private_key2 = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    # Get PEM encoded public key from the matching keypair
    public_pem = public_key1.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    key_payload = IntersectEncryptionPublicKey(public_key=public_pem)
    unencrypted_json = '{"message": "test", "value": 10}'

    # Encrypt with private_key1's public key
    encrypted = intersect_client_encryption(key_payload, unencrypted_json)

    # Verify decryption works with correct private key
    result = intersect_service_decryption(private_key1, encrypted, SampleModel)
    assert result.model.message == "test"
    assert result.model.value == 10

    # Try to decrypt with private_key2 (should fail)
    with pytest.raises(Exception):  # Will raise decryption error
        intersect_service_decryption(private_key2, encrypted, SampleModel)

def test_service_decryption_corrupted_payload_fails(rsa_keypair, public_key_pem):
    """Test that decryption fails with corrupted payload"""
    private_key, _ = rsa_keypair
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)
    unencrypted_json = '{"message": "test", "value": 10}'

    encrypted = intersect_client_encryption(key_payload, unencrypted_json)

    # Corrupt the encrypted data
    corrupted = IntersectEncryptedPayload(
        key=encrypted.key,
        initial_vector=encrypted.initial_vector,
        data=base64.b64encode(b"corrupted data").decode(),
    )

    with pytest.raises(Exception):  # Will raise decryption/validation error
        intersect_service_decryption(private_key, corrupted, SampleModel)

# Integration Tests
def test_full_roundtrip_simple_model(rsa_keypair, public_key_pem):
    """Test full encryption/decryption roundtrip with simple model"""
    private_key, _ = rsa_keypair
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)

    original = SampleModel(message="test message", value=123)
    original_json = original.model_dump_json()

    # Encrypt
    encrypted = intersect_client_encryption(key_payload, original_json)

    # Decrypt
    decrypted = intersect_service_decryption(private_key, encrypted, SampleModel)

    assert decrypted.model.message == original.message
    assert decrypted.model.value == original.value

def test_full_roundtrip_complex_model(rsa_keypair, public_key_pem):
    """Test full encryption/decryption roundtrip with complex model"""
    private_key, _ = rsa_keypair
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)

    original = ComplexSampleModel(
        name="integration test",
        data={"level1": {"level2": {"level3": "value"}}},
        items=[1, "two", 3.0, {"four": 4}],
    )
    original_json = original.model_dump_json()

    encrypted = intersect_client_encryption(key_payload, original_json)
    decrypted = intersect_service_decryption(private_key, encrypted, ComplexSampleModel)

    assert decrypted.model == original

def test_multiple_messages_same_key(rsa_keypair, public_key_pem):
    """Test encrypting and decrypting multiple messages with same RSA key"""
    private_key, _ = rsa_keypair
    key_payload = IntersectEncryptionPublicKey(public_key=public_key_pem)

    messages = [
        SampleModel(message="first", value=1),
        SampleModel(message="second", value=2),
        SampleModel(message="third", value=3),
    ]

    results = []
    for msg in messages:
        encrypted = intersect_client_encryption(key_payload, msg.model_dump_json())
        decrypted = intersect_service_decryption(private_key, encrypted, SampleModel)
        results.append(decrypted.model)

    for original, result in zip(messages, results):
        assert original == result

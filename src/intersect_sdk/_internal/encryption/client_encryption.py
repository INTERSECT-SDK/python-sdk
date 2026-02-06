"""
Client encryption function for intersect_sdk._internal.encryption.client_encryption
RSA asymmetric encryption and AES symmetric encryption
"""
# RSA asymmetric encryption and AES symmetric encryption
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
import os


from .aes_cypher import AESCipher
from .models import IntersectEncryptedPayload, IntersectEncryptionPublicKey
from ..logger import logger

def intersect_client_encryption(
    key_payload: IntersectEncryptionPublicKey,
    unencrypted_model: str,
) -> IntersectEncryptedPayload:
    # Decode and deserialize the public key for asymmetric encrypt
    public_rsa_key = serialization.load_pem_public_key(
        key_payload.public_key.encode(),
        backend=default_backend(),
    )

    # Setup AES
    aes_key: bytes = os.urandom(32)
    aes_initialization_vector: bytes = os.urandom(16)
    cipher = AESCipher(
        key=aes_key,
        initialization_vector=aes_initialization_vector,
    )

    # Encrypt using AES
    logger.info("AES encrypting payload...")
    encrypted_data = cipher.encrypt(unencrypted_model.encode())
    logger.info("AES encrypted the payload!")

    # Asymmetric RSA encrypts AES symmetric key using RSA public key
    logger.info("RSA encrypting AES key...")
    encrypted_aes_key: bytes = public_rsa_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    logger.info("RSA encrypted AES key!")
    logger.info("Done encrypting!")

    return IntersectEncryptedPayload(
        key=base64.b64encode(encrypted_aes_key).decode(),
        initial_vector=base64.b64encode(aes_initialization_vector).decode(),
        data=base64.b64encode(encrypted_data).decode(),
    )

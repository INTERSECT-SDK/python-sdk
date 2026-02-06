"""
Service decryption function for intersect_sdk._internal.encryption.service_decryption
RSA asymmetric encryption and AES symmetric encryption
"""

import json
from typing import Dict, Type
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
import base64

from pydantic import BaseModel

from .aes_cypher import AESCipher
from .models import IntersectEncryptedPayload, IntersectDecryptedPayload
from ..logger import logger


def intersect_service_decryption(
    rsa_private_key: rsa.RSAPrivateKey,
    encrypted_payload: IntersectEncryptedPayload,
    model: Type[BaseModel],
) -> IntersectDecryptedPayload:
    # Decode base64 encoded values from payload
    encrypted_aes_key = base64.b64decode(encrypted_payload.key.encode())
    initial_vector = base64.b64decode(encrypted_payload.initial_vector.encode())
    encrypted_data = base64.b64decode(encrypted_payload.data.encode())

    # Decrypt AES key using RSA
    logger.info("RSA decrypting AES key...")
    decrypted_aes_key: bytes = rsa_private_key.decrypt(
        encrypted_aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    logger.info("RSA decrypted AES key!")

    # Encrypt using AES
    logger.info("AES decrypting payload...")
    cipher = AESCipher(
        key=decrypted_aes_key,
        initialization_vector=initial_vector,
    )

    decrypted_payload: bytes = cipher.decrypt(encrypted_data)
    unencrypted_payload = decrypted_payload.decode()
    logger.info("AES decrypted payload!")

    # Cast unencrypted payload to model and return AES key and IV for possible re-use
    return IntersectDecryptedPayload(
        model=model(**json.loads(unencrypted_payload)),
        aes_key=decrypted_aes_key,
        aes_initialization_vector=initial_vector,
    )

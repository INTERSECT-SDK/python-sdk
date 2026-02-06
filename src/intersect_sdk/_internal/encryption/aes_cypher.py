"""
AESCipher class for intersect_sdk._internal.encryption.aes_cypher
"""
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend


class AESCipher:
    def __init__(self, key: bytes, initialization_vector: bytes):
        if len(key) * 8 != 256:
            raise ValueError("Invalid key size (must be 256 bit)")
        self._key: bytes = key
        # No need to encrypt initialization vectors
        # https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption/#cryptography.hazmat.primitives.ciphers.modes.CBC
        self._initial_vector: bytes = initialization_vector
        self._cipher: Cipher = Cipher(
            algorithms.AES(self._key),
            mode=modes.CBC(self._initial_vector),
            backend=default_backend(),
        )

    def encrypt(self, plaintext: bytes) -> bytes:
        encryptor = self._cipher.encryptor()
        bytes_to_bits = 8
        padder = PKCS7(len(self._initial_vector) * bytes_to_bits).padder()
        padded_data = padder.update(plaintext) + padder.finalize()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        encodedciphertext = base64.b64encode(ciphertext)
        return encodedciphertext

    def decrypt(self, ciphertext: bytes) -> bytes:
        decryptor = self._cipher.decryptor()
        decodedciphertext = base64.b64decode(ciphertext)
        padded_data = decryptor.update(decodedciphertext) + decryptor.finalize()
        bytes_to_bits = 8
        unpadder = PKCS7(len(self._initial_vector) * bytes_to_bits).unpadder()
        plaintext = unpadder.update(padded_data) + unpadder.finalize()
        return plaintext
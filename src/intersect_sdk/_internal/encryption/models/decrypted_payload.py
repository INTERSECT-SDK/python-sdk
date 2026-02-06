from pydantic import BaseModel

class IntersectDecryptedPayload(BaseModel):
    model: BaseModel
    aes_key: bytes
    aes_initialization_vector: bytes
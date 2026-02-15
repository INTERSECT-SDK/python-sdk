from pydantic import BaseModel


class IntersectEncryptedPayload(BaseModel):
    key: str
    initial_vector: str
    data: str
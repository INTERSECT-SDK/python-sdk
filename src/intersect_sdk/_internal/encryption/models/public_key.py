"""Definitions supporting the 'core status' functionality of the core capability."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Annotated


class IntersectEncryptionPublicKey(BaseModel):
    """Public key information for encryption within the INTERSECT-SDK Service."""

    public_key: Annotated[str, Field(title='Public Key PEM')]
    """The PEM encoded public key for asymmetric encryption."""
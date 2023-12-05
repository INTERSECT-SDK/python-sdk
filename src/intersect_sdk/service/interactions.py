from abc import ABC
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel

class InteractionTypeEnum(Enum):
    COMMAND = "COMMAND"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    REQUEST = "REQUEST"
    REPLY = "REPLY"
    EVENT = "EVENT"
    STATUS = "STATUS"

class InteractionRequest(ABC, BaseModel):
  pass
   
class InteractionResponse(ABC, BaseModel):
  pass

class IntersectInteraction():
    def __init__(self, name: str, type: InteractionTypeEnum, req: InteractionRequest, rep: InteractionResponse) -> None:
        self.name = name
        self.type = type
        self.req = req
        self.rep = rep
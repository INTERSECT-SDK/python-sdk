from pydantic import Field
from typing import Dict, Type

from intersect_sdk import service

class HelloWorldRequest(service.InteractionRequest):
    pass

class HelloWorldReply(service.InteractionResponse):
    message: str = Field(..., alias="message")


capabilities: Dict[str, Type] = dict()
capabilities["HelloWorld"] = service.IntersectCapability("HelloWorld")

capabilities["HelloWorld"].addInteraction(service.IntersectInteraction("HelloRequest", service.InteractionTypeEnum.REQUEST, HelloWorldRequest, None))
capabilities["HelloWorld"].addInteraction(service.IntersectInteraction("HelloReply", service.InteractionTypeEnum.REPLY, HelloWorldReply, None))

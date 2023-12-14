from pydantic import Field
from typing import Dict, Type

from intersect_sdk import service

class StatusRequest(service.InteractionRequest):
    count: int = Field(..., alias="count")

capabilities: Dict[str, Type] = dict()
capabilities["Counting"] = service.IntersectCapability("Counting")

capabilities["Counting"].addInteraction(service.IntersectInteraction("Status", service.InteractionTypeEnum.REPLY, StatusRequest, None))
capabilities["Counting"].addInteraction(service.IntersectInteraction("Start", service.InteractionTypeEnum.COMMAND, None, None))
capabilities["Counting"].addInteraction(service.IntersectInteraction("Stop", service.InteractionTypeEnum.COMMAND, None, None))
capabilities["Counting"].addInteraction(service.IntersectInteraction("Restart", service.InteractionTypeEnum.COMMAND, None, None))
capabilities["Counting"].addInteraction(service.IntersectInteraction("Detail", service.InteractionTypeEnum.REQUEST, None, None))

from pydantic import Field

from intersect_sdk import service

class StatusRequest(service.InteractionRequest):
    count: int = Field(..., alias="count")

class StatusInteraction(service.IntersectInteraction):
    def __init__(self):
        super().__init__("Status", service.InteractionTypeEnum.REPLY, StatusRequest, None)

class StartInteraction(service.IntersectInteraction):
    def __init__(self):
        super().__init__("Start", service.InteractionTypeEnum.COMMAND, None, None)

class StopInteraction(service.IntersectInteraction):
    def __init__(self):
        super().__init__("Stop", service.InteractionTypeEnum.COMMAND, None, None)

class RestartInteraction(service.IntersectInteraction):
    def __init__(self):
        super().__init__("Restart", service.InteractionTypeEnum.COMMAND, None, None)

class DetailInteraction(service.IntersectInteraction):
    def __init__(self):
        super().__init__("Detail", service.InteractionTypeEnum.REQUEST, None, None)

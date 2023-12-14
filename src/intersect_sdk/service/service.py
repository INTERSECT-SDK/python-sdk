from typing import Callable, Dict
from pydantic import ValidationError

from ..adapter import Adapter
from ..messages import (Request, Reply)
from .capability import IntersectCapability
from .interactions import IntersectInteraction
from ..config_models import IntersectConfig

class IntersectService(Adapter):

    def __init__(self, config: IntersectConfig):
        super().__init__(config)
        self.__capabilities : Dict[str, IntersectCapability] = dict()

    def load_capabilities(self, cap: Dict[str, IntersectCapability]):
        self.__capabilities.update(cap)

    def get_capability(self, capability_name):
        return self.__capabilities[capability_name]

    def register_interaction_handler(self, capability: IntersectCapability, interaction: IntersectInteraction, handler: Callable = None):
        if handler is not None:
            self.register_message_handler(handler, {interaction.type}, interaction)   

    def unregister_interaction_handler(self, capability: IntersectCapability, interaction: IntersectInteraction, handler: Callable = None):
        if handler is not None:
            self.unregister_message_handler(handler)

    def invoke_interaction(self, interaction: IntersectInteraction, destination: str, request):
        if interaction.req is None:
            payload = None
        else:
            try:
                payload = interaction.req(**request).model_dump_json()
            except ValidationError as e:
                print(e.errors())
                return

        message = self.generate_message(interaction.type, destination, {'interaction_name': interaction.name, 'payload': payload})
        self.send(message)
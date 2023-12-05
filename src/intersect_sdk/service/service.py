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

    def __add_capability(self, capability_name: str):
        self.__capabilities[capability_name] = IntersectCapability(name=capability_name)

    def __remove_capability(self, capability_name: str):
        self.__capabilities.pop(capability_name)

    def get_capability(self, capability_name):
        return self.__capabilities[capability_name]

    def add_interaction(self, capability_name: str, interaction: IntersectInteraction, handler: Callable = None):
        if capability_name not in self.__capabilities:
            self.__add_capability(capability_name=capability_name)
        self.__capabilities[capability_name].addInteraction(interaction=interaction)
        if handler is not None:
            self.register_message_handler(handler, {interaction.type}, interaction)
    
    def remove_interaction(self, capability_name: str, interaction: IntersectInteraction):
        if capability_name in self.__capabilities[capability_name]:
            self.__capabilities[capability_name].removeInteraction(interaction.name)
            #self.unregister_message_handler
        if capability_name in self.__capabilities and self.get_capability(capability_name).getCount() is 0:
            self.__remove_capability(capability_name=capability_name)

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
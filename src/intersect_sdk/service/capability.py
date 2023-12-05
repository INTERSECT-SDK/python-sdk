from typing import Dict, Type

from .interactions import IntersectInteraction

class IntersectCapability:
    def __init__(self, name: str):
        self.__interactions : Dict[str, Type] = dict()
        self.name = name

    def addInteraction(self, interaction: IntersectInteraction):
        self.__interactions[interaction.name] = interaction

    def removeInteraction(self, name:str):
        self.__interactions.pop(name)

    def getCount(self):
        return len(self.__interactions)
    
    def getInteraction(self, name:str):
        return self.__interactions[name]
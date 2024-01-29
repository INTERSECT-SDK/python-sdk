"""Client specific configuration types."""

from typing import List, Literal, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from .shared import ControlPlaneConfig, DataStoreConfigMap


class IntersectClientConfig(BaseModel):
    """The user-provided configuration needed to integrate with INTERSECT as a client."""

    brokers: Union[Annotated[List[ControlPlaneConfig], Field(min_length=1)], Literal['discovery']]
    """
    Configurations for any message brokers the application should attach to

    use literal "discovery" string to discover brokers, use list of brokers otherwise
    """

    data_stores: DataStoreConfigMap
    """
    Configurations for any data stores the application should talk to
    """

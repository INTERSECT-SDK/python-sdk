"""Service specific configuration types."""

from typing import List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat
from typing_extensions import Annotated

from .shared import ControlPlaneConfig, DataStoreConfigMap, HierarchyConfig


class IntersectServiceConfig(BaseModel):
    """The user-provided configuration needed to integrate with INTERSECT."""

    hierarchy: HierarchyConfig
    """
    Configuration of the System-of-System representation
    """

    brokers: Union[Annotated[List[ControlPlaneConfig], Field(min_length=1)], Literal['discovery']]  # noqa: FA100 (Pydantic uses runtime annotations)
    """
    Configurations for any message brokers the application should attach to

    use literal "discovery" string to discover brokers, use list of brokers otherwise
    """

    data_stores: Annotated[DataStoreConfigMap, Field(default_factory=lambda: DataStoreConfigMap())]
    """
    Configurations for any data stores the application should talk to
    """

    status_interval: PositiveFloat = Field(default=300.0, ge=30.0, lt=1500.0)
    """
    How often to send status messages through the broker (seconds) (default: 300)

    This value must be greater than 30 seconds but less than 25 minutes, as every 30 minutes the resource service will check to
    get the last reply time of the adapter, and will automatically mark the adapter as having an
    unknown lifecycle status if the adapter has not made some kind of response. (We give 5 minutes
    as a potential time buffer.)
    """

    # pydantic config
    model_config = ConfigDict(revalidate_instances='always')

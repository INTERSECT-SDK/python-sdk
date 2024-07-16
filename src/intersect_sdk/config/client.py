"""Client specific configuration types."""

from typing import List, Literal, Union

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated, final

from ..client_callback_definitions import IntersectClientCallback
from .shared import ControlPlaneConfig, DataStoreConfigMap


@final
class IntersectClientConfig(BaseModel):
    """The user-provided configuration needed to integrate with INTERSECT as a client."""

    brokers: Union[Annotated[List[ControlPlaneConfig], Field(min_length=1)], Literal['discovery']]  # noqa: FA100 (Pydantic uses runtime annotations)
    """
    Configurations for any message brokers the application should attach to

    use literal "discovery" string to discover brokers, use list of brokers otherwise
    """

    data_stores: Annotated[DataStoreConfigMap, Field(default_factory=lambda: DataStoreConfigMap())]
    """
    Configurations for any data stores the application should talk to
    """

    initial_message_event_config: IntersectClientCallback
    """
    configuration for:
    1) the initial messages you want to send out
    2) the initial events you want to listen to

    Note that at LEAST one of these should be non-empty.
    """

    resend_initial_messages_on_secondary_startup: bool = False
    """
    if set to True, resend the initial messages if the client is restarted

    (default: False)
    """

    terminate_after_initial_messages: bool = False
    """
    if set to True, will never enter the pub/sub loop and will never wait for responses from the services

    (default: False)
    """

    system: Annotated[str, Field('tmp-')]
    """
    Name of the "system", could also be thought of as a "device" (should be unique within a facility)
    """

    facility: Annotated[str, Field('tmp-')]
    """
    Name of the facility (an ORNL institutional designation, i.e. 'neutrons') (NOT abbreviated, should be unique within an organization)
    """

    organization: Annotated[str, Field('tmp-')]
    """
    Name of the organization (i.e. 'ornl') (NOT abbreviated) (should be unique in an INTERSECT cluster)
    """

    # pydantic config
    model_config = ConfigDict(revalidate_instances='always')

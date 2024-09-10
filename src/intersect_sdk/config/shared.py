"""Configuration types shared across both Clients and Services."""

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, PositiveInt
from typing_extensions import Annotated

from ..core_definitions import IntersectDataHandler

HIERARCHY_REGEX = r'^[a-z]((?!--)[a-z0-9-]){2,62}$'
"""
The hierarchy regex needs to be fairly restricted due to the number of different
systems we want to be compatible with. The rules:

- Only allow unreserved characters (alphanumeric and .-~_): https://datatracker.ietf.org/doc/html/rfc3986#section-2.3
- Require lowercase letters to avoid incompatibilities with case-insensitive systems.
- MinIO has been found to forbid _ and ~ characters
- MinIO requires an alphanumeric character at the start of the string
- No adjacent non-alphanumeric characters allowed
- Range should be from 3-63 characters

The following commit tracks several issues with MINIO: https://code.ornl.gov/intersect/additive-manufacturing/ros-intersect-adapter/-/commit/fa71b791be0ccf1a5884910b5be3b5239cf9896f
"""

ControlProvider = Literal['mqtt3.1.1', 'amqp0.9.1']
"""The type of broker we connect to."""


class HierarchyConfig(BaseModel):
    """Configuration for registring this service in a system-of-system architecture."""

    service: Annotated[str, Field(pattern=HIERARCHY_REGEX)]
    """
    The name of this application - should be unique within an INTERSECT system
    """

    subsystem: Optional[str] = Field(default=None, pattern=HIERARCHY_REGEX)  # noqa: FA100 (Pydantic uses runtime annotations)
    """
    An associated subsystem / service-grouping of the system (should be unique within an INTERSECT system)
    """

    system: Annotated[str, Field(pattern=HIERARCHY_REGEX)]
    """
    Name of the "system", could also be thought of as a "device" (should be unique within a facility)
    """

    facility: Annotated[str, Field(pattern=HIERARCHY_REGEX)]
    """
    Name of the facility (an ORNL institutional designation, i.e. 'neutrons') (NOT abbreviated, should be unique within an organization)
    """

    organization: Annotated[str, Field(pattern=HIERARCHY_REGEX)]
    """
    Name of the organization (i.e. 'ornl') (NOT abbreviated) (should be unique in an INTERSECT cluster)
    """

    def hierarchy_string(self, join_str: str = '') -> str:
        """Get the full hierarchy string. This is mostly used internally, but if you're developing a client, it could potentially be helpful.

        Params
          join_str: String used to separate different hierarchy parts in the full string (default: empty string).

        Returns:
          Single string, which will contain all system-of-system parts. For optional parts not configured (i.e. - no subsystem), they will be represented by a "-" character.
        """
        if not self.subsystem:
            return join_str.join([self.organization, self.facility, self.system, '-', self.service])
        return join_str.join(
            [
                self.organization,
                self.facility,
                self.system,
                self.subsystem,
                self.service,
            ]
        )

    # we need to use the Python regex engine instead of the Rust regex engine here, because Rust's does not support lookaheads
    model_config = ConfigDict(regex_engine='python-re')


@dataclass
class ControlPlaneConfig:
    """Configuration for interacting with a broker."""

    protocol: ControlProvider
    """
    The protocol of the broker you'd like to use (i.e. AMQP, MQTT...)
    """
    # TODO - support more protocols and protocol versions as needed - see https://www.asyncapi.com/docs/reference/specification/v2.6.0#serverObject

    username: Annotated[str, Field(min_length=1)]
    """
    Username credentials for broker connection.
    """

    password: Annotated[str, Field(min_length=1)]
    """
    Password credentials for broker connection.
    """

    host: Annotated[str, Field(min_length=1)] = '127.0.0.1'
    """
    Broker hostname (default: 127.0.0.1)
    """

    port: Optional[PositiveInt] = None  # noqa: FA100 (Pydantic uses runtime annotations)
    """
    Broker port. List of common ports:

    - 1883 (MQTT)
    - 4222 (NATS default port)
    - 5222 (XMPP)
    - 5223 (XMPP over TLS)
    - 5671 (AMQP over TLS)
    - 5672 (AMQP)
    - 7400 (DDS Discovery)
    - 7401 (DDS User traffic)
    - 8883 (MQTT over TLS)
    - 61613 (RabbitMQ STOMP - WARNING: ephemeral port)

    NOTE: INTERSECT currently only supports AMQP and MQTT.
    """


@dataclass
class DataStoreConfig:
    """Configuration for interacting with a data store."""

    username: Annotated[str, Field(min_length=1)]
    """
    Username credentials for data store connection.
    """

    password: Annotated[str, Field(min_length=1)]
    """
    Password credentials for data store connection.
    """

    host: Annotated[str, Field(min_length=1)] = '127.0.0.1'
    """
    Data store hostname (default: 127.0.0.1)
    """

    port: Optional[PositiveInt] = None  # noqa: FA100 (Pydantic uses runtime annotations)
    """
    Data store port
    """


@dataclass
class DataStoreConfigMap:
    """Configurations for any data stores the application should talk to."""

    minio: List[DataStoreConfig] = field(default_factory=list)  # noqa: FA100 (Pydantic uses runtime annotations)
    """
    minio configurations
    """

    def get_missing_data_store_types(self) -> Set[IntersectDataHandler]:  # noqa: FA100 (not technically a runtime annotation)
        """Return a set of IntersectDataHandlers which will not be permitted, due to a configuration type missing.

        If all data configurations exist, returns an empty set
        """
        missing = set()
        if not self.minio:
            missing.add(IntersectDataHandler.MINIO)
        return missing

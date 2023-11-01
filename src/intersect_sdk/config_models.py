from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt, field_validator


class HierarchyConfig(BaseModel):
    """
    Configuration for registring this service in a system-of-system architecture
    """

    service: str = Field(min_length=1)
    """
    The name of this application - should be unique within an INTERSECT cluster
    """

    subsystem: Optional[str] = Field(default=None, min_length=1)
    """
    An associated subsystem / service-grouping of the service
    """

    system: str = Field(min_length=1)
    """
    Name of the "system", could also be thought of as a "device"
    """

    facility: str = Field(min_length=1)
    """
    Name of the facility (an ORNL institutional designation, i.e. Neutrons) (NOT abbreviated)
    """

    organization: str = Field(default="Oak Ridge National Laboratory", min_length=1)
    """
    Name of the organization (i.e. ORNL) (NOT abbreviated)
    """


class BrokerConfig(BaseModel):
    """
    Configuration for interacting with the broker
    """

    username: str = Field(min_length=1)
    """
    Username credentials for broker connection.
    """

    password: str = Field(min_length=1)
    """
    Password credentials for broker connection.
    """

    host: str = Field(default="127.0.0.1", min_length=1)
    """
    Broker hostname (default: 127.0.0.1)
    """

    port: PositiveInt = Field(...)
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


class IntersectConfig(BaseModel):
    """
    The user-provided configuration needed to integrate with INTERSECT.
    """

    hierarchy: HierarchyConfig = Field()
    """
    Configuration of the System-of-System representation
    """

    broker: BrokerConfig = Field()
    """
    Configuration for the message broker
    """

    status_interval: PositiveFloat = Field(default=30.0)
    """
    How often to send status messages through the broker (seconds) (default: 30)
    """

    id_counter_init: PositiveInt = Field(default=100)
    """
    Initial value of ID counter (default: 100)
    """

    # TODO: we may want to strongly type Capabilities & move them to this library
    # then we could mark this as a list of strings, and map the strings to Capability objects
    # in the Adapter constructor
    capabilities: List[Any] = Field(default=[])
    """
    List of capabilites offered by this system
    """

    argument_schema: Optional[Dict[str, Any]] = None
    """
    JSON Schema representative of allowed arguments INTERSECT campaigns can make to this system.

    We currently check schemas against the 2020-12 draft - see
    https://json-schema.org/draft/2020-12/json-schema-validation.html
    for more information

    If you do not allow for any arguments other than a generic "data" input
    (which already gets passed in messages), leave this field blank.
    """

    @field_validator("argument_schema")
    def _valid_json_schema(cls, schema: Optional[Dict]):
        if schema is not None:
            from jsonschema import Draft202012Validator as SchemaValidator
            from jsonschema.validators import validator_for

            # custom impl. of check_schema() , gather all errors instead of throwing on first error
            errors: List[str] = []
            Metavalidator = validator_for(SchemaValidator.META_SCHEMA, default=SchemaValidator)
            metavalidator = Metavalidator(
                SchemaValidator.META_SCHEMA, format_checker=SchemaValidator.FORMAT_CHECKER
            )
            # type is ValidationError
            for _error in metavalidator.iter_errors(schema):
                errors.append(f"{_error.json_path} : {_error.message}")

            if errors:
                errStr = "\n    ".join(errors)
                raise ValueError(f"INTERSECT schema config error: \n    {errStr}\n  {schema}")
        return schema

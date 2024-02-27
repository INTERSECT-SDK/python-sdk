from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Literal

from pydantic import TypeAdapter

from ..exceptions import IntersectInvalidBrokerError
from ..logger import logger
from .brokers.mqtt_client import MQTTClient

if TYPE_CHECKING:
    from ...config.shared import ControlPlaneConfig
    from .brokers.broker_client import BrokerClient

GENERIC_MESSAGE_SERIALIZER = TypeAdapter(Any)


def serialize_message(message: Any) -> bytes:
    """Serialize a message to bytes, in preparation for publishing it on a message broker.

    Works as a generic serializer/deserializer
    """
    return GENERIC_MESSAGE_SERIALIZER.dump_json(message, warnings=False)


def create_control_provider(
    config: ControlPlaneConfig,
    topic_handler_callback: Callable[[], defaultdict[str, set[Callable[[bytes], None]]]],
) -> BrokerClient:
    if config.protocol == 'amqp0.9.1':
        # only try to import the AMQP client if the user is using an AMQP broker
        try:
            from .brokers.amqp_client import AMQPClient

            return AMQPClient(
                host=config.host,
                port=config.port or 5672,
                username=config.username,
                password=config.password,
                topics_to_handlers=topic_handler_callback,
            )
        except ImportError as e:
            msg = "Configuration includes AMQP broker, but AMQP dependencies were not installed. Install intersect with the 'amqp' optional dependency to use this backend. (i.e. `pip install intersect_sdk[amqp]`)"
            raise IntersectInvalidBrokerError(msg) from e
    # MQTT
    return MQTTClient(
        host=config.host,
        port=config.port or 1883,
        username=config.username,
        password=config.password,
        topics_to_handlers=topic_handler_callback,
    )


class ControlPlaneManager:
    """The ControlPlaneManager class allows for working with multiple brokers from a single function call."""

    def __init__(
        self,
        control_configs: list[ControlPlaneConfig] | Literal['discovery'],
    ) -> None:
        if control_configs == 'discovery':
            msg = 'Discovery service not implemented yet'
            raise ValueError(msg)
        self._control_providers = [
            create_control_provider(config, self.get_subscription_channels)
            for config in control_configs
        ]

        self._ready = False
        # topics_to_handlers are managed here and transcend connections/disconnections to the broker
        self._topics_to_handlers: defaultdict[str, set[Callable[[bytes], None]]] = defaultdict(set)

    def add_subscription_channel(
        self, channel: str, callbacks: set[Callable[[bytes], None]]
    ) -> None:
        """Start listening for userspace messages on a channel on all configured brokers.

        Note that ALL channels listened to will always handle userspace messages.

        Params:
          channel: string of the channel which we should start listening to
        """
        self._topics_to_handlers[channel] |= callbacks
        if self._ready:
            for provider in self._control_providers:
                provider.subscribe(channel)

    def remove_subscription_channel(self, channel: str) -> bool:
        """Stop subscribing to a channel on all configured brokers.

        Params:
          channel: string of the channel which should no longer be listened to
        Returns: True if channel is no longer being listened to, False if the channel wasn't being listened to in the first place
        """
        try:
            del self._topics_to_handlers[channel]
        except KeyError:
            return False
        else:
            if self._ready:
                for provider in self._control_providers:
                    provider.unsubscribe(channel)
            return True

    def get_subscription_channels(self) -> defaultdict[str, set[Callable[[bytes], None]]]:
        """Get the subscription channels.

        Note that this function gets accessed as a callback from the direct broker implementations.

        Returns:
          the dictionary of topics to callback functions
        """
        return self._topics_to_handlers

    def connect(self) -> None:
        """Connect to all configured brokers and subscribe to any channels configured."""
        # TODO - when implementing discovery service, discovery and connection logic should be applied here
        for provider in self._control_providers:
            provider.connect()
            for channel in self._topics_to_handlers:
                provider.subscribe(channel)
        self._ready = True

    def disconnect(self) -> None:
        """Disconnect from all configured brokers."""
        self._ready = False
        for provider in self._control_providers:
            provider.disconnect()

    def publish_message(self, channel: str, msg: Any) -> None:
        """Publish message on channel for all brokers."""
        if self._ready:
            serialized_message = serialize_message(msg)
            for provider in self._control_providers:
                provider.publish(channel, serialized_message)
        else:
            logger.error('Cannot send message, providers are not connected')

    def is_connected(self) -> bool:
        """Check that we are connected to ALL configured brokers.

        Returns:
          - True if we are currently connected to all brokers we've configured, False if not
        """
        return all(control_provider.is_connected() for control_provider in self._control_providers)

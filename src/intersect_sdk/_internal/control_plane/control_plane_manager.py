from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Literal

from pydantic import TypeAdapter

from ..exceptions import IntersectInvalidBrokerError
from ..logger import logger
from .brokers.mqtt_client import MQTTClient
from .topic_handler import TopicHandler

if TYPE_CHECKING:
    from ...config.shared import ControlPlaneConfig
    from .brokers.broker_client import BrokerClient

GENERIC_MESSAGE_SERIALIZER: TypeAdapter[Any] = TypeAdapter(Any)


def serialize_message(message: Any) -> bytes:
    """Serialize a message to bytes, in preparation for publishing it on a message broker.

    Works as a generic serializer/deserializer
    """
    return GENERIC_MESSAGE_SERIALIZER.dump_json(message, warnings=False)


def create_control_provider(
    config: ControlPlaneConfig,
    topic_handler_callback: Callable[[], dict[str, TopicHandler]],
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
        """Basic constructor.

        Some interaction with message brokers can change based on whether or not a Service or a Client is calling it.
        """
        if control_configs == 'discovery':
            msg = 'Discovery service not implemented yet'
            raise NotImplementedError(msg)
        self._control_providers = [
            create_control_provider(config, self.get_subscription_channels)
            for config in control_configs
        ]

        # flag which indicates if we SHOULD be connected.
        self._ready = False
        # topics_to_handlers are managed here and transcend connections/disconnections to the broker
        self._topics_to_handlers: dict[str, TopicHandler] = {}

    def add_subscription_channel(
        self, channel: str, callbacks: set[Callable[[bytes], None]], persist: bool
    ) -> None:
        """Start listening for messages on a channel on all configured brokers.

        Use the format ${TOPIC}/${TOPIC}/${TOPIC} ... for the channel name, protocol implementations
        are responsible for converting the string to a valid channel.

        This function should usually only be called before you've connected,
        but it's okay to call it after connecting. (Mostly used for Clients.)

        Params:
          channel: string of the channel which we should start listening to
          callbacks: functions to call on subscribing to a message
          persist: if True, expect the associated message queue to live long; if False, it will only live the duration of the application.
            Any queue associated with a Service should always set this to True. Clients will need to subscribe to their own, temporary queues, and should set this to False.
        """
        topic_handler = self._topics_to_handlers.get(channel)
        if topic_handler is None:
            topic_handler = TopicHandler(persist)
            topic_handler.callbacks |= callbacks
            self._topics_to_handlers[channel] = topic_handler
        else:
            topic_handler.callbacks |= callbacks
        if self.is_connected():
            for provider in self._control_providers:
                provider.subscribe(channel, persist)

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
            if self.is_connected():
                for provider in self._control_providers:
                    provider.unsubscribe(channel)
            return True

    def get_subscription_channels(self) -> dict[str, TopicHandler]:
        """Get the subscription channels.

        Note that this function gets accessed as a callback from the direct broker implementations.

        Returns:
          the dictionary of topics to topic information
        """
        return self._topics_to_handlers

    def connect(self) -> None:
        """Connect to all configured brokers.

        Each broker client should utilize their respective on_connect callback to
        subscribe to all channels tracked in the ControlPlaneManager.
        """
        # TODO - when implementing discovery service, discovery and connection logic should be applied here
        for provider in self._control_providers:
            provider.connect()
        self._ready = True

    def disconnect(self) -> None:
        """Disconnect from all configured brokers."""
        self._ready = False
        for provider in self._control_providers:
            provider.disconnect()

    def publish_message(self, channel: str, msg: Any, persist: bool) -> None:
        """Publish message on channel for all brokers."""
        if self.is_connected():
            serialized_message = serialize_message(msg)
            for provider in self._control_providers:
                provider.publish(channel, serialized_message, persist)
        else:
            logger.error('Cannot send message, providers are not connected')

    def is_connected(self) -> bool:
        """Check that we are connected to ALL configured brokers.

        Returns:
          - True if we are currently connected to all brokers we've configured, False if not
        """
        return self._ready and all(
            control_provider.is_connected() for control_provider in self._control_providers
        )

    def considered_unrecoverable(self) -> bool:
        """Check if any broker is considered to be in an unrecoverable state.

        Returns:
          - True if we can't recover, false otherwise
        """
        return any(
            control_provider.considered_unrecoverable()
            for control_provider in self._control_providers
        )

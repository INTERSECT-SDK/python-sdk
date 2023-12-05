# Standard imports
import functools
import json
import threading
import time
import weakref
from builtins import list
from typing import Any, Callable, Dict, List, Optional, Union

from jsonschema import ValidationError

# Project import
from . import base, messages

# intersect imports
from .client import Channel
from .config_models import IntersectConfig
from .exceptions import IntersectWarning
from .logger import logger
from .utils import get_utc, identifier, parse_message_arguments

MessageType = Union[messages.Request, messages.Reply, messages.Event, messages.Status, messages.Command, messages.Acknowledge]
HandlerConfig = List[MessageType]

class Adapter(base.Service):
    """Service with messaging features implemented.

    A Service that has functions to manage broker Channels, create and route messages, manage
    configuration data, and automatically send status messages.

    Attributes:
        action_channel: Channel for accepting Action messages.
        hierarchy: Dictionary of strings to strings defining the service's identification
            metadata.
        message_id_counter:
        reply_channel: Channel for accepting reply Status messages.
        request_channel: Channel for accepting Request messages.
        status: The adapters current Status, as sent in Status message subtypes.
        status_channel: Channel for sending non-reply Status messages.
        status_ticker_active: Boolean controlling whether the status_thread will send messages.
        status_thread: Thread for sending periodic Status messages for this adapter's status.
        types_to_handlers: Dictionary of IntersectMessage types to dictionaries of
            IntersectMessage subtypes to Callables that will be invoked to handle messages of
            that subtype.
    """

    # Member variables
    arguments_parser: str = "json"

    def __init__(self, config: IntersectConfig):
        """Constructor for intializing with broker connection information.

        Args:
            config: INTERSECT config.
        """

        super().__init__(config)

        self.status_ticker_interval = config.status_interval
        self.id_counter_init = config.id_counter_init

        # Set relevant channels
        self.request_channel: Channel = self.connection.channel(f"{self.service_name}/request")
        self.reply_channel: Channel = self.connection.channel(f"{self.service_name}/reply")
        self.event_channel: Channel = self.connection.channel(f"{self.service_name}/event")
        self.status_channel = self.connection.channel(f"{self.service_name}/status")
        self.command_channel = self.connection.channel(f"{self.service_name}/command")
        self.acknowledge_channel = self.connection.channel(f"{self.service_name}/acknowledge")

        # Subscribe to channels with handler functions
        self.request_channel.subscribe(self.resolve_message_receive)
        self.reply_channel.subscribe(self.resolve_message_receive)
        self.event_channel.subscribe(self.resolve_message_receive)
        self.status_channel.subscribe(self.resolve_message_receive)
        self.command_channel.subscribe(self.resolve_message_receive)
        self.acknowledge_channel.subscribe(self.resolve_message_receive)

        # Set attributes for regular status outputs
        self.status_thread: Optional[threading.Thread] = None
        self.status_ticker_active: bool = True
        self.message_id_counter = identifier(self.service_name, self.id_counter_init)

        # Setup the Adapter's hierarchy
        self.hierarchy = config.hierarchy.model_dump()
        self.argument_schema = config.argument_schema

        # weakref to allow garbage collection
        # but allow data access until just before gc occurs
        weak_self = weakref.ref(self)
        self.types_to_handlers: Dict[int, list] = {}

    def __del__(self):
        """Performs finalization upon deletion."""
        self._finalizer()

    def _fill_message(self, msg, destination="None", arguments=None) -> messages:
        msg.header.source = self.service_name
        msg.header.destination = destination
        msg.header.message_id = next(self.identifier)
        msg.header.created = get_utc()
        # The controllers might be expecting something, so send a blank dictionary
        msg.arguments = json.dumps(arguments)
        return msg

    def generate_request_message(self, destination=None, arguments=None) -> messages.Request:
        msg = messages.Request()
        arguments['type'] = "REQUEST"
        self._fill_message(msg, destination=destination, arguments=arguments)
        return msg

    def generate_reply_message(self, destination=None, arguments=None) -> messages.Reply:
        msg = messages.Reply()
        arguments['type'] = "REPLY"
        self._fill_message(msg, destination=destination, arguments=arguments)
        return msg

    def generate_event_message(self, destination=None, arguments=None) -> messages.Event:
        msg = messages.Event()
        arguments['type'] = "EVENT"
        self._fill_message(msg, destination=destination, arguments=arguments)
        return msg

    def generate_status_message(self, destination=None, arguments=None) -> messages.Status:
        msg = messages.Status()
        arguments['type'] = "STATUS"
        self._fill_message(msg, destination=destination, arguments=arguments)
        return msg

    def generate_command_message(self, destination=None, arguments=None) -> messages.Command:
        msg = messages.Command()
        arguments['type'] = "COMMAND"
        self._fill_message(msg, destination=destination, arguments=arguments)
        return msg

    def generate_acknowledge_message(self, destination=None, arguments=None) -> messages.Acknowledge:
        msg = messages.Acknowledge()
        arguments['type'] = "ACKNOWLEDGE"
        self._fill_message(msg, destination=destination, arguments=arguments)
        return msg

    def generate_message(self, message_type: str, destination=None, arguments=None) -> messages:
        if message_type.name == "REQUEST":
            return self.generate_request_message(destination, arguments)
        if message_type.name == "REPLY":
            return self.generate_reply_message(destination, arguments)
        if message_type.name == "EVENT":
            return self.generate_event_message(destination, arguments)
        if message_type.name == "STATUS":
            return self.generate_status_message(destination, arguments)
        if message_type.name == "COMMAND":
            return self.generate_command_message(destination, arguments)
        if message_type.name == "ACKNOWLEDGE":
            return self.generate_acknowledge_message(destination, arguments)           

    def send(self, message: MessageType):
        """Send the message.

        Sends the message to the message broker on the appropriate channels.

        Args:
            message: The Message to send.
        """
        if isinstance(message, messages.Request):
            self.connection.channel(message.header.destination + "/request").publish(message)
        elif isinstance(message, messages.Reply):
            if message.header.destination is None or message.header.destination == "None":
                self.status_channel.publish(message)
            else:
                self.connection.channel(message.header.destination + "/reply").publish(message)
        elif isinstance(message, messages.Event):
            self.connection.channel(message.header.destination + "/event").publish(message)
        elif isinstance(message, messages.Status):
            self.connection.channel(message.header.destination + "/status").publish(message)
        elif isinstance(message, messages.Command):
            self.connection.channel(message.header.destination + "/command").publish(message)
        elif isinstance(message, messages.Acknowledge):
            self.connection.channel(message.header.destination + "/acknowledge").publish(message)

    def resolve_message_receive(self, message) -> bool:
        """Handle amessage.

        Delegates messages to the appropriate handler.

        Args:
            message: The message to handle.
        Returns:
            True if the message was handled correctly.
        """
        if not message.header.destination.startswith(self.service_name):
            return True
        payload = parse_message_arguments(message.arguments, False)
        handlers = self.types_to_handlers.get(payload['type'], [])

        for handler in handlers:
            if handler[1].name == payload['interaction_name']:
                handler[0](message, payload)
        return True

    def register_message_handler(
        self, handler: Callable, types_: HandlerConfig, name=None
    ):
        """Register a message handler callable to be run.

        Register the handler so that it will be run whenever
        a message of one of the given Action, Request, and/or Status
        types is received. Reference
        intersect_sdk.common.message_handler.SampleMessageHandler
        for a callable class.

        Args:
            handler: The message handler callable to register.
            types_: Dictionary of message types.
        """
        for message_type in types_:
            handlers: dict = self.types_to_handlers.setdefault(message_type.name, [])
            for entry in handlers:
                if entry[0] is handler:
                    continue
            handlers.append((handler, name))

    def unregister_message_handler(self, handler: Callable):
        """Unregister a message handler.

        Remove a message handler and no longer give it received messages.

        Args:
            handler: The Callable message handler to unregister.
        """
        for message_subtypes in self.types_to_handlers.values():
            for handlers in message_subtypes.values():
                handlers = filter(handlers, lambda x: x[0] is not handler)

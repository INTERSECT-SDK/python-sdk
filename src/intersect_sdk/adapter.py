# Standard imports
import functools
import json
import threading
import time
import weakref
from builtins import list
from jsonschema import ValidationError
from typing import Any, Callable, Dict, List, Optional, Union

# Project import
from . import base, messages

# intersect imports
from .client import Channel
from .config_models import IntersectConfig
from .exceptions import IntersectWarning
from .logger import logger
from .utils import get_utc, identifier, parse_message_arguments
from .messages import schema_handler

MessageType = Union[messages.Action, messages.Request, messages.Status]
HandlerConfig = Dict[MessageType, List[int]]


def status_tracker(status_on_complete: int, status_on_warn: int = messages.Status.AVAILABLE):
    """Status tracker.

    Args:
        status_on_complete: the status to return on completion.
        status_on_warn: the status to return on warning.
    """

    def status_decorator(function):
        @functools.wraps(function)
        def status_emitter(self, *local_args, **local_kwargs):
            self.send(self.generate_status_busy())
            try:
                tmp = function(self, *local_args, **local_kwargs)
                self.status = status_on_complete
            except IntersectWarning:
                self.status = status_on_warn
                tmp = None
            self.send(self._create_status(status=self.status))
            return tmp

        return status_emitter

    return status_decorator


def force_emit_stop_status(client_ref: weakref.ReferenceType):
    """Accepts a weakref to adapter to ensure stop message on cleanup.

    Usage intent is to use within a weakref finalize call related to an instance
    of Controller. Weakref allows Adapter to be marked for garbage collection. Finalize
    prevents actual data loss before full object cleanup. Calling
    weakref allows access to data just before garbage collection to emit stop.

    Args:
        controller_ref: A ReferenceType for the controller to add pre-garbage collection cleanup to.
    """
    client_obj = client_ref()
    if isinstance(client_obj, Adapter):
        client_obj.status_channel.publish(client_obj.generate_status_stopping())


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
        self.action_channel: Channel = self.connection.channel(f"{self.service_name}/action")
        self.status_channel: Channel = self.connection.channel(f"{self.service_name}/status")
        self.custom_channel: Channel = self.connection.channel(f"{self.service_name}/custom")
        self.request_channel = self.connection.channel(f"{self.service_name}/request")
        self.reply_channel = self.connection.channel(f"{self.service_name}/reply")

        # Subscribe to channels with handler functions
        self.action_channel.subscribe(self.resolve_action_receive)
        self.request_channel.subscribe(self.resolve_request_receive)
        self.reply_channel.subscribe(self.resolve_status_receive)
        self.status_channel.subscribe(self.resolve_status_receive)
        self.custom_channel.subscribe(self.resolve_custom_receive)

        # Set attributes for regular status outputs
        self.status = messages.Status.AVAILABLE
        self.status_thread: Optional[threading.Thread] = None
        self.status_ticker_active: bool = True
        self.message_id_counter = identifier(self.service_name, self.id_counter_init)

        # Setup the Adapter's hierarchy
        self.hierarchy = config.hierarchy.dict()
        self.argument_schema = config.argument_schema

        # weakref to allow garbage collection
        # but allow data access until just before gc occurs
        weak_self = weakref.ref(self)

        # finalizer to support manual cleanup in __del__
        # and unexpected cleanup in program exception
        self._finalizer = weakref.finalize(self, force_emit_stop_status, weak_self)

        # Map of message types to subtypes to lists of handlers for that type
        self.types_to_handlers: Dict[Any, Dict[int, list]] = {}

    def __del__(self):
        """Performs finalization upon deletion."""
        self._finalizer()

    def _generate_action(self, action=None, destination="None", arguments=None) -> messages.Action:
        """Create an Action message.

        Args:
            action: A messages Action type. Used as the message type if set.
            destination: Remote system name string to address the message to.
            arguments: Arguments portion of action message.
        Returns:
            An Action message with sensible default values.
        """
        tmp = messages.Action()
        tmp.header.source = self.service_name
        tmp.header.destination = destination
        tmp.header.message_id = next(self.identifier)
        tmp.header.created = get_utc()
        tmp.action = action
        # The controllers might be expecting something, so send a blank dictionary
        tmp.arguments = json.dumps(arguments)
        return tmp

    def _generate_request(
        self,
        request: messages.Request = None,
        destination: str = "None",
        arguments: Optional[Dict[str, Any]] = None,
    ) -> messages.Request:
        """Create a Request message.

        Args:
            request: A messages Request type. Used as the message type if set.
            destination: Remote system name string to address the message to.
            arguments: User supplied portion of request message details.
        Returns:
            An Request message with sensible default values.
        """
        arguments = arguments if arguments is not None else {}
        tmp = messages.Request()
        tmp.header.source = self.service_name
        tmp.header.destination = destination
        tmp.header.message_id = next(self.identifier)
        tmp.header.created = get_utc()
        tmp.request = request

        # Add system information to user provided details
        tmp.arguments = json.dumps({**self.hierarchy, **arguments})

        return tmp

    def _create_status(
        self,
        status: messages.Status = messages.Status.GENERAL,
        destination: str = "None",
        detail: Optional[Dict[str, Any]] = None,
    ) -> messages.Status:
        """Create a Status message.

        Args:
            request: A messages Status type. Used as the message type if set.
            destination: Remote system name string to address the message to.
            detail: User supplied portion of request message details.
        Returns:
            A Status message with sensible default values.
        """
        detail = detail if detail is not None else {}
        tmp = messages.Status()
        tmp.header.source = self.service_name
        tmp.header.destination = destination
        tmp.header.message_id = next(self.identifier)
        tmp.header.created = get_utc()
        tmp.status = status

        # Add system information to user provided details
        if not detail:
            detail = self.hierarchy
        tmp.detail = json.dumps(detail)

        return tmp

    def _generate_capabilities_availability_status(
        self, detail: Optional[Dict[str, Any]] = None, description: str = ""
    ) -> dict:
        """Creates a message detail section for availibility status.

        Args:
            detail: A dictionary for the message detail section.
            description: The availibility status description to use.
        Return:
            A dictionay of the detail section
        """
        detail = detail if detail is not None else {}
        if "capabilities" not in detail:
            detail["capabilities"] = []

        # Search for an existing Availability_Status
        found_availability_status = False
        for capability in detail["capabilities"]:
            if capability.get("name") == "Availability_Status":
                found_availability_status = True
                break

        # If one wasn't found, create a default OFFLINE one
        if not found_availability_status:
            capability = {
                "name": "Availability_Status",
                "properties": {"status": self.status, "statusDescription": description},
            }
            detail["capabilities"].append(capability)

        # basic way to advertise the schema
        # TODO this should probably be restricted to the Resource Service
        if self.argument_schema:
            detail["argument_schema"] = self.argument_schema

        return detail

    def generate_action_register(self, destination=None, arguments=None) -> messages.Action:
        """Create a REGISTER Action message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Arguments portion of action message.
        Returns:
            A REGISTER Action message with sensible default values.
        """

        msg = self._generate_action(
            action=messages.Action.REGISTER, destination=destination, arguments=arguments
        )
        return msg

    def generate_action_restart(self, destination=None, arguments=None) -> messages.Action:
        """Create a RESTART Action message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Arguments portion of action message.
        Returns:
            A RESTART Action message with sensible default values.
        """

        msg = self._generate_action(
            action=messages.Action.RESTART, destination=destination, arguments=arguments
        )
        return msg

    def generate_action_reset(self, destination=None, arguments=None) -> messages.Action:
        """Create a RESET Action message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Arguments portion of action message.
        Returns:
            A RESET Action message with sensible default values.
        """

        msg = self._generate_action(
            action=messages.Action.RESET, destination=destination, arguments=arguments
        )
        return msg

    def generate_action_set(self, destination=None, arguments=None) -> messages.Action:
        """Create a SET Action message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Arguments portion of action message.
        Returns:
            A SET Action message with sensible default values.
        """

        msg = self._generate_action(
            action=messages.Action.SET, destination=destination, arguments=arguments
        )
        return msg

    def generate_action_start(self, destination=None, arguments=None) -> messages.Action:
        """Create a START Action message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Arguments portion of action message.
        Returns:
            A START Action message with sensible default values.
        """

        msg = self._generate_action(
            action=messages.Action.START, destination=destination, arguments=arguments
        )
        return msg

    def generate_action_stop(self, destination=None, arguments=None) -> messages.Action:
        """Create a STOP Action message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Arguments portion of action message.
        Returns:
            A STOP Action message with sensible default values.
        """

        msg = self._generate_action(
            action=messages.Action.STOP, destination=destination, arguments=arguments
        )
        return msg

    def generate_action_unregister(self, destination=None, arguments=None) -> messages.Action:
        """Create a UNREGISTER Action message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Arguments portion of action message.
        Returns:
            A UNREGISTER Action message with sensible default values.
        """

        msg = self._generate_action(
            action=messages.Action.UNREGISTER, destination=destination, arguments=arguments
        )
        return msg

    def generate_request_all(self, destination=None, arguments=None) -> messages.Request:
        """Create an ALL Request message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Detail portion of Request message.
        Returns:
            An ALL Request message with sensible default values.
        """

        msg = self._generate_request(
            request=messages.Request.ALL, destination=destination, arguments=arguments
        )
        return msg

    def generate_request_detail(self, destination=None, arguments=None) -> messages.Request:
        """Create an DETAIL Request message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Detail portion of Request message.
        Returns:
            An DETAIL Request message with sensible default values.
        """

        msg = self._generate_request(
            request=messages.Request.DETAIL, destination=destination, arguments=arguments
        )
        return msg

    def generate_request_environment(self, destination=None, arguments=None) -> messages.Request:
        """Create an ENVIRONMENT Request message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Detail portion of Request message.
        Returns:
            An ENVIRONMENT Request message with sensible default values.
        """

        msg = self._generate_request(
            request=messages.Request.ENVIRONMENT, destination=destination, arguments=arguments
        )
        return msg

    def generate_request_resources(self, destination=None, arguments=None) -> messages.Request:
        """Create a RESOURCES Request message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Detail portion of Request message.
        Returns:
            A RESOURCES Request message with sensible default values.
        """

        msg = self._generate_request(
            request=messages.Request.RESOURCES, destination=destination, arguments=arguments
        )
        return msg

    def generate_request_status(self, destination=None, arguments=None) -> messages.Request:
        """Create a STATUS Request message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Detail portion of Request message.
        Returns:
            A Status Request message with sensible default values.
        """

        msg = self._generate_request(
            request=messages.Request.STATUS, destination=destination, arguments=arguments
        )
        return msg

    def generate_request_type(self, destination=None, arguments=None) -> messages.Request:
        """Create a TYPE Request message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Detail portion of Request message.
        Returns:
            A TYPE Request message with sensible default values.
        """

        msg = self._generate_request(
            request=messages.Request.TYPE, destination=destination, arguments=arguments
        )
        return msg
    

    def generate_request_uptime(self, destination=None, arguments=None) -> messages.Request:
        """Create an UPTIME Request message.

        Args:
            destination: Remote system name string to address the message to.
            arguments: Detail portion of Request message.
        Returns:
            An UPTIME Request message with sensible default values.
        """

        msg = self._generate_request(
            request=messages.Request.UPTIME, destination=destination, arguments=arguments
        )
        return msg

    def generate_custom_message(self, destination=None, arguments=None, schema=None) -> messages.Custom:
        """Create a Custom Domain Message

        Args:
            destination: Remote system name string to address the message to.
            arguments: Detail portion of Custom message
        Returns:
            A Custom message with sensible default values
        """

        #validate arguments against schema if it exists
        arguments = arguments if arguments is not None else {}
        if schema is not None:
            schema.is_valid(arguments)
        tmp = messages.Custom()
        tmp.header.source = self.service_name
        tmp.header.destination = destination
        tmp.header.message_id = next(self.identifier)
        tmp.header.created = get_utc()
        tmp.custom = messages.Custom.ALL

        tmp.payload = json.dumps(arguments)

        return tmp
    
    def generate_status(
        self,
        status: messages.Status,
        description: str = "",
        detail: Optional[Dict[str, Any]] = None,
    ) -> messages.Status:
        """Used to create Status messages. Adds capabilites if types requires the section.

        Args:
            status: Status message sub-type (i.e. messages.Status.ONLINE).
            description: Description of the status (i.e. "System is online").
            detail: Detail portion of Status message (i.e. dict with domain-specific info).
        Returns:
            A status message
        """
        detail = detail if detail is not None else {}
        # Create status message
        msg = self._create_status(status=status, detail=detail)

        # These message types need the capabilities added to the detail
        status_types_that_require_capabilities = [
            messages.Status.ONLINE,
            messages.Status.OFFLINE,
            messages.Status.STARTING,
            messages.Status.STOPPING,
        ]

        # Add the capability section to message detail if required for status type
        if status in status_types_that_require_capabilities:
            detail_dict = json.loads(msg.detail)
            detail = self._generate_capabilities_availability_status(
                detail=detail_dict,
                description=description,
            )
            msg.detail = json.dumps(detail)

        return msg

    def generate_status_online(
        self,
        detail: Optional[Dict[str, Any]] = None,
    ) -> messages.Status:
        """Create an ONLINE Status message.

        Args:
            detail: Detail portion of Status message.
        Returns:
            An ONLINE Status message with sensible default values.
        """
        detail = detail if detail is not None else {}
        description = f"Service {self.service_name} is online."
        msg = self.generate_status(
            status=messages.Status.ONLINE,
            description=description,
            detail=detail,
        )
        return msg

    def generate_status_offline(
        self,
        detail: Optional[Dict[str, Any]] = None,
    ) -> messages.Status:
        """Create an OFFLINE Status message.

        Args:
            detail: Detail portion of Status message.
        Returns:
            An OFFLINE Status message with sensible default values.
        """
        detail = detail if detail is not None else {}
        description = f"Service {self.service_name} is offline."
        msg = self.generate_status(
            status=messages.Status.OFFLINE,
            description=description,
            detail=detail,
        )
        return msg

    def generate_status_starting(
        self,
        detail: Optional[Dict[str, Any]] = None,
    ) -> messages.Status:
        """Create a STARTING Status message.

        Args:
            detail: Detail portion of Status message.
        Returns:
            An ONLINE Status message with correct metadata showing that the server has started.
        """
        detail = detail if detail is not None else {}
        description = f"Service {self.service_name} online, starting normal status ticker."
        msg = self.generate_status(
            status=messages.Status.STARTING,
            description=description,
            detail=detail,
        )
        return msg

    def generate_status_stopping(
        self,
        detail: Optional[Dict[str, Any]] = None,
    ) -> messages.Status:
        """Create a STOPPING Status message.

        Args:
            detail: Detail portion of Status message.
        Returns:
            An OFFLINE Status message with correct metadata showing that the server has stopped.
        """
        detail = detail if detail is not None else {}
        description = f"Service {self.service_name} is stopping."
        msg = self.generate_status(
            status=messages.Status.STOPPING,
            description=description,
            detail=detail,
        )
        return msg

    def generate_status_available(
        self,
        detail: Optional[Dict[str, Any]] = None,
    ) -> messages.Status:
        """Create an AVAILABLE Status message.

        Args:
            detail: Detail portion of Status message.
        Returns:
            An AVAILABLE Status message with sensible default values.
        """
        detail = detail if detail is not None else {}
        msg = self._create_status(status=messages.Status.AVAILABLE, detail=detail)
        return msg

    def generate_status_ready(
        self,
        detail: Optional[Dict[str, Any]] = None,
    ) -> messages.Status:
        """Create a READY Status message.

        Args:
            detail: Detail portion of Status message.
        Returns:
            A READY Status message with sensible default values.
        """
        detail = detail if detail is not None else {}
        msg = self._create_status(status=messages.Status.READY, detail=detail)
        return msg

    def generate_status_busy(
        self,
        detail: Optional[Dict[str, Any]] = None,
    ) -> messages.Status:
        """Create a BUSY Status message.

        Args:
            detail: Detail portion of Status message.
        Returns:
            A BUSY Status message with sensible default values.
        """
        detail = detail if detail is not None else {}
        msg = self._create_status(status=messages.Status.BUSY, detail=detail)
        return msg

    def generate_status_general(
        self,
        detail: Optional[Dict[str, Any]] = None,
    ) -> messages.Status:
        """Create a GENERAL Status message.

        Args:
            detail: Detail portion of Status message.
        Returns:
            A GENERAL Status message with sensible default values.
        """
        detail = detail if detail is not None else {}
        msg = self._create_status(status=messages.Status.GENERAL, detail=detail)
        return msg

    def send(self, message: MessageType):
        """Send the message.

        Sends the message to the message broker on the appropriate channels.

        Args:
            message: The Message to send.
        """

        if isinstance(message, messages.Status):
            if message.header.destination is None or message.header.destination == "None":
                self.status_channel.publish(message)
            else:
                self.connection.channel(message.header.destination + "/reply").publish(message)
        elif isinstance(message, messages.Action):
            self.connection.channel(message.header.destination + "/action").publish(message)
        elif isinstance(message, messages.Request):
            self.connection.channel(message.header.destination + "/request").publish(message)
        elif isinstance(message, messages.Custom):
            self.connection.channel(message.header.destination + "/custom").publish(message)

    def status_ticker(self):
        """Periodically sends Status messages showing the Server's state."""

        while self.status_ticker_active:
            self.send(self.generate_status_starting())
            self.send(self._create_status(self.status))
            time.sleep(self.status_ticker_interval)

    def start_status_ticker(self):
        """Starts the status thread.

        If the status thread does not exist, starts it. Otherwise prints a message.
        """

        # Start the status thread if it doesn't already exist
        if self.status_thread is None:
            self.status_thread = threading.Thread(
                target=self.status_ticker, daemon=True, name=f"{self.service_name}_status_thread"
            )
            self.status_thread.start()
            logger.info("Started status ticker")
        if self.status_thread is not None:
            logger.info("Status ticker already active")

    def stop_status_ticker(self):
        """Stops the status thread."""

        self.status_ticker_active = False
        if self.status_thread is not None:
            self.status_thread.join()
            self.status_thread = None
        self.status_ticker_active = True
        logger.info("Stopped status ticker")

    def restart_status_ticker(self):
        """Stops the status thread if it exists, then starts a new one."""

        if self.status_thread is not None:
            self.stop_status_ticker()
        self.start_status_ticker()

    def resolve_action_receive(self, message: messages.Action) -> bool:
        """Handle an Action message.

        Delegates messages to the appropriate handler.

        Args:
            message: The Action message to handle.
        Returns:
            True if the message was handled correctly.
        """

        # FIXME is it correct to only look for systems the have
        # this system as a prefix or should this check for equality
        # Ignore messages not addressed to us.
        if not message.header.destination.startswith(self.service_name):
            return True

        # FIXME Decide how to determine when to load data from the message
        # instead of hardcoding in never to do it. Only parse the payload once
        payload = parse_message_arguments(message.arguments, False)

        subtypes = self.types_to_handlers.get(messages.Action, {})
        handlers = subtypes.get(message.action, [])

        for handler in handlers:
            handler[0](message, messages.Action, message.action, payload)
        return True

    def resolve_request_receive(self, message: messages.Request) -> bool:
        """Handle an Request message.

        Delegates messages to the appropriate handler.

        Args:
            message: The Request message to handle.
        Returns:
            True if the message was handled correctly.
        """

        # FIXME is it correct to only look for systems the have
        # this system as a prefix or should this check for equality
        # Ignore messages not addressed to us.
        if not message.header.destination.startswith(self.service_name):
            return True

        # FIXME Decide how to determine when to load data from the message
        # instead of hardcoding in never to do it.
        # Only parse the payload once
        payload = parse_message_arguments(message.arguments, False)

        subtypes = self.types_to_handlers.get(messages.Request, {})
        handlers = subtypes.get(message.request, [])

        for handler in handlers:
            handler[0](message, messages.Request, message.request, payload)
        return True

    def resolve_status_receive(self, message: messages.Status) -> bool:
        """Handle a Status message.

        Delegates messages to the appropriate handler.

        Args:
            message: The Status message to handle.
        Returns:
            True if the message was handled correctly.
        """

        # FIXME is it correct to only look for systems the have
        # this system as a prefix or should this check for equality
        # Ignore messages not addressed to us.
        if not message.header.destination.startswith(self.service_name):
            return True

        # FIXME Decide how to determine when to load data from the message
        # instead of hardcoding in never to do it. Only parse the payload once
        payload = parse_message_arguments(message.detail, False)

        subtypes = self.types_to_handlers.get(messages.Status, {})
        handlers = subtypes.get(message.status, [])

        for handler in handlers:
            handler[0](message, messages.Status, message.status, payload)
        return True

    def resolve_custom_receive(self, message: messages.Custom) -> bool:
        """Handle a Custom message.

        Delegates messages to the appropriate handler.

        Args:
            message: The Status message to handle.
        Returns:
            True if the message was handled correctly.
        """

        # FIXME is it correct to only look for systems the have
        # this system as a prefix or should this check for equality
        # Ignore messages not addressed to us.
        if not message.header.destination.startswith(self.service_name):
            return True

        # FIXME Decide how to determine when to load data from the message
        # instead of hardcoding in never to do it. Only parse the payload once
        payload = parse_message_arguments(message.payload, False)
        subtypes = self.types_to_handlers.get(messages.Custom, {})
        handlers = subtypes.get(message.custom, [])

        for handler in handlers:
            payload = json.loads(message.payload)
            try:
                handler[1].is_valid(payload)
                if handler[1].filter is None:
                    handler[0](message, messages.Custom, message.custom, payload)
                elif handler[1].filter in payload:
                    handler[0](message, messages.Custom, message.custom, payload[handler[1].filter])
            except ValidationError:
                continue
        return True
    
    def register_message_handler(self, handler: Callable, types_: HandlerConfig, schema_handler = None):
        """Register a message handler callable to be run.

        Register the handler so that it will be run whenever
        a message of one of the given Action, Request, and/or Status
        types is received. Reference
        intersect_sdk.common.message_handler.SampleMessageHandler
        for a callable class.

        Args:
            handler: The message handler callable to register.
            types_: Dictionary of message types with lists of handled subtypes.
        """
        for message_type, message_subtypes in types_.items():
            subtypes: dict = self.types_to_handlers.setdefault(message_type, {})
            for item in message_subtypes:
                handlers = subtypes.setdefault(item, [])
                for entry in handlers:
                    if entry[0] is handler:
                        continue
                handlers.append((handler, schema_handler))

    def unregister_message_handler(self, handler: Callable):
        """Unregister a message handler.

        Remove a message handler and no longer give it received messages.

        Args:
            handler: The Callable message handler to unregister.
        """
        for message_subtypes in self.types_to_handlers.values():
            for handlers in message_subtypes.values():
                handlers = filter(handlers, lambda x: x[0] is not handler)

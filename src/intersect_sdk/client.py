"""One-off scripting arrangements and user-created orchestrators are Clients. If you're looking to register your application into INTERSECT, please see the intersect_sdk.service module.

The Client is meant to be a way to interact with specific INTERSECT Services through custom scripts. You'll need to have knowledge
of the schemas of these services when constructing your client, as this class does not make any assumptions about the services
beyond how they would be managed in the SDK's own IntersectService class.

Users do not need to interact with the client other than through its constructor and the lifecycle
"start" and "stop" methods.

The service will automatically handle all system-level interfaces (i.e. status broadcasts).
User-level interfaces are all handled on the same messaging channel, so users should not need to configure
message brokers or the data layer beyond defining credentials in their "IntersectConfig" class.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Sequence, Union
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError
from typing_extensions import Self, TypeAlias

from ._internal.control_plane.control_plane_manager import (
    GENERIC_MESSAGE_SERIALIZER,
    ControlPlaneManager,
)
from ._internal.data_plane.data_plane_manager import DataPlaneManager
from ._internal.exceptions import IntersectError
from ._internal.logger import logger
from ._internal.messages.userspace import (
    UserspaceMessage,
    create_userspace_message,
    deserialize_and_validate_userspace_message,
)
from ._internal.stoppable_thread import StoppableThread
from ._internal.utils import die, send_os_signal
from ._internal.version_resolver import resolve_user_version
from .annotations import IntersectDataHandler, IntersectMimeType
from .config.client import IntersectClientConfig
from .config.shared import HierarchyConfig
from .constants import SYSTEM_OF_SYSTEM_REGEX


class IntersectClientMessageParams(BaseModel):
    """The user implementing the IntersectClient class will need to return this object in order to send a message to another Service."""

    destination: str = Field(pattern=SYSTEM_OF_SYSTEM_REGEX)
    """
    The destination string. You'll need to know the system-of-system representation of the Service.

    Note that this should match what you would see in the schema.
    """

    operation: str
    """
    The name of the operation you want to call from the Service - this should be represented as it is in the Service's schema.
    """

    payload: Any
    """
    The raw Python object you want to have serialized as the payload.

    If you want to just use the service's default value for a request (assuming it has a default value for a request), you may set this as None.
    """

    response_content_type: IntersectMimeType = IntersectMimeType.JSON
    """
    The IntersectMimeType of your response. You'll want this to match with the ContentType of the function from the schema.

    default: IntersectMimeType.JSON
    """

    response_data_handler: IntersectDataHandler = IntersectDataHandler.MESSAGE
    """
    The InteresectDataHandler you want to use (most people can just use IntersectDataHandler.MESSAGE here, unless your data is very large)

    default: IntersectDataHandler.MESSAGE
    """


INTERSECT_JSON_VALUE: TypeAlias = Union[
    List['INTERSECT_JSON_VALUE'],
    Dict[str, 'INTERSECT_JSON_VALUE'],
    str,
    bool,
    int,
    float,
    None,
]
"""
This is a simple type representation of JSON as a Python object. INTERSECT will automatically deserialize service payloads into one of these types.

(Pydantic has a similar type, "JsonValue", which should be used if you desire functionality beyond type hinting. This is strictly a type hint.)
"""


INTERSECT_CLIENT_CALLBACK_TYPE = Callable[
    [str, str, bool, INTERSECT_JSON_VALUE],
    Union[IntersectClientMessageParams, Sequence[IntersectClientMessageParams], None],
]
"""
This is a callable function type which should be defined by the user.

Note: DO NOT handle serialization/deserialization yourself, the SDK will take care of this.

Params
  The SDK will send the function four arguments:
    1) The message source - this is mostly useful for your own control flow loops you write in the function
    2) The name of the operation that triggered the response from your ORIGINAL message - needed for your own control flow loops if sending multiple messages.
    3) A boolean - if True, there was an error; if False, there was not.
    4) The response, as a Python object - the type should be based on the corresponding Service's schema response.
       The Python object will already be deserialized for you. If parameter 3 was "True", then this will be the error message, as a string.
       If parameter 3 was "False", then this will be either an integer, boolean, float, string, None,
       a List[T], or a Dict[str, T], where "T" represents any of the 7 aforementioned types.

Returns
  If you want to send one or many messages in reaction to a message, the function should return an IntersectClientMessageParams object or a list/tuple of IntersectClientMessageParams objects.

  If you are DONE listening to messages, raise a generic Exception from your function.

  If you DON'T want to send another message, but want to continue listening for messages, you can just return None.
Raises
  Any uncaught or raised exceptions the callback function throws will terminate the INTERSECT lifecycle.
"""


class IntersectClient:
    """If you're just wanting to connect into INTERSECT temporarily to send messages between services, use the IntersectClient class.

    Note that the ONLY current stable API is:
    - the constructor
    - startup()
    - shutdown()
    - is_connected()

    No other functions or parameters are guaranteed to remain stable.

    NOTE: the current implementation requires you have knowledge about the schema of the service(s) you're wanting to communicate with.
    """

    def __init__(
        self,
        config: IntersectClientConfig,
        initial_messages: list[IntersectClientMessageParams],
        user_callback: INTERSECT_CLIENT_CALLBACK_TYPE,
        resend_initial_messages_on_secondary_startup: bool = False,
    ) -> None:
        """The constructor performs almost all validation checks necessary to function in the INTERSECT ecosystem, with the exception of checking connections/credentials to any backing services.

        Parameters:
          config: The IntersectConfig class
          user_callback: The callback function you can use to handle response messages from the other Service.
            If this is left empty, you can only send a single message
        """
        # this is called here in case a user created the object using "IntersectClientConfig.model_construct()" to skip validation
        config = IntersectClientConfig.model_validate(config)
        if not callable(user_callback):
            die('user_callback function should be defined in argument to IntersectClient')
        self._user_callback = user_callback

        if not initial_messages or not isinstance(initial_messages, list):
            die('must provide at least one initial message to send')

        self._initial_messages = initial_messages
        self._resend_initial_messages = resend_initial_messages_on_secondary_startup
        self._sent_initial_messages = False

        # use a fake hierarchy so that backing service logic utilizes the same API
        self._hierarchy = HierarchyConfig(
            service='tmp-', system='tmp-', facility='tmp-', organization=f'tmp-{uuid4()!s}'
        )

        self._heartbeat_thread: StoppableThread | None = None
        self._heartbeat = 0.0

        self._data_plane_manager = DataPlaneManager(self._hierarchy, config.data_stores)
        # we SUBSCRIBE to messages on this channel.
        self._userspace_channel_name = f"{self._hierarchy.hierarchy_string('/')}/userspace"
        self._control_plane_manager = ControlPlaneManager(
            control_configs=config.brokers,
        )
        self._control_plane_manager.add_subscription_channel(
            self._userspace_channel_name, {self._handle_userspace_message_raw}
        )

    def startup(self) -> Self:
        """This function connects the client to all INTERSECT systems.

        You will need to call this function at least once in your application's lifecycle.
        You will also need to call it again if you call shutdown() on the service, and want to
        restart the INTERSECT connection without killing your application's process.

        This function should only be called in your own lifecycle functions. The default INTERSECT
        lifecycle loop will call it prior to starting the main lifecycle loop.
        """
        logger.info('Client is starting up')

        self._control_plane_manager.connect()

        # start the heartbeat thread
        if self._heartbeat_thread is None:
            self._heartbeat = time.time()
            self._heartbeat_thread = StoppableThread(
                target=self._heartbeat_ticker, name=f'IntersectClient_{uuid4()!s}_heartbeat_thread'
            )
            self._heartbeat_thread.start()

        if self._resend_initial_messages or not self._sent_initial_messages:
            for message in self._initial_messages:
                self._send_userspace_message(message)

        self._sent_initial_messages = True

        logger.info('Client startup complete')
        return self

    def shutdown(self, reason: str | None = None) -> Self:
        """This function disconnects the client from INTERSECT configurations. It does NOT otherwise drop anything else from memory.

        This function should generally be called immediately after the broker connection loop.

        The function should only be called in your own lifecycle functions. The default INTERSECT
        lifecycle loop will call it once it breaks out of the main lifecycle loop.

        Params:
          - reason: an optional description you may provide as to why the adapter is shutting down (currently unused for client).
        """
        logger.info(f'Client is shutting down (reason: {reason})')

        # Stop listening to the heartbeat
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.stop()
            self._heartbeat_thread.join()
            self._heartbeat_thread = None
            self._heartbeat = 0.0

        self._control_plane_manager.disconnect()

        logger.info('Client shutdown complete')
        return self

    def is_connected(self) -> bool:
        """Check if we're currently connected to the INTERSECT brokers.

        Returns:
          True if we are currently connected to INTERSECT, False if not
        """
        return self._control_plane_manager.is_connected()

    def _handle_userspace_message_raw(self, raw: bytes) -> None:
        """Broker callback, deserialize and validate a userspace message from a broker."""
        self._heartbeat = time.time()
        try:
            message = deserialize_and_validate_userspace_message(raw)
            logger.debug(f'Received userspace message:\n{message}')
            self._handle_userspace_message(message)
        except ValidationError as e:
            logger.warning(
                f'Invalid message received on userspace message channel, ignoring. Full message:\n{e}'
            )
            # NOTE
            # This may seem fairly drastic for an error which would be routinely dropped in the service,
            # but I would argue that it's fine here. If a service isn't sending valid messages,
            # the client has bigger problems.
            send_os_signal()

    def _handle_userspace_message(self, message: UserspaceMessage) -> None:
        """Handle a deserialized userspace message."""
        # ONE: HANDLE CORE COMPAT ISSUES
        # is this first branch necessary? May not be in the future
        if self._hierarchy.hierarchy_string('.') != message['headers'][
            'destination'
        ] or not resolve_user_version(message):
            # NOTE
            # Again, I would argue that while this may seem drastic, it's fine here.
            # A client should NEVER be getting messages not addressed to it in a normal workflow.
            # A client should also know enough about service SDK versions to know if
            # it's even possible to try to send messages between them.
            send_os_signal()
            return

        # TWO: GET DATA FROM APPROPRIATE DATA STORE AND DESERIALIZE IT
        try:
            request_params = GENERIC_MESSAGE_SERIALIZER.validate_json(
                self._data_plane_manager.incoming_message_data_handler(message)
            )
        except ValidationError as e:
            logger.warning(f'Service sent back invalid response:\n{e}')
            # NOTE
            # If the service sent something back which caused ValidationError
            # to fail on an Any-typed TypeAdapter, the problem is with the service.
            # I'd kill the client just to be safe.
            send_os_signal()
            return
        except IntersectError:
            # NOTE
            # This is less controversial here. This indicates that the client
            # couldn't talk to the data plane instance.
            send_os_signal()
            return

        # THREE: CALL USER FUNCTION AND GET RETURN
        try:
            # NOTE: the way the service sends a message, errors and non-errors can be handled identically.
            # Leave it to the user to determine how they want to handle an error.
            user_function_return = self._user_callback(
                message['headers']['source'],
                message['operationId'],
                message['headers']['has_error'],
                request_params,  # type: ignore[arg-type]
            )
        except Exception as e:  # noqa: BLE001 (need to catch all possible exceptions to gracefully handle the thread)
            logger.warning(f"Exception from user's callback function:\n{e}")
            # NOTE
            # This is a DELIBERATE design decision. ALL uncaught Exceptions should terminate the pub/sub loop!
            # Users are even encouraged to deliberately raise Exceptions!
            # Almost every application will want to loop forever until a certain condition.
            # You could argue that OS signals can interfere with other parts of the application.
            # In the future, we may want to allow users to specify an alternate callback.
            send_os_signal()
            return
        if not user_function_return:
            # continue listening for additional messages, but no need to send one out
            return

        if isinstance(user_function_return, Sequence):
            for msg in user_function_return:
                self._send_userspace_message(msg)
        else:
            self._send_userspace_message(user_function_return)

    def _send_userspace_message(self, params: IntersectClientMessageParams) -> None:
        """Send a userspace message, be it an initial message from the user or from the user's callback function."""
        # ONE: VALIDATE AND SERIALIZE FUNCTION RESULTS
        try:
            params = IntersectClientMessageParams.model_validate(params)
        except ValidationError as e:
            logger.error(f'Invalid message parameters:\n{e}')
            # NOTE
            # this is always the client's fault, so probably best to terminate here
            send_os_signal()
            return
        response = GENERIC_MESSAGE_SERIALIZER.dump_json(params.payload, warnings=False)

        # TWO: SEND DATA TO APPROPRIATE DATA STORE
        try:
            response_payload = self._data_plane_manager.outgoing_message_data_handler(
                response, params.response_content_type, params.response_data_handler
            )
        except IntersectError:
            # NOTE
            # This is less controversial here. This indicates that the client
            # couldn't talk to the data plane instance.
            send_os_signal()
            return

        # THREE: SEND MESSAGE
        msg = create_userspace_message(
            source=self._hierarchy.hierarchy_string('.'),
            destination=params.destination,
            service_version='0.0.0',
            content_type=params.response_content_type,
            data_handler=params.response_data_handler,
            operation_id=params.operation,
            payload=response_payload,
        )
        logger.debug(f'Send userspace message:\n{msg}')
        response_channel = f"{params.destination.replace('.', '/')}/userspace"
        self._control_plane_manager.publish_message(response_channel, msg)

    def _heartbeat_ticker(self) -> None:
        """Separate thread which checks to see how long it has been since a broker message was received.

        If a broker has been connected for 5 minutes without sending a message, prepare to terminate the application.
        """
        if self._heartbeat_thread:
            self._heartbeat_thread.wait(300.0)
            while not self._heartbeat_thread.stopped():
                elapsed = time.time() - self._heartbeat
                if elapsed > 300.0:
                    # NOTE
                    # This is by design. We explicitly don't want dangling clients
                    # sucking up bandwidth on brokers. It could even be argued that we should
                    # just call os.abort() here (this way so the Python application can't catch the SIGABRT),
                    # but SIGTERM is the soundest to ensure graceful application shutdown.
                    # However, graceful application shutdown is not as important for clients as it is for services...
                    send_os_signal()
                self._heartbeat_thread.wait(300.0)

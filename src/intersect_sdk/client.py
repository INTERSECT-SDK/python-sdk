"""One-off scripting arrangements and user-created orchestrators are Clients. If you're looking to register your application into INTERSECT, please see the intersect_sdk.service module.

The Client is meant to be a way to interact with specific INTERSECT Services through custom scripts. You'll need to have knowledge
of the schemas of these services when constructing your client, as this class does not make any assumptions about the services
beyond how they would be managed in the SDK's own IntersectService class.

Users do not need to interact with the client other than through its constructor and the lifecycle
"start" and "stop" methods.

Most useful definitions and typings will be found in the client_callback_definitions module.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import ValidationError
from typing_extensions import Self, final

from ._internal.control_plane.control_plane_manager import (
    GENERIC_MESSAGE_SERIALIZER,
    ControlPlaneManager,
)
from ._internal.data_plane.data_plane_manager import DataPlaneManager
from ._internal.exceptions import IntersectError
from ._internal.logger import logger
from ._internal.messages.event import (
    EventMessage,
    deserialize_and_validate_event_message,
)
from ._internal.messages.userspace import (
    UserspaceMessage,
    create_userspace_message,
    deserialize_and_validate_userspace_message,
)
from ._internal.utils import die, send_os_signal
from ._internal.version_resolver import resolve_user_version
from .client_callback_definitions import (
    IntersectClientCallback,
)
from .config.client import IntersectClientConfig
from .config.shared import HierarchyConfig

if TYPE_CHECKING:
    from .client_callback_definitions import (
        INTERSECT_CLIENT_EVENT_CALLBACK_TYPE,
        INTERSECT_CLIENT_RESPONSE_CALLBACK_TYPE,
    )
    from .shared_callback_definitions import IntersectDirectMessageParams


@final
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
        user_callback: INTERSECT_CLIENT_RESPONSE_CALLBACK_TYPE | None = None,
        event_callback: INTERSECT_CLIENT_EVENT_CALLBACK_TYPE | None = None,
    ) -> None:
        """The constructor performs almost all validation checks necessary to function in the INTERSECT ecosystem, with the exception of checking connections/credentials to any backing services.

        Parameters:
          config: The IntersectClientConfig class
          user_callback: The callback function you can use to handle response messages from Services.
            If this is left empty, you can only send a single message
          event_callback: The callback function you can use to handle events from any Service.
        """
        # this is called here in case a user created the object using "IntersectClientConfig.model_construct()" to skip validation
        config = IntersectClientConfig.model_validate(config)

        if user_callback is not None and not callable(user_callback):
            die('user_callback function should be a callable function if defined')
        if event_callback is not None and not callable(event_callback):
            die('event_callback function should be a callable function if defined')
        if not user_callback and not event_callback:
            die('must define at least one of user_callback or event_callback')
        if not user_callback:
            logger.warning(
                'IntersectClient does not have user_callback defined, so cannot react to responses from other services.'
            )
        if not event_callback:
            logger.warning(
                'IntersectClient does not have event_callback defined, so cannot react to events from other services.'
            )
        # special validation block regarding config
        if (
            not config.terminate_after_initial_messages
            and not config.initial_message_event_config.messages_to_send
            and not config.initial_message_event_config.services_to_start_listening_for_events
        ):
            die(
                'IntersectClientConfig.initial_message_event_config: if "IntersectClientConfig.terminate_after_initial_messages" is not True, must define at least one of: initial messages to send, or initial services to listen for events'
            )

        self._initial_messages = config.initial_message_event_config.messages_to_send
        self._resend_initial_messages = config.resend_initial_messages_on_secondary_startup
        self._sent_initial_messages = False
        self._terminate_after_initial_messages = config.terminate_after_initial_messages

        # use a fake hierarchy so that backing service logic utilizes the same API
        self._hierarchy = HierarchyConfig(
            service=f'tmp-{uuid4()!s}',
            system=config.system,
            facility=config.facility,
            organization=config.organization,
        )

        self._data_plane_manager = DataPlaneManager(self._hierarchy, config.data_stores)
        self._control_plane_manager = ControlPlaneManager(
            control_configs=config.brokers,
        )
        if not config.terminate_after_initial_messages:
            # we only SUBSCRIBE to this channel, and we only need to register it if we have a user callback in the first place
            if user_callback:
                # Do not persist, as we use the temporary client information to build this.
                self._control_plane_manager.add_subscription_channel(
                    f"{self._hierarchy.hierarchy_string('/')}/response",
                    {self._handle_userspace_message_raw},
                    persist=False,
                )
            if event_callback:
                # Do not persist, as event messages are meant to be short-lived.
                # Creating a dedicated queue for a Client is not feasible here.
                for (
                    service
                ) in config.initial_message_event_config.services_to_start_listening_for_events:
                    self._control_plane_manager.add_subscription_channel(
                        f"{service.replace('.', '/')}/events",
                        {self._handle_event_message_raw},
                        persist=False,
                    )
        self._user_callback = user_callback
        self._event_callback = event_callback

    @final
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

        if self.considered_unrecoverable():
            logger.error('Cannot start service due to unrecoverable error')
            return self

        # TODO this is necessary to avoid certain data races
        # specifically, trying to publish messages before AMQP channels are open
        # this problem is quite noticeable with the AMQP hello-world example,
        # and has nothing to do with the Service at all.
        time.sleep(1.0)

        if self._resend_initial_messages or not self._sent_initial_messages:
            for message in self._initial_messages:
                self._send_userspace_message(message)

        self._sent_initial_messages = True

        logger.info('Client startup complete')

        if self._terminate_after_initial_messages:
            logger.info('Client terminating')
            send_os_signal()

        return self

    @final
    def shutdown(self, reason: str | None = None) -> Self:
        """This function disconnects the client from INTERSECT configurations. It does NOT otherwise drop anything else from memory.

        This function should generally be called immediately after the broker connection loop.

        The function should only be called in your own lifecycle functions. The default INTERSECT
        lifecycle loop will call it once it breaks out of the main lifecycle loop.

        Params:
          - reason: an optional description you may provide as to why the adapter is shutting down (currently unused for client).
        """
        logger.info(f'Client is shutting down (reason: {reason})')

        self._control_plane_manager.disconnect()

        logger.info('Client shutdown complete')
        return self

    @final
    def is_connected(self) -> bool:
        """Check if we're currently connected to the INTERSECT brokers.

        Returns:
          True if we are currently connected to INTERSECT, False if not
        """
        return self._control_plane_manager.is_connected()

    @final
    def considered_unrecoverable(self) -> bool:
        """Check if any broker is considered to be in an unrecoverable state.

        Returns:
          - True if we can't recover, false otherwise
        """
        return self._control_plane_manager.considered_unrecoverable()

    def _handle_userspace_message_raw(self, raw: bytes) -> None:
        """Broker callback, deserialize and validate a userspace message from a broker."""
        # safety check in case we get messages back faster than we can send them
        if self._terminate_after_initial_messages:
            return

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
                request_params,
            )  # type: ignore[misc]
            # mypy note: when we are in this function, we know that the callback has been defined
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

        self._handle_client_callback(user_function_return)

    def _handle_event_message_raw(self, raw: bytes) -> None:
        """Broker callback, deserialize and validate an event message from a broker."""
        # safety check in case we get messages back faster than we can send them
        if self._terminate_after_initial_messages:
            # safety check in case we get messages back faster than we can send them
            return

        try:
            message = deserialize_and_validate_event_message(raw)
            logger.debug(f'Received userspace message:\n{message}')
            self._handle_event_message(message)
        except ValidationError as e:
            logger.warning(
                f'Invalid message received on event message channel, ignoring. Full message:\n{e}'
            )
            # NOTE
            # Unlike Userspace messages, we can safely discard bad event messages without dropping the pubsub loop.

    def _handle_event_message(self, message: EventMessage) -> None:
        """Handle a deserialized event message."""
        # ONE: HANDLE CORE COMPAT ISSUES
        if not resolve_user_version(message):
            # NOTE
            # Again, I would argue that while this may seem drastic, it's fine here.
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
            event_function_return = self._event_callback(
                message['headers']['source'],
                message['operationId'],
                message['headers']['event_name'],
                request_params,
            )  # type: ignore[misc]
            # mypy note: when we are in this function, we know that the callback has been defined
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
        self._handle_client_callback(event_function_return)

    def _handle_client_callback(self, user_value: IntersectClientCallback | None) -> None:
        """Validate the user's return value from a callback, and send messages + change events listened to as dictated."""
        if not user_value:
            # continue listening for additional messages, but no need to send one out
            return
        try:
            validated_result = IntersectClientCallback.model_validate(user_value)
        except ValidationError as e:
            logger.error(f'Return value does not match IntersectClientCallback specification\n{e}')
            # NOTE - this is deliberate because a user should be returning correct values
            send_os_signal()
            return

        if self._event_callback:
            for add_event in validated_result.services_to_start_listening_for_events:
                self._control_plane_manager.add_subscription_channel(
                    f"{add_event.replace('.', '/')}/events",
                    {self._handle_event_message_raw},
                    persist=False,
                )
            for remove_event in validated_result.services_to_stop_listening_for_events:
                self._control_plane_manager.remove_subscription_channel(
                    f"{remove_event.replace('.', '/')}/events"
                )

        # sending userspace messages without the callback is okay, we just won't get the response
        for message in validated_result.messages_to_send:
            self._send_userspace_message(message)

    def _send_userspace_message(self, params: IntersectDirectMessageParams) -> None:
        """Send a userspace message, be it an initial message from the user or from the user's callback function."""
        # ONE: SERIALIZE FUNCTION RESULTS
        # (function input should already be validated at this point)
        msg_payload = GENERIC_MESSAGE_SERIALIZER.dump_json(params.payload, warnings=False)

        # TWO: SEND DATA TO APPROPRIATE DATA STORE
        try:
            out_payload = self._data_plane_manager.outgoing_message_data_handler(
                msg_payload, params.content_type, params.data_handler
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
            content_type=params.content_type,
            data_handler=params.data_handler,
            operation_id=params.operation,
            payload=out_payload,
        )
        logger.debug(f'Send userspace message:\n{msg}')
        channel = f"{params.destination.replace('.', '/')}/request"
        # WARNING: If both the Service and the Client drop, the Service will execute the command
        # but cannot communicate the response to the Client.
        # in experiment controllers or production, you'll want to set persist to True
        self._control_plane_manager.publish_message(channel, msg, persist=False)

"""Persistent, registered entities into INTERSECT are Services. If you're looking to create your own orchestrator or utilize a temporary script, please see the intersect_sdk.client module.

The Service is at the heart of a client-developed SDK. It works off of a user-defined capability (which can extend from many capabilities),
and automatically integrates the user-defined capability into INTERSECT's message and schema-based
ecosystem.

Users do not need to interact with the service other than through its constructor and the lifecycle
"start" and "stop" methods.

The service will automatically handle all system-level interfaces (i.e. status broadcasts).
User-level interfaces are all handled on the same messaging channel, so users should not need to configure
message brokers or the data layer beyond defining credentials in their "IntersectConfig" class.

Most useful definitions and typings will be found in the service_definitions module.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

from pydantic import ValidationError
from pydantic_core import PydanticSerializationError
from typing_extensions import Self, final

from ._internal.constants import (
    RESPONSE_CONTENT,
    RESPONSE_DATA,
    SHUTDOWN_KEYS,
    STRICT_VALIDATION,
)
from ._internal.control_plane.control_plane_manager import ControlPlaneManager
from ._internal.data_plane.data_plane_manager import DataPlaneManager
from ._internal.exceptions import IntersectApplicationError, IntersectError
from ._internal.interfaces import IntersectEventObserver
from ._internal.logger import logger
from ._internal.messages.event import create_event_message
from ._internal.messages.lifecycle import LifecycleType, create_lifecycle_message
from ._internal.messages.userspace import (
    UserspaceMessage,
    create_userspace_message,
    deserialize_and_validate_userspace_message,
)
from ._internal.schema import get_schema_and_functions_from_capability_implementation
from ._internal.stoppable_thread import StoppableThread
from ._internal.utils import die
from ._internal.version_resolver import resolve_user_version
from .capability.base import IntersectBaseCapabilityImplementation
from .config.service import IntersectServiceConfig
from .core_definitions import IntersectDataHandler, IntersectMimeType
from .version import version_string

if TYPE_CHECKING:
    from ._internal.function_metadata import FunctionMetadata


@final
class IntersectService(IntersectEventObserver):
    """This is the core gateway class for a user's application into INTERSECT.

    A service receives messages from a source, then sends a response message to that same source.
    On a scientific domain level, this can be expressed through a simple functional style: you take in inputs,
    you return your output.

    The service automatically integrates all of the following components:
      - The user-defined capability
      - Any message brokers
      - Any core INTERSECT data layers

    What it does NOT do:
      - deal with any custom messaging logic - i.e. Pyro logic, an internal ZeroMQ system, etc. ... these should be defined on the capability level.
      - deal with any application logic - that should be handled by the user's capability

    Users should generally not need to interact with objects of this class outside of the constructor and the startup() and shutdown() functions. It's advisable
    not to mutate the service object yourself, though you can freely log out properties for debugging purposes.

    Note: The ONLY stable function methods are:
      - the constructor
      - startup()
      - shutdown()
      - is_connected()
      - forbid_keys()
      - allow_keys()
      - allow_all_functions()
      - get_blocked_keys()

    No other functions or parameters are guaranteed to remain stable.
    """

    def __init__(
        self,
        capability: IntersectBaseCapabilityImplementation,
        config: IntersectServiceConfig,
    ) -> None:
        """The constructor performs almost all validation checks necessary to function in the INTERSECT ecosystem, with the exception of checking connections/credentials to any backing services.

        Parameters:
          capability: Your capability implementation class
          config: The IntersectConfig class
        """
        if not isinstance(capability, IntersectBaseCapabilityImplementation):
            die(
                f'IntersectService parameter must inherit from intersect_sdk.IntersectBaseCapabilityImplementation instead of "{capability.__class__.__name__}" .'
            )
        if not hasattr(capability, '__intersect_sdk_observers__'):
            die(
                f'{capability.__class__.__name__} needs to call "super().__init__()" in the constructor.'
            )
        # this is called here in case a user created the object using "IntersectServiceConfig.model_construct()" to skip validation
        config = IntersectServiceConfig.model_validate(config)
        self.capability = capability
        (
            schema,
            function_map,
            event_map,
            status_fn_name,
            status_type_adapter,
        ) = get_schema_and_functions_from_capability_implementation(
            capability.__class__,
            capability_name=config.hierarchy,
            excluded_data_handlers=config.data_stores.get_missing_data_store_types(),
        )
        self._schema = schema
        """
        Stringified schema of the user's application. Gets sent in several status message requests.
        """
        self._function_map = MappingProxyType(function_map)
        """
        INTERNAL USE ONLY

        Immutable mapping of operation IDs (advertised in schema, sent in message) to actual function implementations.

        You can get user-defined properties from the method via getattr(_function_map.method, KEY), the keys get set
        in the intersect_message decorator function (annotations.py).
        """
        self._event_map = MappingProxyType(event_map)
        """
        INTERNAL USE ONLY

        Immutable mapping of event names to actual function implementations.
        """

        self._function_keys: set[str] = set()
        """
        INTERNAL USE ONLY

        If a function has any key in this set, the function will not run.

        Beware! Since this hash set can be mutated, there are potential problems with concurrent operations
        if you do mutate the hash set. Only mutate this property via the public methods to minimize potential
        concurrency issues.
        """

        self._hierarchy = config.hierarchy

        self._status_thread: StoppableThread | None = None
        self._status_ticker_interval = config.status_interval
        self._status_retrieval_fn: Callable[[], bytes] = (
            (
                lambda: status_type_adapter.dump_json(
                    getattr(self.capability, status_fn_name)(), by_alias=True, warnings='error'
                )
            )
            if status_type_adapter and status_fn_name
            else lambda: b'null'
        )

        self._status_memo = self._status_retrieval_fn()

        self._data_plane_manager = DataPlaneManager(self._hierarchy, config.data_stores)
        # we PUBLISH messages on this channel
        self._lifecycle_channel_name = f"{config.hierarchy.hierarchy_string('/')}/lifecycle"
        # we PUBLISH event messages on this channel
        self._events_channel_name = f"{config.hierarchy.hierarchy_string('/')}/events"
        # we SUBSCRIBE to messages on this channel
        self._userspace_channel_name = f"{config.hierarchy.hierarchy_string('/')}/userspace"
        self._control_plane_manager = ControlPlaneManager(
            control_configs=config.brokers,
        )
        # our userspace queue should be able to survive shutdown
        self._control_plane_manager.add_subscription_channel(
            self._userspace_channel_name,
            {self._handle_userspace_message_raw},
            persist=True,
        )

        # we generally start observing and don't stop, doesn't really matter if we startup or shutdown
        self.capability._intersect_sdk_register_observer(self)  # noqa: SLF001 (we don't want users calling or overriding it, but this is fine.)

    @final
    def startup(self) -> Self:
        """This function connects the service to all INTERSECT systems.

        You will need to call this function at least once in your application's lifecycle.
        You will also need to call it again if you call shutdown() on the service, and want to
        restart the INTERSECT connection without killing your application's process.

        This function should only be called in your own lifecycle functions. The default INTERSECT
        lifecycle loop will call it prior to starting the main lifecycle loop.

        NOTE: any functions which were manually blocked will continue to be blocked
        if you restart the service; call "service.allow_all_keys()" to unblock
        all functions.
        """
        logger.info('Service is starting up')

        self._control_plane_manager.connect()

        if self.considered_unrecoverable():
            logger.error('Cannot start service due to unrecoverable error')
            return self

        self._send_lifecycle_message(
            lifecycle_type=LifecycleType.STARTUP,
            payload={'schema': self._schema, 'status': self._status_memo},
        )

        # Start the status thread if it doesn't already exist
        if self._status_thread is None:
            self._status_thread = StoppableThread(
                target=self._status_ticker, name=f'IntersectService_{uuid4()!s}_status_thread'
            )
            self._status_thread.start()

        logger.info('Service startup complete')
        return self

    @final
    def shutdown(self, reason: str | None = None) -> Self:
        """This function disconnects the service from all INTERSECT systems. It does NOT otherwise drop anything else from memory.

        You should call this function whenever your
        application is terminating. You may also call this function
        if you need to temporarily disconnect from INTERSECT systems,
        although this usecase is relatively niche.

        The function should only be called in your own lifecycle functions. The default INTERSECT
        lifecycle loop will call it once it breaks out of the main lifecycle loop.

        Params:
          - reason: an optional description you may provide as to why the adapter is shutting down.
        """
        logger.info(f'Service is shutting down (reason: {reason})')

        # Stop polling
        if self._status_thread is not None:
            self._status_thread.stop()
            self._status_thread.join()
            self._status_thread = None

        try:
            self._send_lifecycle_message(lifecycle_type=LifecycleType.SHUTDOWN, payload=reason)
        except Exception as e:  # noqa: BLE001  (this could fail on numerous protocols)
            logger.error(
                'Could not send shutdown message, INTERSECT Core will eventually assume this Service has shutdown.'
            )
            logger.debug(e)

        self._control_plane_manager.disconnect()

        logger.info('Service shutdown complete')
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

    def forbid_keys(self, keys: set[str]) -> Self:
        """Block all functions annotated with any key in "keys", and send out an appropriate message.

        NOTE: if you want to bulk forbid everything, you may want to call
        adapter.shutdown() to disconnect entirely from INTERSECT.

        Params:
          keys: keys of functions you want to block
        """
        self._function_keys |= keys
        self._send_lifecycle_message(
            lifecycle_type=LifecycleType.FUNCTIONS_BLOCKED,
            payload=tuple(keys),
        )
        return self

    def allow_keys(self, keys: set[str]) -> Self:
        """Allow all functions annotated with any key in "keys", and send out an appropriate message.

        NOTE: if the function has multiple keys, the function will only be "allowed"
        if all keys which have been forbidden are now allowed. If you want to bulk allow
        everything, use "service.allow_all_functions()"

        Params:
          keys: keys of functions you want to block
        """
        self._function_keys -= keys
        self._send_lifecycle_message(
            lifecycle_type=LifecycleType.FUNCTIONS_ALLOWED,
            payload=tuple(keys),
        )
        return self

    def allow_all_functions(self) -> Self:
        """Allow every function established in the service, and send out an appropriate message.

        If you want to only allow certain functions, use "service.allow_keys()"
        """
        payload = tuple(self._function_keys)
        self._function_keys.clear()
        self._send_lifecycle_message(
            lifecycle_type=LifecycleType.FUNCTIONS_ALLOWED,
            payload=payload,
        )
        return self

    def block_all_functions(self) -> Self:
        """Block every function which _can_ be blocked in the service, and send out an appropriate message.

        Note that this does NOT disconnect from INTERSECT, and will not block functions which
        have no markings.
        """
        self._function_keys = set.union(
            *(getattr(m, SHUTDOWN_KEYS) for m in (f.method for f in self._function_map.values()))
        )
        self._send_lifecycle_message(
            lifecycle_type=LifecycleType.FUNCTIONS_BLOCKED,
            payload=tuple(self._function_keys),
        )
        return self

    def get_blocked_keys(self) -> set[str]:
        """Returns a set of the function keys which indicate the function should be blocked.

        Note that this returns a shallow copy, as the inner reference should NOT be mutated externally.
        """
        return self._function_keys.copy()

    def _handle_userspace_message_raw(self, raw: bytes) -> None:
        """Main broker callback function.

        Deserializes and validates a userspace message from a broker.

        This function is also responsible for publishing all response messages from the broker
        """
        try:
            message = deserialize_and_validate_userspace_message(raw)
            logger.debug(f'Received userspace message:\n{message}')
            response_msg = self._handle_userspace_message(message)
            if response_msg:
                logger.debug(
                    'Send %s message:\n%s',
                    'error' if response_msg['headers']['has_error'] else 'userspace',
                    response_msg,
                )
                response_channel = f"{message['headers']['source'].replace('.', '/')}/userspace"
                # Persistent userspace messages may be useful for orchestration.
                # Persistence will not hurt anything.
                self._control_plane_manager.publish_message(
                    response_channel, response_msg, persist=True
                )
        except ValidationError as e:
            logger.warning(
                f'Invalid message received on userspace message channel, ignoring. Full message:\n{e}'
            )

    def _handle_userspace_message(self, message: UserspaceMessage) -> UserspaceMessage | None:
        """Main logic for handling a userspace message, minus all broker logic.

        Params
          message: UserspaceMessage from a client
        Returns
          The response message we want to send to the client, or None if we don't want to send anything.
        """
        # ONE: HANDLE CORE COMPAT ISSUES
        # is this first branch necessary? May not be in the future
        if self._hierarchy.hierarchy_string('.') != message['headers']['destination']:
            return None
        if not resolve_user_version(message):
            return self._make_error_message(
                f'SDK version incompatibility. Service version: {version_string} . Sender version: {message["headers"]["sdk_version"]}',
                message,
            )

        # TWO: OPERATION EXISTS AND IS AVAILABLE
        operation = message['operationId']
        operation_meta = self._function_map.get(operation)
        if operation_meta is None:
            err_msg = f'Tried to call non-existent operation {operation}'
            logger.warning(err_msg)
            return self._make_error_message(err_msg, message)
        if self._function_keys & getattr(operation_meta.method, SHUTDOWN_KEYS):
            err_msg = f"Function '{operation}' is currently not available for use."
            logger.error(err_msg)
            return self._make_error_message(err_msg, message)

        # THREE: GET DATA FROM APPROPRIATE DATA STORE
        try:
            request_params = self._data_plane_manager.incoming_message_data_handler(message)
        except IntersectError:
            # could theoretically be either a service or client issue
            # XXX send a better error message?
            return self._make_error_message('Could not get data from data handler', message)

        try:
            # FOUR: CALL USER FUNCTION AND GET MESSAGE
            response = self._call_user_function(operation, operation_meta, request_params)
            # FIVE: SEND DATA TO APPROPRIATE DATA STORE
            response_data_handler = getattr(operation_meta.method, RESPONSE_DATA)
            response_content_type = getattr(operation_meta.method, RESPONSE_CONTENT)
            response_payload = self._data_plane_manager.outgoing_message_data_handler(
                response, response_content_type, response_data_handler
            )
        except ValidationError as e:
            # client issue with request parameters
            return self._make_error_message(f'Bad arguments to application:\n{e}', message)
        except IntersectApplicationError:
            # domain-level exception; do not send specifics about the exception because it may leak internals
            return self._make_error_message('Service domain logic threw exception.', message)
        except IntersectError:
            # XXX send a better error message? This is a service issue
            return self._make_error_message('Could not send data to data handler', message)
        finally:
            self._check_for_status_update()

        # SIX: SEND MESSAGE
        return create_userspace_message(
            source=message['headers']['destination'],
            destination=message['headers']['source'],
            content_type=response_content_type,
            data_handler=response_data_handler,
            operation_id=message['operationId'],
            payload=response_payload,
        )

    def _call_user_function(
        self,
        fn_name: str,
        fn_meta: FunctionMetadata,
        fn_params: bytes,
    ) -> bytes:
        """Entrypoint into capability. This should be a private function, only call it yourself for testing purposes.

        Basic validations defined from a user's type definitions will also occur here.

        Params
        fn_name = operation. These get represented in the schema as "channels".
        fn_meta = all information stored about the user's operation. This includes user-defined params and the request/response (de)serializers.
        fn_params = the request argument.
           If this value is empty or the bytes literal "null", and users have a request type, we will try to call the user's function with
           their default value as the parameter, or "None" if there isn't a default value.
           Values nested on a lower level should be handled automatically by Pydantic.
           A note on this value: at this point, we still want the parameters to be a JSON string (not a Python object),
           as if the object is first converted to Python and THEN validated, users will not have the option
           to choose strict validation.

        Returns:
            If the capability executed with no problems, a byte-string of the response will be returned.
            NOTE: You should make sure you are returning a type which matches your return annotation; if you don't, this causes later issues.

        Raises:
          IntersectApplicationException - this catches both invalid message arguments, as well as if the capability itself throws an Exception.
            It's meant to be for control-flow, it doesn't represent a fatal error.
          ValidationError - this is a Pydantic error which occurs if the input fails to validate against the user's model.
            Note that this error is never raised outside this function if the USER's code causes this exception (by doing internal pydantic validation themselves),
            but only as related to the actual request parameters.

        NOTE: running this function should normally not cause application failure. Users can terminate their application inside their capability class,
        but in almost all circumstances, this should be discouraged (outside of the constructor).
        """
        if fn_meta.request_adapter:
            try:
                if not fn_params or fn_params == b'null':
                    # strict=True here does nothing, because ConfigDict property validate_default may not be set and we validate defaults when generating the schema
                    default_value = fn_meta.request_adapter.get_default_value()
                    try:
                        request_obj = default_value.value  # type: ignore[union-attr]
                    except AttributeError:
                        request_obj = fn_meta.request_adapter.validate_python(
                            None,
                        )
                else:
                    request_obj = fn_meta.request_adapter.validate_json(
                        fn_params,
                        strict=getattr(fn_meta.method, STRICT_VALIDATION),
                    )
            except ValidationError as e:
                err_msg = f'Bad arguments to application:\n{e}\n'
                logger.warning(err_msg)
                raise
            try:
                response = getattr(self.capability, fn_name)(request_obj)
            except (
                Exception
            ) as e:  # (need to catch all possible exceptions to gracefully handle the thread)
                logger.warning(f'Capability raised exception:\n{e}\n')
                raise IntersectApplicationError from e
        else:
            try:
                response = getattr(self.capability, fn_name)()
            except (
                Exception
            ) as e:  # (need to catch all possible exceptions to gracefully handle the thread)
                logger.warning(f'Capability raised exception:\n{e}\n')
                raise IntersectApplicationError from e

        try:
            return fn_meta.response_adapter.dump_json(response, by_alias=True, warnings='error')
        except PydanticSerializationError as e:
            logger.error(
                f'IMPORTANT!!!! Your INTERSECT capability function did not return a value matching your response type. You MUST fix this for your message to be sent out! Full error:\n{e}\n'
            )
            raise IntersectApplicationError from e

    def _on_observe_event(self, event_name: str, event_value: Any, operation: str) -> None:
        """This is the service function which handles events from the capabilities (as opposed to handling messages).

        This function needs to:
          1) verify that "event_name" is correctly registered for the user "entrypoint" function
          2) verify that "event_name" can emit "event_value" for "operation"
          3) try to parse "event_value" into the type the user specified (there will be an event name to type annotation mapping)
          4) If the value correctly passes schema validation, fire the event

        Note that if validation fails, we simply log the error out and return. We do not broadcast an error message.
        """
        event_meta = self._event_map.get(event_name)
        if event_meta is None or operation not in event_meta.operations:
            logger.error(
                f"Event name '{event_name}' was not registered on operation '{operation}', so event will not be emitted.\nEvent value: {event_value}"
            )
            return
        try:
            response = event_meta.type_adapter.dump_json(
                event_value, by_alias=True, warnings='error'
            )
        except PydanticSerializationError as e:
            logger.error(
                f"Value emitted for event name '{event_name}' from operation '{operation}' does not match schema.\nEvent value: {event_value}\nPydantic error: {e}"
            )
            return
        try:
            response_payload = self._data_plane_manager.outgoing_message_data_handler(
                response, event_meta.content_type, event_meta.data_transfer_handler
            )
        except IntersectError:
            # error should already be logged from the outgoing_message_data_handler function
            return

        msg = create_event_message(
            source=self._hierarchy.hierarchy_string('.'),
            operation_id=operation,
            content_type=event_meta.content_type,
            data_handler=event_meta.data_transfer_handler,
            event_name=event_name,
            payload=response_payload,
        )
        # Event messages are meant to be short-lived and should not persist.
        self._control_plane_manager.publish_message(self._events_channel_name, msg, persist=False)

    def _make_error_message(
        self, error_string: str, original_message: UserspaceMessage
    ) -> UserspaceMessage:
        """Generate an error message.

        Params:
          error_string: The error string to send as the payload
          original_message: The original UserspaceMessage
        Returns:
          the UserspaceMessage we will send as a reply
        """
        return create_userspace_message(
            source=original_message['headers']['destination'],
            destination=original_message['headers']['source'],
            content_type=IntersectMimeType.STRING,
            data_handler=IntersectDataHandler.MESSAGE,
            operation_id=original_message['operationId'],
            payload=error_string,
            has_error=True,
        )

    def _send_lifecycle_message(self, lifecycle_type: LifecycleType, payload: Any = None) -> None:
        """Send out a lifecycle message."""
        msg = create_lifecycle_message(
            source=self._hierarchy.hierarchy_string('.'),
            destination=self._lifecycle_channel_name,
            lifecycle_type=lifecycle_type,
            payload=payload,
        )
        logger.debug(f'Send lifecycle message:\n{msg}')
        # Lifecycle messages are meant to be short-lived, only the latest message has any usage for systems uninterested in logging,
        # and queues will be regularly polled about these. Do not persist them.
        self._control_plane_manager.publish_message(
            self._lifecycle_channel_name, msg, persist=False
        )

    def _check_for_status_update(self) -> bool:
        """Call the user's status retrieval function to see if it equals the cached value. If it does not, send out a status update function.

        This will also always update the last cached value.

        Returns:
          True if there was a status update, False if there wasn't
        """
        next_status = self._status_retrieval_fn()
        if next_status != self._status_memo:
            self._status_memo = next_status
            self._send_lifecycle_message(
                lifecycle_type=LifecycleType.STATUS_UPDATE,
                payload={'schema': self._schema, 'status': next_status},
            )
            return True
        return False

    def _status_ticker(self) -> None:
        """Periodically sends lifecycle polling messages showing the Service's state. Runs in a separate thread."""
        # initial wait should guarantee that polling message does not beat initial startup message
        if self._status_thread:
            if self._status_ticker_interval < 60.0:
                self._status_thread.wait(60.0)
            else:
                self._status_thread.wait(self._status_ticker_interval)
            while not self._status_thread.stopped():
                if not self._check_for_status_update():
                    self._send_lifecycle_message(
                        lifecycle_type=LifecycleType.POLLING,
                        payload={'schema': self._schema, 'status': self._status_memo},
                    )
                self._status_thread.wait(self._status_ticker_interval)

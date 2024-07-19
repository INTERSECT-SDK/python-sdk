import json
import logging
import time
import wonderwords

from os import getenv
from uuid import UUID

from intersect_sdk import (
    INTERSECT_JSON_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    IntersectClientMessageParams,
    default_intersect_lifecycle_loop,
)
 
from capability_catalog.capability_helpers import dataclassFromDict

from capability_catalog.system.system_manager.types import (
    SystemManagerCapabilityResult,
    SystemManagerCapabilityStatus,
    SystemStatusChangeEnum, SystemStatusChange,
    SystemStatus, SubsystemStatus, ServiceStatus, ResourceStatus,
    EnableSystemCommand, DisableSystemCommand,
    EnableSubsystemCommand, DisableSubsystemCommand,
    EnableServiceCommand, DisableServiceCommand,
    EnableResourceCommand, DisableResourceCommand,
    GetSystemStatusReply,
    GetSubsystemStatusRequest, GetSubsystemStatusReply,
    GetServiceStatusRequest, GetServiceStatusReply,
    GetResourceStatusRequest, GetResourceStatusReply,
    RegisterServiceRequest, RegisterServiceReply
)

from capability_catalog.system.system_manager.system_management import (
    IntersectResourceState,
    IntersectServiceState,
    IntersectSystemState,
    SystemInformation, SubsystemInformation, ServiceInformation, ResourceInformation
)

logging.basicConfig(level=logging.INFO)

wordgen = wonderwords.RandomWord()

svc_org_name : str = getenv("INTERSECT_ORGANIZATION_NAME", "test-org")
svc_fac_name : str = getenv("INTERSECT_FACILITY_NAME", "test-facility")
svc_sys_name : str = getenv("INTERSECT_SYSTEM_NAME", "test-system")
svc_sub_name : str = getenv("INTERSECT_SUBSYSTEM_NAME", "infrastructure-management") 
svc_svc_name : str = getenv("INTERSECT_SERVICE_NAME", "system-manager")

msg_destination : str = f'{svc_org_name}.{svc_fac_name}.{svc_sys_name}.{svc_sub_name}.{svc_svc_name}'

class SampleOrchestrator:
    """This class contains the callback function.

    It uses a class because we want to modify our own state from the callback function.

    State is managed through a message stack. We initialize a request-reply-request-reply... chain with the Service,
    and the chain ends once we've popped all messages from our message stack.
    """
    def __init__(self) -> None:
        """Basic constructor for the orchestrator class, call before creating the IntersectClient.

        As the only thing exposed to the Client is the callback function, the orchestrator class may otherwise be
        created and managed as the SDK developer sees fit.

        The messages are initialized in the order they are sent for readability purposes.
        The message stack is a list of tuples, each with the message and the time to wait before sending it.
        """
        self._service_names = [ "svc." + x for x in wordgen.random_words(3) ]
        self._subsys_names = [ "subsys." + x for x in wordgen.random_words(3) ]
        self.message_stack = list()

    def client_callback(
        self, source: str, operation: str, _has_error: bool, payload: INTERSECT_JSON_VALUE
    ) -> IntersectClientCallback:
        """ Processes service responses for System Manager sample client
        """
        print('Source:', json.dumps(source))
        print('Operation:', json.dumps(operation))
        print('Payload:', json.dumps(payload))
        print()

        if operation == "SystemManager.get_system_status":
            response : GetSystemStatusReply = dataclassFromDict(GetSystemStatusReply, payload)
            print(response)
            # create services
            for i in range(3):
                self.message_stack.append(
                    (IntersectClientMessageParams(
                        destination=msg_destination,
                        operation='SystemManager.register_service',
                        payload=RegisterServiceRequest(service_name=self._service_names[i],
                                                       subsystem_name=self._subsys_names[i],
                                                       service_description=wordgen.word(),
                                                       service_capabilities=wordgen.random_words(2, include_categories=["verbs"]),
                                                       service_resources=list(),
                                                       service_labels=list(),
                                                       service_properties=list()),
                    ), float(i))
                )
                self.message_stack.append(
                    (IntersectClientMessageParams(
                        destination=msg_destination,
                        operation='SystemManager.get_subsystem_status',
                        payload=GetSubsystemStatusRequest(subsystem_id=UUID(int=0),
                                                          subsystem_name=self._subsys_names[i]),
                    ), float(i+1))
                )
            self.message_stack.reverse()
        elif operation == "register_service":
            response : RegisterServiceReply = dataclassFromDict(RegisterServiceReply, payload)
            print(response)
            # get service status
            self.message_stack.append(
                (IntersectClientMessageParams(
                    destination=msg_destination,
                    operation='SystemManager.get_service_status',
                    payload=GetServiceStatusRequest(service_name="",
                                                    service_id=response.service_uuid),
                ), 1.0)
            )

        print()
        if not self.message_stack:
            # break out of pub/sub loop
            raise Exception
        message, wait_time = self.message_stack.pop()
        time.sleep(wait_time)
        return IntersectClientCallback(messages_to_send=[message])
    

if __name__ == '__main__':
    from_config_file = {
        'data_stores': {
            'minio': [
                {
                    'username': 'AKIAIOSFODNN7EXAMPLE',
                    'password': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                    'port': 9000,
                },
            ],
        },
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
            },
        ],
    }
    # The counter will start after the initial message.
    # If the service is already active and counting, this may do nothing.
    initial_messages = [
        IntersectClientMessageParams(
            destination=msg_destination,
            operation='SystemManager.get_system_status',
            payload=None,
        )
    ]
    orchestrator = SampleOrchestrator()
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(messages_to_send=initial_messages),
        **from_config_file,
    )
    client = IntersectClient(
        config=config,
        user_callback=orchestrator.client_callback,
    )
    default_intersect_lifecycle_loop(client)

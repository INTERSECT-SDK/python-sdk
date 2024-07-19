import json
import logging
import random
import time
import wonderwords

from os import getenv
from typing import Dict, List

from intersect_sdk import (
    INTERSECT_JSON_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    IntersectClientMessageParams,
    default_intersect_lifecycle_loop
)
 
from capability_catalog.capability_helpers import dataclassFromDict
from capability_catalog.capability_types import IntersectUUID, INTERSECT_INVALID_UUID

from capability_catalog.system.systems_registrar.types import (
    SystemsRegistrarCapabilityResult,
    SystemsRegistrarCapabilityStatus,
    SystemRegistration, SubsystemRegistration,
    SystemResourceRegistration, SystemServiceRegistration,
    RegisterSystemRequest, RegisterSystemReply,
    RegisterSubsystemRequest, RegisterSubsystemReply,
    RegisterSystemResourceRequest, RegisterSystemResourceReply,
    RegisterSystemServiceRequest, RegisterSystemServiceReply,
    GetSystemUUIDRequest, GetSystemUUIDReply,
    GetSubsystemUUIDRequest, GetSubsystemUUIDReply,
    GetSystemResourceUUIDRequest, GetSystemResourceUUIDReply,
    GetSystemServiceUUIDRequest, GetSystemServiceUUIDReply
)

logging.basicConfig(level=logging.INFO)

wordgen = wonderwords.RandomWord()

svc_org_name : str = getenv("INTERSECT_ORGANIZATION_NAME", "test-org")
svc_fac_name : str = getenv("INTERSECT_FACILITY_NAME", "test-facility")
svc_sys_name : str = getenv("INTERSECT_SYSTEM_NAME", "intersect")
svc_sub_name : str = getenv("INTERSECT_SUBSYSTEM_NAME", "infrastructure-management") 
svc_svc_name : str = getenv("INTERSECT_SERVICE_NAME", "domain-registrar")
svc_cap_name : str = "SystemsRegistrar"

msg_destination : str = f'{svc_org_name}.{svc_fac_name}.{svc_sys_name}.{svc_sub_name}.{svc_svc_name}'

class SampleOrchestrator:
    """This class contains the callback function.

    It uses a class because we want to modify our own state from the callback function.

    State is managed through a message stack. We initialize a request-reply-request-reply... chain with the Service,
    and the chain ends once we've popped all messages from our message stack.
    """

    class SystemRegistrationInfo:
        full_name  : str
        secret     : bytes
        uuid       : IntersectUUID = None
        subsystems : Dict[str, IntersectUUID] = dict()
        resources  : Dict[str, IntersectUUID] = dict()
        services   : Dict[str, IntersectUUID] = dict()

        def __init__(self, name : str, secret : bytes) -> None:
            self.full_name = name
            self.secret = secret

    def __init__(self) -> None:
        """Basic constructor for the orchestrator class, call before creating the IntersectClient.

        As the only thing exposed to the Client is the callback function, the orchestrator class may otherwise be
        created and managed as the SDK developer sees fit.

        The messages are initialized in the order they are sent for readability purposes.
        The message stack is a list of tuples, each with the message and the time to wait before sending it.
        """
        self._org_names = [ f"org-{o}" for o in wordgen.random_words(amount=10, word_max_length=5) ]
        self._fac_names = [ f"fac-{f}" for f in wordgen.random_words(amount=10, word_max_length=5) ]
        self._sys_names = [ f"sys-{s}" for s in wordgen.random_words(amount=10, word_max_length=5) ]
        self._sub_names = [ f"sub-{b}" for b in wordgen.random_words(amount=10, word_max_length=5) ]
        self._svc_names = [ f"svc-{c}" for c in wordgen.random_words(amount=10, word_max_length=5) ]
        self._res_names = [ f"res-{r}" for r in wordgen.random_words(amount=10, word_max_length=5) ]

        self._system_registrations = list()
        self._subsystem_registrations = list()
        self._resource_registrations = list()
        self._service_registrations = list()

        self._sent_resource_registrations = False
        self._sent_subsys_registrations = False
        self._sent_service_registrations = False

        self._systems = dict()
        
        self.message_stack = list()

    def organizations(self) -> List[str]:
        return self._org_names
    
    def facilities(self) -> List[str]:
        return self._fac_names
    
    def systems(self) -> List[str]:
        return self._sys_names
    
    def subsystems(self) -> List[str]:
        return self._sub_names
    
    def resources(self) -> List[str]:
        return self._res_names
    
    def services(self) -> List[str]:
        return self._svc_names
    
    def add_system(self,
                   name : str,
                   full_name : str,
                   secret : bytes) -> None:
        sys_info = SampleOrchestrator.SystemRegistrationInfo(name=full_name,
                                                             secret=secret)
        self._systems[name] = sys_info

    def get_system(self,
                   name : str) -> SystemRegistrationInfo:
        return self._systems[name]

    def add_subsystem(self,
                      sys_name : str,
                      sub_name : str,
                      uuid : IntersectUUID = INTERSECT_INVALID_UUID) -> None:
        sys_info = self.get_system(sys_name)
        sys_info.subsystems[sub_name] = uuid
    
    def add_resource(self,
                     sys_name : str,
                     res_name : str,
                     uuid : IntersectUUID = INTERSECT_INVALID_UUID) -> None:
        sys_info = self.get_system(sys_name)
        sys_info.resources[res_name] = uuid

    def add_service(self,
                     sys_name : str,
                     svc_name : str,
                     uuid : IntersectUUID = INTERSECT_INVALID_UUID) -> None:
        sys_info = self.get_system(sys_name)
        sys_info.services[svc_name] = uuid

    def client_callback(
        self, source: str, operation: str, _has_error: bool, payload: INTERSECT_JSON_VALUE
    ) -> IntersectClientCallback:
        """ Processes service responses for Systems Registrar sample client
        """
        got_all_responses = False
        if operation != f"{svc_cap_name}.get_system_uuid": 
            print('Source:', json.dumps(source))
            print('Operation:', json.dumps(operation))
            print('Payload:', json.dumps(payload))
            print()
            if operation == f"{svc_cap_name}.register_system":
                response : RegisterSystemReply = dataclassFromDict(RegisterSystemReply, payload)
                print(response)
                # capture responses in order
                self._system_registrations.append(response)
            elif operation == f"{svc_cap_name}.register_subsystem":
                response : RegisterSubsystemReply = dataclassFromDict(RegisterSubsystemReply, payload)
                print(response)
                # capture responses in order
                self._subsystem_registrations.append(response)
            elif operation == f"{svc_cap_name}.register_system_resource":
                response : RegisterSystemResourceReply = dataclassFromDict(RegisterSystemResourceReply, payload)
                print(response)
                # capture responses in order
                self._resource_registrations.append(response)
            elif operation == f"{svc_cap_name}.register_system_service":
                response : RegisterSystemServiceReply = dataclassFromDict(RegisterSystemServiceReply, payload)
                print(response)
                # capture responses in order
                self._service_registrations.append(response)
            print()
        
        if len(self._service_registrations) == 10:
            # record service uuids
            i = 0
            for resp in self._service_registrations:
                sys_name = self._sys_names[i]
                sys_info = self.get_system(sys_name)
                sys_info.services[self._svc_names[i]] = resp.service_id
                i += 1
            self._service_registrations.clear()
            got_all_responses = True

        elif len(self._resource_registrations) == 10:
            # record resource uuids
            i = 0
            for resp in self._resource_registrations:
                sys_name = self._sys_names[i]
                sys_info = self.get_system(sys_name)
                sys_info.resources[self._res_names[i]] = resp.resource_id
                i += 1
            self._resource_registrations.clear()

            if not self._sent_subsys_registrations:
                # register subsystems
                i = 0
                for sub_name in self._sub_names:
                    sys_name = self._sys_names[i]
                    i += 1
                    sys_info = self.get_system(sys_name)
                    print(f"DEBUG: registering subsys {sub_name} in system {sys_name}")
                    self.message_stack.append(
                        (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation=f'{svc_cap_name}.register_subsystem',
                            payload=RegisterSubsystemRequest(subsystem_name=sub_name,
                                                            system_id=sys_info.uuid,
                                                            system_secret=sys_info.secret,
                                                            requested_id=INTERSECT_INVALID_UUID)
                        ), 1.0))
                self.message_stack.reverse()
                self._sent_subsys_registrations = True
        
        elif len(self._subsystem_registrations) == 10:
            # record subsystem uuids
            i = 0
            for resp in self._subsystem_registrations:
                sys_name = self._sys_names[i]
                sys_info = self.get_system(sys_name)
                sys_info.subsystems[self._sub_names[i]] = resp.subsystem_id
                i += 1
            self._subsystem_registrations.clear()
    
            if not self._sent_service_registrations:
                # register services
                i = 0
                for svc_name in self._svc_names:
                    sys_name = self._sys_names[i]
                    sub_name = self._sub_names[i]
                    i += 1
                    sys_info = self.get_system(sys_name)
                    sub_uuid = INTERSECT_INVALID_UUID
                    if sub_name in sys_info.subsystems:
                        sub_uuid = sys_info.subsystems[sub_name]
                    print(f"DEBUG: registering service {svc_name} in system {sys_name} subsys {sub_name}")
                    self.message_stack.append(
                        (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation=f'{svc_cap_name}.register_system_service',
                            payload=RegisterSystemServiceRequest(service_name=svc_name,
                                                                system_id=sys_info.uuid,
                                                                subsystem_id=sub_uuid,
                                                                system_secret=sys_info.secret,
                                                                requested_id=INTERSECT_INVALID_UUID)
                        ), 1.0))
                self.message_stack.reverse()
                self._sent_service_registrations = True

        elif len(self._system_registrations) == 10:
            # record system uuids
            i = 0
            for resp in self._system_registrations:
                sys_name = self._sys_names[i]
                i += 1
                sys_info = self.get_system(sys_name)
                sys_info.uuid = resp.system_id
            self._system_registrations.clear()
            
            if not self._sent_resource_registrations:
                # register resources
                i = 0
                for res_name in self._res_names:
                    sys_name = self._sys_names[i]
                    i += 1
                    sys_info = self.get_system(sys_name)
                    print(f"DEBUG: registering resource {res_name} in system {sys_name}")
                    self.message_stack.append(
                        (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation=f'{svc_cap_name}.register_system_resource',
                            payload=RegisterSystemResourceRequest(resource_name=res_name,
                                                                system_id=sys_info.uuid,
                                                                system_secret=sys_info.secret,
                                                                requested_id=INTERSECT_INVALID_UUID)
                        ), 1.0))
                self.message_stack.reverse()
                self._sent_resource_registrations = True
        
        if got_all_responses:
            # break out of pub/sub loop
            raise Exception
        
        if self.message_stack:
            message, wait_time = self.message_stack.pop()
            time.sleep(wait_time)
            
        else:
            message = IntersectClientMessageParams(
                        destination=msg_destination,
                        operation=f'{svc_cap_name}.get_system_uuid',
                        payload=GetSystemUUIDRequest(organization_name=self._org_names[0],
                                                     facility_name=self._fac_names[0],
                                                     system_name=self._sys_names[0]))
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
    
    
    initial_messages = list()
    orchestrator = SampleOrchestrator()
    i = 0
    for sys_name in orchestrator.systems():
        secret = ""
        if random.randint(1,99) >= 42:
            secret = str(random.randbytes(20))
        org_name = orchestrator.organizations()[i]
        fac_name = orchestrator.facilities()[i]
        i += 1
        full_name = f'{org_name}.{fac_name}.{sys_name}'
        orchestrator.add_system(sys_name, full_name, secret)
        initial_messages.append(
            IntersectClientMessageParams(
                destination=msg_destination,
                operation=f'{svc_cap_name}.register_system',
                payload=RegisterSystemRequest(organization_name=org_name,
                                              facility_name=fac_name,
                                              system_name=sys_name,
                                              system_secret=secret,
                                              requested_id=INTERSECT_INVALID_UUID)))

    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(messages_to_send=initial_messages),
        **from_config_file,
    )
    client = IntersectClient(
        config=config,
        user_callback=orchestrator.client_callback,
    )
    default_intersect_lifecycle_loop(client)

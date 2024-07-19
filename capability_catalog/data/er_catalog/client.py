import json
import logging
import random
import time
import wonderwords

from dataclasses import asdict, dataclass
from typing import Dict, List
from uuid import UUID, uuid3, uuid4

from intersect_sdk import (
    INTERSECT_JSON_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    IntersectClientMessageParams,
    default_intersect_lifecycle_loop,
)

from capability_catalog.capability_helpers import dataclassFromDict
from capability_catalog.capability_types import (
    IntersectUUID, INTERSECT_INVALID_UUID,
    IntersectEntity, IntersectEntityRelation
)

from capability_catalog.system.system_catalog.types import (
    SystemManagementEntityTypes,
    SystemManagementEntityRelationTypes
)

from capability_catalog.data.er_catalog.types import (
    ERCatalogCapabilityResult,
    ERCatalogCapabilityStatus,
    CreateEntityCommand, RemoveEntityCommand,
    CreateRelationCommand, RemoveRelationCommand,
    GetEntityInformationRequest, GetEntityInformationReply,
    GetEntityRelationshipsRequest, GetEntityRelationshipsReply,
    GetEntitySourceRelationshipsRequest, GetEntitySourceRelationshipsReply,
    GetEntityTargetRelationshipsRequest, GetEntityTargetRelationshipsReply,
    GetSourceEntitiesByRelationRequest, GetSourceEntitiesByRelationReply,
    GetTargetEntitiesByRelationRequest, GetTargetEntitiesByRelationReply,
    GetEntitiesByTypeRequest, GetEntitiesByTypeReply,
    GetEntitiesByLabelRequest, GetEntitiesByLabelReply,
    GetEntitiesByPropertyRequest, GetEntitiesByPropertyReply
)

logging.basicConfig(level=logging.INFO)

wordgen = wonderwords.RandomWord()

my_org_name : str = "my-organization"
my_fac_name : str = "my-facility"
my_sys_name : str = "intersect"
my_sub_name : str = "data-management"
my_svc_name : str = "er-catalog"

msg_destination : str = f'{my_org_name}.{my_fac_name}.{my_sys_name}.{my_sub_name}.{my_svc_name}'

class SampleOrchestrator:
    """This class contains the callback function.

    It uses a class because we want to modify our own state from the callback function.

    State is managed through a message stack. We initialize a request-reply-request-reply... chain with the Service,
    and the chain ends once we've popped all messages from our message stack.
    """

    class SystemRegistrationInfo:
        full_name  : str
        uuid       : IntersectUUID = None
        subsystems : Dict[str, IntersectUUID] = dict()
        resources  : Dict[str, IntersectUUID] = dict()
        services   : Dict[str, IntersectUUID] = dict()

        def __init__(self, name : str) -> None:
            self.full_name = name

    def __init__(self) -> None:
        """Basic constructor for the orchestrator class, call before creating the IntersectClient.

        As the only thing exposed to the Client is the callback function, the orchestrator class may otherwise be
        created and managed as the SDK developer sees fit.

        The messages are initialized in the order they are sent for readability purposes.
        The message stack is a list of tuples, each with the message and the time to wait before sending it.
        """
        self._org_names = [ f"org_{o}" for o in wordgen.random_words(amount=3, word_max_length=5) ]
        self._fac_names = [ f"fac_{f}" for f in wordgen.random_words(amount=3, word_max_length=5) ]
        self._sys_names = [ f"sys_{s}" for s in wordgen.random_words(amount=10, word_max_length=5) ]
        self._sub_names = [ f"sub_{b}" for b in wordgen.random_words(amount=10, word_max_length=5) ]
        self._svc_names = [ f"svc_{c}" for c in wordgen.random_words(amount=10, word_max_length=5) ]
        self._res_names = [ f"res_{r}" for r in wordgen.random_words(amount=10, word_max_length=5) ]

        self.namespace_uuid = uuid4()

        self._created_sub = False
        self._created_svc = False
        self._created_res = False

        self._entity_creations : int = 0
        self._relation_creations : int = 0
        self._entity_queries : int = 0
        self._relation_queries : int = 0

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
                   full_name : str) -> None:
        sys_info = SampleOrchestrator.SystemRegistrationInfo(name=full_name)
        sys_info.uuid = uuid3(self.namespace_uuid, full_name)
        self._systems[name] = sys_info

    def get_system(self,
                   name : str) -> SystemRegistrationInfo:
        return self._systems[name]

    def add_subsystem(self,
                      sys_name : str,
                      sub_name : str) -> None:
        sys_info = self.get_system(sys_name)
        sys_info.subsystems[sub_name] = uuid3(sys_info.uuid, sub_name)

    def get_subsystem_uuid(self,
                           sys_name : str,
                           sub_name : str) -> IntersectUUID:
        sys_info = self.get_system(sys_name)
        return sys_info.subsystems[sub_name]

    def add_resource(self,
                     sys_name : str,
                     res_name : str) -> None:
        sys_info = self.get_system(sys_name)
        sys_info.resources[res_name] = uuid3(sys_info.uuid, res_name)

    def get_resource_uuid(self,
                          sys_name : str,
                          res_name : str) -> IntersectUUID:
        sys_info = self.get_system(sys_name)
        return sys_info.resources[res_name]

    def add_service(self,
                    sys_name : str,
                    svc_name : str) -> None:
        sys_info = self.get_system(sys_name)
        sys_info.services[svc_name] = uuid3(sys_info.uuid, svc_name)

    def get_service_uuid(self,
                         sys_name : str,
                         svc_name : str) -> None:
        sys_info = self.get_system(sys_name)
        return sys_info.services[svc_name]

    def client_callback(
        self, source: str, operation: str, _has_error: bool, payload: INTERSECT_JSON_VALUE
    ) -> IntersectClientCallback:
        """ Processes service responses for ER Catalog sample client
        """
        got_all_responses = False
        if operation != "EntityRelationCatalog.get_entity_information":
            print('Source:', json.dumps(source))
            print('Operation:', json.dumps(operation))
            print('Payload:', json.dumps(payload))
            print()
            if operation == "EntityRelationCatalog.create_entity":
                response : ERCatalogCapabilityResult = dataclassFromDict(ERCatalogCapabilityResult, payload)
                print(response)
                self._entity_creations += 1
            elif operation == "EntityRelationCatalog.create_relation":
                response : ERCatalogCapabilityResult = dataclassFromDict(ERCatalogCapabilityResult, payload)
                print(response)
                self._relation_creations += 1
            elif operation == "EntityRelationCatalog.get_entity_relationships":
                response : GetEntityRelationshipsReply = dataclassFromDict(GetEntityRelationshipsReply, payload)
                print(response)
                self._entity_queries += 1
            elif operation == "EntityRelationCatalog.get_entities_by_type":
                response : GetEntitiesByTypeReply = dataclassFromDict(GetEntitiesByTypeReply, payload)
                print(response)
                self._entity_queries += 1
            elif operation == "EntityRelationCatalog.get_entities_by_label":
                response : GetEntitiesByLabelReply = dataclassFromDict(GetEntitiesByLabelReply, payload)
                print(response)
                self._entity_queries += 1
            elif operation == "EntityRelationCatalog.get_source_entities_by_relation":
                response : GetSourceEntitiesByRelationReply = dataclassFromDict(GetSourceEntitiesByRelationReply, payload)
                print(response)
                self._relation_queries += 1
            elif operation == "EntityRelationCatalog.get_target_entities_by_relation":
                response : GetTargetEntitiesByRelationReply = dataclassFromDict(GetTargetEntitiesByRelationReply, payload)
                print(response)
                self._relation_queries += 1
            print()

        if not self._created_sub and self._entity_creations == 10:
            # create subsystem entities and relationships to parent systems
            self._created_sub = True
            i = 0
            for sub_name in orchestrator.subsystems():
                sys_name = self._sys_names[i]
                sys_info = orchestrator.get_system(sys_name)
                i += 1
                orchestrator.add_subsystem(sys_name, sub_name)
                sub_uuid = self.get_subsystem_uuid(sys_name, sub_name)
                rand_label = wordgen.word(word_max_length=6)
                rand_prop1 = f'property1={wordgen.word()}'
                rand_prop2 = f'property2={wordgen.word()}'
                sub_entity = IntersectEntity(entity_description=f'The {sub_name} subsystem of {sys_name}',
                                             entity_name=sub_name,
                                             entity_type=SystemManagementEntityTypes.SUBSYSTEM,
                                             entity_uuid=sub_uuid,
                                             entity_labels=[rand_label],
                                             entity_properties=[rand_prop1, rand_prop2])
                sub_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.SYSTEM_SUBSYS,
                                                       source_id=sys_info.uuid, target_id=sub_uuid, relation_properties=list())
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.create_entity',
                            payload=CreateEntityCommand(entity=sub_entity),
                     ), 1.0))
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.create_relation',
                            payload=CreateRelationCommand(relation=sub_relation),
                     ), 1.0))

        if not self._created_res and self._entity_creations == 20:
            # create resource entities and relationships to parent systems
            i = 0
            self._created_res = True
            for res_name in orchestrator.resources():
                sys_name = self._sys_names[i]
                sys_info = orchestrator.get_system(sys_name)
                i += 1
                orchestrator.add_resource(sys_name, res_name)
                res_uuid = self.get_resource_uuid(sys_name, res_name)
                rand_label = wordgen.word(word_max_length=6)
                rand_prop1 = f'property1={wordgen.word()}'
                rand_prop2 = f'property2={wordgen.word()}'
                res_entity = IntersectEntity(entity_description=f'The {res_name} resource of {sys_name}',
                                             entity_name=res_name,
                                             entity_type=SystemManagementEntityTypes.RESOURCE,
                                             entity_uuid=res_uuid,
                                             entity_labels=[rand_label],
                                             entity_properties=[rand_prop1, rand_prop2])
                res_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.SYSTEM_RESOURCE,
                                                       source_id=sys_info.uuid, target_id=res_uuid, relation_properties=list())
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.create_entity',
                            payload=CreateEntityCommand(entity=res_entity),
                     ), 1.0))
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.create_relation',
                            payload=CreateRelationCommand(relation=res_relation),
                     ), 1.0))


        if not self._created_svc and self._entity_creations == 30:
            # create service entities and relationships to parent systems
            i = 0
            self._created_svc = True
            for svc_name in orchestrator.services():
                sys_name = self._sys_names[i]
                res_name = orchestrator.resources()[i]
                sys_info = orchestrator.get_system(sys_name)
                i += 1
                orchestrator.add_service(sys_name, svc_name)
                svc_uuid = self.get_service_uuid(sys_name, svc_name)
                res_uuid = self.get_resource_uuid(sys_name, res_name)
                rand_label = wordgen.word(word_max_length=6)
                rand_prop1 = f'property1={wordgen.word()}'
                rand_prop2 = f'property2={wordgen.word()}'
                svc_entity = IntersectEntity(entity_description=f'The {svc_name} service of {sys_name}',
                                             entity_name=svc_name,
                                             entity_type=SystemManagementEntityTypes.SERVICE,
                                             entity_uuid=svc_uuid,
                                             entity_labels=[rand_label],
                                             entity_properties=[rand_prop1, rand_prop2])
                svc_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.SYSTEM_SERVICE,
                                                       source_id=sys_info.uuid, target_id=svc_uuid, relation_properties=list())
                res_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.SERVICE_RESOURCE,
                                                       source_id=svc_uuid, target_id=res_uuid, relation_properties=list())
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.create_entity',
                            payload=CreateEntityCommand(entity=svc_entity),
                     ), 1.0))
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.create_relation',
                            payload=CreateRelationCommand(relation=svc_relation),
                     ), 1.0))
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.create_relation',
                            payload=CreateRelationCommand(relation=res_relation),
                     ), 1.0))


        if self._relation_creations == 30:
            for sys_name in orchestrator.systems():
                sys_info = orchestrator.get_system(sys_name)
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.get_entity_relationships',
                            payload=GetEntityRelationshipsRequest(entity_id=sys_info.uuid, relation_name=""),
                     ), 1.0))
            self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.get_entities_by_type',
                            payload=GetEntitiesByTypeRequest(type=SystemManagementEntityTypes.FACILITY),
                     ), 1.0))
            self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.get_entities_by_label',
                            payload=GetEntitiesByLabelRequest(label=orchestrator.organizations()[2]),
                     ), 1.0))
            self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.get_source_entities_by_relation',
                            payload=GetSourceEntitiesByRelationRequest(relation_name=SystemManagementEntityRelationTypes.SYSTEM_SERVICE),
                     ), 1.0))
            self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='EntityRelationCatalog.get_target_entities_by_relation',
                            payload=GetTargetEntitiesByRelationRequest(relation_name=SystemManagementEntityRelationTypes.SYSTEM_SERVICE),
                     ), 1.0))


        if self._entity_queries == 12 and self._relation_queries == 2:
            got_all_responses = True

        if got_all_responses:
            # break out of pub/sub loop
            raise Exception

        if self.message_stack:
            message, wait_time = self.message_stack.pop(0)
            time.sleep(wait_time)
        else:
            # try to do a bad entity lookup
            message = IntersectClientMessageParams(
                        destination=msg_destination,
                        operation='EntityRelationCatalog.get_entity_information',
                        payload=GetEntityInformationRequest(entity_id=INTERSECT_INVALID_UUID))
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
    for org_name in orchestrator.organizations():
        fac_name = orchestrator.facilities()[i]
        i += 1
        org_uuid = uuid3(orchestrator.namespace_uuid, org_name)
        fac_uuid = uuid3(org_uuid, fac_name)
        org_entity = IntersectEntity(entity_description=f'The {org_name} organization',
                                     entity_name=org_name,
                                     entity_type=SystemManagementEntityTypes.ORGANIZATION,
                                     entity_uuid=org_uuid,
                                     entity_labels=list(),
                                     entity_properties=list())
        fac_entity = IntersectEntity(entity_description=f'The {fac_name} facility at {org_name}',
                                     entity_name=fac_name,
                                     entity_type=SystemManagementEntityTypes.FACILITY,
                                     entity_uuid=fac_uuid,
                                     entity_labels=[org_name],
                                     entity_properties=list())
        fac_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.ORG_FACILITY,
                                               source_id=org_uuid, target_id=fac_uuid, relation_properties=list())
                
        initial_messages.append(
            IntersectClientMessageParams(
                destination=msg_destination,
                operation='EntityRelationCatalog.create_entity',
                payload=CreateEntityCommand(entity=org_entity)))
        initial_messages.append(
            IntersectClientMessageParams(
                destination=msg_destination,
                operation='EntityRelationCatalog.create_entity',
                payload=CreateEntityCommand(entity=fac_entity)))
        initial_messages.append(
            IntersectClientMessageParams(
                    destination=msg_destination,
                    operation='EntityRelationCatalog.create_relation',
                    payload=CreateRelationCommand(relation=fac_relation)))
    
    for sys_name in orchestrator.systems():
        org_name = orchestrator.organizations()[i%3]
        fac_name = orchestrator.facilities()[i%3]
        org_uuid = uuid3(orchestrator.namespace_uuid, org_name)
        fac_uuid = uuid3(org_uuid, fac_name)
        i += 1
        full_name = f'{org_name}.{fac_name}.{sys_name}'
        orchestrator.add_system(sys_name, full_name)
        sys_info = orchestrator.get_system(sys_name)
        rand_label = wordgen.word(word_max_length=6)
        rand_prop1 = f'property1={wordgen.word()}'
        rand_prop2 = f'property2={wordgen.word()}'
        sys_entity = IntersectEntity(entity_description=f'The {full_name} system',
                                     entity_name=sys_name,
                                     entity_type=SystemManagementEntityTypes.SYSTEM,
                                     entity_uuid=sys_info.uuid,
                                     entity_labels=[org_name, fac_name, rand_label],
                                     entity_properties=[rand_prop1, rand_prop2])
        sys_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.FACILITY_SYSTEM,
                                               source_id=fac_uuid, target_id=sys_info.uuid, relation_properties=list())
        
        initial_messages.append(
            IntersectClientMessageParams(
                destination=msg_destination,
                operation='EntityRelationCatalog.create_entity',
                payload=CreateEntityCommand(entity=sys_entity)))
        initial_messages.append(
            IntersectClientMessageParams(
                    destination=msg_destination,
                    operation='EntityRelationCatalog.create_relation',
                    payload=CreateRelationCommand(relation=sys_relation)))

    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(messages_to_send=initial_messages),
        **from_config_file,
    )
    client = IntersectClient(
        config=config,
        user_callback=orchestrator.client_callback,
    )
    default_intersect_lifecycle_loop(client)

import json
import logging
import time
import wonderwords

from dataclasses import asdict

from lorem_text import lorem

from intersect_sdk import (
    INTERSECT_JSON_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    IntersectClientMessageParams,
    default_intersect_lifecycle_loop,
)

from capability_catalog.capability_helpers import dataclassFromDict
from capability_catalog.data.data_storage.types import (
    DataStorageCapabilityResult,
    DataStorageCapabilityStatus,
    DataCollectionDetails, DataItemDetails, DataNamespaceDetails,
    CreateDataCollectionCommand,
    CreateDataItemFromLocalFileCommand,
    CreateDataItemFromBytesCommand,
    CreateDataNamespaceCommand,
    RemoveDataCollectionCommand,
    RemoveDataItemCommand,
    RemoveDataNamespaceCommand,
    UpdateDataItemCommand,
    GetDataCollectionDetailsRequest, GetDataCollectionDetailsReply,
    GetDataItemAsBytesRequest, GetDataItemAsBytesReply,
    GetDataItemAsLocalFileRequest, GetDataItemAsLocalFileReply,
    GetDataItemDetailsRequest, GetDataItemDetailsReply,
    GetDataNamespaceDetailsRequest, GetDataNamespaceDetailsReply,
    ListDataCollectionsRequest, ListDataCollectionsReply,
    ListDataItemsRequest, ListDataItemsReply,
    ListDataNamespacesReply
)

logging.basicConfig(level=logging.INFO)

wordgen = wonderwords.RandomWord()

my_org_name : str = "my-organization"
my_fac_name : str = "my-facility"
my_sys_name : str = "my-test-system"
my_sub_name : str = "data-management"
my_svc_name : str = "data-manager"
mv_svc_desc : str = "Manages the system's data storage, transfer, and publishing capabilities."

msg_destination : str = f'{my_org_name}.{my_fac_name}.{my_sys_name}.{my_sub_name}.{my_svc_name}'


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
        self._namespace = "namespace-" + wordgen.word(word_max_length=10)
        self._collection = "collection-" + wordgen.word(word_max_length=10)
        self.message_stack = list()

    def client_callback(
        self, source: str, operation: str, _has_error: bool, payload: INTERSECT_JSON_VALUE
    ) -> IntersectClientCallback:
        """ Processes service responses for Data Storage sample client
        """
        print('Source:', json.dumps(source))
        print('Operation:', json.dumps(operation))
        print('Payload:', json.dumps(payload))
        print()

        if operation == "create_data_namespace":
            response : DataStorageCapabilityResult = dataclassFromDict(DataStorageCapabilityResult, payload)
            print(response)
            # create an item in the namespace
            self.message_stack.append(
                (IntersectClientMessageParams(
                    destination=msg_destination,
                    operation='DataStorage.create_data_item_from_bytes',
                    payload=CreateDataItemFromBytesCommand(item_name=wordgen.word(word_max_length=10),
                                                           item_namespace=self._namespace,
                                                           item_collection="",
                                                           item_contents=bytes(lorem.paragraphs(3),'utf-8'),
                                                           item_properties=list()),
                 ), 1.0))
        elif operation == "create_data_collection":
            response : DataStorageCapabilityResult = dataclassFromDict(DataStorageCapabilityResult, payload)
            print(response)
            # create an item in the collection
            self.message_stack.append(
                (IntersectClientMessageParams(
                    destination=msg_destination,
                    operation='DataStorage.create_data_item_from_bytes',
                    payload=CreateDataItemFromBytesCommand(item_name=wordgen.word(word_max_length=10),
                                                           item_namespace=self._namespace,
                                                           item_collection=self._collection,
                                                           item_contents=bytes(lorem.paragraphs(2),'utf-8'),
                                                           item_properties=list()),
                 ), 1.0))
        elif operation == "create_data_item_from_bytes":
            response : DataStorageCapabilityResult = dataclassFromDict(DataStorageCapabilityResult, payload)
            print(response)
            # query namespace items
            self.message_stack.append(
                (IntersectClientMessageParams(
                    destination=msg_destination,
                    operation='DataStorage.list_data_items',
                    payload=ListDataItemsRequest(ns_name=self._namespace, coll_name=""),
                 ), 1.0))
        elif operation == "list_data_items":
            response : ListDataItemsReply = dataclassFromDict(ListDataItemsReply, payload)
            print(response)
            if len(response.item_names):
                for item in response.item_names:
                    # query item details then read data item
                    self.message_stack.append(
                        (IntersectClientMessageParams(
                                destination=msg_destination,
                                operation='DataStorage.get_data_item_details',
                                payload=GetDataItemDetailsRequest(item_name=item,
                                                                  item_namespace=response.ns_name,
                                                                  item_collection=response.coll_name),
                         ), 1.0))
                    self.message_stack.append(
                        (IntersectClientMessageParams(
                                destination=msg_destination,
                                operation='DataStorage.get_data_item_as_bytes',
                                payload=GetDataItemDetailsRequest(item_name=item,
                                                                  item_namespace=response.ns_name,
                                                                  item_collection=response.coll_name),
                         ), 3.0))
                    self.message_stack.reverse()           
        elif operation == "list_data_namespaces":
            response : ListDataNamespacesReply = dataclassFromDict(ListDataNamespacesReply, payload)
            print(response)
            if len(response.ns_names):
                for ns in response.ns_names:
                    # query namespace details
                    self.message_stack.append(
                        (IntersectClientMessageParams(
                                destination=msg_destination,
                                operation='DataStorage.get_data_namespace_details',
                                payload=GetDataNamespaceDetailsRequest(ns_name=ns),
                         ), 1.0))
                    self.message_stack.append(
                        (IntersectClientMessageParams(
                                destination=msg_destination,
                                operation='DataStorage.list_data_collections',
                                payload=ListDataCollectionsRequest(ns_name=self._namespace),
                        ), 3.0))
                    self.message_stack.reverse()
            else:
                # create namespace
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='DataStorage.create_data_namespace',
                            payload=CreateDataNamespaceCommand(ns_name=self._namespace),
                     ), 1.0))
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='DataStorage.list_data_namespaces',
                            payload=None,
                     ), 3.0))
                self.message_stack.reverse()
        elif operation == "list_data_collections":
            response : ListDataCollectionsReply = dataclassFromDict(ListDataCollectionsReply, payload)
            print(response)
            if len(response.coll_names):
                for coll in response.coll_names:
                    # query collection details
                    self.message_stack.append(
                        (IntersectClientMessageParams(
                                destination=msg_destination,
                                operation='DataStorage.get_data_collection_details',
                                payload=GetDataCollectionDetailsRequest(coll_name=coll, coll_namespace=self._namespace),
                         ), 1.0))
                    self.message_stack.append(
                        (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='DataStorage.list_data_items',
                            payload=ListDataItemsRequest(ns_name=self._namespace, coll_name=coll),
                         ), 2.0))
                    self.message_stack.reverse()
            else:
                # create collection
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='DataStorage.create_data_collection',
                            payload=CreateDataCollectionCommand(coll_name=self._collection,
                                                                coll_namespace=self._namespace,
                                                                coll_properties=list()),
                     ), 1.0))
                self.message_stack.append(
                    (IntersectClientMessageParams(
                            destination=msg_destination,
                            operation='DataStorage.list_data_collections',
                            payload=ListDataCollectionsRequest(ns_name=self._namespace),
                     ), 2.0))
                self.message_stack.reverse()

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
            operation='DataStorage.list_data_namespaces',
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

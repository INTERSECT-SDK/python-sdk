from dataclasses import dataclass
from enum import StrEnum
from typing import List

from capability_catalog.capability_types import IntersectFilepath, IntersectTimeStamp

@dataclass
class DataStorageCapabilityStatus:
    status : str

@dataclass
class DataStorageCapabilityResult:
    success : bool

@dataclass
class DataNamespaceDetails:
    ns_name        : str
    ns_create_time : IntersectTimeStamp
    ns_coll_count  : int = 0
    ns_item_count  : int = 0
    ns_data_size   : int = 0
    
    
@dataclass
class DataCollectionDetails:
    coll_name        : str
    coll_namespace   : str
    coll_create_time : IntersectTimeStamp
    #coll_properties  : List[IntersectKeyVal] = None
    coll_properties  : List[str]
    coll_item_count  : int = 0
    coll_data_size   : int = 0

@dataclass
class DataItemDetails:
    item_name        : str
    item_namespace   : str
    item_create_time : IntersectTimeStamp
    item_update_time : IntersectTimeStamp
    item_collection  : str
    #item_properties  : List[IntersectKeyVal] = None
    item_properties  : List[str]
    item_data_size   : int = 0

# Interaction Parameters & Results

@dataclass
class CreateDataNamespaceCommand:
    ns_name : str

@dataclass
class RemoveDataNamespaceCommand:
    ns_name : str

@dataclass
class CreateDataCollectionCommand:
    coll_name        : str
    coll_namespace   : str
    #coll_properties  : List[IntersectKeyVal] = None
    coll_properties  : List[str]

@dataclass
class RemoveDataCollectionCommand:
    coll_name        : str
    coll_namespace   : str

@dataclass
class CreateDataItemFromBytesCommand:
    item_name       : str
    item_namespace  : str
    item_contents   : bytes
    item_collection : str
    #item_properties : List[IntersectKeyVal] = None
    item_properties : List[str]

@dataclass
class CreateDataItemFromLocalFileCommand:
    item_name       : str
    item_namespace  : str
    local_file_path : IntersectFilepath
    item_collection : str
    #item_properties : List[IntersectKeyVal] = None
    item_properties : List[str]
    
@dataclass
class RemoveDataItemCommand:
    item_name       : str
    item_namespace  : str
    item_collection : str

@dataclass
class UpdateDataItemCommand:
    item_name       : str
    item_namespace  : str
    item_collection : str
    item_properties : List[str]
    #item_properties : List[IntersectKeyVal] = None

@dataclass
class GetDataNamespaceDetailsRequest:
    ns_name : str

@dataclass
class GetDataNamespaceDetailsReply:
    ns_details : DataNamespaceDetails
    error      : str

@dataclass
class GetDataCollectionDetailsRequest:
    coll_name      : str
    coll_namespace : str

@dataclass
class GetDataCollectionDetailsReply:
    coll_details : DataCollectionDetails
    error        : str

@dataclass
class GetDataItemDetailsRequest:
    item_name       : str
    item_namespace  : str
    item_collection : str

@dataclass
class GetDataItemDetailsReply:
    item_details : DataItemDetails
    error        : str

@dataclass
class GetDataItemAsBytesRequest:
    item_name       : str
    item_namespace  : str
    item_collection : str

@dataclass
class GetDataItemAsBytesReply:
    item_contents : bytes
    error         : str

@dataclass
class GetDataItemAsLocalFileRequest:
    item_name       : str
    item_namespace  : str
    item_collection : str

@dataclass
class GetDataItemAsLocalFileReply:
    local_file_path : IntersectFilepath
    is_temp_file    : bool
    error           : str


@dataclass
class ListDataNamespacesReply:
    ns_names : List[str]

@dataclass
class ListDataCollectionsRequest:
    ns_name : str

@dataclass
class ListDataCollectionsReply:
    coll_names : List[str]
    error      : str

@dataclass
class ListDataItemsRequest:
    ns_name   : str
    coll_name : str

@dataclass
class ListDataItemsReply:
    ns_name    : str
    coll_name  : str
    item_names : List[str]
    error      : str

# Asynchronous Events

@dataclass
class DataNamespaceCreation:
    ns_details : DataNamespaceDetails

@dataclass
class DataNamespaceRemoval:
    ns_details : DataNamespaceDetails

@dataclass
class DataCollectionCreation:
    coll_details : DataCollectionDetails

@dataclass
class DataCollectionRemoval:
    coll_details : DataCollectionDetails

@dataclass
class DataItemCreation:
    item_details : DataItemDetails

@dataclass
class DataItemRemoval:
    item_details : DataItemDetails

@dataclass
class DataItemUpdate:
    item_details : DataItemDetails
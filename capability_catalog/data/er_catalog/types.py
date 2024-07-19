from dataclasses import dataclass
from enum import StrEnum
from typing import List

from capability_catalog.capability_types import (
    IntersectUUID,
    IntersectEntity,
    IntersectEntityRelation
)

@dataclass
class ERCatalogCapabilityStatus:
    status : str

@dataclass
class ERCatalogCapabilityResult:
    success : bool

# Interaction Parameters & Results

@dataclass
class CreateEntityCommand:
    entity : IntersectEntity

@dataclass
class RemoveEntityCommand:
    entity_id : IntersectUUID

@dataclass
class CreateRelationCommand:
    relation : IntersectEntityRelation

@dataclass
class RemoveRelationCommand:
    relation_name : str
    source_id     : IntersectUUID
    target_id     : IntersectUUID

@dataclass
class GetEntityInformationRequest:
    entity_id : IntersectUUID

@dataclass
class GetEntityInformationReply:
    entity_info : IntersectEntity
    error       : str

@dataclass
class GetEntityRelationshipsRequest:
    entity_id     : IntersectUUID
    relation_name : str # optional name of specific relations to query

@dataclass
class GetEntityRelationshipsReply:
    relationships : List[IntersectEntityRelation]
    error         : str

@dataclass
class GetEntitySourceRelationshipsRequest:
    entity_id     : IntersectUUID
    relation_name : str # optional name of specific relations to query

@dataclass
class GetEntitySourceRelationshipsReply:
    relationships : List[IntersectEntityRelation]
    error         : str

@dataclass
class GetEntityTargetRelationshipsRequest:
    entity_id     : IntersectUUID
    relation_name : str # optional name of specific relations to query

@dataclass
class GetEntityTargetRelationshipsReply:
    relationships : List[IntersectEntityRelation]
    error         : str

@dataclass
class GetSourceEntitiesByRelationRequest:
    relation_name : str

@dataclass
class GetSourceEntitiesByRelationReply:
    sources : List[IntersectUUID]
    error   : str

@dataclass
class GetTargetEntitiesByRelationRequest:
    relation_name : str

@dataclass
class GetTargetEntitiesByRelationReply:
    targets : List[IntersectUUID]
    error   : str

@dataclass
class GetEntitiesByTypeRequest:
    type : str

@dataclass
class GetEntitiesByTypeReply:
    entities : List[IntersectUUID]
    error    : str

@dataclass
class GetEntitiesByLabelRequest:
    label : str

@dataclass
class GetEntitiesByLabelReply:
    entities : List[IntersectUUID]
    error    : str

@dataclass
class GetEntitiesByPropertyRequest:
    property         : str
    value_expression : str # optional expression to match against property value

@dataclass
class GetEntitiesByPropertyReply:
    entities : List[IntersectUUID]
    error    : str

# Asynchronous Events

@dataclass
class ERCatalogEntityCreation:
    entity_id   : IntersectUUID
    entity_name : str
    entity_type : str

@dataclass
class ERCatalogEntityRemoval:
    entity_id   : IntersectUUID
    entity_name : str
    entity_type : str

@dataclass
class ERCatalogRelationCreation:
    relation_name : str
    source_id     : IntersectUUID
    target_id     : IntersectUUID

@dataclass
class ERCatalogRelationRemoval:
    relation_name : str
    source_id     : IntersectUUID
    target_id     : IntersectUUID
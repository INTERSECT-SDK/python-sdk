from dataclasses import dataclass
from enum import StrEnum
from typing import List
from uuid import UUID, SafeUUID

from capability_catalog.capability_types import (
    IntersectEntity,
    IntersectUUID
)

capability_namespace_uuid : UUID = "cccccccc-cccc-cccc-cccc-cccccccccccc"

class SystemManagementEntityTypes(StrEnum):
    CAPABILITY   = "ENTITY_SERVICE_CAPABILITY"
    FACILITY     = "ENTITY_FACILITY"
    ORGANIZATION = "ENTITY_ORGANIZATION"
    RESOURCE     = "ENTITY_RESOURCE"
    SERVICE      = "ENTITY_SERVICE"
    SUBSYSTEM    = "ENTITY_SUBSYSTEM"
    SYSTEM       = "ENTITY_SYSTEM"

class SystemManagementEntityRelationTypes(StrEnum):
    FACILITY_SYSTEM    = "FACILITY_HAS_SYSTEM"
    ORG_FACILITY       = "ORGANIZATION_HAS_FACILITY"
    ORG_SYSTEM         = "ORGANIZATION_HAS_SYSTEM"
    SERVICE_CAPABILITY = "SERVICE_PROVIDES_CAPABILITY"
    SERVICE_RESOURCE   = "SERVICE_USES_RESOURCE"
    SUBSYS_RESOURCE    = "SUBSYSTEM_HAS_RESOURCE"
    SUBSYS_SERVICE     = "SUBSYSTEM_HAS_SERVICE"
    SYSTEM_RESOURCE    = "SYSTEM_HAS_RESOURCE"
    SYSTEM_SERVICE     = "SYSTEM_HAS_SERVICE"
    SYSTEM_SUBSYS      = "SYSTEM_HAS_SUBSYSTEM"

@dataclass
class SystemInformationCatalogCapabilityStatus:
    status : str

@dataclass
class SystemInformationCatalogCapabilityResult:
    success : bool

# Interaction Parameters & Results

@dataclass
class CreateSystemResourceCommand:
    resource_description : str
    resource_id          : IntersectUUID
    resource_name        : str
    resource_labels      : List[str]
    resource_properties  : List[str]

@dataclass
class CreateSystemServiceCommand:
    service_description  : str
    service_id           : IntersectUUID
    subsystem_id         : IntersectUUID
    service_name         : str
    service_capabilities : List[str]
    service_labels       : List[str]
    service_properties   : List[str]
    service_resources    : List[IntersectUUID]

@dataclass
class CreateSubsystemCommand:
    subsystem_description  : str
    subsystem_id           : IntersectUUID
    subsystem_name         : str
    subsystem_labels       : List[str]
    subsystem_properties   : List[str]
    subsystem_resources    : List[IntersectUUID]

@dataclass
class GetSubsystemIdsReply:
    subsystem_ids : List[IntersectUUID]
    error         : str

@dataclass
class GetSubsystemNamesReply:
    subsystem_names : List[str]
    error           : str

@dataclass
class GetSubsystemInformationRequest:
    subsystem_id   : IntersectUUID
    subsystem_name : str

@dataclass
class GetSubsystemInformationReply:
    subsystem_info : IntersectEntity
    error          : str

@dataclass
class GetSystemServiceIdsRequest:
    subsystem_name : str

@dataclass
class GetSystemServiceIdsReply:
    service_ids : List[IntersectUUID]
    error       : str

@dataclass
class GetSystemServiceNamesRequest:
    subsystem_name : str

@dataclass
class GetSystemServiceNamesReply:
    service_names : List[str]
    error         : str

@dataclass
class GetSystemServicesByCapabilityRequest:
    capability_name : str
    subsystem_name  : str

@dataclass
class GetSystemServicesByCapabilityReply:
    service_ids : List[IntersectUUID]
    error       : str

@dataclass
class GetSystemServicesByResourceRequest:
    resource_name  : str
    subsystem_name : str

@dataclass
class GetSystemServicesByResourceReply:
    service_ids : List[IntersectUUID]
    error       : str

@dataclass
class GetSystemServiceInformationRequest:
    service_id   : IntersectUUID
    service_name : str

@dataclass
class GetSystemServiceInformationReply:
    service_info : IntersectEntity
    error        : str

@dataclass
class GetSystemResourceIdsRequest:
    subsystem_name : str

@dataclass
class GetSystemResourceIdsReply:
    resource_ids : List[IntersectUUID]
    error        : str

@dataclass
class GetSystemResourceNamesRequest:
    subsystem_name : str

@dataclass
class GetSystemResourceNamesReply:
    resource_names : List[str]
    error          : str

@dataclass
class GetSystemResourceInformationRequest:
    resource_id   : IntersectUUID
    resource_name : str

@dataclass
class GetSystemResourceInformationReply:
    resource_info : IntersectEntity
    error         : str

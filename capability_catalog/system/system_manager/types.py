from dataclasses import dataclass
from enum import StrEnum
from typing import List

from capability_catalog.capability_types import IntersectTimeStamp, IntersectUUID

@dataclass
class SystemManagerCapabilityStatus:
    status : str

@dataclass
class SystemManagerCapabilityResult:
    success : bool

class SystemStatusChangeEnum(StrEnum):
    RESOURCE_ENABLED   = "RESOURCE_ENABLED"
    RESOURCE_DISABLED  = "RESOURCE_DISABLED"
    SERVICE_ENABLED    = "SERVICE_ENABLED"
    SERVICE_DISABLED   = "SERVICE_DISABLED"
    SUBSYSTEM_ENABLED  = "SUBSYSTEM_ENABLED"
    SUBSYSTEM_DISABLED = "SUBSYSTEM_DISABLED"
    SYSTEM_ENABLED     = "SYSTEM_ENABLED"
    SYSTEM_DISABLED    = "SYSTEM_DISABLED"
    UNKNOWN            = "UNKNOWN_SYSTEM_STATUS_CHANGE"

@dataclass
class SystemStatus:
    system_id          : IntersectUUID
    status             : str
    status_description : str
    last_change_time   : IntersectTimeStamp

@dataclass
class SubsystemStatus:
    system_id          : IntersectUUID
    subsystem_id       : IntersectUUID
    status             : str
    status_description : str
    last_change_time   : IntersectTimeStamp

@dataclass
class ServiceStatus:
    system_id          : IntersectUUID
    service_id         : IntersectUUID
    status             : str
    status_description : str
    last_change_time   : IntersectTimeStamp

@dataclass
class ResourceStatus:
    system_id          : IntersectUUID
    resource_id        : IntersectUUID
    status             : str
    status_description : str
    last_change_time   : IntersectTimeStamp


# Interaction Parameters & Results

@dataclass
class EnableResourceCommand:
    resource_id        : IntersectUUID
    resource_name      : str
    change_description : str

@dataclass
class DisableResourceCommand:
    resource_id        : IntersectUUID
    resource_name      : str
    change_description : str

@dataclass
class EnableServiceCommand:
    service_id         : IntersectUUID
    service_name       : str
    change_description : str

@dataclass
class DisableServiceCommand:
    service_id         : IntersectUUID
    service_name       : str
    change_description : str

@dataclass
class EnableSystemCommand:
    system_id          : IntersectUUID
    system_name        : str
    change_description : str

@dataclass
class DisableSystemCommand:
    system_id          : IntersectUUID
    system_name        : str
    change_description : str

@dataclass
class EnableSubsystemCommand:
    subsystem_id       : IntersectUUID
    subsystem_name     : str
    change_description : str

@dataclass
class DisableSubsystemCommand:
    subsystem_id       : IntersectUUID
    subsystem_name     : str
    change_description : str

@dataclass
class GetSystemStatusReply:
    status : SystemStatus
    error  : str

@dataclass
class GetResourceStatusRequest:
    resource_id   : IntersectUUID
    resource_name : str

@dataclass
class GetResourceStatusReply:
    status : ResourceStatus
    error  : str

@dataclass
class GetServiceStatusRequest:
    service_id   : IntersectUUID
    service_name : str

@dataclass
class GetServiceStatusReply:
    status : ServiceStatus
    error  : str

@dataclass
class GetSubsystemStatusRequest:
    subsystem_id   : IntersectUUID
    subsystem_name : str

@dataclass
class GetSubsystemStatusReply:
    status : SubsystemStatus
    error  : str

@dataclass
class RegisterServiceRequest:
    service_name         : str
    subsystem_name       : str
    service_description  : str
    service_capabilities : List[str]
    service_resources    : List[IntersectUUID]
    service_labels       : List[str]
    service_properties   : List[str]

@dataclass
class RegisterServiceReply:
    service_uuid : IntersectUUID
    error        : str

# Asynchronous Events

@dataclass
class SystemStatusChange:
    system_id          : IntersectUUID
    current_status     : str
    change_description : str
    change_time        : IntersectTimeStamp
    subsystem_id       : IntersectUUID
    resource_id        : IntersectUUID
    service_id         : IntersectUUID
    prior_status       : str

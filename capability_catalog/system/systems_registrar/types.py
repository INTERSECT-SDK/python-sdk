from dataclasses import dataclass
from enum import StrEnum
from typing import List
from uuid import UUID

from capability_catalog.capability_types import IntersectUUID

INTERSECT_INVALID_UUID : IntersectUUID = UUID(int=0)

@dataclass
class SystemsRegistrarCapabilityStatus:
    status : str

@dataclass
class SystemsRegistrarCapabilityResult:
    success : bool

# Interaction Parameters & Results

@dataclass
class RegisterSystemRequest:
    organization_name : str
    facility_name     : str
    system_name       : str
    system_secret     : str
    requested_id      : IntersectUUID

@dataclass
class RegisterSystemReply:
    system_id : IntersectUUID
    error     : str

@dataclass
class RegisterSubsystemRequest:
    subsystem_name : str
    system_id      : IntersectUUID
    system_secret  : str
    requested_id   : IntersectUUID

@dataclass
class RegisterSubsystemReply:
    subsystem_id : IntersectUUID
    error        : str

@dataclass
class RegisterSystemResourceRequest:
    resource_name : str
    system_id     : IntersectUUID
    system_secret : str
    requested_id  : IntersectUUID

@dataclass
class RegisterSystemResourceReply:
    resource_id : IntersectUUID
    error       : str

@dataclass
class RegisterSystemServiceRequest:
    service_name  : str
    system_id     : IntersectUUID
    subsystem_id  : IntersectUUID
    system_secret : str
    requested_id  : IntersectUUID

@dataclass
class RegisterSystemServiceReply:
    service_id : IntersectUUID
    error      : str
    
@dataclass
class GetSystemUUIDRequest:
    organization_name : str
    facility_name     : str
    system_name       : str

@dataclass
class GetSystemUUIDReply:
    system_id : IntersectUUID
    error     : str

@dataclass
class GetSubsystemUUIDRequest:
    system_id      : IntersectUUID
    subsystem_name : str

@dataclass
class GetSubsystemUUIDReply:
    subsystem_id : IntersectUUID
    error        : str

@dataclass
class GetSystemResourceUUIDRequest:
    system_id     : IntersectUUID
    resource_name : str

@dataclass
class GetSystemResourceUUIDReply:
    resource_id : IntersectUUID
    error       : str

@dataclass
class GetSystemServiceUUIDRequest:
    system_id    : IntersectUUID
    subsystem_id : IntersectUUID
    service_name : str

@dataclass
class GetSystemServiceUUIDReply:
    service_id : IntersectUUID
    error      : str

# Asynchronous Events

@dataclass
class SystemRegistration:
    system_id         : IntersectUUID
    system_name       : str
    organization_name : str
    facility_name     : str

@dataclass
class SubsystemRegistration:
    system_id      : IntersectUUID
    subsystem_id   : IntersectUUID
    subsystem_name : str

@dataclass
class SystemResourceRegistration:
    system_id     : IntersectUUID
    resource_id   : IntersectUUID
    resource_name : str

@dataclass
class SystemServiceRegistration:
    system_id    : IntersectUUID
    subsystem_id : IntersectUUID
    service_id   : IntersectUUID
    service_name : str
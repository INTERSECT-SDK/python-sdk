import warnings

from datetime import datetime, timezone
from typing import Dict, Generic, Set, Union
from uuid import uuid1, uuid3

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectService,
    intersect_message
)

from capability_catalog.capability_types import (
    IntersectUUID, INTERSECT_INVALID_UUID, INTERSECT_NAMESPACE_UUID
)

from capability_catalog.utility.availability_status.types import (
    AvailabilityStatus,
    AvailabilityStatusEnum
)

from capability_catalog.system.system_manager.types import (
    EnableServiceCommand, DisableServiceCommand,
    RegisterServiceRequest
)

from capability_catalog.system.systems_registrar.types import (
    RegisterSystemRequest, RegisterSystemReply,
    RegisterSubsystemRequest, RegisterSubsystemReply,
    RegisterSystemResourceRequest, RegisterSystemResourceReply,
    RegisterSystemServiceRequest, RegisterSystemServiceReply,
    GetSystemUUIDRequest, GetSystemUUIDReply,
    GetSubsystemUUIDRequest, GetSubsystemUUIDReply,
    GetSystemResourceUUIDRequest, GetSystemResourceUUIDReply,
    GetSystemServiceUUIDRequest, GetSystemServiceUUIDReply
)

class SystemsRegistrarCapability(IntersectBaseCapabilityImplementation):
    """ A prototype implementation of the INTERSECT 'Systems Registrar' microservice capability """

    # Internal Metadata Classes
    class SystemState:
        system_id     : IntersectUUID
        system_name   : str
        system_secret : str
        subsystem_ids : Dict[str, IntersectUUID]
        resource_ids  : Dict[str, IntersectUUID]
        service_ids   : Dict[str, IntersectUUID]

        def __init__(self, sys_name : str, sys_id : IntersectUUID, sys_secret : str) -> None:
            self.system_id = sys_id
            self.system_name = sys_name
            self.system_secret = sys_secret
            self.subsystem_ids = dict()
            self.resource_ids = dict()
            self.service_ids = dict()

    def __init__(self, service_hierarchy : HierarchyConfig) -> None:
        super().__init__()
        self.capability_name = "SystemsRegistrar"

        # Private Data
        self._service_desc    : str = "Manages UUIDs for an INTERSECT registration domain."
        self._service_name    : str = service_hierarchy.service
        self._system_name     : str = service_hierarchy.system
        self._subsys_name     : str = "infrastructure-management"
        self._org_name        : str = service_hierarchy.organization
        self._facility_name   : str = service_hierarchy.facility

        self._current_status : str = AvailabilityStatusEnum.UNKNOWN
        self._prior_status   : str = AvailabilityStatusEnum.UNKNOWN
        self._last_update_description : str = ""
        self._last_update_time : datetime = datetime.now(timezone.utc)
        self._capability_status : str = f'SystemsRegistrarCapability - {self._current_status}'

        self._domain_uuid : IntersectUUID = uuid3(INTERSECT_NAMESPACE_UUID, f'{self.capability_name}@{service_hierarchy.hierarchy_string("%")}')
        self._all_assigned_uuids : Set[IntersectUUID] = set()
        self._systems : Dict[IntersectUUID, SystemsRegistrarCapability.SystemState] = dict()
        self._system_ids_by_name : Dict[str, IntersectUUID] = dict()

        self._iservice : IntersectService = None

        # name services we depend on (this should really be hidden from end users)
        self.system_manager = f'{self._org_name}.{self._facility_name}.{self._system_name}.infrastructure-management.system-manager'

        # self-registration
        sys_uuid, err = self._register_system(org=self._org_name,
                                              facility=self._facility_name,
                                              system_name=self._system_name,
                                              secret="")
        sys_state = self._get_system(system_uuid=sys_uuid, system_secret="")
        if sys_state is not None:
            sub_uuid, err = self._register_subsystem(system=sys_state,
                                                     subsystem_name=self._subsys_name)
            svc_uuid, err = self._register_service(system=sys_state,
                                                   service_name=self._service_name,
                                                   subsystem_uuid=sub_uuid)
            
    def get_capability_status(self) -> AvailabilityStatus:
        self.update_capability_status()
        curr_status = AvailabilityStatus(current_status=self._current_status,
                                         previous_status=self._prior_status,
                                         status_description=self._capability_status,
                                         status_change_time=self._last_update_time)
        return curr_status
    
    def update_capability_status(self) -> None:
        self._update_status()

    def startup(self, svc : IntersectService) -> None:
        self._iservice = svc
        self._current_status = AvailabilityStatusEnum.AVAILABLE
        self._update_status("service associated")


    # Private methods

    def _generate_domain_tree(self) -> str:
        tree : str = "- Domain System Tree:\n"
        for sys_state in self._systems.values():
            tree += f'  + System: {sys_state.system_name} [{sys_state.system_id}]\n'
            tree += f'    - Resources:\n'  + "".join(f'      * {res} [{id}]\n'for res, id in sys_state.resource_ids.items())
            tree += f'    - Subsystems:\n' + "".join(f'      * {sub} [{id}]\n'for sub, id in sys_state.subsystem_ids.items())
            tree += f'    - Services:\n'   + "".join(f'      * {svc} [{id}]\n'for svc, id in sys_state.service_ids.items())
        return tree

    def _update_status(self, update : str = None) -> None:
        if update:
            self._last_update_time = datetime.now(timezone.utc)
            self._last_update_description = update
        system_list = self._generate_domain_tree()
        self._capability_status = \
            f'\nSystemsRegistrarCapability - {self._current_status}\n' + \
            f'- Last Update ({self._last_update_time}): {self._last_update_description}\n' + \
            f'{system_list}\n'

    def _get_system(self,
                    system_uuid   : IntersectUUID,
                    system_secret : str) -> Union[SystemState, None]:
        if system_uuid in self._systems:
            sys_state = self._systems[system_uuid]
            if system_secret is not None: # registrations
                if system_secret == sys_state.system_secret:
                    return sys_state
                else:
                    print(f'WARNING: System secret for {system_uuid} did not match!')
            else: # lookups
                return sys_state
        return None

    def _register_system(self,
                         org         : str,
                         facility    : str,
                         system_name : str,
                         secret      : str,
                         wants_uuid  : IntersectUUID = None) -> tuple[IntersectUUID, str]:
        sys_uuid = INTERSECT_INVALID_UUID
        error : str = None

        full_name = f'{org}.{facility}.{system_name}'

        if wants_uuid is None:
            # generate service UUID within system UUID namespace
            sys_uuid = uuid3(self._domain_uuid, full_name)
        else:
            sys_uuid = wants_uuid
                
        # check if the requested UUID conflicts with another assignment
        if sys_uuid in self._all_assigned_uuids:
            error = f"UUID assignment {sys_uuid} for System {full_name} conflicts with an existing entity"
            sys_uuid = INTERSECT_INVALID_UUID
        else:
            self._all_assigned_uuids.add(sys_uuid)
            self._system_ids_by_name[full_name] = sys_uuid
            self._systems[sys_uuid] = \
                SystemsRegistrarCapability.SystemState(sys_id=sys_uuid,
                                                       sys_name=full_name,
                                                       sys_secret=secret)
            update_msg = f'registered system {full_name} with UUID {sys_uuid}'
            print(f"DEBUG: [{self.capability_name}] {update_msg}")
            self._update_status(update_msg)

        return sys_uuid, error

    def _register_subsystem(self,
                            system         : SystemState,
                            subsystem_name : str,
                            wants_uuid     : IntersectUUID = None) -> tuple[IntersectUUID, str]:
        sub_uuid = INTERSECT_INVALID_UUID
        error : str = None
        system_uuid = system.system_id
            
        if wants_uuid is None:
            # generate service UUID within system UUID namespace
            sub_uuid = uuid3(system_uuid, subsystem_name)
        else:
            sub_uuid = wants_uuid
                
        # check if the requested UUID conflicts with another assignment
        if sub_uuid in self._all_assigned_uuids:
            error = f"UUID assignment {sub_uuid} for Subsystem {subsystem_name} conflicts with an existing entity"
            sub_uuid = INTERSECT_INVALID_UUID
        else:
            self._all_assigned_uuids.add(sub_uuid)
            system.subsystem_ids[subsystem_name] = sub_uuid
            update_msg = f'assigned {sub_uuid} to subsystem {subsystem_name} in system {system.system_name}'
            print(f"DEBUG: [{self.capability_name}] {update_msg}")
            self._update_status(update_msg)

        return sub_uuid, error

    def _register_resource(self,
                           system        : SystemState,
                           resource_name : str,
                           wants_uuid    : IntersectUUID = None) -> tuple[IntersectUUID, str]:
        res_uuid = INTERSECT_INVALID_UUID
        error : str = None
        system_uuid = system.system_id

        if wants_uuid is None:
            # generate service UUID within system UUID namespace
            res_uuid = uuid3(system_uuid, resource_name)
        else:
            res_uuid = wants_uuid
                
        # check if the requested UUID conflicts with another assignment
        if res_uuid in self._all_assigned_uuids:
            error = f"UUID assignment {res_uuid} for Resource {resource_name} conflicts with an existing entity"
            res_uuid = INTERSECT_INVALID_UUID
        else:
            self._all_assigned_uuids.add(res_uuid)
            system.resource_ids[resource_name] = res_uuid
            update_msg = f'assigned {res_uuid} to resource {resource_name} in system {system.system_name}'
            print(f"DEBUG: [{self.capability_name}] {update_msg}")
            self._update_status(update_msg)

        return res_uuid, error

    def _register_service(self,
                          system         : SystemState,
                          service_name   : str,
                          subsystem_uuid : IntersectUUID = None,
                          wants_uuid     : IntersectUUID = None) -> tuple[IntersectUUID, str]:
        svc_uuid = INTERSECT_INVALID_UUID
        error : str = None
        system_uuid = system.system_id
        
        if wants_uuid is None:
            if subsystem_uuid is None:
                # generate service UUID within system UUID namespace
                svc_uuid = uuid3(system_uuid, service_name)
            else:
                if subsystem_uuid in system.subsystem_ids.values():
                    svc_uuid = uuid3(subsystem_uuid, service_name)
                else:
                    error = f"Subsystem with UUID {subsystem_uuid} not found in System {system_uuid}!"
        else:
            svc_uuid = wants_uuid
                
        if svc_uuid != INTERSECT_INVALID_UUID:
            # check if the requested UUID conflicts with another assignment
            if svc_uuid in self._all_assigned_uuids:
                error = f"UUID assignment {svc_uuid} for Service {service_name} conflicts with an existing entity"
                svc_uuid = INTERSECT_INVALID_UUID
            else:
                self._all_assigned_uuids.add(svc_uuid)
                system.service_ids[service_name] = svc_uuid
                update_msg = f'assigned {svc_uuid} to service {service_name} in system {system.system_name}'
                print(f"DEBUG: [{self.capability_name}] {update_msg}")
                self._update_status(update_msg)

        return svc_uuid, error


    # Interactions

    @intersect_message()
    def register_system(self, params: RegisterSystemRequest) -> RegisterSystemReply:
        error_msg = ""
        req_id = None
        if params.requested_id != INTERSECT_INVALID_UUID:
            req_id = params.requested_id
        sys_uuid, error = self._register_system(org=params.organization_name,
                                                facility=params.facility_name,
                                                system_name=params.system_name,
                                                secret=params.system_secret,
                                                wants_uuid=req_id)
        if error != None:
            error_msg = error
        
        if error_msg != "":
            warnings.warn(f'ERROR: {error_msg}')
        
        return RegisterSystemReply(system_id=sys_uuid, error=error_msg)

    @intersect_message()
    def register_subsystem(self, params: RegisterSubsystemRequest) -> RegisterSubsystemReply:
        error_msg = ""
        subsys_uuid = INTERSECT_INVALID_UUID
        if params.system_id != INTERSECT_INVALID_UUID:
            system = self._get_system(system_uuid=params.system_id,
                                      system_secret=params.system_secret)
            if system is not None:
                req_id = None
                if params.requested_id != INTERSECT_INVALID_UUID:
                    req_id = params.requested_id
                subsys_uuid, error = self._register_subsystem(system=system,
                                                              subsystem_name=params.subsystem_name,
                                                              wants_uuid=req_id)
                if error != None:
                    error_msg = error
            else:
                error_msg = f"System with UUID {params.system_id} not found!"
        else:
            error_msg = f"Invalid System UUID {params.system_id} provided!"
        
        if error_msg != "":
            warnings.warn(f'ERROR: {error_msg}')
        
        return RegisterSubsystemReply(subsystem_id=subsys_uuid, error=error_msg)

    @intersect_message()
    def register_system_resource(self, params: RegisterSystemResourceRequest) -> RegisterSystemResourceReply:
        error_msg = ""
        res_uuid = INTERSECT_INVALID_UUID
        if params.system_id != INTERSECT_INVALID_UUID:
            system = self._get_system(system_uuid=params.system_id,
                                      system_secret=params.system_secret)
            if system is not None:
                req_id = None
                if params.requested_id != INTERSECT_INVALID_UUID:
                    req_id = params.requested_id
                res_uuid, error = self._register_resource(system=system,
                                                          resource_name=params.resource_name,
                                                          wants_uuid=req_id)
                if error != None:
                    error_msg = error
            else:
                error_msg = f"System with UUID {params.system_id} not found!"
        else:
            error_msg = f"Invalid System UUID {params.system_id} provided!"
        
        if error_msg != "":
            warnings.warn(f'ERROR: {error_msg}')
        
        return RegisterSystemResourceReply(resource_id=res_uuid, error=error_msg)

    @intersect_message()
    def register_system_service(self, params: RegisterSystemServiceRequest) -> RegisterSystemServiceReply:
        error_msg = ""
        svc_uuid = INTERSECT_INVALID_UUID
        if params.system_id != INTERSECT_INVALID_UUID:
            system = self._get_system(system_uuid=params.system_id,
                                      system_secret=params.system_secret)
            if system is not None:
                req_id = None
                if params.requested_id != INTERSECT_INVALID_UUID:
                    req_id = params.requested_id
                svc_uuid, error = self._register_service(system=system,
                                                         service_name=params.service_name,
                                                         subsystem_uuid=params.subsystem_id,
                                                         wants_uuid=req_id)
                if error != None:
                    error_msg = error
            else:
                error_msg = f"System with UUID {params.system_id} not found!"
        else:
            error_msg = f"Invalid System UUID {params.system_id} provided!"
        
        if error_msg != "":
            warnings.warn(f'ERROR: {error_msg}')
        
        return RegisterSystemServiceReply(service_id=svc_uuid, error=error_msg)
    
    @intersect_message()
    def get_system_uuid(self, params: GetSystemUUIDRequest) -> GetSystemUUIDReply:
        error_msg = ""
        sys_uuid  = INTERSECT_INVALID_UUID

        sys_full_name = f'{params.organization_name}.{params.facility_name}.{params.system_name}'
        if sys_full_name in self._system_ids_by_name:
            sys_uuid = self._system_ids_by_name[sys_full_name]
        else:
            error_msg = f"System with name {sys_full_name} not found!"
            warnings.warn(f'ERROR: {error_msg}')
        
        return GetSystemUUIDReply(system_id=sys_uuid, error=error_msg)

    @intersect_message()
    def get_subsystem_uuid(self, params: GetSubsystemUUIDRequest) -> GetSubsystemUUIDReply:
        error_msg   = ""
        subsys_uuid = INTERSECT_INVALID_UUID
        
        subsys_name = params.subsystem_name
        sys_uuid    = params.system_id
        if sys_uuid != INTERSECT_INVALID_UUID:
            system = self._get_system(system_uuid=sys_uuid, system_secret=None)
            if system is not None:
                if subsys_name in system.subsystem_ids:
                    subsys_uuid = system.subsystem_ids[subsys_name]
                else:
                    error_msg = f"Subsystem with name {subsys_name} not found!"
            else:
                error_msg = f"System with UUID {sys_uuid} not found!"
        else:
            error_msg = f"Invalid System UUID {sys_uuid} provided!"
        
        if error_msg != "":
            warnings.warn(f'ERROR: {error_msg}')
        
        return GetSubsystemUUIDReply(subsystem_id=subsys_uuid, error=error_msg)

    @intersect_message()
    def get_system_resource_uuid(self, params: GetSystemResourceUUIDRequest) -> GetSystemResourceUUIDReply:
        error_msg = ""
        res_uuid  = INTERSECT_INVALID_UUID
        
        res_name  = params.resource_name
        sys_uuid  = params.system_id
        if sys_uuid != INTERSECT_INVALID_UUID:
            system = self._get_system(system_uuid=sys_uuid, system_secret=None)
            if system is not None:
                if res_name in system.resource_ids:
                    res_uuid = system.resource_ids[res_name]
                else:
                    error_msg = f"Resource with name {res_name} not found!"
            else:
                error_msg = f"System with UUID {sys_uuid} not found!"
        else:
            error_msg = f"Invalid System UUID {sys_uuid} provided!"
        
        if error_msg != "":
            warnings.warn(f'ERROR: {error_msg}')
        
        return GetSystemResourceUUIDReply(resource_id=res_uuid, error=error_msg)

    @intersect_message()
    def get_system_service_uuid(self, params: GetSystemServiceUUIDRequest) -> GetSystemServiceUUIDReply:
        error_msg = ""
        svc_uuid  = INTERSECT_INVALID_UUID
        
        svc_name  = params.service_name
        sys_uuid  = params.system_id
        if sys_uuid != INTERSECT_INVALID_UUID:
            system = self._get_system(system_uuid=sys_uuid, system_secret=None)
            if system is not None:
                if svc_name in system.service_ids:
                    svc_uuid = system.service_ids[svc_name]
                else:
                    error_msg = f"Service with name {svc_name} not found!"
            else:
                error_msg = f"System with UUID {sys_uuid} not found!"
        else:
            error_msg = f"Invalid System UUID {sys_uuid} provided!"
        
        if error_msg != "":
            warnings.warn(f'ERROR: {error_msg}')
        
        return GetSystemServiceUUIDReply(service_id=svc_uuid, error=error_msg)

if __name__ == '__main__':
    print("This is a service implementation module. It is not meant to be executed.")

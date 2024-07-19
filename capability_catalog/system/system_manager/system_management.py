from dataclasses import dataclass
from typing import Dict, List, Union
from uuid import uuid3, uuid4

from capability_catalog.capability_types import (
    IntersectEntity,
    IntersectUUID, INTERSECT_INVALID_UUID
)

from capability_catalog.system.system_catalog.types import (
    SystemManagementEntityTypes,
    SystemManagementEntityRelationTypes
)

@dataclass
class SystemInformation:
    system_entity       : IntersectEntity
    system_facility     : str
    system_organization : str
    system_enabled      : int = 0

@dataclass
class SubsystemInformation:
    subsystem_entity    : IntersectEntity
    system_uuid         : IntersectUUID
    subsystem_resources : List[IntersectUUID]
    subsystem_services  : List[IntersectUUID]
    subsystem_enabled   : int = 0

@dataclass
class ServiceInformation:
    service_entity       : IntersectEntity
    system_uuid          : IntersectUUID
    service_capabilities : List[str]
    service_resources    : List[IntersectUUID]
    subsystem_uuid       : IntersectUUID = None
    service_enabled      : int = 0

@dataclass
class ResourceInformation:
    resource_entity  : IntersectEntity
    system_uuid      : IntersectUUID
    subsystem_uuid   : IntersectUUID = None
    resource_enabled : int = 0

class ResourceManager:
    """ Management of System Resources """

    def __init__(self, system : 'IntersectSystemState') -> None:
        self._system = system
        self._resources : Dict[str, ResourceInformation] = dict()

    # Public Methods

    def __str__(self) -> str:
        return f'- Resources:\n{self.inspect_resources()}\n'

    def add_resource(self, new_resource : ResourceInformation) -> None:
        self._resources[new_resource.resource_entity.entity_name] = new_resource
        if new_resource.subsystem_uuid is not None:
            ss_info = self._system.subsystems.get_subsystem_by_uuid(new_resource.subsystem_uuid)
            if ss_info is not None:
                self._system.subsystems.add_subsystem_resource(subsystem_name=ss_info.subsystem_entity.entity_name,
                                                               resource_id=new_resource.resource_entity.entity_uuid)

    def remove_resource(self, resource_name : str) -> None:
        if resource_name in self._resources:
            del self._resources[resource_name]

    def enable_resource(self, resource_id : IntersectUUID) -> None:
        res = self.get_resource_by_uuid(resource_id)
        if res is not None:
            res.resource_enabled = 1

    def disable_resource(self, resource_id : IntersectUUID) -> None:
        res = self.get_resource_by_uuid(resource_id)
        if res is not None:
            res.resource_enabled = 0

    def get_resource_by_name(self, resource_name : str) -> Union[ResourceInformation, None]:
        if resource_name in self._resources:
            return self._resources[resource_name]
        else:
            return None
        
    def get_resource_by_uuid(self, resource_id : IntersectUUID) -> Union[ResourceInformation, None]:
        for resource in self._resources.values():
            if resource.resource_entity.entity_uuid == resource_id:
                return resource
        return None
    
    def get_resources_by_subsystem(self, subsystem_id : IntersectUUID) -> Union[List[ResourceInformation], None]:
        match_list = list()
        for resource in self._resources.values():
            if resource.subsystem_uuid == subsystem_id:
                match_list.append(resource)
        if len(match_list):
            return match_list
        else:
            return None

    def get_resource_names(self) -> List[str]:
        return list(self._resources.keys())
    
    def get_resource_uuids(self) -> List[IntersectUUID]:
        res_ids = list()
        for res in self._resources.values():
            res_ids.append(res.resource_entity.entity_uuid)
        return res_ids

    def get_all_resources(self) -> List[ResourceInformation]:
        return self._resources.values()
    
    def inspect_resources(self) -> str:
        res_str = ""
        for rinfo in self._resources.values():
            res_str += f'> {rinfo.resource_entity.entity_name} ({rinfo.resource_entity.entity_uuid}):\n' + \
                       f'  {rinfo.resource_entity.entity_description}\n'
        return res_str

class ServiceManager:
    """ Management of System Services """

    def __init__(self, system : 'IntersectSystemState') -> None:
        self._system = system
        self._services : Dict[str, ServiceInformation] = dict()

    # Public Methods

    def __str__(self) -> str:
        return f'- Services:\n{self.inspect_services()}\n'

    def add_service(self, new_service : ServiceInformation) -> None:
        self._services[new_service.service_entity.entity_name] = new_service
        if new_service.subsystem_uuid is not None:
            ss_info = self._system.subsystems.get_subsystem_by_uuid(new_service.subsystem_uuid)
            if ss_info is not None:
                self._system.subsystems.add_subsystem_service(subsystem_name=ss_info.subsystem_entity.entity_name,
                                                              service_id=new_service.service_entity.entity_uuid)

    def remove_service(self, service_name : str) -> None:
        if service_name in self._services:
            del self._services[service_name]

    def enable_service(self, service_id : IntersectUUID) -> None:
        svc = self.get_service_by_uuid(service_id)
        if svc is not None:
            svc.service_enabled = 1

    def disable_service(self, service_id : IntersectUUID) -> None:
        svc = self.get_service_by_uuid(service_id)
        if svc is not None:
            svc.service_enabled = 0

    def get_service_by_name(self, service_name : str) -> Union[ServiceInformation, None]:
        if service_name in self._services:
            return self._services[service_name]
        else:
            return None
        
    def get_service_by_uuid(self, service_id : IntersectUUID) -> Union[ServiceInformation, None]:
        for service in self._services.values():
            if service.service_entity.entity_uuid == service_id:
                return service
        return None

    def get_services_by_subsystem(self, subsystem_id : IntersectUUID) -> Union[List[str], None]:
        match_list = list()
        for service in self._services.values():
            if service.subsystem_uuid == subsystem_id:
                match_list.append(service.service_entity.entity_name)
        if len(match_list):
            return match_list
        else:
            return None

    def get_service_names(self) -> List[str]:
        return list(self._services.keys())
    
    def get_service_uuids(self) -> List[IntersectUUID]:
        svc_ids = list()
        for svc in self._services.values():
            svc_ids.append(svc.service_entity.entity_uuid)
        return svc_ids

    def get_all_services(self) -> List[ServiceInformation]:
        return list(self._services.values())
    
    def inspect_services(self) -> str:
        svc_str = ""
        for sinfo in self._services.values():
            svc_str += f'> {sinfo.service_entity.entity_name} ({sinfo.service_entity.entity_uuid}):\n' + \
                       f'  {sinfo.service_entity.entity_description}\n'
        return svc_str
    
class SubsystemManager:
    """ Management of Subsystems """

    def __init__(self, system : 'IntersectSystemState') -> None:
        self._system = system
        self._subsystems : Dict[str, 'SubsystemInformation'] = dict()

    # Public Methods

    def __str__(self) -> str:
        return f'- Subsystems:\n{self.inspect_subsystems()}\n'
    
    def add_subsystem(self, new_subsystem : 'SubsystemInformation') -> None:
        self._subsystems[new_subsystem.subsystem_entity.entity_name] = new_subsystem

    def remove_subsystem(self, subsystem_name : str) -> None:
        if subsystem_name in self._subsystems:
            del self._subsystems[subsystem_name]

    def enable_subsystem(self, subsystem_name : str) -> None:
        if subsystem_name in self._subsystems:
            subsys = self._subsystems[subsystem_name]
            for svc_id in subsys.subsystem_services:
                self._system.services.enable_service(svc_id)
            subsys.subsystem_enabled = 1
    
    def disable_subsystem(self, subsystem_name : str) -> None:
        if subsystem_name in self._subsystems:
            subsys = self._subsystems[subsystem_name]
            for svc_id in subsys.subsystem_services:
                self._system.services.disable_service(svc_id)
            subsys.subsystem_enabled = 0

    def get_subsystem_by_name(self, subsystem_name : str) -> Union['SubsystemInformation', None]:
        if subsystem_name in self._subsystems:
            return self._subsystems[subsystem_name]
        else:
            return None
        
    def get_subsystem_by_uuid(self, subsystem_id : IntersectUUID) -> Union['SubsystemInformation', None]:
        for subsys in self._subsystems.values():
            if subsys.subsystem_entity.entity_uuid == subsystem_id:
                return subsys
        return None

    def add_subsystem_resource(self, subsystem_name : str, resource_id : IntersectUUID) -> None:
        if subsystem_name in self._subsystems:
            subsys = self._subsystems[subsystem_name]
            subsys.subsystem_resources.append(resource_id)

    def add_subsystem_service(self, subsystem_name : str, service_id : IntersectUUID) -> None:
        if subsystem_name in self._subsystems:
            subsys = self._subsystems[subsystem_name]
            subsys.subsystem_services.append(service_id)
    
    def get_subsystem_resources(self, subsystem_name : str) -> Union[List[IntersectUUID], None]:
        if subsystem_name in self._subsystems:
            return self._subsystems[subsystem_name].subsystem_resources
        else:
            return None

    def get_subsystem_services(self, subsystem_name : str) -> Union[List[IntersectUUID], None]:
        if subsystem_name in self._subsystems:
            return self._subsystems[subsystem_name].subsystem_services
        else:
            return None

    def get_subsystem_names(self) -> List[str]:
        return list(self._subsystems.keys())
    
    def get_subsystem_uuids(self) -> List[IntersectUUID]:
        ss_ids = list()
        for subsys in self._subsystems.values():
            ss_ids.append(subsys.subsystem_entity.entity_uuid)
        return self._subsystems.keys()
    
    def inspect_subsystems(self) -> str:
        ss_str = ""
        for subsys in self._subsystems.values():
            ss_str += f'> {subsys.subsystem_entity.entity_name} ({subsys.subsystem_entity.entity_uuid}):\n' + \
                      f'  {subsys.subsystem_entity.entity_description}\n'
        return ss_str


class IntersectResourceState:
    # Public Methods
    def __init__(self,
                 res_name    : str,
                 sys_uuid    : IntersectUUID,
                 subsys_uuid : IntersectUUID = None,
                 res_uuid    : IntersectUUID = None,
                 res_desc    : str = "No resource description provided.",
                 res_labels  : List[str] = list(),
                 res_props   : List[str] = list()) -> None:

        if res_uuid is None:
            # generate resource UUID within system UUID namespace
            res_uuid = uuid3(sys_uuid, res_name)
        
        res_entity = IntersectEntity(entity_uuid=res_uuid,
                                     entity_name=res_name,
                                     entity_type=SystemManagementEntityTypes.RESOURCE,
                                     entity_description=res_desc,
                                     entity_labels=res_labels,
                                     entity_properties=res_props)
        self._descriptor = ResourceInformation(resource_entity=res_entity,
                                               system_uuid=sys_uuid,
                                               subsystem_uuid=subsys_uuid)

    def __str__(self) -> str:
        return f'resource(name={self.name}, uuid={self.uuid}, sys_uuid={self.system_uuid})\n'

    @property
    def name(self) -> str:
        return self._descriptor.resource_entity.entity_name
    
    @property
    def description(self) -> str:
        return self._descriptor.resource_entity.entity_description

    @property
    def system_uuid(self) -> IntersectUUID:
        return self._descriptor.system_uuid
    
    @property
    def subsystem_uuid(self) -> IntersectUUID:
        return self._descriptor.subsystem_uuid

    @property
    def uuid(self) -> IntersectUUID:
        return self._descriptor.resource_entity.entity_uuid

    @property
    def labels(self) -> List[str]:
        return self._descriptor.resource_entity.entity_labels
    
    @property
    def properties(self) -> List[str]:
        return self._descriptor.resource_entity.entity_properties
    
    @property
    def entity(self) -> IntersectEntity:
        return self._descriptor.resource_entity

    @property
    def information(self) -> ResourceInformation:
        return self._descriptor


class IntersectServiceState:
    # Public Methods
    def __init__(self,
                 svc_name     : str,
                 system_info  : SystemInformation,
                 subsys_info  : SubsystemInformation = None,
                 svc_uuid     : IntersectUUID = None,
                 svc_desc     : str = "No service description provided.",
                 svc_labels   : List[str] = list(),
                 svc_props    : List[str] = list()) -> None:
        self._system = system_info
        self._subsystem = subsys_info

        sys_uuid = self._system.system_entity.entity_uuid
        if svc_uuid is None:
            # generate service UUID within system UUID namespace
            svc_uuid = uuid3(sys_uuid, svc_name)

        subsys_uuid = None
        if self._subsystem is not None:
            subsys_uuid = self._subsystem.subsystem_entity.entity_uuid

        svc_entity = IntersectEntity(entity_uuid=svc_uuid,
                                     entity_name=svc_name,
                                     entity_type=SystemManagementEntityTypes.SERVICE,
                                     entity_description=svc_desc,
                                     entity_labels=svc_labels,
                                     entity_properties=svc_props)
        self._descriptor = ServiceInformation(service_entity=svc_entity,
                                              system_uuid=sys_uuid,
                                              service_capabilities=list(),
                                              service_resources=list(),
                                              subsystem_uuid=subsys_uuid)

    def __str__(self) -> str:
        return f'Service(name={self.name}, uuid={self.uuid}, system={self.system_uuid})\n' + \
               f'------ Description ------\n{self.description()}\n'

    @property
    def name(self) -> str:
        return self._descriptor.service_entity.entity_name
    
    @property
    def description(self) -> str:
        return self._descriptor.service_entity.entity_description

    @property
    def system(self) -> SystemInformation:
        return self._system
    
    @property
    def subsystem(self) -> Union[SubsystemInformation, None]:
        return self._subsystem

    @property
    def system_uuid(self) -> IntersectUUID:
        return self._descriptor.system_uuid
    
    @property
    def subsystem_uuid(self) -> IntersectUUID:
        return self._descriptor.subsystem_uuid

    @property
    def uuid(self) -> IntersectUUID:
        return self._descriptor.service_entity.entity_uuid

    @property
    def labels(self) -> List[str]:
        return self._descriptor.service_entity.entity_labels
    
    @property
    def properties(self) -> List[str]:
        return self._descriptor.service_entity.entity_properties
    
    @property
    def entity(self) -> IntersectEntity:
        return self._descriptor.service_info

    @property
    def information(self) -> ServiceInformation:
        return self._descriptor


class IntersectSystemState:
    # Public Methods
    def __init__(self,
                 sys_name   : str,
                 fac_name   : str = "UNKNOWN_FACILITY",
                 org_name   : str = "UNKNOWN_ORGANIZATION",
                 sys_desc   : str = "No system description provided.",
                 sys_labels : List[str] = list(),
                 sys_props  : List[str] = list(),
                 sys_uuid   : IntersectUUID = INTERSECT_INVALID_UUID) -> None:

        if sys_uuid == INTERSECT_INVALID_UUID:
            # TODO: use SystemsRegistrar capability to get a system namespace UUID
            sys_uuid = uuid4()

        sys_entity = IntersectEntity(entity_uuid=sys_uuid,
                                     entity_name=sys_name,
                                     entity_type=SystemManagementEntityTypes.SYSTEM,
                                     entity_description=sys_desc,
                                     entity_labels=sys_labels,
                                     entity_properties=sys_props)
        self._descriptor = SystemInformation(system_entity=sys_entity,
                                             system_facility=fac_name,
                                             system_organization=org_name)
        
        self._resource_mgr = ResourceManager(system=self)
        self._service_mgr = ServiceManager(system=self)
        self._subsys_mgr = SubsystemManager(system=self)

    def __str__(self) -> str:
        return f'System(name={self.full_name}, uuid={self.uuid})\n' + \
                '------ Description ------\n' + \
                self.description() + \
                '------ Resources ------\n' + \
                self.resources.inspect_resources() + \
                '------ Services ------\n' + \
                self.services.inspect_services() + \
                '------ Subsystems ------\n' + \
                self.subsystems.inspect_subsystems() + '\n' + \
                '------------------------\n'

    @property
    def name(self) -> str:
        return self._descriptor.system_entity.entity_name

    @property
    def full_name(self) -> str:
        return f'{self.organization}.{self.facility}.{self.name}'
    
    @property
    def description(self) -> str:
        return self._descriptor.system_entity.entity_description

    @property
    def facility(self) -> str:
        return self._descriptor.system_facility

    @property
    def organization(self) -> str:
        return self._descriptor.system_organization

    @property
    def uuid(self) -> IntersectUUID:
        return self._descriptor.system_entity.entity_uuid
    
    @property
    def labels(self) -> List[str]:
        return self._descriptor.system_entity.entity_labels
    
    @property
    def properties(self) -> List[str]:
        return self._descriptor.system_entity.entity_properties

    @property
    def resources(self):
        return self._resource_mgr

    @property
    def services(self):
        return self._service_mgr
    
    @property
    def subsystems(self):
        return self._subsys_mgr
    
    @property
    def entity(self) -> IntersectEntity:
        return self._descriptor.system_entity
    
    @property
    def information(self) -> SystemInformation:
        return self._descriptor

import warnings

from datetime import datetime, timezone
from typing import Generic
from uuid import uuid3

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectClientMessageParams,
    IntersectService,
    intersect_message
)

from capability_catalog.capability_types import (
    IntersectUUID, INTERSECT_INVALID_UUID, INTERSECT_NAMESPACE_UUID,
    IntersectEntity, IntersectEntityRelation
)

from capability_catalog.utility.availability_status.types import (
    AvailabilityStatusEnum,
    AvailabilityStatus
)

from capability_catalog.data.er_catalog.types import (
    CreateEntityCommand,
    CreateRelationCommand
)

from capability_catalog.system.system_catalog.types import (
    SystemManagementEntityTypes,
    SystemManagementEntityRelationTypes,
    SystemInformationCatalogCapabilityResult,
    CreateSubsystemCommand,
    CreateSystemResourceCommand,
    CreateSystemServiceCommand,
    GetSubsystemIdsReply,
    GetSubsystemNamesReply,
    GetSubsystemInformationRequest, GetSubsystemInformationReply,
    GetSystemResourceIdsRequest, GetSystemResourceIdsReply,
    GetSystemResourceNamesRequest, GetSystemResourceNamesReply,
    GetSystemResourceInformationRequest, GetSystemResourceInformationReply,
    GetSystemServiceIdsRequest, GetSystemServiceIdsReply,
    GetSystemServiceNamesRequest, GetSystemServiceNamesReply,
    GetSystemServiceInformationRequest, GetSystemServiceInformationReply,
    GetSystemServicesByCapabilityRequest, GetSystemServicesByCapabilityReply,
    GetSystemServicesByResourceRequest, GetSystemServicesByResourceReply
)

from capability_catalog.system.system_manager.system_management import (
    IntersectSystemState,
    SubsystemInformation,
    ServiceInformation,
    ResourceInformation
)

from capability_catalog.system.system_manager.types import (
    EnableServiceCommand, DisableServiceCommand,
    RegisterServiceRequest
)

class SystemInformationCatalogCapability(IntersectBaseCapabilityImplementation):
    """ A prototype implementation of the INTERSECT 'System Information Catalog' microservice capability """

    def __init__(self, service_hierarchy : HierarchyConfig, system : IntersectSystemState) -> None:
        super().__init__()
        self.capability_name = "SystemInformationCatalog"

        # Private Data
        self._service_desc    : str = "Manages information on the local INTERSECT system's services, subsystems, and resources."
        self._service_name    : str = service_hierarchy.service
        self._system_name     : str = service_hierarchy.system
        self._subsys_name     : str = "infrastructure-management"
        self._org_name        : str = service_hierarchy.organization
        self._facility_name   : str = service_hierarchy.facility

        self._current_status          : str = AvailabilityStatusEnum.UNKNOWN
        self._prior_status            : str = AvailabilityStatusEnum.UNKNOWN
        self._last_update_description : str = ""
        self._last_update_time        : datetime = datetime.now(timezone.utc)

        self._system   : IntersectSystemState = system
        self._iservice : IntersectService = None

        # name services we depend on (this should really be hidden from end users)
        self.er_catalog = f'{self._org_name}.{self._facility_name}.intersect.data-management.er-catalog'
        self.system_manager = f'{self._org_name}.{self._facility_name}.{self._system_name}.infrastructure-management.system-manager'

    def get_capability_status(self) -> AvailabilityStatus:
        curr_status = AvailabilityStatus(current_status=self._current_status,
                                         previous_status=self._prior_status,
                                         status_description=self._last_update_description,
                                         status_change_time=self._last_update_time)
        return curr_status

    def startup(self, svc : IntersectService) -> None:
        self._iservice = svc

        # use local system & service to finish initialization

        org_name = self._org_name
        org_uuid = uuid3(INTERSECT_NAMESPACE_UUID, org_name)
        org_entity = IntersectEntity(entity_description=f'The {org_name} organization',
                                     entity_name=org_name,
                                     entity_type=SystemManagementEntityTypes.ORGANIZATION,
                                     entity_uuid=org_uuid,
                                     entity_labels=list(),
                                     entity_properties=list())
        org_entity_request = IntersectClientMessageParams(
            destination=self.er_catalog,
            operation='EntityRelationCatalog.create_entity',
            payload=CreateEntityCommand(entity=org_entity))
        self._iservice.create_external_request(request=org_entity_request)

        fac_name = self._facility_name
        if fac_name != "":
            fac_uuid = uuid3(org_uuid, fac_name)
            fac_entity = IntersectEntity(entity_description=f'The {fac_name} facility at {org_name}',
                                        entity_name=fac_name,
                                        entity_type=SystemManagementEntityTypes.FACILITY,
                                        entity_uuid=fac_uuid,
                                        entity_labels=list(),
                                        entity_properties=list())
            fac_entity_request = IntersectClientMessageParams(
                destination=self.er_catalog,
                operation='EntityRelationCatalog.create_entity',
                payload=CreateEntityCommand(entity=fac_entity))
            self._iservice.create_external_request(request=fac_entity_request)

            orgfac_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.ORG_FACILITY,
                                                      source_id=org_uuid, target_id=fac_uuid, relation_properties=list())
            fac_relation_request = IntersectClientMessageParams(
                destination=self.er_catalog,
                operation='EntityRelationCatalog.create_relation',
                payload=CreateRelationCommand(relation=orgfac_relation))
            self._iservice.create_external_request(request=fac_relation_request)

        sys_entity = self._system.entity
        sys_uuid = sys_entity.entity_uuid
        sys_entity_request = \
                IntersectClientMessageParams(
                    destination=self.er_catalog,
                    operation='EntityRelationCatalog.create_entity',
                    payload=CreateEntityCommand(entity=sys_entity)
                )
        self._iservice.create_external_request(request=sys_entity_request)

        if fac_name != "":
            facsys_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.FACILITY_SYSTEM,
                                                      source_id=fac_uuid, target_id=sys_uuid, relation_properties=list())
            sys_relation_request = IntersectClientMessageParams(
                destination=self.er_catalog,
                operation='EntityRelationCatalog.create_relation',
                payload=CreateRelationCommand(relation=facsys_relation))
            self._iservice.create_external_request(request=sys_relation_request)
        else:
            orgsys_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.ORG_SYSTEM,
                                                      source_id=org_uuid, target_id=sys_uuid, relation_properties=list())
            sys_relation_request = IntersectClientMessageParams(
                destination=self.er_catalog,
                operation='EntityRelationCatalog.create_relation',
                payload=CreateRelationCommand(relation=orgsys_relation))
            self._iservice.create_external_request(request=sys_relation_request)

        svc_info = self._system.services.get_service_by_name(self._service_name)
        if svc_info:
            svc_info.service_capabilities.append(self.capability_name)
        else:
            register_request = \
                IntersectClientMessageParams(
                    destination=self.system_manager,
                    operation='SystemManager.register_service',
                    payload=RegisterServiceRequest(service_name=self._service_name,
                                                    subsystem_name=self._subsys_name,
                                                   service_description=self._service_desc,
                                                   service_capabilities=[self.capability_name],
                                                   service_resources=list(),
                                                   service_labels=list(),
                                                   service_properties=list())
                )
            self._iservice.create_external_request(request=register_request)
            
            enable_request = \
                IntersectClientMessageParams(
                    destination=self.system_manager,
                    operation='SystemManager.enable_service',
                    payload=EnableServiceCommand(service_id=INTERSECT_INVALID_UUID,
                                                service_name=self._service_name,
                                                change_description="STARTUP")
                )
            self._iservice.create_external_request(request=enable_request)

            disable_request = \
                IntersectClientMessageParams(
                    destination=self.system_manager,
                    operation='SystemManager.disable_service',
                    payload=DisableServiceCommand(service_id=INTERSECT_INVALID_UUID,
                                                service_name=self._service_name,
                                                change_description="SHUTDOWN")
                )
            self._iservice.add_shutdown_messages([(disable_request, None)])

    # Private methods

    def update_capability_status(self) -> None:
        self._capability_status = f'SysInfoCatalogCapability - {self._current_status}'
    

    # Interactions

    @intersect_message()
    def create_subsystem(self, params: CreateSubsystemCommand) -> SystemInformationCatalogCapabilityResult:
        if params.subsystem_name != "":
            sys_uuid = self._system.entity.entity_uuid
            sub_name = params.subsystem_name
            sub_uuid = params.subsystem_id
            print(f"[{self.capability_name}] ++++  Creating subsystem {params.subsystem_name} with UUID={sub_uuid}")
            
            sub_entity = IntersectEntity(entity_description=params.subsystem_description,
                                         entity_name=sub_name,
                                         entity_type=SystemManagementEntityTypes.SUBSYSTEM,
                                         entity_uuid=sub_uuid,
                                         entity_labels=params.subsystem_labels,
                                         entity_properties=params.subsystem_properties)
            
            sub_info = SubsystemInformation(subsystem_entity=sub_entity,
                                            system_uuid=sys_uuid,
                                            subsystem_resources=params.subsystem_resources,
                                            subsystem_services=list())
            self._system.subsystems.add_subsystem(sub_info)

            sub_entity_request = \
                IntersectClientMessageParams(
                    destination=self.er_catalog,
                    operation='EntityRelationCatalog.create_entity',
                    payload=CreateEntityCommand(entity=sub_entity)
                )
            self._iservice.create_external_request(request=sub_entity_request)

            sub_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.SYSTEM_SUBSYS,
                                                   source_id=sys_uuid, target_id=sub_uuid,
                                                   relation_properties=list())
            sub_relation_request = \
                IntersectClientMessageParams(
                    destination=self.er_catalog,
                    operation='EntityRelationCatalog.create_relation',
                    payload=CreateRelationCommand(relation=sub_relation)
                )
            self._iservice.create_external_request(request=sub_relation_request)

            for res_uuid in params.subsystem_resources:
                res_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.SUBSYS_RESOURCE,
                                                       source_id=sub_uuid, target_id=res_uuid,
                                                       relation_properties=list())
                subres_relation_request = \
                    IntersectClientMessageParams(
                        destination=self.er_catalog,
                        operation='EntityRelationCatalog.create_relation',
                        payload=CreateRelationCommand(relation=res_relation)
                    )
                self._iservice.create_external_request(request=subres_relation_request)

            return SystemInformationCatalogCapabilityResult(success=True)
        else:
            err = "ERROR: invalid subsystem name"
            warnings.warn(err)
            return SystemInformationCatalogCapabilityResult(success=False)

    @intersect_message()
    def create_system_resource(self, params: CreateSystemResourceCommand) -> SystemInformationCatalogCapabilityResult:
        if params.resource_name != "":
            sys_uuid = self._system.entity.entity_uuid
            res_name = params.resource_name
            res_uuid = params.resource_id
            print(f"[{self.capability_name}] ++++  Creating resource {res_name} with UUID={res_uuid}")
            
            res_entity = IntersectEntity(entity_description=params.resource_description,
                                         entity_name=res_name,
                                         entity_type=SystemManagementEntityTypes.RESOURCE,
                                         entity_uuid=res_uuid,
                                         entity_labels=params.resource_labels,
                                         entity_properties=params.resource_properties)
            
            res_info = ResourceInformation(resource_entity=res_entity,
                                           system_uuid=sys_uuid)
            self._system.resources.add_resource(res_info)

            res_entity_request = \
                IntersectClientMessageParams(
                    destination=self.er_catalog,
                    operation='EntityRelationCatalog.create_entity',
                    payload=CreateEntityCommand(entity=res_entity)
                )
            self._iservice.create_external_request(request=res_entity_request)

            res_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.SYSTEM_RESOURCE,
                                                   source_id=sys_uuid, target_id=res_uuid,
                                                   relation_properties=list())
            res_relation_request = \
                IntersectClientMessageParams(
                    destination=self.er_catalog,
                    operation='EntityRelationCatalog.create_relation',
                    payload=CreateRelationCommand(relation=res_relation)
                )
            self._iservice.create_external_request(request=res_relation_request)

            return SystemInformationCatalogCapabilityResult(success=True)
        else:
            err = "ERROR: invalid resource name"
            warnings.warn(err)
            return SystemInformationCatalogCapabilityResult(success=False)

    @intersect_message()
    def create_system_service(self, params: CreateSystemServiceCommand) -> SystemInformationCatalogCapabilityResult:
        if params.service_name != "":
            sys_uuid = self._system.entity.entity_uuid
            svc_name = params.service_name
            svc_uuid = params.service_id
            sub_uuid = params.subsystem_id
            
            print(f"[{self.capability_name}] ++++  Creating service {svc_name} with UUID={svc_uuid}")
            
            svc_props = params.service_properties
            if len(params.service_capabilities) > 0:
                cap_list : str = "capabilities=" + ','.join(params.service_capabilities)
                svc_props.append(cap_list)

            svc_entity = IntersectEntity(entity_description=params.service_description,
                                         entity_name=svc_name,
                                         entity_type=SystemManagementEntityTypes.SERVICE,
                                         entity_uuid=svc_uuid,
                                         entity_labels=params.service_labels,
                                         entity_properties=svc_props)
            
            svc_info = ServiceInformation(service_entity=svc_entity,
                                          system_uuid=sys_uuid,
                                          service_capabilities=params.service_capabilities,
                                          service_resources=params.service_resources,
                                          subsystem_uuid=sub_uuid)
            self._system.services.add_service(svc_info)

            svc_entity_request = \
                IntersectClientMessageParams(
                    destination=self.er_catalog,
                    operation='EntityRelationCatalog.create_entity',
                    payload=CreateEntityCommand(entity=svc_entity)
                )
            self._iservice.create_external_request(request=svc_entity_request)

            if sub_uuid != INTERSECT_INVALID_UUID:
                svc_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.SUBSYS_SERVICE,
                                                       source_id=sub_uuid, target_id=svc_uuid,
                                                       relation_properties=list())
            else:
                svc_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.SYSTEM_SERVICE,
                                                       source_id=sys_uuid, target_id=svc_uuid,
                                                       relation_properties=list())
            svc_relation_request = \
                IntersectClientMessageParams(
                    destination=self.er_catalog,
                    operation='EntityRelationCatalog.create_relation',
                    payload=CreateRelationCommand(relation=svc_relation)
                )
            self._iservice.create_external_request(request=svc_relation_request)

            for res_uuid in params.service_resources:
                res_relation = IntersectEntityRelation(relation_name=SystemManagementEntityRelationTypes.SERVICE_RESOURCE,
                                                       source_id=svc_uuid, target_id=res_uuid,
                                                       relation_properties=list())
                svcres_relation_request = \
                    IntersectClientMessageParams(
                        destination=self.er_catalog,
                        operation='EntityRelationCatalog.create_relation',
                        payload=CreateRelationCommand(relation=res_relation)
                    )
                self._iservice.create_external_request(request=svcres_relation_request)

            return SystemInformationCatalogCapabilityResult(success=True)
        else:
            err = "ERROR: invalid service name"
            warnings.warn(err)
            return SystemInformationCatalogCapabilityResult(success=False)


if __name__ == '__main__':
    print("This is a service implementation module. It is not meant to be executed.")

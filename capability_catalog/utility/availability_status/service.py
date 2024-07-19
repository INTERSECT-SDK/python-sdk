from datetime import datetime, timezone
from typing import Generic

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectService,
    intersect_message,
    intersect_status
)

from capability_catalog.utility.availability_status.types import (
    AvailabilityStatus,
    AvailabilityStatusEnum,
    AvailabilityStatusResult,
    SetAvailabilityStatusCommand
)

class AvailabilityStatusCapability(IntersectBaseCapabilityImplementation):
    """ A prototype implementation of the INTERSECT 'Availability Status' microservice capability """

    def __init__(self, service_hierarchy : HierarchyConfig) -> None:
        super().__init__()
        self.capability_name = "AvailabilityStatus"

        # Private Data
        self._service_name    : str = service_hierarchy.service
        self._system_name     : str = service_hierarchy.system
        self._subsys_name     : str = "infrastructure-management"
        self._org_name        : str = service_hierarchy.organization
        self._facility_name   : str = service_hierarchy.facility

        self._iservice : IntersectService = None

        self._current_status : str = AvailabilityStatusEnum.UNKNOWN
        self._prior_status   : str = AvailabilityStatusEnum.UNKNOWN
        self._last_update_description : str = ""
        self._last_update_time : datetime = datetime.now(timezone.utc)

    def get_capability_status(self) -> AvailabilityStatus:
        return self._get_availability_status()
    
    def update_capability_status(self) -> None:
        self._update_status()

    def startup(self, svc : IntersectService) -> None:
        self._iservice = svc

    @intersect_status()
    def status(self) -> AvailabilityStatus:
        self._update_status()
        status = self._get_availability_status()
        print("DEBUG: @intersect_status\n", status.status_description)
        return status

    @intersect_message()
    def get_availability_status(self) -> AvailabilityStatus:
        return self._get_availability_status()

    @intersect_message()
    def set_availability_status(self, params: SetAvailabilityStatusCommand) -> AvailabilityStatusResult:
        self._set_availability_status(params.new_status, params.status_description)
        return AvailabilityStatusResult(success=True)

    def _update_status(self) -> None:
        if self._iservice:
            self._last_update_time = datetime.now(timezone.utc)
            aggregate_status_desc : str = ""
            for capability in self._iservice.capabilities:
                cap_name = capability.capability_name
                if cap_name != self.capability_name:
                    cap_status_fn = getattr(capability, "get_capability_status", None)
                    if cap_status_fn:
                        cap_status : AvailabilityStatus = cap_status_fn()
                        if cap_status:
                            curr_status = cap_status.current_status
                            prev_status = cap_status.previous_status
                            status_time = cap_status.status_change_time
                            status_desc = cap_status.status_description
                            aggregate_status_desc += f'[{cap_name}] @ {status_time} - {curr_status} (previously {prev_status})\n{status_desc}\n'
            self._last_update_description = aggregate_status_desc

    def _get_availability_status(self) -> AvailabilityStatus:
        curr_status = AvailabilityStatus(current_status=self._current_status,
                                         previous_status=self._prior_status,
                                         status_description=self._last_update_description,
                                         status_change_time=self._last_update_time)
        return curr_status
    
    def _set_availability_status(self,
                                 new_status : str,
                                 description : str) -> None:
        # update state
        utcnow = datetime.now(timezone.utc)
        self._prior_status = self._current_status
        self._current_status = new_status
        if description is not None:
            self._last_update_description = description
        self._last_update_time = utcnow

if __name__ == '__main__':
    print("This is a service implementation module. It is not meant to be executed.")

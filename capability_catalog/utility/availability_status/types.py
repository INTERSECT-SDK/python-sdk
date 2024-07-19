from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from capability_catalog.capability_types import IntersectTimeStamp

class AvailabilityStatusEnum(StrEnum):
    AVAILABLE = "SERVICE_FULLY_AVAILABLE"
    DEGRADED = "SERVICE_DEGRADED"
    UNAVAILABLE = "SERVICE_UNAVAILABLE"
    UNKNOWN = "SERVICE_AVAILABILITY_UNKNOWN"

@dataclass
class AvailabilityStatus:
    current_status : str = ""
    previous_status : str = ""
    status_description : str = ""
    status_change_time : IntersectTimeStamp = datetime.now(timezone.utc)

@dataclass
class SetAvailabilityStatusCommand:
    new_status : str = ""
    status_description : str = ""

@dataclass
class AvailabilityStatusResult:
    success : bool
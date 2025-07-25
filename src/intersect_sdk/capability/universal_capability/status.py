"""Definitions supporting the 'core status' functionality of the core capability."""

from __future__ import annotations

import datetime  # noqa: TC003
from typing import Annotated

from pydantic import BaseModel, Field


class IntersectCoreStatus(BaseModel):
    """Core status information about the INTERSECT-SDK Service as a whole."""

    uptime: datetime.timedelta
    logical_cpus: Annotated[int, Field(title='Logical CPUs')]
    physical_cpus: Annotated[int, Field(title='Physical CPUs')]
    cpu_percentages: Annotated[list[float], Field(title='CPU Percentages')]
    service_cpu_percentage: Annotated[float, Field(title='Service CPU Usage Percentage')]
    """CPU usage of the INTERSECT-SDK Service, does not apply to subprocesses"""
    memory_total: int
    memory_usage_percentage: float
    service_memory_percentage: Annotated[float, Field(title='Service Memory Usage Percentage')]
    """Memory usage of the INTERSECT-SDK Service, does not apply to subprocesses"""
    disk_total: int
    disk_usage_percentage: float

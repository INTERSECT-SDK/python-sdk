"""This is a universal capability which should provide common functionality for ALL Services.

A Client should be able to reliably set the operation of a request to point to this function, regardless of the Service they want to talk to.

NOTE: While users should generally not need to ever import this class directly, it SHOULD remain stable. Therefore, it does NOT belong in `_internal`, which does not have a stability guarantee.
"""

import datetime
import os
import time
from typing import Dict, final

import psutil

from ...service_definitions import intersect_message, intersect_status
from ..._internal.encryption.models import IntersectEncryptionPublicKey  
from ..base import IntersectBaseCapabilityImplementation
from .status import IntersectCoreStatus


@final
class IntersectSdkCoreCapability(IntersectBaseCapabilityImplementation):
    """Core capability present in every INTERSECT Service.

    This may be called explicitly by any Client interacting with any SDK service. Set the operation to be "intersect_sdk.<ENDPOINT>".
    """

    intersect_sdk_capability_name = 'intersect_sdk'
    """We always reserve the 'intersect_sdk' capability name for this core capability.

    Importantly, this capability must always be inserted first when generating the schema and the function mapping. Since the schema generator will check for duplicate names, any attempt
    by a user to call their capability 'intersect_sdk' will always fail.
    """

    def __init__(self) -> None:  # noqa: D107
        super().__init__()
        self.process = psutil.Process(os.getpid())
        """psutil.Process caches most functions it calls after it calls the function once, so just save the object itself"""


    @intersect_status
    def system_capability(self) -> IntersectCoreStatus:
        """The status of this Capability reflects core system information which is okay to broadcast across the INTERSECT-SDK system.

        As the INTERSECT status function, this function is called periodically, but we also want to allow calls to it explicitly.
        """
        mem_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        # TODO we should provide an option to list GPU information available (we could check out the GPUtil library, but there may be better approaches)
        return IntersectCoreStatus(
            uptime=datetime.timedelta(seconds=time.time() - self.process.create_time()),
            logical_cpus=psutil.cpu_count() or 0,
            physical_cpus=psutil.cpu_count(logical=False) or 0,
            # do not block the thread when checking CPU percentages
            cpu_percentages=psutil.cpu_percent(interval=0.0, percpu=True),
            service_cpu_percentage=self.process.cpu_percent(interval=0.0),
            memory_total=mem_info.total,
            memory_usage_percentage=mem_info.percent,
            service_memory_percentage=self.process.memory_percent(),
            disk_total=disk_info.total,
            disk_usage_percentage=disk_info.percent,
        )
    
    @intersect_message()
    def get_public_key(self) -> Dict[str, str]:
        """Returns the public key for clients / services to use for encryption"""
        return IntersectEncryptionPublicKey(public_key=self._public_key_pem)


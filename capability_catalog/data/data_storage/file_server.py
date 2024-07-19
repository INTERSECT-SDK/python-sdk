import logging

from os import getenv

from intersect_sdk import (
    HierarchyConfig,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop
)

from capability_catalog.utility.availability_status.service import AvailabilityStatusCapability
from capability_catalog.data.data_storage.file_service import FileDataStorageCapability

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    from_config_file = {
        'data_stores': {
            'minio': [
                {
                    'username': 'AKIAIOSFODNN7EXAMPLE',
                    'password': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                    'port': 9000,
                },
            ],
        },
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
            },
        ],
    }

    my_org_name : str = getenv("INTERSECT_ORGANIZATION_NAME", "test-org")
    my_fac_name : str = getenv("INTERSECT_FACILITY_NAME", "test-facility")
    my_sys_name : str = getenv("INTERSECT_SYSTEM_NAME", "test-system")
    my_sys_desc : str = getenv("INTERSECT_SYSTEM_DESCRIPTION", "A mock system for testing")
    my_sub_name : str = getenv("INTERSECT_SUBSYSTEM_NAME", "test-subsys") 
    my_svc_name : str = getenv("INTERSECT_SERVICE_NAME", "test-service")
    my_svc_desc : str = getenv("INTERSECT_SERVICE_DESCRIPTION", "A mock service for testing")
    
    config = IntersectServiceConfig(
        hierarchy=HierarchyConfig(
            organization=my_org_name,
            facility=my_fac_name,
            system=my_sys_name,
            subsystem=my_sub_name,
            service=my_svc_name,
        ),
        schema_version='0.0.1',
        status_interval=30.0,
        **from_config_file,
    )

    avail_status_capability = AvailabilityStatusCapability(service_hierarchy=config.hierarchy)
    data_store_capability = FileDataStorageCapability(service_hierarchy=config.hierarchy)
    all_caps = [avail_status_capability, data_store_capability]
    service = IntersectService(all_caps, config)

    logger.info('Starting service, use Ctrl+C to exit.')
    default_intersect_lifecycle_loop(service)

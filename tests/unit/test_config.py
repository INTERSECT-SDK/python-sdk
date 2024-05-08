import pytest
from intersect_sdk import (
    ControlPlaneConfig,
    DataStoreConfig,
    DataStoreConfigMap,
    HierarchyConfig,
    IntersectClientCallback,
    IntersectClientConfig,
    IntersectServiceConfig,
)
from pydantic import TypeAdapter, ValidationError

# TESTS #####################


def test_empty_hierarchy():
    with pytest.raises(ValidationError) as ex:
        HierarchyConfig()
    errors = ex.value.errors()
    assert len(errors) == 4
    assert all(e['type'] == 'missing' for e in errors)
    locations = [e['loc'] for e in errors]
    assert ('organization',) in locations
    assert ('facility',) in locations
    assert ('system',) in locations
    assert ('service',) in locations


def test_invalid_hierarchy():
    with pytest.raises(ValidationError) as ex:
        HierarchyConfig(
            organization='no.periods',
            facility='no_underscores',
            system='',
            subsystem='no/slashes',
            service='a',
        )
    errors = ex.value.errors()
    assert len(errors) == 5
    assert all(e['type'] == 'string_pattern_mismatch' for e in errors)
    locations = [e['loc'] for e in errors]
    assert ('organization',) in locations
    assert ('facility',) in locations
    assert ('system',) in locations
    assert ('subsystem',) in locations
    assert ('service',) in locations


# NOTE: with dataclasses, need to validate dictionaries instead of the dataclass directly


def test_missing_control_plane_config():
    with pytest.raises(ValidationError) as ex:
        TypeAdapter(ControlPlaneConfig).validate_python({})
    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 3
    assert {'type': 'missing', 'loc': ('username',)} in errors
    assert {'type': 'missing', 'loc': ('password',)} in errors
    assert {'type': 'missing', 'loc': ('protocol',)} in errors


def test_invalid_control_plane_config():
    with pytest.raises(ValidationError) as ex:
        TypeAdapter(ControlPlaneConfig).validate_python(
            ControlPlaneConfig(
                host='',
                username='',
                password='',
                port=0,
                protocol='mqtt',
            ).__dict__
        )
    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 5
    assert {'type': 'string_too_short', 'loc': ('username',)} in errors
    assert {'type': 'string_too_short', 'loc': ('password',)} in errors
    assert {'type': 'string_too_short', 'loc': ('host',)} in errors
    assert {'type': 'greater_than', 'loc': ('port',)} in errors
    assert {'type': 'literal_error', 'loc': ('protocol',)} in errors


def test_missing_data_plane_config():
    with pytest.raises(ValidationError) as ex:
        TypeAdapter(DataStoreConfig).validate_python({})
    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 2
    assert {'type': 'missing', 'loc': ('username',)} in errors
    assert {'type': 'missing', 'loc': ('password',)} in errors


def test_invalid_data_plane_config():
    with pytest.raises(ValidationError) as ex:
        TypeAdapter(DataStoreConfig).validate_python(
            DataStoreConfig(
                host='',
                username='',
                password='',
                port=0,
            ).__dict__
        )
    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 4
    assert {'type': 'string_too_short', 'loc': ('username',)} in errors
    assert {'type': 'string_too_short', 'loc': ('password',)} in errors
    assert {'type': 'string_too_short', 'loc': ('host',)} in errors
    assert {'type': 'greater_than', 'loc': ('port',)} in errors


def test_missing_client_config():
    with pytest.raises(ValidationError) as ex:
        IntersectClientConfig()
    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 2
    assert {'type': 'missing', 'loc': ('brokers',)} in errors
    assert {'type': 'missing', 'loc': ('initial_message_event_config',)} in errors


def test_empty_client_config():
    with pytest.raises(ValidationError) as ex:
        IntersectClientConfig(brokers=[], initial_message_event_config=IntersectClientCallback())
    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 2
    assert {'loc': ('brokers', 'list[ControlPlaneConfig]'), 'type': 'too_short'}
    assert {'loc': ('brokers', "literal['discovery']"), 'type': 'literal_error'} in errors


def test_missing_service_config():
    with pytest.raises(ValidationError) as ex:
        IntersectServiceConfig()
    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 2
    assert {'type': 'missing', 'loc': ('brokers',)} in errors
    assert {'type': 'missing', 'loc': ('hierarchy',)} in errors


def test_invalid_service_config():
    with pytest.raises(ValidationError) as ex:
        IntersectServiceConfig(
            hierarchy=100,
            brokers=[],
            data_stores={},
            status_interval=1,
        )
    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 4
    assert {'loc': ('hierarchy',), 'type': 'model_type'} in errors
    assert {'loc': ('brokers', 'list[ControlPlaneConfig]'), 'type': 'too_short'} in errors
    assert {'loc': ('brokers', "literal['discovery']"), 'type': 'literal_error'} in errors
    assert {'loc': ('status_interval',), 'type': 'greater_than_equal'} in errors


# VALIDS ################


def test_valid_service_config():
    config = IntersectServiceConfig(
        hierarchy=HierarchyConfig(
            service='serv',
            system='ello-14',
            facility='this-works',
            organization='org',
        ),
        brokers=[
            ControlPlaneConfig(
                username='user',
                password='secret',
                host='http://hardknock.life',
                port='1883',
                protocol='mqtt3.1.1',
            ),
            ControlPlaneConfig(
                username='fine',
                password='fine',
                host='www.nowhere.gov',
                port='5672',
                protocol='amqp0.9.1',
            ),
        ],
        data_stores=DataStoreConfigMap(
            minio=[
                DataStoreConfig(username='idc', password='idc', host='idc', port='6'),
                DataStoreConfig(
                    username='idc', password='idc', host='somewhereelse.com', port='9999'
                ),
            ]
        ),
        status_interval=500.5,
    )
    assert config.hierarchy.subsystem is None
    assert config.hierarchy.hierarchy_string('/') == 'org/this-works/ello-14/-/serv'
    # make sure string values can be coerced into integers when specified
    assert all(isinstance(b.port, int) for b in config.brokers)
    assert all(isinstance(d.port, int) for d in config.data_stores.minio)

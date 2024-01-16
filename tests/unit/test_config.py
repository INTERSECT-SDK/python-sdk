from pathlib import Path
from typing import List

from intersect_sdk import IntersectConfigParseException, load_config_from_file

# HELPERS ################


def get_fixture_path(fixture):
    return Path(__file__).absolute().parents[1] / 'fixtures' / fixture


def get_property_errors(errlines: List[str]) -> List[str]:
    """
    returns all of the Pydantic property errors (i.e. hierarchy.service, broker.username, ...)
    """
    return list(filter(lambda y: not y.startswith(' '), errlines))[1:]


def get_schema_errors(errlines: List[str]) -> List[str]:
    """
    schema errors will always have the same space indentations
    and start with "$."
    """
    return [x.strip().split(' ')[0] for x in filter(lambda y: y.strip().startswith('$.'), errlines)]


# TESTS #####################


def test_load_config_from_aether():
    try:
        load_config_from_file('idonotexist.json')
        raise AssertionError
    except IntersectConfigParseException as ex:
        assert ex.returnCode == 66


def test_load_bad_file():
    try:
        load_config_from_file(__file__)
        raise AssertionError
    except IntersectConfigParseException as ex:
        assert ex.returnCode == 66


def test_valid_config():
    config = load_config_from_file(get_fixture_path('test-config-valid.toml'))
    assert config.id_counter_init == 125
    assert config.hierarchy.organization == 'organization'


def test_invalid_config():
    try:
        load_config_from_file(get_fixture_path('test-config-invalid.yaml'))
        raise AssertionError
    except IntersectConfigParseException as ex:
        assert ex.returnCode == 65
        lines = ex.message.splitlines()
        assert '9 validation errors' in lines[0]
        property_errors = get_property_errors(lines)
        for property_err in [
            'hierarchy.service',
            'hierarchy.subsystem',
            'hierarchy.system',
            'hierarchy.facility',
            'broker.username',
            'broker.password',
            'broker.port',
            'id_counter_init',
            'argument_schema',
        ]:
            assert property_err in property_errors
        schema_errors = get_schema_errors(lines)
        assert len(schema_errors) == 3
        assert '$.properties' in schema_errors
        assert '$.type' in schema_errors
        assert '$.description' in schema_errors


def test_invalid_config_2():
    try:
        load_config_from_file(get_fixture_path('test-config-invalid-nested-schema.toml'))
        raise AssertionError
    except IntersectConfigParseException as ex:
        assert ex.returnCode == 65
        lines = ex.message.splitlines()
        assert '9 validation errors' in lines[0]
        property_errors = get_property_errors(lines)
        for property_err in [
            'hierarchy.service',
            'hierarchy.subsystem',
            'hierarchy.system',
            'hierarchy.facility',
            'broker.username',
            'broker.password',
            'broker.port',
            'id_counter_init',
            'argument_schema',
        ]:
            assert property_err in property_errors
        schema_errors = get_schema_errors(lines)
        assert len(schema_errors) == 3
        assert '$.properties.weapon.type' in schema_errors
        assert '$.properties.weapon.minLength' in schema_errors
        assert '$.properties.weapon.title' in schema_errors


def test_incomplete_config():
    FIXTURE = get_fixture_path('test-config-incomplete.json')

    # broker creds are missing from file, first naively load
    try:
        load_config_from_file(FIXTURE)
        raise AssertionError
    except IntersectConfigParseException as ex:
        assert ex.returnCode == 65
        lines = ex.message.splitlines()
        assert '2 validation errors' in lines[0]

    # now try running with the callback, this should complete all required fields
    # (this callback gives users a lot of control over how to determine variables programmatically)
    def _add_broker_creds_callback(struct):
        struct['broker']['username'] = 'user'
        struct['broker']['password'] = 'password'

    config = load_config_from_file(FIXTURE, _add_broker_creds_callback)
    assert config.broker.username == 'user'
    assert config.broker.password == 'password'

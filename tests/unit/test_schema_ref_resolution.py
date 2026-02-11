import json
from collections.abc import Iterable
from pathlib import Path

from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012

from intersect_sdk.schema import get_schema_from_capability_implementations
from tests.fixtures.example_schema import FAKE_HIERARCHY_CONFIG, DummyCapabilityImplementation


def get_fixture_path(fixture: str) -> Path:
    return Path(__file__).absolute().parents[1] / 'fixtures' / fixture


def iter_ref_values(schema: object) -> Iterable[str]:
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key == '$ref' and isinstance(value, str):
                yield value
            else:
                yield from iter_ref_values(value)
    elif isinstance(schema, list):
        for item in schema:
            yield from iter_ref_values(item)


def assert_refs_resolve(schema: dict) -> None:
    resource = Resource.from_contents(schema, default_specification=DRAFT202012)
    base_uri = ''
    resolver = Registry().with_resource(base_uri, resource).resolver(base_uri)
    unresolved: list[str] = []
    for ref in iter_ref_values(schema):
        try:
            resolver.lookup(ref)
        except Unresolvable:
            unresolved.append(ref)
    assert not unresolved, f'Unresolved $ref entries: {sorted(set(unresolved))}'


def test_fixture_schema_refs_resolve() -> None:
    """Verifies that the generated JSON schema contains valid $ref entries."""
    with Path.open(get_fixture_path('example_schema.json'), 'rb') as f:
        schema = json.load(f)
    assert_refs_resolve(schema)


def test_generated_schema_refs_resolve() -> None:
    """Assert that the INTERSECT-SDK can generate a schema with valid $ref entries."""
    schema = get_schema_from_capability_implementations(
        [DummyCapabilityImplementation],
        FAKE_HIERARCHY_CONFIG,
    )
    assert_refs_resolve(schema)

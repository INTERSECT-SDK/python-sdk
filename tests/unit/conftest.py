import weakref

import pytest

from intersect_sdk import Adapter, BrokerConfig, HierarchyConfig, IntersectConfig
from intersect_sdk.base import Service
from intersect_sdk.client import Channel, Client


@pytest.fixture(name="mock_config")
def _fixture_config():
    return IntersectConfig(
        broker=BrokerConfig(address="bar", port=8888, username="joe", password="changeme"),
        hierarchy=HierarchyConfig(
            service="foo",
            subsystem="Example Client Subsystem",
            system="Example Client System",
            facility="Example Facility",
            organization="Oak Ridge National Laboratory",
        ),
        argument_schema={
            "title": "Name",
            "description": (
                "Schema representation of a name split into 3 parts. This is considered bad design,"
                " and you should have only a single field for the full name"
            ),
            "type": "object",
            "required": ["firstName", "lastName"],
            "properties": {
                "firstName": {
                    "type": "string",
                    "title": "First Name",
                    "default": "Chuck",
                },
                "lastName": {
                    "type": "string",
                    "title": "Last Name",
                    "default": "Norris",
                },
                "middleInitial": {
                    "type": "string",
                    "title": "Middle initial",
                    "minLength": 1,
                    "maxLength": 1,
                },
            },
        },
    )


@pytest.fixture(name="mock_service")
def _fixture_service(mock_config, monkeypatch):
    monkeypatch.setattr(Client, "connect", lambda cls, host_tuple, username, password: "")

    return Service(mock_config)


@pytest.fixture(name="mock_adapter")
def _fixture_adapter(mock_config, monkeypatch):
    # Mock out the methods / objects that require external service (i.e. message broker)
    monkeypatch.setattr(weakref, "finalize", lambda cls, stop_status_func, weak_self: lambda: "")
    monkeypatch.setattr(Channel, "subscribe", lambda cls, receive_action: "")
    monkeypatch.setattr(Channel, "publish", lambda cls, receive_action: "")
    monkeypatch.setattr(Client, "connect", lambda cls, host_tuple, username, password: "")

    return Adapter(mock_config)

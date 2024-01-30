"""TODO: This is all old code we currently aren't using."""

from __future__ import annotations

import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def discover_broker(address: str, broker_endpoint: str) -> tuple[str, str, int]:
    """Get the metadata for a broker from the discovery service.

    Args:
        address: A string containing the address for the discovery service.
        broker_endpoint: specific API for broker
    Returns:
        Three strings. The first is the name of the broker type (as used in
        _create_broker_client()), the second is the broker's address, and
        the third is the broker's port number.
    """
    url = f'{address}/v0.1/{broker_endpoint}'

    # Get scheme associated with the `url` string
    scheme = urlparse(url).scheme

    # Only accept `http` and `https` schemes, otherwise raise error
    if scheme not in ('http', 'https'):
        msg = f'URL scheme is {scheme}, only http or https schemes are accepted'
        raise ValueError(msg)

    request = Request(url)  # noqa: S310 (scheme checked earlier)
    with urlopen(request) as response:  # noqa: S310 (scheme checked earlier)
        body = response.read()

    broker_info = json.loads(body.decode('utf-8'))
    endpoint = broker_info['endpoint']
    backend_name = broker_info['backendName']
    address, port = endpoint.split(':', 1)

    return backend_name, address, port

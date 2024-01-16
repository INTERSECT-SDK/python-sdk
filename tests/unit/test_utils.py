import json
from datetime import datetime

import pytest
from intersect_sdk.utils import get_utc, identifier, parse_message_arguments


def test_parse_message_arguments():
    args = {'foo': 'bar'}

    output = parse_message_arguments(json.dumps(args), load=False)
    assert args == output

    # TODO: eventually, this would pull remote data loading
    output = parse_message_arguments(json.dumps(args), load=True)
    assert args == output

    with pytest.raises(TypeError):
        parse_message_arguments(args)

    with pytest.raises(TypeError):
        parse_message_arguments({})


def test_identifier():
    id_generator = identifier('system')
    for idx in range(5):
        assert next(id_generator) == f'system{idx}'


def test_utcdatetime():
    utc = datetime.utcnow().isoformat() + 'Z'
    utc_common = get_utc()
    assert utc[:-11] == utc_common[:-11]

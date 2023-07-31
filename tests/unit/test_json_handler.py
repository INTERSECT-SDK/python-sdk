from google.protobuf import json_format as pb_json

from intersect_sdk.messages import JsonHandler
from intersect_sdk.messages import demo_pb2 as demo

test_request = demo.Request()
test_request.arguments = "a"

test_generic = demo.Generic()
test_generic.type = demo.Generic.Type.Value("REQUEST")
test_generic.message = pb_json.MessageToJson(test_request)
test_generic.length = len(test_generic.message)
test_generic_json = pb_json.MessageToJson(test_generic)

test_bad_generic = demo.Generic()
test_bad_generic.type = -1
test_bad_generic_json = pb_json.MessageToJson(test_bad_generic)


def test_serialize():
    json_handler = JsonHandler()
    serialized = json_handler.serialize(test_request)
    assert isinstance(serialized, str)
    sample_generic = pb_json.Parse(serialized, demo.Generic())
    assert sample_generic.type == demo.Generic.Type.REQUEST
    assert isinstance(sample_generic.message, str)
    sample_message_body = pb_json.Parse(sample_generic.message, demo.Request())
    assert sample_message_body == test_request

    try:
        json_handler.serialize(test_generic)
        raise AssertionError()
    except TypeError:
        assert True


def test_deserialize():
    json_handler = JsonHandler()
    deserialized = json_handler.deserialize(test_generic_json)
    assert isinstance(deserialized, demo.Request)
    assert deserialized.arguments == "a"

    try:
        json_handler.deserialize(test_bad_generic_json)
        raise AssertionError()
    except TypeError:
        assert True

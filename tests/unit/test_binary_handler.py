from intersect_sdk.messages import BinaryHandler
from intersect_sdk.messages import demo_pb2 as demo

test_request = demo.Request()
test_request.arguments = "a"

test_generic = demo.Generic()
test_generic.type = demo.Generic.Type.Value("REQUEST")
test_generic.message = test_request.SerializeToString()
test_generic.length = len(test_generic.message)
test_generic_bytes = test_generic.SerializeToString()

test_bad_generic = demo.Generic()
test_bad_generic.type = -1
test_bad_generic_bytes = test_bad_generic.SerializeToString()


def test_serialize():
    binary_handler = BinaryHandler()
    serialized = binary_handler.serialize(test_request)
    assert isinstance(serialized, bytes)
    sample_generic = demo.Generic()
    sample_generic.ParseFromString(serialized)
    assert sample_generic.type == demo.Generic.Type.REQUEST
    assert isinstance(sample_generic.message, str)
    sample_message_body = demo.Request()
    sample_message_body.ParseFromString(sample_generic.message.encode())
    assert sample_message_body == test_request

    try:
        binary_handler.serialize(test_generic)
        raise AssertionError()
    except TypeError:
        assert True


def test_deserialize():
    binary_handler = BinaryHandler()
    deserialized = binary_handler.deserialize(test_generic_bytes)
    assert isinstance(deserialized, demo.Request)
    assert deserialized.arguments == "a"

    try:
        binary_handler.deserialize(test_bad_generic_bytes)
        raise AssertionError()
    except TypeError:
        assert True

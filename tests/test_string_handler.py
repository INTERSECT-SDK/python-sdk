from google.protobuf import text_format as pb_text

from intersect.messages import StringHandler
from intersect.messages import demo_pb2 as demo

test_request = demo.Request()
test_request.arguments = "a"

test_generic = demo.Generic()
test_generic.type = demo.Generic.Type.Value("REQUEST")
test_generic.message = pb_text.MessageToString(test_request)
test_generic.length = len(test_generic.message)
test_generic_str = pb_text.MessageToString(test_generic)

test_bad_generic = demo.Generic()
test_bad_generic.type = -1
test_bad_generic_str = pb_text.MessageToString(test_bad_generic)


def test_serialize():
    str_handler = StringHandler()
    serialized = str_handler.serialize(test_request)
    assert isinstance(serialized, str)
    sample_generic = pb_text.Parse(serialized, demo.Generic())
    assert sample_generic.type == demo.Generic.Type.REQUEST
    assert isinstance(sample_generic.message, str)
    sample_message_body = pb_text.Parse(sample_generic.message, demo.Request())
    assert sample_message_body == test_request

    try:
        str_handler.serialize(test_generic)
        assert False
    except TypeError:
        assert True


def test_deserialize():
    str_handler = StringHandler()
    deserialized = str_handler.deserialize(test_generic_str)
    assert isinstance(deserialized, demo.Request)
    assert deserialized.arguments == "a"

    try:
        str_handler.deserialize(test_bad_generic_str)
        assert False
    except TypeError:
        assert True

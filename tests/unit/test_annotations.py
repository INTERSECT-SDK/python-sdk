import pytest
from intersect_sdk import intersect_message
from pydantic import ValidationError


# this should immediately fail when trying to define the class itself
# don't even need to create an object for it
def test_invalid_annotation_params():
    with pytest.raises(ValidationError) as ex:

        class BadAnnotationArgs:
            @intersect_message(
                request_content_type=0,
                response_content_type=0,
                response_data_transfer_handler='MESSAGE',
                strict_request_validation='red',
            )
            def bad_annotations(self, param: bool) -> bool:
                ...

    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 4
    assert {'type': 'enum', 'loc': ('request_content_type',)} in errors
    assert {'type': 'int_parsing', 'loc': ('response_data_transfer_handler',)} in errors
    assert {'type': 'enum', 'loc': ('response_content_type',)} in errors
    assert {'type': 'bool_parsing', 'loc': ('strict_request_validation',)} in errors

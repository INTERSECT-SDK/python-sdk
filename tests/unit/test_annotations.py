import pytest
from intersect_sdk import (
    IntersectBaseCapabilityImplementation,
    IntersectEventDefinition,
    intersect_event,
    intersect_message,
    intersect_status,
)
from pydantic import ValidationError


# this should immediately fail when trying to define the class itself
# don't even need to create an object for it
def test_invalid_annotation_params():
    with pytest.raises(ValidationError) as ex:

        class BadAnnotationArgs(IntersectBaseCapabilityImplementation):
            @intersect_message(
                request_content_type=0,
                response_content_type=0,
                response_data_transfer_handler='MESSAGE',
                strict_request_validation='red',
            )
            def bad_annotations(self, param: bool) -> bool: ...

    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 4
    assert {'type': 'enum', 'loc': ('request_content_type',)} in errors
    assert {'type': 'enum', 'loc': ('response_data_transfer_handler',)} in errors
    assert {'type': 'enum', 'loc': ('response_content_type',)} in errors
    assert {'type': 'bool_parsing', 'loc': ('strict_request_validation',)} in errors


def test_incorrect_intersect_event_annotations():
    with pytest.raises(ValidationError) as ex:

        class BadEventArgs(IntersectBaseCapabilityImplementation):
            @intersect_event()
            def some_func(self) -> bool: ...

    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 1
    assert {'type': 'missing_keyword_only_argument', 'loc': ('events',)} in errors

    with pytest.raises(ValidationError) as ex:

        class BadEventArgs2(IntersectBaseCapabilityImplementation):
            @intersect_event(events={})
            def some_func(self) -> bool: ...

    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 1
    assert {'type': 'too_short', 'loc': ('events',)} in errors

    with pytest.raises(ValidationError) as ex:

        class BadEventArgs3(IntersectBaseCapabilityImplementation):
            @intersect_event(events={'one': IntersectEventDefinition()})
            def some_func(self) -> bool: ...

    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 1
    assert {'type': 'missing', 'loc': ('event_type',)} in errors

    # special case: we have a custom vaildator for event_type which fails on some common instantiations
    with pytest.raises(ValidationError) as ex:

        class BadEventArgs4(IntersectBaseCapabilityImplementation):
            @intersect_event(
                events={
                    'one': IntersectEventDefinition(
                        event_type=5, content_type=0, data_handler='test'
                    )
                }
            )
            def some_func(self) -> bool: ...

    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 3
    assert {'type': 'value_error', 'loc': ('event_type',)} in errors
    assert {'type': 'enum', 'loc': ('content_type',)} in errors
    assert {'type': 'enum', 'loc': ('data_handler',)} in errors

    # make sure that improper use of model_construct() will not pass inner validation (users are free to use it as long as they construct a valid model)
    with pytest.raises(ValidationError) as ex:

        class BadEventArgs5(IntersectBaseCapabilityImplementation):
            @intersect_event(
                events={
                    'one': IntersectEventDefinition.model_construct(
                        data_handler='no', content_type='no'
                    )
                }
            )
            def some_func(self) -> bool: ...

    errors = [{'type': e['type'], 'loc': e['loc']} for e in ex.value.errors()]
    assert len(errors) == 3
    assert {
        'type': 'enum',
        'loc': (
            'events',
            'one',
            'content_type',
        ),
    } in errors
    assert {
        'type': 'enum',
        'loc': (
            'events',
            'one',
            'data_handler',
        ),
    } in errors
    assert {
        'type': 'missing',
        'loc': (
            'events',
            'one',
            'event_type',
        ),
    } in errors


# only tests @classmethod applied first, schema_invalids tests @classmethod applied last
def test_classmethod_rejected(caplog: pytest.LogCaptureFixture):
    with pytest.raises(TypeError) as ex:

        class ClassMethod1(IntersectBaseCapabilityImplementation):
            @intersect_message()
            @classmethod
            def bad_annotations(cls, param: bool) -> bool: ...

    assert 'The `@classmethod` decorator cannot be used with `@intersect_message()`' in str(ex)

    with pytest.raises(TypeError) as ex2:

        class ClassMethod2(IntersectBaseCapabilityImplementation):
            @intersect_status()
            @classmethod
            def bad_annotations(cls, param: bool) -> bool: ...

    assert 'The `@classmethod` decorator cannot be used with `@intersect_status()`' in str(ex2)


def test_staticmethod_invalids():
    with pytest.raises(TypeError) as ex:

        class Test1(IntersectBaseCapabilityImplementation):
            @intersect_message()
            @staticmethod
            def bad_annotations(param: bool) -> bool: ...

    assert 'The `@staticmethod` decorator should be applied after `@intersect_message`' in str(ex)

    with pytest.raises(TypeError) as ex2:

        class Test2(IntersectBaseCapabilityImplementation):
            @intersect_status()
            @staticmethod
            def bad_annotations(param: bool) -> bool: ...

    assert 'The `@staticmethod` decorator should be applied after `@intersect_status`' in str(ex2)

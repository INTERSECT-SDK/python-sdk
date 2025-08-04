# Submission Rules

There are a few rules we have for submitting examples to IntersectSDK.

## File naming convention

The client file should match the format `<EXAMPLE>_client.py` , where `<EXAMPLE>` roughly corresponds to the name of the example.

The service files should all match the format `<PURPOSE>_service.py`, where `<PURPOSE>` roughly corresponds to the name of the example and, if multiple services, what the service does.

Modules are allowed but should be contained within the example directory. Any module file with shared imports should not end with `_client.py` or `_service.py` .

## Schemas for services

All example services should have an associated schema file (.json) in the repository. Here are a few ways we can
generate the schema for the HelloWorld Service:

1) Write your own script which uses `get_schema_from_capability_implementations` from the INTERSECT-SDK, which returns a dictionary. You'll need to provide this function your CapabilityImplementation class, your HierarchyConfig, and your application version. You can then dump the dictionary to JSON (please use `indent=2` as an argument).

```python
# imports condensed for readability
import json
from ...sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    intersect_message,
    intersect_status,
    get_schema_from_capability_implementations,
)

# copy the CapabilityImplementation EXACTLY as-is. Note that docstrings will be added to the schema!
class HelloServiceCapabilityImplementation(IntersectBaseCapabilityImplementation):
    """
    Rudimentary capability implementation example.

    All capability implementations are required to have an @intersect_status decorated function,
    but we do not use it here.

    The operation we are calling is `say_hello_to_name` , so the message being sent will need to have
    an operationId of `say_hello_to_name`. The operation expects a string sent to it in the payload,
    and will send a string back in its own payload.
    """

    # it's best to define the capability name here, it must be defined on the class
    # for an example of defining this at runtime, you could also call:
    #
    # >>> HelloServiceCapabilityImplementation.intersect_sdk_capability_name = 'HelloExample'
    #
    # ... but you must do this BEFORE initializing the Service or calling the schema generation function
    intersect_sdk_capability_name = 'HelloExample'

    @intersect_status()
    def status(self) -> str:
        """
        Basic status function which returns a hard-coded string.
        """
        return 'Up'

    @intersect_message()
    def say_hello_to_name(self, name: str) -> str:
        """
        Takes in a string parameter and says 'Hello' to the parameter!
        """
        return f'Hello, {name}!'

if __name__ == '__main__':
    # HierarchyConfig should EXACTLY match the example service's HierarchyConfig
    hierarchy = HierarchyConfig(
        organization='oak-ridge-national-laboratory',
        facility='facility',
        system='system',
        subsystem='subsystem',
        service='service',
    )
    schema = get_schema_from_capability_implementations([HelloServiceCapabilityImplementation], hierarchy)


    print(json.dumps(schema, indent=2))
```

2) Copy the Service class. Instead of calling `service.startup()` or `default_intersect_lifecycle_loop`, you can instead execute the following code. NOTE: compared to method `1)`, this involves less code but requires data-service connections to actually execute the code.

```python
import json
# other imports omitted

if __name__ == '__main__':
    # everything before service creation omitted
    service = IntersectService([capability], config)
    print(json.dumps(service._schema, indent=2))
```

## Dependencies

1) Try to avoid any dependency not installed as a mandatory `intersect_sdk` dependency. `pydantic`, `typing_extensions`, and `annotated_types` are dependencies which are mandatory as part of an `intersect_sdk` installation, and usage of these libraries is encouraged.
2) All broker examples should use MQTT for the configuration, with the exception of `1_hello_world_amqp`.

## Validation

Validation should be expressed as declaratively as possible, through `pydantic`, `typing_extensions`, `typing`, and `annotated_types` imports. Try to avoid implementing validation directly in the function body, as that cannot be represented in the generated schemas.

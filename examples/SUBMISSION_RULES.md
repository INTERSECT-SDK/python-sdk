# Submission Rules

There are a few rules we have for submitting examples to IntersectSDK.

## Schemas and services

All example services should have an associated schema file (.json) in the repository. Here are a few ways we can
generate the schema for the HelloWorld Service

1) Write your own script which uses `get_schema_from_model` from the INTERSECT-SDK, which returns a dictionary. You'll need to provide this function your CapabilityImplementation class, your HierarchyConfig, and your application version. You can then dump the dictionary to JSON (please use `indent=2` as an argument).

```python
# imports condensed for readability
import json
from ...sdk import (
    HierarchyConfig,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
    intersect_message,
    intersect_status,
    get_schema_from_model,
)

# copy the CapabilityImplementation EXACTLY as-is. Note that docstrings will be added to the schema!
class HelloServiceCapabilityImplementation:
    """
    Rudimentary capability implementation example.

    All capability implementations are required to have an @intersect_status decorated function,
    but we do not use it here.

    The operation we are calling is `say_hello_to_name` , so the message being sent will need to have
    an operationId of `say_hello_to_name`. The operation expects a string sent to it in the payload,
    and will send a string back in its own payload.
    """

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
    # app_version is necessary for schema but you can just use 0.0.1 for all examples
    app_version = '0.0.1'
    # HierarchyConfig should EXACTLY match the example service's HierarchyConfig
    hierarchy = HierarchyConfig(
        organization='oak-ridge-national-laboratory',
        facility='facility',
        system='system',
        subsystem='subsystem',
        service='service',
    )
    schema = get_schema_from_model(HelloServiceCapabilityImplementation, hierarchy, app_version)


    print(json.dumps(schema, indent=2))
```

2) Copy the Service class. Instead of calling `service.startup()` or `default_intersect_lifecycle_loop`, you can instead execute the following code. NOTE: compared to method `1)`, this involves less code but requires data-service connections to actually execute the code.

```python
import json
# other imports omitted

if __name__ == '__main__':
    # everything before service creation omitted
    service = IntersectService(capability, config)
    print(json.dumps(service._schema, indent=2))
```

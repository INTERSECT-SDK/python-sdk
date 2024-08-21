# Upgrade Guide

This document describes breaking changes and how to upgrade. For a complete list of changes including minor and patch releases, please refer to the [changelog](CHANGELOG.md).

## 0.7.0

### Services

Services now provide a list of capabilities, instead of just a single capability. You will need to explicitly set your capability's `capability_name` property, and will provide a list of Capabilities to the Service instead of a single capability. So you will need to change former code which looks like this:

```python
from intersect_sdk import IntersectBaseCapabilityImplementation, IntersectService, intersect_message

class MyCapabilityImplementation(IntersectBaseCapabilityImplementation):

   @intersect_message
   def my_endpoint(self, param: str) -> str:
      # ... implementation

if __name__ == '__main__':
    # etc.
    capability = MyCapabilityImplementation()
    service = IntersectService(capability,
       # ... other params
    )
```

to this:

```python
from intersect_sdk import IntersectBaseCapabilityImplementation, IntersectService, intersect_message

class MyCapabilityImplementation(IntersectBaseCapabilityImplementation):

   @intersect_message
   def my_endpoint(self, param: str) -> str:
      # ... implementation

if __name__ == '__main__':
    # etc.
    capability = MyCapabilityImplementation()
    capability.capability_name = 'MyCapability'
    service = IntersectService([capability],
       # ... other params
    )
```

Additionally, this reserves the `intersect_sdk_call_service` function - if you are using this function as a name, **you must change its name**. (You should avoid starting your functions with `__intersect_sdk_`, `_intersect_sdk_`, or `intersect_sdk` - these functions could potentially be reserved by the BaseCapability in the future.)

### Clients

When calling another Service's operation, the namespacing has changed from `<function_name>` to `<capability_name>.<function_name>` . So for example, if we were calling `my_endpoint` in the above Service example, the code would change from:

```python
params = IntersectClientMessageParams(
    operation='my_endpoint',
   # ... other parameters unchanged
)

```

to

```python
params = IntersectClientMessageParams(
    operation='MyCapability.my_endpoint',
   # ... other parameters unchanged
)

```

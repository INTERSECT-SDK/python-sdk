# Upgrade Guide

This document describes breaking changes and how to upgrade. For a complete list of changes including minor and patch releases, please refer to the [changelog](CHANGELOG.md).

## 0.8.0

### Service-2-Service callback function

The SDK will now provide the callback function with four arguments instead of one. The message payload was originally the only argument, and is now the fourth argument; the value of this will remain unchanged.

For example, in the following example, you will need to change service_response_handler's function definition from:

```python
class Capability(IntersectBaseCapabilityImplementation):
    @intersect_message()
    def service_call_function(self, text: str) -> None:
        msg_to_send = IntersectDirectMessageParams(
            destination='example-organization.example-facility.example-system.example-subsystem.service-two',
            operation='ServiceTwo.test_service',
            payload=text,
        )

        # Send intersect message to another service
        self.intersect_sdk_call_service(msg_to_send, self.service_response_handler)

    @intersect_event(events={'response_event': IntersectEventDefinition(event_type=str)})
    def service_response_handler(self, msg: Any) -> None:
        # handle response msg
```

to

```python
class Capability(IntersectBaseCapabilityImplementation):
    @intersect_message()
    def service_call_function(self, text: str) -> None:
        msg_to_send = IntersectDirectMessageParams(
            destination='example-organization.example-facility.example-system.example-subsystem.service-two',
            operation='ServiceTwo.test_service',
            payload=text,
        )

        # Send intersect message to another service
        self.intersect_sdk_call_service(msg_to_send, self.service_response_handler)

    @intersect_event(events={'response_event': IntersectEventDefinition(event_type=str)})
    def service_response_handler(self, _source: str, _operation: str, _has_error: bool, msg: Any) -> None:
        # handle response msg
```

### Capability names

On a Capability class, `capability_name` has been changed to `intersect_sdk_capability_name`, to explicitly keep intersect-sdk constructs in the `intersect_sdk_` namespace. With this convention, you should also avoid creating variables or functions which begin with `intersect_sdk_` .

If your capability name contained any characters other than alphanumerics, underscores, and hyphens, it is no longer valid (for example: spaces are not accepted).

A breaking change involves how the capability name is set; this is to allow for schema generation without instantiating a capability instance (which may involve external dependencies). You CANNOT do this on an instance anymore:

```python
class Capability(IntersectBaseCapabilityImplementation):
   ...

if __name__ == '__main__':
   instance = Capability()
   # DON'T DO THIS - THIS WILL NOT WORK
   instance.intersect_sdk_capability_name = 'MyCapability'
```

The most idiomatic way to set `intersect_sdk_capability_name` is as a class variable:

```python
class Capability(IntersectBaseCapabilityImplementation):
   intersect_sdk_capability_name = 'MyCapability'

   # still have total freedom to modify the constructor parameters
   def __init__(self):
      ...

   @intersect_message
   def example_class_function(self, req: str) -> str:
      ...

if __name__ == '__main__':
   instance = Capability()
   # no need to further modify the instance or the class
   config = IntersectServiceConfig(
      # ... omitted for brevity
   )
   service = IntersectService([instance], config)
```

It is still possible to modify the _class variable_ of the Capability at runtime, as long as you do not create the Service instance yet:

```python
class Capability(IntersectBaseCapabilityImplementation):
   ...

if __name__ == '__main__':
   instance = Capability()
   # no need to further modify the instance or the class
   config = IntersectServiceConfig(
      # ... omitted for brevity
   )
   Capability.intersect_sdk_capability_name = os.environ.get('CAPABILITY_NAME') # ok
   # make sure the class variable is set before creating the instance
   service = IntersectService([instance], config)
```

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

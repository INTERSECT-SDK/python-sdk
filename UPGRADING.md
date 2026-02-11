# Upgrade Guide

This document describes breaking changes and how to upgrade. For a complete list of changes including minor and patch releases, please refer to the [changelog](CHANGELOG.md).

## 0.9.0

Note that SDK 0.9.0 is completely incompatible with any version <0.9.0 , due to backend message structure changes.

### Event declaration change

The SDK no longer use the `@intersect_event` decorator for event, and also does not use the `events` attribute on the `@intersect_message` decorator anymore. Instead, create a dictionary of event names to `IntersectEventDefinitions` as the class variable `intersect_sdk_events` on your Capability. This class variable should not be mutated after the IntersectService has been initialized with the Capability.

---

An example of the old way of doing events:

```python
from intersect_sdk import intersect_event, intersect_message, IntersectBaseCapabilityImplementation, IntersectEventDefinition

class Capability(IntersectBaseCapabilityImplementation):
   intersect_sdk_capability_name = 'example_capability'

   @intersect_event(events={'integer_event': IntersectEventDefinition(event_type=int)})
   def response_event_function_1(self):
      self.intersect_sdk_emit_event('integer_event', 1)

   @intersect_event(events={'integer_event': IntersectEventDefinition(event_type=int)}) # note event duplication
   def response_event_function_2(self):
      self.intersect_sdk_emit_event('integer_event', 2)

   @intersect_message(events={'pig_latin': IntersectEventDefinition(event_type=str)})
   def emit_event_from_message(self, input_val: str) -> str:
      if len(input_val) < 2:
         resp = f'{input_val}ay'
      else:
         resp = f'{input_val[1:]}{input_val[0]}ay'
      self.intersect_sdk_emit_event('pig_latin', resp)
      return resp
```

Changed to the new way, this becomes:

```python
from intersect_sdk import intersect_message, IntersectBaseCapabilityImplementation, IntersectEventDefinition

class Capability(IntersectBaseCapabilityImplementation):
   intersect_sdk_capability_name = 'example_capability'
   intersect_sdk_events = {
      'integer_event': IntersectEventDefinition(event_type=int),
      'pig_latin': IntersectEventDefinition(event_type=str),
   }

   # decorators are no longer needed
   def response_event_function_1(self):
      self.intersect_sdk_emit_event('integer_event', 1)

   def response_event_function_2(self):
      self.intersect_sdk_emit_event('integer_event', 2)

   # "events" property no longer needed
   @intersect_message()
   def emit_event_from_message(self, input_val: str) -> str:
      if len(input_val) < 2:
         resp = f'{input_val}ay'
      else:
         resp = f'{input_val[1:]}{input_val[0]}ay'
      self.intersect_sdk_emit_event('pig_latin', resp)
      return resp
```

Also note that this change allows you to use a Capability object and call `capability.intersect_sdk_emit_event('integer_event', 1)` without explicitly creating a function to doing so; the old way had a bug which prevented this pattern.

### Content-Type specification

The `IntersectMimeType` enumerated class requirement for the `request_content_type` and `response_content_type` properties of the `@intersect_message` decorator, and the `content_type` field of the `IntersectEventDefinition` class, has been removed and replaced with a freeform string value; by default, this value is always `application/json`. Unless you are returning binary data, you do not need to set these fields yourself.

The SDK no longer requires single values to be JSON serializable; however, receiving/returning multiple values simultaneously still has the expectation that all binary values are Base64-encoded.

If you are using a value _other_ than `application/json` (i.e. you are just returning raw image data), then the return type or `event_type` of the IntersectEventDefinition MUST be `bytes`. Also note that no automatic validation of inputs will occur, you will have to do manual validation yourself.

### Installing optional dependencies

The `amqp` optional dependency group has been removed, by default AMQP support is required and included when installing `intersect-sdk`.

### Dropped Python 3.8 and 3.9 support

Older Python versions which are officially end-of-life are not supported by INTERSECT-SDK. Please update your Python version to at least 3.10 .

### MQTT support change

We no longer support MQTT 3.1.1 and now support MQTT 5.0 instead; for any `IntersectServiceConfig` or `IntersectClientConfig` configurations, you will need to change `mqtt3.1.1` to `mqtt5.0` .

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

`IntersectClientMessageParams` has been renamed to `IntersectDirectMessageParams` because this object can be used in both Clients and in the new Service-to-Service calls.

When calling another Service's operation, the namespacing has changed from `<function_name>` to `<capability_name>.<function_name>` . So for example, if we were calling `my_endpoint` in the above Service example, the code would change from:

```python
params = IntersectClientMessageParams(
    operation='my_endpoint',
   # ... other parameters unchanged
)

```

to

```python
params = IntersectDirectMessageParams(
    operation='MyCapability.my_endpoint',
   # ... other parameters unchanged
)

```

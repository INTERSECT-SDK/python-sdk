Core Concepts
=============

The INTERSECT-SDK is meant to be a library, not a framework. Its goal is to minimize the amount of code you have to write to integrate with
the INTERSECT ecosystem, but otherwise has no opinions as to how you construct your application. INTERSECT-SDK can be integrated directly into a
scientific application, can be run as a standalone application, and can be integrated into other types of applications (such as REST APIs).

Service
-------

The INTERSECT Service is the main gateway between a user's scientific application and the wider INTERSECT ecosystem. It will handle all interaction
with backing services (such as message brokers and the data plane) and will manage all incoming/outgoing traffic with your application. There are only
a few things you need to provide to the service: your own CapabilityImplementation class, and the service configuration.

The IntersectServiceConfig class requires you to provide credentials for all message brokers and data stores, your hierarchy (or "system-of-system") representation,
the semantic version of your CapabilityImplementation's schema, and the status interval (how often you update your status and send it out to INTERSECT Core.)

Note that you will need a valid connection to at least one broker and one instance of each data plane type (currently: MINIO) to activate your service.
Your CapabilityImplementation will also need to be able to generate a schema.

CapabilityImplementation
------------------------

If you've written REST APIs, writing a CapabilityImplementation will look very similar. You need to provide a single CapabilityImplementation class; you have complete control over your constructor, your class state variables, and your class methods.
The only restriction is that your class will have to extend ``IntersectBaseCapabilityImplementation``. If you override the ``__init__()`` function, be sure to call ``super().__init__()``

A CapabilityImplementation class contains several ``@intersect_message()`` annotated functions, and one ``@intersect_status()`` annotated function.
These functions are INTERSECT's entrypoints into your application.

Message functions should take in up to one argument, and should produce a return value. Status functions should take in no parameters,
should produce a return value, and should be something which is cheap to call.

When writing a message function or a status function, all parameters and return values must contain a valid type annotation.
Please see the :doc:`pydantic` page for more information about valid types.

Arguments to the ``@intersect_message()`` decorator can be used to specify specific details about your function; for example, the Content-Types of both the request and response parameter, the data provider for the response data, and whether you want to allow type coercion in the request.

CapabilityImplementation - Events
---------------------------------

You can emit events globally as part of an ``@intersect_message()`` annotated function by configuring the ``events`` argument to the decorator as a dictionary/mapping of event names (as strings) to IntersectEventDefinitions.
An IntersectEventDefinition consists of an event_type, which is the typing of the event you'll emit.

You can also emit events without having to react to an external request by annotating a function with ``@intersect_event()`` and providing the ``events`` argument to the decorator.

You can emit an event by calling ``self.intersect_sdk_emit_event(event_name, event)`` . The typing of ``event`` must match the typing in the decorator configuration.
Calling this function will only be effective if called from either an ``@intersect_message`` or ``@intersect_event`` decorated function, or an inner function called from a decorated function.

You can specify the same event name on multiple functions, but it must always contain the same IntersectEventDefinition configuration.

Client
------

Clients can be used to script interaction with INTERSECT. The only configuration needed by clients can be addressed in the IntersectClientConfig;
you need to provide credentials for all message brokers and data stores. Just like Services, clients need to have at least one message broker connection
and at least one connection to each data provider type to work.

Users need to provide clients with initial messages to send and a callback function which handles interaction with messages from other services.

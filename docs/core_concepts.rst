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

A CapabilityImplementation class contains several ``@intersect_message()`` annotated function, and one ``@intersect_status()`` annotation.
These functions are INTERSECT's entrypoints into your application.

Message functions should take in up to one argument, and should produce a return value. Status functions should take in no parameters,
should produce a return value, and should be something which is cheap to call.

When writing a message function or a status function, all parameters and return values must contain a valid type annotation.
Please see the :doc:`pydantic` page for more information about valid types.

Arguments to the ``@intersect_message()`` decorator can be used to specify specific details about your function; for example, the Content-Types of both the request and response parameter, the data provider for the response data, and whether you want to allow type coercion in the request.

Client
------

Clients can be used to script interaction with INTERSECT. The only configuration needed by clients can be addressed in the IntersectClientConfig;
you need to provide credentials for all message brokers and data stores. Just like Services, clients need to have at least one message broker connection
and at least one connection to each data provider type to work.

Users need to provide clients with initial messages to send and a callback function which handles interaction with messages from other services.

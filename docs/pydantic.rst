Pydantic
========

`Pydantic <https://docs.pydantic.dev/latest/>`_ is a widely used data validation library in the Python ecosystem; frameworks such as
FastAPI, huggingface, and SQLModel use Pydantic. In addition to data validation, Pydantic is also able to generate schemas.

INTERSECT-SDK uses Pydantic extensively in internal code. When creating your own CapabilityImplementation for a Service, INTERSECT-SDK
allows users to use Pydantic to customize their own types and the schemas generated from them. Types which cannot be validated by Pydantic
cannot be converted into schemas, and being able to generate an overall schema

Users are encouraged to try to express validation through Pydantic as much as possible. If validation can be expressed through schema,
this can assist UIs and external APIs in ensuring that little to no invalid parameters will be sent to your application, reducing system
strain and increasing ease of use for external users.

Usage
-----

External users would benefit most by understanding the `Models <https://docs.pydantic.dev/latest/concepts/models/>`_, `Fields <https://docs.pydantic.dev/latest/concepts/fields/>`_,
and `Types <https://docs.pydantic.dev/latest/concepts/types/>`_ documentation pages on Pydantic's own documentation website.

INTERSECT-SDK will handle the schema generation logic, but users are able to customize fields themselves. For example, users can combine ``typing_extensions.Annotated``
with ``pydantic.Field`` to specify regular expression patterns for string, minimum lengths for arrays/lists, and many other validation concepts.

For handling complex objects, your class should either extend ``pydantic.BaseModel`` or be a `Python Dataclass <https://docs.python.org/3/library/dataclasses.html>`_.

To forbid type coercion (i.e. casting a JSON string to a Python integer), you can use ``@intersect_message(strict_request_validation=True)`` on your annotation. Most users will not need this,
but if you have concerns you can refer to `Pydantic's Conversion Table <https://docs.pydantic.dev/latest/concepts/conversion_table/>`_ to determine what is and is not allowed.
Note that in INTERSECT, the input source will always be JSON.

Note that INTERSECT has a few additional restrictions on types from Pydantic:

* ``typing.Any`` and ``object`` are considered invalid types due to their inability to construct a strongly-typed schema.

* If you are using a Mapping type (such as Dict), the key type must be either ``str``, ``float``, or ``int``. Note that using floating-point or integer keys requires allowing type coercion, and that float and integer keys cannot effectively communicate minimum/maximum values or ranges through the generated schema. However, regular expressions can be effectively communicated, i.e. ``Annotated[str, Field(pattern=r'<YOUR_REGEX_HERE>')]``.

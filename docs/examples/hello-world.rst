Hello world
===========

This is a basic example on how to communicate with the INTERSECT SDK. The ``adapter.py`` subscribes to ``Request`` INTERSECT messages of the ``DETAIL`` subtype. The adapter will respond with a "Hello, World!" message in its reply. The ``requestor.py`` publishes ``Status`` INTERSECT messages of the ``GENERAL`` subtype. See the sections below for running the example using Docker compose or from within a Python environment.

Using a Python environment
--------------------------

This section discusses the ``hello-world`` examples in ``examples/python-environment/``. The ``hello-world-dict`` example uses a dictionary for configuration settings while the example in ``hello-world-yml`` uses a YAML configuration file. Run the examples in a Python virtual environment which was discussed in the :doc:`../installation` section.

First, if a broker is not already running, run the broker in a separate terminal session as discussed on the :doc:`../installation` page.

After starting the broker and activating the virtual environment, run the adapter and requestor as follows in separate terminal sessions:

.. code-block:: bash

   # First, run the adapter
   python adapter.py

   # Next, run the requestor in a separate terminal
   python requestor.py

After several seconds, the output from ``adapter.py`` is

.. code-block:: text

   Waiting to connect to broker...
   Press Ctrl-C to exit:
   Adapter Uptime: 6 seconds
   Adapter Uptime: 11 seconds
   Received request from Requestor, sending reply...
   Adapter Uptime: 16 seconds
   Adapter Uptime: 21 seconds

and the output from ``requestor.py`` is

.. code-block:: text

  Waiting to connect to message broker...
  Press Ctrl-C to exit:
  Requestor will send request in 5 seconds...
  Request sent!
  Reply from Hello World Adapter:
  {"message": "Hello, World!"}
  Requestor Uptime: 11 seconds
  Requestor Uptime: 16 seconds
  Requestor Uptime: 21 seconds

Using Docker compose
--------------------

This section discusses the ``hello-world`` examples in ``examples/docker-compose/``. The ``hello-world`` example uses YAML configuration files for configuration settings.
Follow the steps below to run these examples using ``docker compose``.

Add U/XCAMS credentials to authenitcate with GitLab PyPI package repository for SDK.

Create an ``.env`` file with the GitLab credentials that docker compose will use:

.. code-block:: bash

   # inside .env file:
   GITLAB_USERNAME=(UCAMS ID)
   GITLAB_PASSWORD=(GitLab token)

Now, start up the broker, adapter and requestor using docker compose:

.. code-block:: bash

   # Build and run via docker compose
   docker compose --env-file .env build
   docker compose --env-file .env up

After several seconds, the output from ``hello-world-adapter:`` is

.. code-block:: text

   Waiting to connect to broker...
   Press Ctrl-C to exit:
   Adapter Uptime: 6 seconds
   Adapter Uptime: 11 seconds
   Received request from Requestor, sending reply...
   Adapter Uptime: 16 seconds
   Adapter Uptime: 21 seconds

and the output from ``hello-world-requestor`` is

.. code-block:: text

  Waiting to connect to message broker...
  Press Ctrl-C to exit:
  Requestor will send request in 5 seconds...
  Request sent!
  Reply from Hello World Adapter:
  {"message": "Hello, World!"}
  Requestor Uptime: 11 seconds
  Requestor Uptime: 16 seconds
  Requestor Uptime: 21 seconds

When finished, cleanup!

.. code-block:: bash

  # cleanup
  docker compose down

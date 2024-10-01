Installation and usage
======================

INTERSECT-SDK requires a Python version >= 3.8.10 .

After installing Python, make a folder for your project, then create a virtual environment in that folder and activate the environment as follows:

.. code-block:: bash

   # Create a project folder and change to that directory
   mkdir myproject
   cd myproject

   # Create a virtual environment and activate it
   python -m venv venv
   source venv/bin/activate

Next, install the intersect-sdk package into the virtual environment using the command shown below.

.. code-block:: bash

   # Install the intersect-sdk package into the virtual environment
   pip install intersect-sdk

You should now be able to import the package in a Python script, notebook, or program using:

.. code-block::

   import intersect_sdk

Use the command shown below to deactivate the virtual environment:

.. code-block:: bash

   # Deactivate the virtual environment
   deactivate

If you would like to run the examples, such as the :doc:`examples/hello-world` example, you may need to install Docker and run a broker service. See the sections below for more information.

Docker
------

`Docker <https://www.docker.com>`_ is used to create containers for using the Python SDK and to run the examples. Download and install Docker using the instructions provided on their website.

Backing Services (Brokers, Data planes)
---------------------------------------

A Docker Compose configuration for SDK development is included below. This sets up the primary backing services (message brokers, data storage layers) needed to use INTERSECT.

Note that this configuration is meant for testing, and should not be included in production.

.. literalinclude:: ../docker-compose.yml

From the repository root, run the backing services using the Docker commands shown below.

.. code-block:: bash

   # if you are copypasting from this website instead of running from the repository root, you should make sure you copy the contents into docker-compose.yml.
   docker compose up -d

To see the broker's management UI, you can navigate to ``localhost:15672`` in your browser. The login credentials mirror `RABBITMQ_USERNAME` and `RABBITMQ_PASSWORD` from the docker-compose file.

To cleanup:

.. code-block:: bash

   docker compose down -v

Installation and usage
======================

Install Python via `Anaconda <https://www.anaconda.com>`_ or `Conda <https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html>`_. Anaconda installs Python along with many other graphical tools and scientific packages. Conda is an open-source packaging, dependency, and environment management tool which also installs Python. Notice that Miniconda is a smaller version of Anaconda that includes only Conda and a few dependencies.

After installing Python, make a folder for your project, then create a virtual environment in that folder and activate the environment as follows:

.. code-block:: text

   mkdir myproject
   cd myproject

   python -m venv venv
   source venv/bin/activate

Next, install the intersect-sdk package into the virtual environment using the command shown below. The ``<token>`` must be replaced with your GitLab token. For example, if your token is ``12345`` then replace ``<token>`` in the URL with ``12345`` then run the command. See the **Authenticating** section below for information on how to generate a token.

.. code-block:: text

   pip install -i https://user:<token>@code.ornl.gov/api/v4/groups/5609/-/packages/pypi/simple intersect-sdk

You should now be able to import the package in a Python script, notebook, or program using:

.. code-block::

   import intersect_sdk

Use the command shown below to deactivate the virtual environment:

.. code-block:: text

  deactivate

If you would like to run the examples, such as the :doc:`examples/hello-world` example, you may need to install Docker and run a broker service. See the sections below for more information.

Authenticating
--------------

Some INTERSECT dependencies are stored on private package registries on code.ornl.gov; therefore, a personal access token is required for installation. Create a personal access token on the `Access Tokens page <https://code.ornl.gov/-/profile/personal_access_tokens>`_ in GitLab Preferences with ``read_api`` or ``api`` permissions then save the auto-generated key. This key is only displayed immediately after generating it, so be sure to save it (otherwise a new token will need to be generated).

For the Docker containers, you need to login to the GitLab Container registry using the command shown below. Then sign in with your UCAMS or XCAMS credentials.

.. code-block::

   docker login code.ornl.gov:4567

Docker
------

`Docker <https://www.docker.com>`_ is used to create containers for using the Python SDK and to run the examples. Download and install Docker using the instructions provided on their website. See the **Authenticating** section below to use the GitLab Container registry which contains INTERSECT dependencies.

Broker
------

A broker configuration for SDK developoment is available on the INTERSECT GitLab at https://code.ornl.gov/intersect/sdk/broker. This broker is meant for testing and development purposes and should not be used for deploying INTERSECT in production.

Run the broker using the Docker commands shown below. See the previous section regarding authentication for the login command.

.. code-block::

   docker login code.ornl.gov:4567
   docker run --rm -p 1883:1883 code.ornl.gov:4567/intersect/sdk/broker/0.2.0

To expose the management UI as well, add ``-p 15672:15672`` to the command. Then you can navigate to ``localhost:15672`` in your browser. The login credentials will be those found in the broker's `definitions file <https://code.ornl.gov/intersect/sdk/broker/-/blob/0.2.0/definitions.json>`_.


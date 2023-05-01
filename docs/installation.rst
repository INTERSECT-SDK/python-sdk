Installation
============

Here

Broker
------

Here.

Authenticating
--------------

Some dependencies are stored on private package registries on code.ornl.gov. A personal access token is required in order to install these with either poetry or pip. Create a personal access token on the `Access Tokens page <https://code.ornl.gov/-/profile/personal_access_tokens>`_ in GitLab Preferences with ``read_api`` or ``api`` permissions then save the auto-generated key. This key is only displayed immediately after generating it, so be sure to save it (otherwise a new token will need to be generated).

For the Docker containers, you need to login to the GitLab Container registry using the command shown below. Then sign in with your UCAMS or XCAMS credentials.

.. code-block::

   docker login code.ornl.gov:4567

Docker
------

`Docker <https://www.docker.com>`_ is used to create containers for using the Python SDK and to run the examples. See the Authenticating section above to use the GitLab Container registry.

Poetry
------

The `poetry <https://python-poetry.org>`_ packaging and dependency management tool can be used to install the Python SDK.

Conda
-----

The `conda <https://docs.conda.io/en/latest/>`_ packaging, dependency, and environment management tool can also be used to intall the Python SDK. Install conda from the `Anaconda <https://www.anaconda.com>`_ website or follow the `Conda installation <https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html>`_ steps. Notice that Miniconda is a mini version of Anaconda that includes only conda and its dependencies. If you prefer to have conda plus over 7,500 open-source packages, install Anaconda.

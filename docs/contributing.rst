Contributing
============

Read the sections below if you would like to contribute to the development of the INTERSECT Python SDK package.

Installing for package development
----------------------------------

Follow the steps discussed in this section to install the intersect-sdk package in a Python development environment. First, install Python and PDM on your local machine. See the :doc:`installation` page for more details. Next, clone the sdk repository as follows:

.. code-block:: bash

   git clone https://code.ornl.gov/intersect/sdk/python-sdk/sdk.git

Create a Python virtual environment in the root level of the repository and activate the environment.

.. code-block:: bash

   # Create a virtual environment and activate it
   cd sdk
   python -m venv venv
   source venv/bin/activate

Use PDM to install the intersect-sdk package and its dependencies into the virtual environment.

.. code-block:: bash

   # Install the intersect-sdk package into the virtual environment using PDM
   pdm install

Check the installation by running one of the examples, such as the :doc:`examples/hello-world` example. Use the command shown below to deactivate the virtual environment:

.. code-block:: bash

   deactivate

PDM
------

The `PDM <https://pdm.fming.dev/latest/>`_ packaging and dependency management tool is used to install the intersect-sdk package in editable (developer) mode. It is also used to run linter checks, formatter checks, and unit tests. Download and install PDM using the instructions on the PDM website.

Documentation
-------------

Documentation for the INTERSECT Python SDK is generated with `Sphinx <https://www.sphinx-doc.org/en/master/>`_ from the ``docs`` directory.

Testing
-------

The `pytest <https://docs.pytest.org>`_ framework is used to run tests.

Style guide
-----------

Adhere to the `pep8 <https://pep8.org>`_ style guide for writing Python code.

Linting
-------

Use the `ruff-lint <https://docs.astral.sh/ruff/linter>`_ linter tool when writing Python code. Instructions for setting up flake8 with Visual Studio Code are available `here <https://code.visualstudio.com/docs/python/linting>`__. Instructions for setting up flake8 with Sublime Text are available `here <https://lsp.sublimetext.io/>`__ for the LSP-ruff package.

When overriding a rule in code, or overriding a rule in ``pyproject.toml``, always provide a short comment with the ``# noqa`` rule justifying why the rule override is necessary.

Formatting
----------

Use the `ruff-format <https://docs.astral.sh/ruff/formatter/>`_ formatter for Python code. Instructions for using this formatter with Visual Studio Code are available `here <https://code.visualstudio.com/docs/python/editing>`__. Instructions for using the formatter with Sublime Text are available `here <https://lsp.sublimetext.io/>`__ for the LSP-ruff package.

Docstrings
----------

Docstrings for Python classes, functions, and modules should adhere to the `Google style <https://google.github.io/styleguide/pyguide.html>`_. The docstrings are processed by the `napoleon extension <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/>`_ for the Sphinx generated documentation.

We require docstrings for all public classes, functions, and modules.

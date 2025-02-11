========================================
Contributing to the StarlingX Test Repo
========================================

This document outlines the contribution guidelines for the `starlingx/test` repository.

StarlingX Test is an open-source project, and we welcome contributions from the community.  
This guide explains the requirements for code contributions, pre-commit checks, and documentation compliance.

1. Setting Up Your Development Environment
==========================================

1.1 Clone the Repository
------------------------

First, clone the repository and set up your environment:

.. code-block:: bash

    git clone https://opendev.org/starlingx/test.git
    cd test

1.2 Install Dependencies
------------------------

Ensure you have **Python 3.11** installed, then install dependencies using `pipenv`:

.. code-block:: bash

    pip install --user pipenv
    pipenv install --dev

1.3 Enable Pre-Commit Hooks
---------------------------

Pre-commit hooks are required to ensure code formatting and docstring compliance:

.. code-block:: bash

    pre-commit install

Once installed, **pre-commit will automatically run** on every commit.

2. Code Contribution Guidelines
===============================

2.1 Code Style
--------------

- Python code must be formatted with ``black`` and ``isort``.  
- Line length should not exceed 200 characters.
- Use **f-strings** instead of ``%`` formatting or ``.format()``.

2.2 Docstring Standards
-----------------------

All docstrings should follow the **Google Python Style Guide** and must be formatted consistently to pass pre-commit checks.

- **Google-style docstrings** are required for all **functions and classes**, with the following exceptions:

  - **Module-level docstrings** are **not required** or enforced by pre-commit hooks.  

    However, they are **recommended** for utility scripts and config files to clarify their intended use for other developers.  

  - ``__init__`` methods are **allowed** to have docstrings but are **not required**.  

    If a docstring is present, it should describe the purpose of the constructor and any initialization logic.  

The pre-commit hooks automatically enforce **PEP 257** and **Google-style docstrings** using ``pydocstyle``, ``pydoclint``, and ``interrogate``.

For auto-generating docstrings that align with these standards, see: :ref:`auto-docstrings`.

2.3 Type Hinting
----------------

All function signatures must include **type hints** for arguments and return values.

**Example (Required Formatting):**

.. code-block:: python

    def add(a: int, b: int) -> int:
        """
        Adds two numbers.

        Args:
            a (int): The first number.
            b (int): The second number.

        Returns:
            int: The sum of `a` and `b`.
        """
        return a + b

3. Pre-Commit Hooks & Linting
=============================

This repository uses **pre-commit hooks** to enforce formatting, linting, and docstring compliance.

3.1 Installed Pre-Commit Hooks
------------------------------

The following tools are run automatically on every commit:

- **black**: Enforces PEP 8-compliant code formatting.
- **isort**: Ensures import statements are correctly ordered.
- **flake8**: Static code analysis and linting.
- **pydocstyle**: Enforces PEP 257 and Google-style docstring formatting.
- **pydoclint**: Ensures function signatures and docstrings match.
- **interrogate**: Ensures all functions and classes have docstrings.

3.2 Running Pre-Commit Hooks Manually
-------------------------------------

You can run pre-commit checks manually before committing:

.. code-block:: bash

    pre-commit run --all-files

4. Handling Return Types in Docstrings & Type Hints
===================================================

4.1 Why Are Return Types Required in Both Docstrings and Type Hints?
--------------------------------------------------------------------

We enforce **return type hints** (e.g., ``-> type``) and **docstring return types** (e.g., ``Returns:`` section) **to ensure consistency**.

**Why is this required?**

- Ensures clarity in documentation.
- Helps enforce consistency across the project.
- Required by pre-commit hooks (`pydocstyle`, `pydoclint`, `interrogate`).

4.2 Example of Correct Formatting
---------------------------------

**Correct Example:**

.. code-block:: python

    def multiply(a: int, b: int) -> int:
        """
        Multiplies two integers.

        Args:
            a (int): The first integer.
            b (int): The second integer.

        Returns:
            int: The product of `a` and `b`.
        """
        return a * b

**Incorrect Example (Missing `Returns:` section):**

.. code-block:: python

    def multiply(a: int, b: int) -> int:
        """Multiplies two integers."""
        return a * b  # Missing `Returns:` section in docstring.

.. _auto-docstrings:

5. Auto-Generating Docstrings in VSCode & PyCharm
=================================================

To simplify docstring compliance, you can use IDE plugins.

5.1 VSCode: Auto-Generating Docstrings
--------------------------------------

1. Install the [Python Docstring Generator](https://marketplace.visualstudio.com/items?itemName=njpwerner.autodocstring).
2. Configure VSCode to generate **Google-style docstrings** that align with pre-commit checks.

   Add the following settings to your ``settings.json``:

   .. code-block:: json

      {
          "autoDocstring.docstringFormat": "google",
          "autoDocstring.includeName": true,
          "autoDocstring.includeExtendedSummary": true,
          "autoDocstring.guessTypes": true,
          "autoDocstring.startOnNewLine": true,
          "autoDocstring.quoteStyle": "\"\"\"",
          "autoDocstring.generateDocstringOnEnter": true
      }

3. Save the file and restart VSCode.

5.2 PyCharm: Auto-Generating Docstrings
---------------------------------------

1. Open **PyCharm**.
2. Go to **File → Settings → Tools → Python Integrated Tools**.
3. Find the **Docstring format** dropdown and select **Google**.
4. Click **Apply** and **OK**.

6. References
=============

- `OpenStack Contributor Guide <https://docs.openstack.org/contributors/en_GB/common/setup-gerrit.html>`_
- `OpenStack Individual Contributor License Agreement (ICLA) <https://review.opendev.org/settings/new-agreement>`_
- `OpenDev Developer Documentation <https://docs.opendev.org/opendev/infra-manual/latest/developers.html>`_
- `StarlingX Contributor Guidelines <https://docs.starlingx.io/contributor/index.html>`_
- `StarlingX Code Submission Guide <https://docs.starlingx.io/developer_resources/code-submission-guide.html>`_
- `How to Contribute to StarlingX (YouTube) <https://www.youtube.com/watch?v=oHmx0M3cYlE>`_
- `OpenStack Git Commit Message Guidelines <https://wiki.openstack.org/wiki/GitCommitMessages>`_
- `Google Python Style Guide <https://google.github.io/styleguide/pyguide.html#381-docstrings>`_
- `PEP 257 (Docstring Conventions) <https://peps.python.org/pep-0257/>`_
- `PEP 484 (Type Hints) <https://peps.python.org/pep-0484/>`_
- `PEP 498 (f-Strings) <https://peps.python.org/pep-0498/>`_
- `pydocstyle Documentation <https://www.pydocstyle.org/en/latest/>`_
- `pydoclint Documentation <https://github.com/jsh9/pydoclint>`_
- `interrogate Documentation <https://interrogate.readthedocs.io/en/latest/>`_
- `pre-commit <https://pre-commit.com/>`_
- `black <https://black.readthedocs.io/en/stable/>`_
- `isort <https://pycqa.github.io/isort/>`_
- `flake8 <https://flake8.pycqa.org/en/latest/>`_
- `AutoDocstring for VSCode <https://github.com/autosoft-dev/autoDocstring>`_
- `VSCode: Auto-Generating Docstrings <https://code.visualstudio.com/docs/python/editing#_auto-generating-docstrings>`_
- `PyCharm: Creating Documentation Comments <https://www.jetbrains.com/help/pycharm/creating-documentation-comments.html>`_

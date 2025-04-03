============================
**framework/** Documentation
============================

The **framework/** directory contains core infrastructure for the StarlingX Test
Automation Framework, including logging, SSH, threading, database operations,
REST clients, runner logic, and other essential utilities that power keyword
execution and test orchestration.

Design Principles
=================

The framework layer is built for reliability, extensibility, and separation of concerns:

- **Reusable building blocks**: Shared services such as SSH, threading, and logging are centralized here.
- **Test-agnostic logic**: This layer should not depend on specific testcases or keyword domains.
- **Isolation from test logic**: Business logic and automation commands live in `keywords/` or `testcases/`,
  while framework components focus on supporting infrastructure.
- **Consistent logging and error handling**: All modules use the same logger and exception patterns.

--------
Contents
--------

.. toctree::
   :maxdepth: 1

   ssh/index

Directory Structure
===================

An overview of the key subdirectories in **framework/**:

.. code-block:: bash

   framework/
   ├── database/           # Handles test result storage and querying
   ├── exceptions/         # Custom framework exception classes
   ├── logging/            # Logging setup, formatting, and filtering
   ├── pytest_plugins/     # Plugins for customizing test discovery and result capture
   ├── resources/          # Static resources and backup files
   ├── rest/               # REST client interfaces and response helpers
   ├── runner/             # Scripts and objects for test execution
   ├── scanning/           # Handles scan and upload of test artifacts
   ├── ssh/                # SSH connections, prompts, and secure transfers
   ├── threading/          # Multi-threading infrastructure
   ├── validation/         # Generic input validation utilities
   └── web/                # Web automation helpers (actions, conditions, locators)

========================================
**framework/logging/** Documentation
========================================

The **framework/logging/** directory provides centralized logging for the StarlingX Test Automation Framework. It standardizes log format, sources, and behavior across keywords, test cases, and framework utilities.

--------
Contents
--------

.. contents::
   :local:
   :depth: 2

Overview
========

Logging is handled via a singleton instance of `AutomationLogger`, which wraps Python's `logging` module but adds:

- Structured test step logging
- Automatic source tagging (e.g., AUT, TST, SSH)
- Support for per-test logs and exception filtering
- CLI + file output with unified formatting

Accessing the Logger
=====================

Always use:

.. code-block:: python

   from framework.logging.automation_logger import get_logger
   get_logger().log_info("My log message")

This ensures:

- You don’t manually instantiate or manage loggers.
- All logs use the centralized format and handler structure.
- Logging behavior (formatting, filtering, file output) is consistent.

Logging Conventions
====================

Log messages are tagged with a **source** code:

- ``AUT`` – General automation logs
- ``TST`` – Structured test execution steps
- ``TSU`` – Structured setup steps
- ``TTD`` – Structured teardown steps
- ``SSH`` – SSH commands and output
- ``KEY`` – Keyword-level trace logs
- ``EXC`` – Exception logs (stack traces)
- ``LIB`` – 3rd-party logs

Framework Methods
------------------

The following methods are available:

.. list-table::
   :header-rows: 1

   * - Method
     - Description
     - Source
   * - ``log_info()``
     - Log a general message
     - AUT
   * - ``log_debug()``
     - Log a debug message
     - AUT
   * - ``log_warning()``
     - Log a warning
     - AUT
   * - ``log_error()``
     - Log a non-exception error
     - AUT
   * - ``log_exception()``
     - Log an exception (no stack trace duplication)
     - EXC
   * - ``log_keyword()``
     - Auto-logged when keyword wrappers are used
     - KEY
   * - ``log_ssh()``
     - Logs SSH commands sent and received
     - SSH
   * - ``log_test_case_step()``
     - Structured, numbered test execution step
     - TST
   * - ``log_setup_step()``
     - Structured, numbered setup step
     - TSU
   * - ``log_teardown_step()``
     - Structured, numbered teardown step
     - TTD


Structured Step Logging
=======================

The test framework supports structured logging for each stage of test execution:
Setup, Execution, and Teardown.

Each stage has a corresponding logger method:

- get_logger().log_setup_step("...")
- get_logger().log_test_case_step("...")
- get_logger().log_teardown_step("...")

These methods log clearly formatted, numbered steps using a consistent visual layout.
Each stage uses its own prefix (TSU, TST, TTD) to aid visual scanning and support
machine parsing or grep-based analysis.

Example usage:
::

   get_logger().log_setup_step("Connecting to system")
   get_logger().log_test_case_step("Create PVC")
   get_logger().log_teardown_step("Disconnecting from system")

Example log output:
::

   [2025-06-18 16:44:01] TSU INFO    ... :: -------------------- [ Setup Step 1: Connecting to system ] -------------------------------
   [2025-06-18 16:44:01] TST INFO    ... :: -------------------- [ Test Step 1: Create PVC ] ------------------------------------------
   [2025-06-18 16:44:01] TTD INFO    ... :: -------------------- [ Teardown Step 1: Disconnecting from system ] -----------------------

Each step banner auto-increments a counter and maintains consistent alignment
regardless of description length. Counters reset automatically at the beginning
of each test case.

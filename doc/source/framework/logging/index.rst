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
- ``TST`` – Structured test steps
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
     - Structured, numbered test steps
     - TST

Structured Test Step Logging
=============================

Use `log_test_case_step()` to structure your test case flow:

.. code-block:: python

   get_logger().log_test_case_step("Lock the host")
   get_logger().log_test_case_step("Assign label foo=bar")
   get_logger().log_test_case_step("Verify label is assigned")

This automatically prints:

.. code-block::

   Test Step 1: Lock the host
   Test Step 2: Assign label foo=bar
   Test Step 3: Verify label is assigned

Step numbers are reset between tests using `

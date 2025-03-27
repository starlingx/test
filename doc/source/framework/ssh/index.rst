================================
**framework/ssh/** Documentation
================================

The **framework/ssh/** directory provides SSH-related infrastructure for the
StarlingX Test Framework. It includes utilities for establishing remote
connections, handling interactive prompts, and performing secure file transfers.

This layer is designed to be reusable across the entire framework, and abstracts
SSH complexity away from keywords and test logic.

--------
Contents
--------

.. toctree::
   :maxdepth: 1
   :caption: SSH Modules


Overview
========

The SSH layer encapsulates all logic related to:

- **Establishing connections** (with or without jump hosts).
- **Executing remote commands** (including interactive or sudo-based workflows).
- **Handling prompts** using reusable response objects.
- **Secure file transfers** using built-in Paramiko support.
- **Cleaning up output** (e.g., removing ANSI sequences).

These modules are used by keyword implementations to run system-level commands
on remote hosts in a consistent and fault-tolerant manner.

Connection Behavior
===================

The SSH connection adapts based on the test lab's setup and the type of command being executed:

1. Check whether a jump host is required.
2. If needed, connect to the jump host using Paramiko.
3. Open a channel to the final destination (target host).
4. Establish the SSH session to the target host.
5. Use one of the following modes:

   - ``exec_command()`` for simple non-interactive commands.
   - ``invoke_shell()`` when prompt interaction or ``sudo`` is needed.

6. Execute the command and capture output.
7. Strip any ANSI escape sequences for cleaner parsing/logs.

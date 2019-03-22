=========================
System Inventory/Host Ops
=========================

.. contents::
   :local:
   :depth: 1

-----------------------
sysinv_ho_01
-----------------------

:Test ID: sysinv_ho_01
:Test Title: export hosts information using host-bulk-export cli
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Export the information of current hosts using cli

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~


1. Authenticate with platform keystone

2. export the hosts information using

.. code:: bash

  system host-bulk-export –filename <hosts-file-name>


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

2. <host-file-name> is generated containing the information of all hosts in the current configuration


~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_ho_02
-----------------------

:Test ID: sysinv_ho_02
:Test Title: host operations (bulk-add; list; show; delete) in parallel on multiple hosts
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

host operations (bulk-add, list, show, delete) in parallel on multiple hosts

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Add multiple hosts using controller-0 (up to the max. limit e.g. currently 50)

.. code:: bash

  system host-bulk-add <host-file.xml>

2. Connected to controller-1, delete hosts at the same time

.. code:: bash

  system host-delete host1
  system host-delete host2

3. repeat 1 and 2

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. verify the hosts are added without errors

2. the hosts are deleted without errors

3. verify the operations are successfully executed

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_ho_03
-----------------------

:Test ID: sysinv_ho_03
:Test Title: Test BMC functionality
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Test BMC functionality (host-reset; power-on;power-off) - requires BMC network on management VLAN

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

BMC must be configured with its statick IP address, using BMC tools. BMC should be reachable from controllers.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Configure BMC on controller-1 (assuming is the stand-by controller)

- Login to platform Horizon

- Go to Admin / Platform / Host Inventory, "Hosts" tab

- click on "Edit host", then Board Management, and fill it out with the BMC info.

2. Verify Power  off / on works as expected

- Lock controller-1

.. code:: bash

  system host-lock controller-1

-  turn it down

.. code:: bash

   system host-power-off controller-1

- Wait until it's off

- turn it on

.. code:: bash

  system host-power-on controller-1

3. Verify reset works

- Send the reset signal

.. code:: bash

  system host-reset controller-1

- wait until it becomes 'online'

4. Unlock the controller

.. code:: bash

  system host-unlock controller-1


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. BMC is configured and reachable from controller-0

2. node powers off, then on

3. Node reboots

   Check alarms are raised and cleared as expected


~~~~~~~~~~
References
~~~~~~~~~~

N/A



======================
System Inventory/Check
======================

Verify different system settings

.. contents::
   :local:
   :depth: 1

-----------------------
sysinv_check_01
-----------------------

:Test ID: sysinv_check_01
:Test Title: get the information of the software version and patch level using cli
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify the software version and patch level using cli

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

System up and running

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Get the software version with the command

.. code:: bash

  system show

2. Get the applied patches with the command

.. code:: bash

  sudo sw-patch query

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. "software_version" row lists the correct version.

2. Patch ID column lists the current patch level.

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_check_02
-----------------------

:Test ID: sysinv_check_02
:Test Title: query the system type using cli
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Check system_mode and system_type using CLI

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

System up and running

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Authenticate with platform keystone

2. Query system_mode and system_type

.. code:: bash

  system show | grep -e  system_mode -e system_type


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

Simplex: system_mode simplex, system_type All-in-one

Duplex: system_mode duplex, system_type All-in-one

Standard: system_mode duplex, system_type Standard


~~~~~~~~~~
References
~~~~~~~~~~

N/A

-----------------------
sysinv_check_03
-----------------------

:Test ID: sysinv_check_03
:Test Title: resynchronize a host to the ntp server
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Resynchronize a node to the NTP server. If a time discrepancy greater than ~17 min is found, the ntpd service is stopped.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

System up and running.
A NTP server reachable.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Make sure the node has a NTP server (that works) defined.

2. Change the time on worker-0, with a difference of 20 min.

3. Lock and unlock the host

.. code:: bash

  system host-lock worker-0; system host-unlock worker-0

4. Wait for the node to come back and verify the time has been fixed.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

2. Alarms 250.001 (configuration os out of date) and 200.006 (ntpd process has failed) are raised.

3. Alarms are cleared

4. time has been sync'd

~~~~~~~~~~
References
~~~~~~~~~~

N/A

-----------------------
sysinv_check_04
-----------------------

:Test ID: sysinv_check_04
:Test Title: swact active controller using rest api via floating oam ip
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Execute a swact using REST API + OAM floating IP

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

TBD

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_check_05
-----------------------

:Test ID: sysinv_check_05
:Test Title: verify VM is consumming hugepage memory from the the affined NUMA node
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify the instance created with cpu pinning consumes hugepages from the NUMA node associated to the CPU.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create a flavor with extra spec: 'hw:cpu_policy': 'dedicated'

2. lock a worker to boot the vm

3. Launch a vm

4. check the memory consumed by the vm, verify it’s on the same numa as the pinned cpu

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. the flavor is created without any error

2. expected result: the worker is locked without any error

3. the vm booted successfully

4. both huge-page memory and the pinned cpu are on the same numa node

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_check_06
-----------------------

:Test ID: sysinv_check_06
:Test Title: verify wrong interface profiles will be rejected
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Wrong interface profiles are rejected

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create an interface profile of a worker node

.. code:: bash

  system ifprofile-add <profile_name> <worker-n>

2. Apply the profile you just created to a worker node with mismatching network interfaces

.. code:: bash

  system host-apply-ifprofile <worker-y> <profile_name>


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

2. the action is rejected with an error message

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_check_07
-----------------------

:Test ID: sysinv_check_07
:Test Title: Check Resource Usage panel is working properly
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Resource usage in Horizon works as expected.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Login to OpenStack Horizon using 'admin'

2. Go to Admin / Overview

3. Download a CVS summary

4. Check the file contains the right information.


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

2. Reports should be displayed without issue

3. csv report should be downloaded.

4. report contains the same information as displayed.

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_check_08
-----------------------

:Test ID: sysinv_check_08
:Test Title: Delete the mgmt. interface and re-add it to the same port
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Delete the mgmt. interface and re-add it to the same port

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

On a working configuration, use a worker node

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Lock the worker node

.. code:: bash

  system host-lock worker-1

2. Delete the mgmt interface

.. code:: bash

  system host-if-list worker-1 , grep mgmt
  system host-if-delete worker-1 <mgmt UUID>

3. Re-add the mgmt interface

.. code:: bash

  system host-if-add -c platform worker-1 mgmt0 <name or UUID interface>


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

the mgmt interface is successfully added - the communication over the mgmt. interface is working

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_check_09
-----------------------

:Test ID: sysinv_check_09
:Test Title: verify that the cpu data can be seen via cli
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

host-cpu-list shows the right information

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. On a worker node, list the cpu processors using

.. code:: bash

  system host-cpu-list worker-1

2. show the detailed information of a specific logical core

.. code:: bash

  system host-cpu-show worker-1 <logical_cpu_number>


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. get the list without errors

2. the information about numa_node, physical_core, assigned_function and etc. are displayed correctly

~~~~~~~~~~
References
~~~~~~~~~~

N/A


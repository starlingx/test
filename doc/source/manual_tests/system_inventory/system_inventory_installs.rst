=========================
System Inventory/Installs
=========================

.. contents::
   :local:
   :depth: 1

-----------------------
sysinv_inst_01
-----------------------

:Test ID: sysinv_inst_01
:Test Title: Install with with dynamic IP addressing
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Install using dynamic IPs

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Install controller-0, configure it with system configuration file, using DYNAMIC_ALLOCATION IP addressing

2. Bring up controller-1:

- Verify the DHCP discover FM log occurs as expected on host discovery

- Verify that Mgmt. interface FM alarms are raised and cleared as expected

- Check the mgmt IP addresses assigned are in expected range (as specified in /etc/dnsmasq.conf)

3. Bring up the system and check the system functioning as expected

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. the active controller is up and all services are running

2. DHCP discover FM log occurs as expected on host discovery

   - mgmt. or infra. interface FM alarms are raised and cleared as expected

   - mgmt. and infra. IP addresses assigned are in expected range

3. Config is up and running

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_inst_02
-----------------------

:Test ID: sysinv_inst_02
:Test Title: Install with with static addressing and pxeboot
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Install using static IPs

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Install controller-0, configure it with system configuration file with STATIC_ALLOCATION IP addressing and pxeboot

2. Bring up controller-1

- Add the host to the inventory

.. code:: bash

  system host-add -n controller-1 -p controller -i <mgmt_ip>


- power on the node and configure it after install finishes


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. active controller is up and all servers are running

2.  mgmt. interface FM alarms are raised and cleared as expected

- static IPs in mgmt. range are accepted when update the personality of the node


~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_inst_03
-----------------------

:Test ID: sysinv_inst_03
:Test Title: Reinstall a node on a dynamic addressing system
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Reinstalling a node using dynamic IPs

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

A configuration already working, using dynamic IPs

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Lock the host to be reinstalled - worker-1 in this case

.. code:: bash

  system host-lock worker-1

2. Delete the host from inventory

.. code:: bash

  system host-delete worker-1

3. Power off the host

4. Power it on (make sure it boots from management NIC)

5. Configure the node personality

.. code:: bash

  system host-update <id> personality=worker hostname=worker-1

6. Allow the node to be installed and proceed to configure it.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. node gets locked

2. node doesn't show up in host-list

5. node with worker personallity assigned

6. node working in the config


~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_inst_04
-----------------------

:Test ID: sysinv_inst_04
:Test Title: Reinstall a node on a static addressing system
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Reinstalling a node using static IPs

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

A configuration already working, using static IPs

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Lock the host to be reinstalled - worker-1 in this case

.. code:: bash

  system host-lock worker-1

2. Delete the host from inventory

.. code:: bash

  system host-delete worker-1

3. Power off the host

4. Add the host to the inventory

.. code:: bash

  system host-add -n worker-1 -p worker -i <mgmt_ip>

5. Power it on (make sure it boots from management NIC)

6. Allow the node to be installed and proceed to configure it.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. node gest locked

2. node doesn't show up in host-list

4. node with worker personallity assigned

6. node working in the config


~~~~~~~~~~
References
~~~~~~~~~~

N/A



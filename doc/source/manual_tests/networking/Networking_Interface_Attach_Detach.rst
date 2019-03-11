====================================
Networking Interface Attach / Detach
====================================

The Attach / Detach subdomain should cover all the possible scenarios where we
can loose connection between NIC`s, this is no matter the kind of hardware or
virtual environment that we are using for our testing. In some cases we want
to know how is the NIC driver going to work with a simple unplug action.

.. contents::
   :local:
   :depth: 1

--------------------
NET_IN_AT_DA_07
--------------------

:Test ID: NET_IN_AT_DA_07
:Test Title: Detach and attach on instances with E1000 interfaces (hardware).
:Tags: Interface Attach/Detach

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify interface detach and attach on instances with E1000 interfaces over
hardware.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) Instances created with e1000 network driver.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Get subnet ID for created network.

   ::

   $ openstack network list



2. From subnet get por ID.

   ::

   $ openstack port list


3. Detach the port by using the following command line:

   ::

      $ openstack stack port set <port id> --device none

4. Attach the port back.

   ::

     $ openstack port set <port id> --device <vm id>

5. Perform VM operations such as stop, start/pause/Unpause Suspend/Resume and
migration.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

After the detach / attach operation, our VM should be alive and capable of
performing all kind or regular actions.

--------------------
NET_IN_AT_DA_08
--------------------

:Test ID: NET_IN_AT_DA_08
:Test Title: Detach and attach on instances with e1000 (virtualized).
:Tags: Interface Attach/Detach

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) Instances created with rtl8139 network driver.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Get subnet ID for created network.

   ::

   $ openstack network list



2. From subnet get por ID.

   ::

   $ openstack port list


3. Detach the port by using the following command line:

   ::

      $ openstack stack port set <port id> --device none

4. Attach the port back.

   ::

     $ openstack port set <port id> --device <vm id>


5. Perform VM operations such as stop, start/pause/Unpause Suspend/Resume and
migration.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

After the detach / attach operation, our VM should be alive and capable of
performing all kind or regular actions.

--------------------
NET_IN_AT_DA_09
--------------------

:Test ID: NET_IN_AT_DA_09
:Test Title: Detach and attach on instances with rtl8139 (hardware).
:Tags: Interface Attach/Detach

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) Instances created with rtl8139 network driver.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Get subnet ID for created network.

   ::

   $ openstack network list



2. From subnet get por ID.

   ::

   $ openstack port list


3. Detach the port by using the following command line:

   ::

      $ openstack stack port set <port id> --device none

4. Attach the port back.

   ::

     $ openstack port set <port id> --device <vm id>

5. Perform VM operations such as stop, start/pause/Unpause Suspend/Resume and
migration.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

After the detach / attach operation, our VM should be alive and capable of
performing all kind or regular actions.

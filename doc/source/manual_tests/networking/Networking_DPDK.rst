===============
Networking DPDK
===============

The Data Plane Development Kit is a set of data plane libaries and network
interface controller drivers for fast packet processing, currently managed as
an open-source project. Our intention with this subdomain is to demostrate
that the implementation for those libraries are healthy engouht and is not
causing issues for the networking domain. This include all the possible
scenarios.

.. contents::
   :local:
   :depth: 1

--------------------
NET_DPDK_OVS_02
--------------------

:Test ID: NET_DPDK_OVS_02
:Test Title: Verify OVS version
:Tags: DPDK

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test should print on the screen the OVS version that we are using in our
environment. Go to [0] for references.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) Any configuration up and running.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Execute the following instruction:

::

      $ovs-vswitch --version

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

The instruction should print on the screen the OVS version installed in our
system. In this case is DPDK 2.11.

--------------------
NET_DPDK_OVS_03
--------------------

:Test ID: NET_DPDK_OVS_03
:Test Title: Verify DPDK version
:Tags: DPDK

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test should print on the screen the DPDK version that we are using in our
environment. Go to [1] for references.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) Any configuration up and running.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Execute the following instruction:

::

      $ovs-vsctl get Open_vSwitch . dpdk_version

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

The instruction should print on the screen the DPDK version installed in our
system. In this case is DPDK 18.11.

~~~~~~~~~~~
References:
~~~~~~~~~~~

[0] - [https://docs.openvswitch.org/en/latest/intro/what-is-ovs/]
[1] - [https://www.dpdk.org]

==================================
Networking Internal DNS resolution
==================================

Users of an OpenStack cloud would like to look up their instances by name in
an intuitive way using the Domain Name System. This subdomain show the way
that we are testing this feature.

.. contents::
   :local:
   :depth: 1

-----------------
NET_IN_DNS_RES_03
-----------------

:Test ID: NET_IN_DNS_RES_03
:Test Title: Disable internal DNS on AIO simplex system
:Tags: DNS

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test case shows the way that DNS can be disabled and how is going to
affect the communication with the VM's.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a)Install any AIO symplex system.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Enable DNS resolution (Ml2 network service parameter will be created with
   value=dns), by issuing the following commands:

   ::

      $ system service-parameter-add network ml2 exentsion_drivers=dns
      $ system service-parameter-add network default dns_domain=<your_domain.com>


2. Lock/Unlock controllers.

3. Boot 2 VM's.

4. Ping between VM's via their hostnames. The communication between VM's
   should be successful.

5. Perform VM actions: stop/pause/resume. VM's survives actions and internal
   DNS resolution is not impacted.

6. Disable DNS resolution by deleting system service parameter associated with
   network/dns service.

   ::

      $ system service-parameter-delete <net-id>

7. Lock/Unlock the controller.

8. Create 2 new VM's.

9. Attempt to ping between new VM's via their hostnames.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

After disabling/deleting internal dns resolution, VM's shouldn't be able to
resolve IP's via hostnames.

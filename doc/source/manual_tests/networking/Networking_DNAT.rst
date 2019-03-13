===============
Networking DNAT
===============

.. contents::
   :local:
   :depth: 1

-----------
NET_DNAT_08
-----------

:Test ID: NET_DNAT_08
:Test Title: External Access to VM through UDP-lite.
:Tags: DNAT

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify that we have external access to a Virtual Machine using UDP-lite
protocol.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) 4 VMs

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create two port forwarding rules

::

      $ neutron portorwarding-create <router> --inside-addr <addr>--inside-port <port#> --outside-port <port#> --protocol {udp-lite} [--description <user defined string>]

3. Create 2 porforwanding from GUI, admin-> routers -> tenant <id>-router->
   Port Forwarding-> Add Rule:

::

    public-ip:8080 (upd-lite) -> private-ip 1:80 (VM1)
    public-ip:8081 (upd-lite) -> private-ip2 1:80 (VM2)
    public-ip:8082 (upd-lite) -> private-ip3 1:80 (VM3)
    public-ip:8084 (upd-lite) -> private-ip4 1:80 (VM4)

4. Enable SNAT for the router:

::

      $ neutron router-update tenant<id>-router --external-gateway-info type-dict network_id=<external network id>,enable_snat=true

4. Connect through ssh to VM to make port open to listen.

5. Send upd-list packets to each VM from outside. Verify only the routed VM
   received packets from outside using the designated port with the specified
   protocol,

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

With the port forwarding, we should be able to send upd-lite packages through
each VM with the port specification.

-----------
NET_DNAT_11
-----------

:Test ID: NET_DNAT_11
:Test Title: External Access to VM after VM Maintenance
:Tags: DNAT

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify that external access to the VM still open after any of the VM
Maintenance operation such as Live-Migrate, Cold-Migrate and Evacuation.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

1. Create a Router

2. Launch a VM

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create a port forwarding rule

::

      $ neutron portforwarding-create <router> --insde-addr <addr> --inside-port <port#> --outside-port <port#>

2. Perform live migration

3. Evacuate VM

4. Perform cold migration

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

After the port rule creation, the instance should keep comunication with the
compute-controller after regular maintenance operations.

-----------
NET_DNAT_12
-----------

:Test ID: NET_DNAT_12
:Test Title: Access to VM works after Locking operations
:Tags: DNAT

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify that VM stills accessible after lock/unlock operations on compute node.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

1. Create a Router
2. Launch a VM

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create a port forwarding rule

::

      $ neutron portforwarding-create <router> --inside-addr <addr> --inside-port <port#>  --outside-port <port#>

2. Perform evacuate of the VM on the existing compute.

3. Verify access after the lock/unlock operation of the VM, the VM should be
   reachable. This can be accomplished with a ping to the vm following the port
   forwarding rule.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

This test should show that the VM is reachable after a normal lock/unlock
operation, no matter that the compute where it was created with specific port
rules and forwarding.

~~~~~~~~~~~
References:
~~~~~~~~~~~

[0] - [https://docs.openstack.org/newton/networking-guide/intro-nat.html]

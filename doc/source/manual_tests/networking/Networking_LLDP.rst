===============
Networking LLDP
===============

.. contents::
   :local:
   :depth: 1

--------------
NET_HP_LLDP_01
--------------

:Test ID: NET_HP_LLDP_01
:Test Title: System list of lldp host through the agent.
:Tags: LLDP

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test case verify that the agent for LLDP host port is working.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Environment up and running with instances.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Log in as Keystone admin if it is needed

2. Execute "system host-lldp-agent-list <node>"

   ::

      $ system host-lldp-agent-list <node>

3. Verify the output

   ::

     +--------------------------------------+------------+----------+------------+---------+--------------------------------------+--------------------+
     | uuid                                 | local_port | status   | chassis_id | port_id | system_name                          | system_description |
     +--------------------------------------+------------+----------+----------  +---------+--------------------------------------+--------------------+
     | c922211f-82f2-4b0c-8f72-0d5a811eeca3 | eth1000    | rx=      | 52:54:00   | 52:54   | controller-0:                        | CentOS Linux 7     |
     |                                      |            | enabled, | :3b:65:    | :00:    | f9a2c26a-0365-4bc7-a118-db501bb5a093 | (Core)             |
     |                                      |            | tx=      | df         | 3b:65   |                                      |                    |
     |                                      |            | enabled  |            | :df     |                                      |                    |
     |                                      |            |          |            |         |                                      |                    |
     +--------------------------------------+------------+----------+------------+---------+--------------------------------------+--------------------+

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

If the command line is working, lldp agent should show information regarding
the host where you are running it. Otherwise the agent is not running.

--------------
NET_HP_LLDP_02
--------------

:Test ID: NET_HP_LLDP_01
:Test Title: System list of lldp host through the agent.
:Tags: LLDP

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

With this test we are showing all the "neighbors" using the LLDP agent.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Environment up and running with instances.

Test Steps
~~~~~~~~~~

1. Log in as Keystone admin if it is needed.

2. Execute "system host-lldp-neighbor-show <id>":

   ::

      $ system host-lldp-neighbor-show <id>

      ~(keystone_admin)]$ system lldp-agent-show a94bd2be-94c3-4c00-aa6d-615f485f6a8a
      +---------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
      | Property                                                                                         | Value                                                                                                                                                              |
      +---------------------+-----------------------------------------------------------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------|
      | uuid                                                                                             | a94bd2be-94c3-4c00-aa6d-615f485f6a8a | host_uuid | 6d890372-852a-4af9-b328-d1e37861e940 | created_at | 2019-03-06T22:13:55.813757+00:00 | updated_at | None | uuid |
      | a94bd2be-94c3-4c00-aa6d-615f485f6a8a                                                             | local_port | enp2s1 | chassis_id | 52:54:00:52:7f:03 | port_identifier | 52:54:00:b2:cb:cb | ttl | 120 | system_description | CentOS Linux 7                       |
      | (Core) Linux 3.10.0-862.11.6.el7.36.tis.x86_64 #1 SMP PREEMPT Mon Mar 4 06:18:35 UTC 2019 x86_64 | system_name | controller-0:acc2b608-93d7-489d-82c7-e7f649fd2b13                                                                                                    |
      | system_capabilities                                                                              | bridge, router | management_address | 10.10.10.3, fe80::5054:ff:feb2:cbcb | port_description | enp2s1 | dot1_lag | capable=y,enabled=n | dot1_vlan_names           |
      | None                                                                                             | dot3_mac_status | None | dot3_max_frame | None                                                                                                                     |
      +---------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

3. Verify that the command line output shows the neighbor information
according with the ID.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

Instruction should show main characteristics from neighbor using lldp agent.

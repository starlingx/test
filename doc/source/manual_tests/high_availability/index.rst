
=================
High availability
=================

Titanium Clouds Service Management (SM) and Maintenance (Mtce)
Systems handle transient and persistent networking failures between
controllers and service hosts (storage/compute) For instance, a
transient loss of Management Network Carrier on the active controller
currently triggers an immediate fail-over to the standby controller even
though the very same failure may exist for that controller as well ; i.e.
it may be no more healthy that the current active controller. A persistent
loss of heartbeat messaging to several or all nodes in the system results in
the forced failure and reboot of all affected nodes once connectivity has been
re-established.In most of these cases the network event that triggered fault
handling is external to the system ; i.e. the reboot of a common messaging
switch for instance, and truly beyond the control of Titanium Cloud HA
(High Availability) Services. In such cases it's best to be more fault
tolerant/forgiving than over active.


----------------------
Overall  Requirements
----------------------

This test will require access to the following configurations:
- Regular system
- Storage system
- AIO-DX systems

----------
Test Cases
----------

.. contents::
   :local:
   :depth: 1

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
HA_Cloud_Recovery_improvements_01
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Test ID: HA_Cloud_Recovery_improvements_01
:Test Title: test_split_brain_avd_activer_or_standby_based_on_only_storage_and
 standby_controller_blocked_on_active_controller
:Tags: P2,HA,Recovery improvement,regression


+++++++++++++++++++
Testcase Objective
+++++++++++++++++++
Purpose of this test is to verify split brain scenario swact on active
controller by blocking standby controller and storage on active controller

++++++++++++++++++++
Test Pre-Conditions
++++++++++++++++++++
 System should be a storage system

+++++++++++
Test Steps
+++++++++++
1. Using below cli disconnects management storage-0 and controller-1 active
   controller-0. Execute below command to block both storage and controller
   first storage should be blocked and immediately controller should be
   blocked.
   code::
   Execute sudo iptables -I INPUT 1 -s 192.168.222.204 -j DROP
   ...
2. Verify connection failure alarm
3. Verify controller-1 becomes active. Verify system host-list from
   controller-1
4. Reboot new standby controller-0. Once reboot complete verify system
   host-list from active controller.

++++++++++++++++++
Expected Behavior
++++++++++++++++++
 controller-1 becomes active
 System host-list shows right states

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
HA_Cloud_Recovery_improvements_02
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Test ID: HA_Cloud_Recovery_improvements_02
:Test Title: test_aio_dx_direct_active_controller_lost_connection_to_standby_ip
:Tags: P2,HA,Recovery improvement,regression

+++++++++++++++++++
Testcase Objective
+++++++++++++++++++
Purpose of this test is to verify standby controller reboot when it is lost
connectivity to active controller.

++++++++++++++++++++
Test Pre-Conditions
++++++++++++++++++++
System should be AIO-DX direct connection. System should be connected to
BMC module and provisioned. If the BMC not provisioned expected behavior
there wont be reboot on standby controller

+++++++++++
Test Steps
+++++++++++
1. Block the standby ip(Management ip) from active controller.
   code::
   iptables -I INPUT 1 -s 192.168.222.204
   ...

++++++++++++++++++
Expected Behavior
++++++++++++++++++
The stadby controller(controller-1) becomes active
System host-list shows right states
controller-0 reboots if the BMC provisioned

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
HA_Cloud_Recovery_improvements_03
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Test ID: HA_Cloud_Recovery_improvements_03
:Test Title: test_split_brain-avd_aio_dx_direct_active_controller_lost
 connection_to_standby_ip_table_drop_on_mgt_infra_and_oam
:Tags: P2,HA,Recovery improvement,regression

+++++++++++++++++++
Testcase Objective
+++++++++++++++++++
To verify split-brain scenario by triggering connection failure on MGT infra
and OAM  on AIO-DX-Direct standby controller

++++++++++++++++++++
Test Pre-Conditions
++++++++++++++++++++
System should be a AIO-DX-Direct connected system

+++++++++++
Test Steps
+++++++++++
1. Provision BMC verify BMC provisioned.(if BMC not available there won't
   be a reboot for loss of connection expected behavior at the time of
   connection loss is different)
2. From standby controller to active controller to drop MGT infra and OAM.
   Example as below.
   code::
   sudo iptables -I INPUT 1 -s 192.168.204.4 -j DROP && sudo iptables -I \
   INPUT 1 -s 192.168.205.3 -j DROP && sudo iptables -I \
   INPUT 1 -s 128.150.150.96 -j DROP
   ...
3. Verify loss of connectivity and alarm on active controller

++++++++++++++++++
Expected Behavior
++++++++++++++++++
 Verify loss of connectivity and alarm on active controller
 System host-list shows right states

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
HA_Cloud_Recovery_improvements_04
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Test ID: HA_Cloud_Recovery_improvements_04
:Test Title: test_split-brain-avd_active/standby_number_of_the_nodes_reachable
 _changes_couple_of_times
:Tags: P2,HA,Recovery improvement,regression

++++++++++++++++++++
Testcase Objective:
++++++++++++++++++++
Purpose of this test is to verify Active standby controller selection criteria
on split brain scenario is based on healthier controller.This scenario will be
repeated after active standby selected and again connection failure on compute.

+++++++++++++++++++++
Test Pre-Conditions:
+++++++++++++++++++++
The system should have at least 3 or more computes with 2 controller.

+++++++++++
Test Steps
+++++++++++

1. From Active controller controller-0 block control and compute-0
   communication (if management and infra provisioned both need to be blocked)
   code::
   sudo iptables -I INPUT  1 -s 192.168.223.57  -j DROP && sudo iptables\
   -I INPUT  1 -s 192.168.222.156 -j DROP  && sudo iptables -I INPUT 1 \
   -s 192.168.222.4 -j DROP  && sudo iptables -I INPUT 1 -s \
   128.224.150.57 -j DROP
   ...
2. Verify connection failure alarm.
3. Verify swact
4. unblock compute-0 to controller-0 from controller-0 suing iptables command.
   code::
   sudo iptables -D INPUT -s 192.168.223.57  -j DROP && sudo iptables -D \
   INPUT -s 192.168.222.156 -j DROP  && sudo iptables -D INPUT -s \
   192.168.222.4 -j DROP  && sudo iptables -D INPUT -s 192.168.223.4 -j \
   DROP
   ...
5. Repeat the above step current active controller block traffic on
   controller-1 to compute-0

+++++++++++++++++++
Expected Behavior
+++++++++++++++++++
 controller-1 becomes active
 System host-list shows right states

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
HA_Cloud_Recovery_improvements_05
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Test ID: HA_Cloud_Recovery_improvements_05
:Test Title: test_MNFA_timeouts_2mins_1_hour
:Tags: P2,HA,Recovery improvement,regression

++++++++++++++++++++
Testcase Objective
++++++++++++++++++++
Purpose of this test is to validate the trigger of MNFA(Multi Node Failure
Avoidance)  mode  trigger on alarm based on different timeouts 2mins or 1 hour

+++++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++++
The system should have at least 3 or more computes with 2 controller.

+++++++++++
Test Steps
+++++++++++
1. From Active controller set mnfa_timeout (2mins or 1 hour ) on MNFA can
   stay active before graceful recovery of affected hosts. Use below commands.
   Eg:
   code::
   system service-parameter-list
   system service-parameter-modify service=platform section=maintenance \
   mnfa_timeout = 2 service
   system service-parameter-apply platform
   ...
2. Apply the change and alarm 250.001   controller-0 Configuration is
   out-of-date cleared using command
   system service-parameter-apply platform
3. Trigger heart beat failure by powering off any nodes other than active
   controller
4. Verify event-list --log  to see below MNFA enter and exit. If the
   mnfa_timeout is set to 120
   seconds mnfa enter exit log time difference will be 120 seconds.
   If is it set to 1 hour it will be 1hour. Below stings will be seen on alarm.

   host=controller-1.event=mnfa_enter
   host=controller-1.event=mnfa_exit

++++++++++++++++++
Expected Behavior
++++++++++++++++++
In the above test MNFA enter and exit would be triggered in event-list log

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
HA_Cloud_Recovery_improvements_06
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Test ID: HA_Cloud_Recovery_improvements_06
:Test Title: test_MNFA_timeouts_default
:Tags: P2,HA,Recovery improvement,regression

+++++++++++++++++++
Testcase Objective
+++++++++++++++++++
Purpose of this test is to validate the trigger of MNFA mode  with the default
values.

++++++++++++++++++++
Test Pre-Conditions
++++++++++++++++++++
The system should have at least 3 or more computes with 2 controller.

+++++++++++
Test Steps
+++++++++++

1. From Active controller
   Set mnfa_timeout (2mins or 1 hour ) on MNFA can stay active before graceful
   recovery of affected hosts.
   Eg:
   To check current values for mnfa_timeout use system service-parameter-list
   code::
   system service-parameter-modify service=platform section=maintenance \
   mnfa_timeout=<value>
   system service-parameter-apply platform
2. Apply the change and alarm 250.001 controller-0 Configuration is
   out-of-date cleared using command system service-parameter-apply platform
3. Trigger heart beat failure by powering off any nodes other than active
   controller.
4. Verify system event-list --log to see below MNFA enter and exit.
5. Verify system hosts-list. It will show hosts as degraded when host is in
   off-line during the MNFA enter and exit.
   host=controller-1.event=mnfa_enter
   host=controller-1.event=mnfa_exit

++++++++++++++++++
Expected Behavior
++++++++++++++++++
In the above test MNFA enter and exit would be triggered in event-list log

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
HA_Cloud_Recovery_improvements_07
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Test ID: HA_Cloud_Recovery_improvements_07
:Test Title: test_pull_management_and_OAM_cable_on_active_controller
:Tags: P2,HA,Recovery improvement,regression

++++++++++++++++++++
Testcase Objective:
++++++++++++++++++++
This test is to verify OAM & MGT cable pull alarm and swact

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++
Any 2+2 system installed latest load.

+++++++++++
Test Steps
+++++++++++

1. Verify no alarms for fm alarm-list
2. Physically remove OAM and MGT cable on active controller(controller-0) cable
3. Verify alarm ID (400.005,200.005)
4. Verify standby controller(controller-0) was swacted sudo sm-dump
5. Verify system host-list on new active controller
   all the hosts are available and standby controller off-line.

++++++++++++++++++
Expected Behavior
++++++++++++++++++
system swact with alarms for cable pull on OAM and MGT

:Test ID: HA_Cloud_Recovery_improvements_08
:Test Title: test_pull_management_cable_on_standby_controller
:Tags: P2,HA,Recovery improvement,regression

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
HA_Cloud_Recovery_improvements_08
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

++++++++++++++++++++
Testcase Objective:
++++++++++++++++++++
Pull management cable on standby and verify alarm.

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++
Any 2+2 system installed latest load.

++++++++++++
Test Steps:
++++++++++++

1. Verify no alarms for fm alarm-list
2. Physically remove  MGT cable on standby controller(controller-0) cable
3. Verify current alarm list fm alarm-list alarm id(400.005,200.005)
4. Verify no change in active controller and other hosts states standby
   host will be off-line.
   code ::
   system host-list
   ...

++++++++++++++++++
Expected Behavior
++++++++++++++++++
Verify management failed alarm  ID (400.005,200.005)
Verify hosts state system host-list

-----------
References:
-----------
https://wiki.openstack.org/wiki/StarlingX/Containers/Installationem

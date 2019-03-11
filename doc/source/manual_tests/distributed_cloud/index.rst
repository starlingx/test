=================
Distributed Cloud
=================

This test plan covers Distributed Cloud regression. It covers basic
functionality for the following features:

- Alarm
- Installation and commissioning
- DOR
- Keystone
- Process Kill
- Share Configuration
- VM operational

--------------------
Overall Requirements
--------------------

IP4 & IP6 Distributed Cloud system installed successful.

----------
Test Cases
----------

.. contents::
   :local:
   :depth: 1

~~~~~~~~~~~
DC_ALARM_01
~~~~~~~~~~~

:Test ID: DC_ALARM_01
:Test Title: test_Alarm Aggregation
:Tags: P4, Distributed Cloud, Alarm, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

This test is ensure to alarm aggregation working well in StarlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

IP4 Distributed Cloud system installed successful.

++++++++++
Test Steps
++++++++++

1. Add subcloud
    a. Row appears in dcmanager alarm summary

2. Manage subcloud
    a. Snmp trapdest pushed to subcloud
    b. Row in dcmanager alarm summary updated to actual alarm values

3. Delete Subcloud
    a. Row removed from dcmanager alarm summary

4. Trigger Alarm (Managed Subcloud)
    a. System alarm-summary on subcloud matches dcmanager alarm summary on
       system controller within 10 seconds

5. Clear Alarm (Managed Subcloud)
    a. System alarm-summary on subcloud matches dcmanager alarm summary on
       system controller within 10 seconds

6. Trigger Alarm (Unmanaged Subcloud): (previously managed
    a. System alarm-summary on subcloud matches dcmanager alarm summary on
       system controller within 10 seconds

7. Clear Alarm (Unmanaged Subcloud) : (previously managed
    a. System alarm-summary on subcloud matches dcmanager alarm summary on
       system controller within 10 seconds

8. Cut connectivity to subcloud, trigger alarms
    a. System alarm-summary on subcloud matches dcmanager alarm summary on
       system controller 15 minutes of reconectivity,

9. Large scale alarm event: Trigger many alarms quickly on subcloud-1. During
   this period slowly (less than 10 per minute) trigger alarms on subcloud-4.
   Subcloud-1 alarm summary updates once every 30 seconds on subcloud-4
   matches dcmanager alarm summary on system controller within 10 seconds (i.e
   not throttled).

10. Trigger large amount of alarms quickly for a long time on all subclouds
    Each alarm summary updates once every 30 seconds until the event is over

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

As above.

~~~~~~~~~~~~~~~~~~
DC_INSTALLATION_02
~~~~~~~~~~~~~~~~~~

:Test ID: DC_INSTALLATION_02
:Test Title: Basic installation and commissioning of distributed cloud system non-interactive config controller
:Tags: P1, Distributed Cloud, Alarm, Regression

++++++++++++++
Test Objective
++++++++++++++

This test is to ensure the installation working well in StarlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

1. Provision a distributed cloud system using the interactive
   config_controller using the customer documented procedure.
2. Validate the fields make sense and will not accept erroneous information.
3. Ensure you have a working system at the end of the procedure,
   i.e. VMs can be launched, volumes created, subclouds operating as expected.

In this test, enable the following: IPv6

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Installation success.

~~~~~~~~~~~~~~~~~~
DC_INSTALLATION_03
~~~~~~~~~~~~~~~~~~

:Test ID: DC_INSTALLATION_03
:Test Title: test_Delete a subcloud and readd with same config
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure delete subcloud working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Subcloud installed.

++++++++++
Test Steps
++++++++++

Delete a subcloud.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Subcloud deleted successfully.

~~~~~~~~~
DC_LOG_04
~~~~~~~~~

:Test ID: DC_LOG_04
:Test Title: test_Distributed cloud log file generation and rotation
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure DC log working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

DC lab installed.

++++++++++
Test Steps
++++++++++

1. Distributed cloud log files should be found here:

   .. code:: sh

     /var/log/dcmanager/*
     /var/log/dcorch/*

2. Ensure the directories are listed in /etc/logrotate.d/syslog
3. Check the rotation by 'vim /etc/logrotate.d/syslog/' and edit
   the 'size' field to a small value, e.g. 10K:

   .. code:: sh

     /var/log/dcmanager/*.log
     /var/log/dcorch/*.log
     {
       nodateext
       size 10M
       start 1
       rotate 20
       missingok
       notifempty
       compress
       sharedscripts
       postrotate
       systemctl reload syslog-ng > /dev/null 2>&1 || true
       endscript
     }

4. ps -ef | grep logmgmt and then kill the process
5. ps -ef | grep syslog-ng and then kill the process
6. Ensure the logs are rotated
7. Restore the config at the end of the test

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Every steps executed successfully.

~~~~~~~~~
DC_DOR_05
~~~~~~~~~

:Test ID: DC_DOR_05
:Test Title: test_DOR: Entire System (all subclouds managed)
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure DOR for entire system working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Distributed Cloud system is installed and VMs have been created,
traffic is running, ping test is running.

++++++++++
Test Steps
++++++++++

Do a full system DOR.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Ensure the entire system recovers.

~~~~~~~~~
DC_DOR_06
~~~~~~~~~

:Test ID: DC_DOR_06
:Test Title: test_DOR: Single Subcloud - Managed
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure DOR for Single managed subcloud working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Distributed Cloud system is installed and VMs have been created, traffic
is running, ping test is running.

++++++++++
Test Steps
++++++++++

Do a DOR only on a managed subcloud.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Ensure the system recovers.

~~~~~~~~~
DC_DOR_07
~~~~~~~~~

:Test ID: DC_DOR_07
:Test Title: test_DOR: Single Subcloud - Unmanaged
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure DOR for Single unmanaged subcloud working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Distributed Cloud system is installed and VMs have been created, traffic
is running, ping test is running.

++++++++++
Test Steps
++++++++++

Do a DOR only on a unmanaged subcloud.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Ensure the system recovers.

~~~~~~~~~
DC_DOR_08
~~~~~~~~~

:Test ID: DC_DOR_08
:Test Title: test DOR System Controller
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++++++
Testcase Objective
++++++++++++++++++

To ensure DOR for system controller working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Distributed Cloud system is installed and VMs have been created, traffic
is running, ping test is running.

++++++++++
Test Steps
++++++++++

Do a DOR only on the system controller.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Ensure the system recovers and ensure the subclouds are operational
while the system controller is down.

~~~~~~~~~~~~~~~~~~
DC_INSTALLATION_09
~~~~~~~~~~~~~~~~~~

:Test ID: DC_INSTALLATION_09
:Test Title: test_Installation and Commissioning: Configure AIO-DX Subcloud - IPv4
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure installation DX IPv4 working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Configure AIO-DX subclouds in IPv4.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Ensure dc DX subcloud installation successfully.

~~~~~~~~~~~~~~~~~~
DC_INSTALLATION_10
~~~~~~~~~~~~~~~~~~

:Test ID: DC_INSTALLATION_10
:Test Title: test_Installation and Commissioning: Configure AIO-DX Subcloud - IPv6
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure installation DX IPv6 working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Configure AIO-DX subclouds in IPv6.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Ensure dc DX subcloud installation successfully.

~~~~~~~~~~~~~~~~~~
DC_INSTALLATION_11
~~~~~~~~~~~~~~~~~~

:Test ID: DC_INSTALLATION_11
:Test Title: test_Installation and Commissioning: Configure AIO-SX Subcloud - IPv4
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure installation SX IPv4 working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Configure AIO-SX subclouds in IPv4.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Ensure dc SX subcloud installation successfully.

:Test ID: DC_INSTALLATION_12
:Test Title: test_Installation and Commissioning: Configure AIO-SX Subcloud - IPv6
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure installation DX IPv6 working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Configure AIO-SX subclouds in IPv6.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Ensure dc SX subcloud installation successfully.

~~~~~~~~~~~~~~~~~~
DC_INSTALLATION_13
~~~~~~~~~~~~~~~~~~

:Test ID: DC_INSTALLATION_13
:Test Title: test_Installation and Commissioning: Configure Standard Subcloud - IPv4
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure installation standard IPv4 working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Configure Standard subclouds in IPv4.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Ensure dc Standard subcloud installation successfully.

:Test ID: DC_INSTALLATION_14
:Test Title: test_Installation and Commissioning: Configure Standard Subcloud - IPv6
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure installation standard IPv6 working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Configure Standard subclouds in IPv6.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Ensure dc Standard subcloud installation successfully.

~~~~~~~~~~~~~~~~~~
DC_INSTALLATION_15
~~~~~~~~~~~~~~~~~~

:Test ID: DC_INSTALLATION_15
:Test Title: test_Installation and Commissioning: Setup Distributed Cloud with IPv6 configuration
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure installation standard IPv6 working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

As the title.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Ensure dc installation successfully.

~~~~~~~~~~~~~~
DC_KEYSTONE_16
~~~~~~~~~~~~~~

:Test ID: DC_KEYSTONE_16
:Test Title: test_endpoint list from subcloud region, no longer lists all services in the endpoint region
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure endpoint list from subcloud working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

From the subcloud region, run:

.. code:: bash

  $ openstack endpoint list

  returns eg. Region subcloud-6

  Service Types eg. placement, compute, cloudformation, network, patching,
  alarming, metric, image, event, orchestration, nfv, platform, volumev2
  (each listed with Interface admin, internal and public)

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Confirm:

- The only endpoints returned should be for that specific subcloud region
  Service Type (Name)
  identity (keystone), image (glance), volume (cinder) platform (sysinv),
  alarming, placement, compute (nova), orchestration cloudformation (heat),
  network (neutron), patching, metering (ceilometer), nfv (vim) etc.
- Keystone Service Name should only list a small number of endpoints
  e.g. returns ID, Region, service Name, Service Type, Enabled, Interface, URL
  pass
  BUILD_ID="2018-07-08_21-40-00"
  System_Controller WCp 90-91

~~~~~~~~~~~~~~
DC_KEYSTONE_17
~~~~~~~~~~~~~~

:Test ID: DC_KEYSTONE_17
:Test Title: test_endpoint list from central region should return the service catalog for all Regions
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure endpoint list from central region working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

From the centrol region, run:

.. code:: sh

  $ openstack endpoint list

  eg. the ID, Region (such as subcloud-#), Service Name keystone, Service Type
  identity and respective Interface URLs are returned

  | subcloud-1 | keystone | identity | True | internal
  | http://[fd01:2::2]:5000/v3 |
  | subcloud-1 | keystone | identity | True | admin
  | http://[fd01:2::2]:5000/v3 |
  | subcloud-# | keystone | identity | True | internal
  | http://[fd01:3::2]:5000/v3 |
  | subcloud-# | keystone | identity | True | admin
  | http://[fd01:3::2]:5000/v3

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

From the central region, this returns the service catalog for all Regions. For
example, the central region includes an endpoint filter group for a particular
region: Region that is associated to the central keystone services project:

.. code:: sh

  Pass
  BUILD_ID=2018-07-08_21-40-00
  System_Controller wcp 90-91
  yow-cgcs-wildcat-89

~~~~~~~~~~~
DC_PKILL_18
~~~~~~~~~~~

:Test ID: DC_PKILL_18
:Test Title: test_Process Kill and Recovery in Subcloud
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure process killing on subcloud working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

1. Kill one critical processes in the system controller
   (use sm-dump to determine which are critical).
2. Ensure the system behaves as expected with respect to process recovery
   and alarming.
3. Ensure the system continues to operate after the process failure.
4. Repeat for one major processes.
5. Repeat for one minor processes.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All killed processes will be recovered.

~~~~~~~~~~~
DC_PKILL_19
~~~~~~~~~~~

:Test ID: DC_PKILL_19
:Test Title: test_Process Kill and Recovery: System Controller
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure process killing on system controller working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

++++++++++
Test Steps
++++++++++

1. Kill distributed cloud related processes using either:

   .. code:: sh

     ps -ef | grep <processname> to determine the pid OR
     sudo sm-dump --pid

2. Kill via `sudo kill -9 <pid>` or `sudo killall <processname>`.
3. After two kills, the max kills threshold should be reached in sm.log,
   and swact should occur.
4. Ensure the event log shows the failures.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All killed processes will be recovered. Here are observations from testing (for reference):

- dcorch-engine done (2 kills = swact)
- dcmanager-manager done (multiple kills done but no swact sometimes CGTS-9741)
- dcmanager-api done (2 kills = swact)
- dcorch-snmp done (2 kills = swact)
- dcorch-sysinv-api-proxy done (2 kills = swact)
- dcorch-nova-api-proxy done (kill once and the process cannot recover
  eventually we will swact CGTS-9742)
- dcorch-neutron-api-proxy done (kill once and swact. Tried later and saw kill
  once and process cannot recover - eventually we will swact CGTS-9742)
- dcorch-cinder-api-proxy done (similar behaviour to dcmanager-manager)
- drbd-patch-vault NOT SURE HOW TO KILL (tried systemctl and service
  but there is no process)
- patch-vault-fs NOT SURE HOW TO KILL (tried systemctl and service
  but there is no process)
- dcorch-patch-api-proxy (done, kill once and saw swact, later multiple kills
  and no swact, later two kills and a swact - inconsistent behaviour)

~~~~~~~~~~
DC_SYNC_20
~~~~~~~~~~

:Test ID: DC_SYNC_20
:Test Title: test_Shared Configuration Propagation: Cinder - Quotas
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure Shared Configuration Propagation, Cinder - Quotas on DC working well
in StarlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Assumption: The distributed cloud system is already installed and
commissioned. This includes a System Controller and multiple subclouds.
At least one subcloud should be in unmanaged state, meaning the changes
to that cloud should be queued until they can be propagated.

Note, this would assume that the subclouds are setup to use cinder storage
on the system controller.

1. Define the cinder quota on the System Controller.
2. Confirm that the changes are propagated to any subclouds that are managed.
3. Confirm that the changes are not propagated to subclouds that are not
   managed.
4. Manage the unmanaged subcloud.
5. Ensure it is eventually updated with the expected quotas.
6. Attempt to exceed the quota. Note, ensure this quota applies to
   all subclouds, not per individual subcloud.
7. Ensure this is rejected.
8. Attempt to update the quota locally on an unmanaged subcloud.
9. Ensure the subcloud can exceed the overall system quota.
10. Manage the unmanaged subcloud.
11. Ensure that nothing can be launched until the usage drops into
    the expected range.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~
DC_SYNC_21
~~~~~~~~~~

:Test ID: DC_SYNC_21
:Test Title: test_Shared Configuration Propagation: DNS
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure Shared Configuration Propagation DNS on DC working well in
StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Assumption: The distributed cloud system is already installed and
commissioned. This includes a System Controller and multiple subclouds.
At least one subcloud should be in unmanaged state, meaning the changes
to that cloud should be queued until they can be propagated.

1. Define valid DNS servers on the System Controller.
2. Confirm that the changes are propagated to any subclouds that are managed.
3. Confirm that DNS changes are not propagated to subclouds that are not
   managed.
4. Manage the unmanaged subcloud.
5. Ensure it is eventually updated with the expected DNS servers.
6. Restore the subcloud back to unmanaged state at the end of the test.
7. Repeat test but this time, remove one of the DNS servers.
8. Ensure the changes are propagated to the managed nodes but not unmanaged,
   but once the unmanaged node is managed, the changes should be propagated.
9. Repeat test but this time, include an invalid DNS server.
10. Ensure the changes are propagated to the managed nodes but not unmanaged,
    but once the unmanaged node is managed, the changes should be propagated.
11. Ensure there is no impact due to having an invalid DNS server propagated
    through the system.
12. Repeat test but this time make a local DNS change on the subcloud
    while the subcloud is unmanaged.
13. Ensure the DNS servers are not overwritten in the audit interval
    (10 minutes).
14. Change the subcloud so it is managed.
15. Verify the local changes are overwritten when the system is synchronized.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~
DC_SYNC_22
~~~~~~~~~~

:Test ID: DC_SYNC_22
:Test Title: test_Shared Configuration Propagation: Glance
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure Shared Configuration Propagation glance on DC working well in
StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

1. Create glance image in system controller: new image create.
2. Check new image seen on sub cloud: new image showing on sub cloud.
3. Launch VM by using new image in subcloud, VM launched.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~
DC_SYNC_23
~~~~~~~~~~

:Test ID: DC_SYNC_23
:Test Title: test Shared Configuration Propagation: Keystone - User Information
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure Shared Configuration Propagation keystone on DC working well in
StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Assumption: The distributed cloud system is already installed and
commissioned. This includes a System Controller and multiple subclouds.
At least one subcloud should be in unmanaged state, meaning the changes
to that cloud should be queued until they can be propagated.

++++++++++
Test Steps
++++++++++

1. SC (System Controller): create a new user, should see the new created user
   test-1:

   .. code:: sh

     openstack user create --password Li69nux* test-1
     opentstack user list

2. In managed SubC, opentstack user list should see the new created user
   test-1.

3. In unmanaged SubC, opentstack user list should NOT see the new created user
   test-1.

4. Manage the unmanaged subcloud: dcmanager subcloud manage subcloud-name
   unmanaged SubC shows managed
   dcmanager subcloud list
   in this managed cloud: opentstack user list
   should see the new created user test-1

5. Restore the subcloud back to unmanaged state
   dcmanager subcloud unmanage subcloud-name
   managed SubC shows unmanaged
   dcmanager subcloud list
   in SC: remove one of the users: openstack user delete test-1
   user should not be seen in SC

6. In unmanaged SubC, opentstack user list
   should still see user test-1

7. Manage the unmanaged subcloud: dcmanager subcloud manage subcloud-name
   user should not be seen in managed SubC

8. Change user password in SC
   make sure the PW is changed in SC

9. Check managed SubC of the change
   user password is changed in managed SubC

10. Check unmanaged SubC of the change
    user password is NOT changed in unmanaged SubC

11. Manage the unmanaged subcloud: dcmanager subcloud manage subcloud-name
    user password is changed in managed SubC

12. Create a local user on the subcloud while the subcloud is unmanaged
    Ensure the user information is not overwritten in the audit interval
    (15 minutes)

13. Change the subcloud so it is managed
    Verify the local changes are overwritten when the system is synchronized

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~
DC_SYNC_24
~~~~~~~~~~

:Test ID: DC_SYNC_24
:Test Title: test_Shared Configuration Propagation: LDAP
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure Shared Configuration Propagation LDAP on DC working well in
StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Assumption: The distributed cloud system is already installed and
commissioned. This includes a System Controller and multiple subclouds.
At least one subcloud should be in unmanaged state, meaning the changes
to that cloud should be queued until they can be propagated.

++++++++++
Test Steps
++++++++++

1. Create LDAP user on SystemController "ldap_testing", Verify changes on main
   cloud propagate to sub cloud:

   .. code:: sh

     sudo ldapusersetup

2. Modify an existing LDAP user on the SystemController, verify changes on
   main cloud propagate to sub cloud:

   .. code:: sh

     date; sudo ldapmodifyuser systest replace userPassword Li69nux*

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~
DC_SYNC_25
~~~~~~~~~~

:Test ID: DC_SYNC_25
:Test Title: test_Shared Configuration Propagation: Neutron - Quotas
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure Shared Configuration Propagation Neutron Quotas on DC working
well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Assumption: The distributed cloud system is already installed and
commissioned. This includes a System Controller and multiple subclouds.
At least one subcloud should be in unmanaged state, meaning the changes
to that cloud should be queued until they can be propagated.

1. Define the following quotas on the System Controller:

   .. code:: sh

     openstack --os-region-name SystemController quota set admin --floating-ips 20 --ports 50

2. Confirm that the changes are propagated to any subclouds that are managed.
3. Confirm that the changes are not propagated to subclouds that are not
   managed.
4. Manage the unmanaged subcloud.
5. Ensure it is eventually updated with the expected quotas.
6. Attempt to exceed the quota. Note, ensure this quota applies to
   all subclouds, not per individual subcloud.
7. Ensure this is rejected.
8. List the quota usage from all the subclouds and ensure it is accurate.
9. Attempt to update the quota locally on an unmanaged subcloud.
10. Ensure the subcloud can exceed the overall system quota.
11. Manage the unmanaged subcloud.
12. Ensure that nothing can be launched until the usage drops into the
    expected range.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~
DC_SYNC_26
~~~~~~~~~~

:Test ID: DC_SYNC_26
:Test Title: test_Shared Configuration Propagation: Neutron - Security Groups
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure Shared Configuration Propagation Neutron security groups on
DC working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Assumption: The distributed cloud system is already installed and
commissioned. This includes a System Controller and multiple subclouds.
At least one subcloud should be in unmanaged state, meaning the changes to
that cloud should be queued until they can be propagated.

1. Define a new security group, set the group properties and define some
   security group rules on the System Controller.
2. Confirm that the changes are propagated to any subclouds that are managed.
3. Confirm that the changes are not propagated to subclouds that are not
   managed.
4. Manage the unmanaged subcloud.
5. Ensure it is eventually updated with the expected security group
   information.
6. Restore the subcloud to unmanaged at the end of the test.
7. Repeat test but this time, modify the security group, i.e. group
   properties, group rules.
8. Ensure the changes are propagated to the managed nodes but not unmanaged,
   but once the unmanaged node is managed, the changes should be propagated.
9. Repeat test but this time, delete the security group.
10. Ensure the changes are propagated to the managed nodes but not unmanaged,
    but once the unmanaged node is managed, the changes should be propagated.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~
DC_SYNC_27
~~~~~~~~~~

:Test ID: DC_SYNC_27
:Test Title: test_Shared Configuration Propagation: Nova - Flavors
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure Shared Configuration Propagation Nova Flavors on DC working well in
StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Assumption: The distributed cloud system is already installed and
commissioned. This includes a System Controller and multiple subclouds.
At least one subcloud should be in unmanaged state, meaning the changes
to that cloud should be queued until they can be propagated.

1. Define the following flavors on the System Controller:

   .. code:: bash

     Group 1:

     nova --os-region-name SystemController flavor-create s.f1 auto 512 1 1
     openstack --os-region-name SystemController flavor create
     --public m1.extra_tiny --id auto --ram 256 --disk 0 --vcpus 1 --rxtx-factor 1

     Group 2:

     nova --os-region-name SystemController flavor-create s.f1 auto 512 1 1
     nova --os-region-name SystemController flavor-key s.f1 set
     hw:cpu_policy=shared
     nova --os-region-name SystemController flavor-key s.f1 set
     hw:mem_page_size=2048

     Group 3:
     nova --os-region-name SystemController flavor-create s.p1 auto 512 1 1
     --is-public false
     nova --os-region-name SystemController flavor-access-add s.p1 <tenant_id>

2. Confirm that the changes are propagated to any subclouds that are managed.
3. Confirm that the changes are not propagated to subclouds that are not
   managed.
4. Manage the unmanaged subcloud.
5. Ensure it is eventually updated with the expected flavors.
6. Ensure you can deploy a VM with one of the propagated flavors.
7. Restore the subcloud back to unmanaged state at the end of the test.
8. Repeat test but this time, remove one of the flavors from each group.
9. Ensure the changes are propagated to the managed nodes but not unmanaged,
   but once the unmanaged node is managed, the changes should be propagated.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~
DC_SYNC_28
~~~~~~~~~~

:Test ID: DC_SYNC_28
:Test Title: test_Shared Configuration Propagation: Nova - Keypairs
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++++++
Testcase Objective
++++++++++++++++++

To ensure Shared Configuration Propagation Nova keypairs Quotas on DC
working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

++++++++++
Test Steps
++++++++++

Assumption: The distributed cloud system is already installed and
commissioned. This includes a System Controller and multiple subclouds.
At least one subcloud should be in unmanaged state, meaning the changes
to that cloud should be queued until they can be propagated.

1. Define a key pair on the System Controller:

   .. code:: bash

     nova --os-region-name SystemController keypair-add kp_test

2. Confirm that the changes are propagated to any subclouds that are managed.
3. Confirm that the changes are not propagated to subclouds that are not
   managed.
4. Manage the unmanaged subcloud.
5. Ensure it is eventually updated with the expected keypair.
6. Restore the subcloud back to unmanaged state at the end of the test.
7. Repeat test but this time, remove the keypair.
8. Ensure the changes are propagated to the managed nodes but not unmanaged,
   but once the unmanaged node is managed, the changes should be propagated.
9. Ensure you can use those keypairs to launch VMs.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~
DC_SYNC_29
~~~~~~~~~~

:Test ID: DC_SYNC_29
:Test Title: test_Shared Configuration Propagation: Nova - Quotas
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++++++
Testcase Objective
++++++++++++++++++

To ensure Shared Configuration Propagation Nova Quotas on DC working well
in StarlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Assumption: The distributed cloud system is already installed and
commissioned. This includes a System Controller and multiple subclouds.
At least one subcloud should be in unmanaged state, meaning the changes
to that cloud should be queued until they can be propagated.

1. Define the following quotas on the System Controller:

   .. code:: bash

     nova --os-region-name SystemController quota-update <project_id>
     --user <user name> --cores 20
     nova --os-region-name SystemController quota-delete --tenant <project_id>
     --user <user name>
     nova --os-region-name SystemController quota-class-update --instances 30
     --ram 50 default

2. Confirm that the changes are propagated to any subclouds that are managed.
3. Confirm that the changes are not propagated to subclouds that are not
   managed.
4. Manage the unmanaged subcloud.
5. Ensure it is eventually updated with the expected quotas.
6. Attempt to exceed the quota. Note, ensure this quota applies.
   to all subclouds, not per individual subcloud.
7. Ensure this is rejected.
8. List the quota usage from all the subclouds and ensure it is accurate.

   .. code:: bash

     nova --os-region-name SystemController quota-show --detail
     nova --os-region-name SystemController quota-show --detail --user <user name>

9. Attempt to update the quota locally on an unmanaged subcloud.
10. Ensure the subcloud can exceed the overall system quota.
11. Manage the unmanaged subcloud.
12. Ensure that nothing can be launched until the usage drops into
    the expected range.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~
DC_SYNC_30
~~~~~~~~~~

:Test ID: DC_SYNC_30
:Test Title: test_Shared Configuration Propagation: NTP
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure Shared Configuration Propagation NTP on DC working well in
StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Assumption: The distributed cloud system is already installed and
commissioned. This includes a System Controller and multiple subclouds.
At least one subcloud should be in unmanaged state, meaning the changes
to that cloud should be queued until they can be propagated.

1. Define valid NTP servers on the System Controller.
2. Confirm that the changes are propagated to any subclouds that are managed.
3. Confirm that the changes are not propagated to subclouds that are not
   managed.
4. Manage the unmanaged subcloud.
5. Ensure it is eventually updated with the expected NTP servers.
6. Restore the subcloud back to unmanaged state at the end of the test.
7. Repeat test but this time, remove one of the NTP servers.
8. Ensure the changes are propagated to the managed nodes but not unmanaged,
   but once the unmanaged node is managed, the changes should be propagated.
9. Repeat test but this time, include an invalid NTP server.
10. Ensure the changes are propagated to the managed nodes but not unmanaged,
    but once the unmanaged node is managed, the changes should be propagated.
11. Ensure there are alarms for the unreachable NTP servers. These alarms
    should be reported for each managed subcloud.
12. Repeat test but this time make a local NTP change on the subcloud
    while the subcloud is unmanaged.
13. Ensure the NTP servers are not overwritten in the audit interval
    (10 minutes).
14. Change the subcloud so it is managed.
15. Verify the local changes are overwritten when the system is synchronized.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~
DC_SYNC_31
~~~~~~~~~~

:Test ID: DC_SYNC_31
:Test Title: test_Shared Configuration Propagation: SNMP
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure Shared Configuration Propagation SNMP on DC working well in
StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

Assumption: The distributed cloud system is already installed and
commissioned. This includes a System Controller and multiple subclouds.
At least one subcloud should be in unmanaged state, meaning the changes
to that cloud should be queued until they can be propagated.

1. Define a valid SNMP community string and trap destination on the
   System Controller.
2. Confirm that the changes are propagated to any subclouds that are managed.
3. Confirm that the changes are not propagated to subclouds that are not
   managed.
4. Manage the unmanaged subcloud.
5. Ensure it is eventually updated with the expected SNMP information.
6. Restore the subcloud back to unmanaged state at the end of the test.
7. Initiate an action on the subcloud that would generate a SNMP trap,
   e.g. fileystem threshold exceeded for nova-local.
8. Sure the SNMP trap is generated.
9. Repeat test but this time, modify the community string.
10. Ensure the changes are propagated to the managed nodes but not
    unmanaged, but once the unmanaged node is managed, the changes should
    be propagated.
11. Ensure traps can still be generated.
12. Repeat test but this time make a local SNMP trap destination change
    on the subcloud while the subcloud is unmanaged.
13. Ensure the SNMP info is not overwritten in the audit interval
    (10 minutes).
14. Change the subcloud so it is managed.
15. Verify the local changes are overwritten when the system is synchronized.
16. Ensure traps can be generated.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~~~~~~~~~
DC_INSTALLATION_32
~~~~~~~~~~~~~~~~~~

:Test ID: DC_INSTALLATION_32
:Test Title: test_Subcloud swacting
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure subcloud swacting on DC working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

1. Swact subcloud controllers, Controllers swacted without alarms.

2. Change some of the the shared configuration on the system controller,
   e.g. NTP. Ensure changes are still propagated after swact.
3. Change some of the same configuration on the subcloud, i.e. DNS.
   Ensure the changes are overwritten by audit.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~~~~~~~~~~~
DC_INSTALLATION_33
~~~~~~~~~~~~~~~~~~

:Test ID: DC_INSTALLATION_33
:Test Title: test SystemController swacting
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure system controller swacting on DC working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

1. Swact system controller. System controller swact successfully without alarms
2. Change some of the configuration on the subcloud so it is out of sync with
   the system controller.
3. Ensure changes are still overwritten by audit.
4. Change some of the configuration in the system controller.
5. Ensure changes are still propagated to the subclouds

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test steps are passed.

~~~~~~~~
DC_VM_34
~~~~~~~~

:Test ID: DC_VM_34
:Test Title: test_VM operations on sync online subcloud
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++++++
Test Objective
++++++++++++++++++

To ensure VM operation on subcloud working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

++++++++++
Test Steps
++++++++++

1. VM launch, VM launch success.
2. VM rebuild
3. VM live migration
4. VM cold migration
5. VM evacuation
6. VM delete

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All test steps are passed.

~~~~~~~~
DC_VM_35
~~~~~~~~

:Test ID: DC_VM_35
:Test Title: test_VM Operations: on isolated subcloud
:Tags: P4, Distributed Cloud, Regression, AUTOMATABLE

++++++++++++++
Test Objective
++++++++++++++

To ensure VM operation on isolated subcloud working well in StartlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

NA

++++++++++
Test Steps
++++++++++

1. Before subcloud isolated: Launch VM, Vm Launch success.
2. VM image is cached, hit shows 0:

   .. code:: bash

     glance-cache-manage -H ${subcloud_floating_ip} list-cached

3. Sub cloud isolate by shutting off main cloud or pulling off Mgt cables on
   both controllers.
4. Cut off mgmt network connection (pull Maincloud mgmt cable)
5. Launch VM with cached image, VM launch success.
6. VM rebuild
7. VM live migration
8. VM cold migration
9. VM evacuation
10. Vm delete

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

All Test Step are passed.

----------
References
----------

NA

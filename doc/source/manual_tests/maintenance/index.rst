===========
Maintenance
===========

This test plan covers maintenance manual regression. It covers basic
functionality for the following features.

- PTP (Precision Time Protocol)
- Port fail management and/or OAM
- Collectd + InfluxDb - RMON Replacement (ALL METRICS)

--------------------
Overall Requirements
--------------------

Any TIS system can be used.

----------
Test Cases
----------

.. contents::
   :local:
   :depth: 1

~~~~~~~~~
MTC_PTP_1
~~~~~~~~~

:Test ID: MTC_PTP_1
:Test Title: test_configure_PTP_Service_using_GUI
:Tags: P1 MTC, PTP, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

Purpose of this test is to validate configuration of PTP from GUI
and verify alarm cleared.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

++++++++++
Test Steps
++++++++++

1. Launch horizon and login as admin
2. Open System Configuration page in horizon
3. Click PTP and edit.
4. Check mark to enabled
5. Save verify out of configuration 250.001
6. Lock and unlock all the nodes starting with standby controller.
7. After all the nodes are bring locked and unlock and they are up.
8. Verify Configuration out-of-date alarms are cleared for both
   controllers.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Able to edit the PTP from horizon GUI.

~~~~~~~~~
MTC_PTP_2
~~~~~~~~~

:Test ID: MTC_PTP_2
:Test Title: test_PTP_service_clock_sync_with_time_change_and_reboot_host
:Tags: P1 MTC, PTP, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

To verify PTP service clock sync with reboot.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Ensure all the hosts ether-net hardware is supported for software or
hardware mode transmit and receive time stamp.
E.g: Below show software mode supported ether-net:

   .. code:: sh

     ethtool -T <Interface>
     Time stamping parameters for enp134s0f0:
     Capabilities:
     software-transmit     (SOF_TIMESTAMPING_TX_SOFTWARE)
     software-receive      (SOF_TIMESTAMPING_RX_SOFTWARE)
     software-system-clock (SOF_TIMESTAMPING_SOFTWARE)
     PTP Hardware Clock: none
     Hardware Transmit Timestamp Modes: none
     Hardware Receive Filter Modes: none

++++++++++
Test Steps
++++++++++

1. Enabled PTP using following command:

   .. code:: sh

     system ptp-modify --enabled=True --mode=software

2. Lock and unlock all the hosts starting with standby controller to
   clear alarm Configuration out-of-date alarm id 250.001

3. Verify the time all sync after lock and unlock

4. Change time Eg: date +%T -s "11:14:00" in one of the host

5. Reboot the hosts where time is change and verify time is sync with
   other hosts after reboot.

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Time was sync after reboot.


~~~~~~~~~
MTC_PTP_3
~~~~~~~~~

:Test ID: MTC_PTP_3
:Test Title: test_ptp4l_process_failure_detection_by_alarm_200.006_and_recovery
:Tags: P1 MTC, PTP, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

This test is to verify phc2sys process failure detection by alarm and
alarm clear on recovery.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Enable PTP as per instruction- -  in Test case 1 or 2

++++++++++
Test Steps
++++++++++

1. Find the process id for phc2sys
2. Use the above process id and kill the process sudo kill -9 process ID
3. Verify alarm and process restart
4. Try steps 1 and 2 to verify multiple times

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Process restart on process kill and alarm

~~~~~~~~~
MTC_PTP_4
~~~~~~~~~

:Test ID: MTC_PTP_4
:Test Title: test_ptp4l_process_failure_detection_alarm_200.006_and_recovery
:Tags: P1 MTC, PTP, Regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

This test is to verify ptp4l process failure detection by alarm and alarm clear
 on recovery.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Enable PTP as per instruction in Test case 1 or 2


++++++++++
Test Steps
++++++++++

1. Find the process id for ptp4l.
2. Use the above process id and kill the process sudo kill -9 process ID
3. Verify alarm and process restart.
4. Try steps 1 and 2 to verify multiple times.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Process restart on process kill and alarm.

~~~~~~~~~~~~~~~~
MTC_MgtOAMdown_5
~~~~~~~~~~~~~~~~

:Test ID: MTC_MgtOAMdown_5
:Test Title: test_pull_management_cable_on_active_controller
:Tags: P1 MTC, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

This test is to verify management cable pull on active controller
and verify standby controller becoming active with host-list available
on all the hosts except the other controller.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Install 2+2 system.

++++++++++
Test Steps
++++++++++

1. Remove management cable from active controller(controller-0)
2. Verify alarm for communication failure
3. Verify swact to controller-1

++++++++++++++++++
Expected Behaviour
++++++++++++++++++

Controller swact and alarm for communication failure.

~~~~~~~~~~~~~~~~
MTC_MgtOAMdown_6
~~~~~~~~~~~~~~~~

:Test ID: MTC_MgtOAMdown_6
:Test Title: test_that_compute_host_will_reboot_if_management_network_is_down
:Tags: P1 MTC, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

This test is to verify that management cable pull on compute node
alarm generated for communication failure.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Install 2+2 system.

++++++++++
Test Steps
++++++++++

1. Remove management cable from compute node.
2. Verify alarm for communication failure.
3. Verify compute reboot once cable is put back.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Alarm for communication failure and reboot

~~~~~~~~~~~~~~~~~~~~~~~~~~~
MTC_collectdIusflexDbRmon_7
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Test ID: MTC_collectdIusflexDbRmon_7
:Test Title: test_ntp_connectivity_failure_alarm_and_sample_data
:Tags: P1 MTC, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

To verify NTP connection failure alarm and sample data.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Install 2+2 system.

++++++++++
Test Steps
++++++++++

1. Verify no alarms on NTP.
2. Verify sample data for NTP value should be 3 or 2 for
   NTP connection is good and no alarms.
3. Execute  below cli retrieve database info

   .. code:: sh

     while true; do  influx -database=collectd -execute="SELECT * FROM ntpq_value
     ORDER by time DESC LIMIT 4"; sleep 31; done

4. When there is no failure above sample data will showed NTP connection
   failure is 1
5. Trigger a failure by update NTP server address in system configuration in
   horizon to unknown.
6. Verify fm alarm list for NTP alarm for text server configuration doesn't
    have reachable NTP server.
7. Query on database using below command. NTP connection
   failure will be indicated by 0

   .. code:: sh

    while true; do  influx -database=collectd -execute="SELECT * FROM
    ntpq_value ORDER by time DESC LIMIT 4"; sleep 31; done

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Alarm for communication failure and reboot.

----------
References
----------

https://wiki.openstack.org/wiki/StarlingX/Containers/Installation

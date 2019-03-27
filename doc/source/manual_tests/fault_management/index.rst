=================
Fault Management
=================
This test plan covers Fault Management manual regression. It covers basic
functionality for the following features:

- Enhanced_Log_Management
- SNMP

----------------------
Overall  Requirements:
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

```````````````````````````````
FM_Enhanced_Log_Management_01
```````````````````````````````
:Test ID: FM_Enhanced_Log_Management_01
:Test Title: test_verify_install_of_SDK_module_on_Ubuntu
:Tags: P2,FM,Enhanced log management,regression

+++++++++++++++++++
Testcase Objective:
+++++++++++++++++++
Purpose of this test is to verify split brain scenario swact on active
controller by blocking standby controller and storage on active controller

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++
system should be installed with load that has this feature.
External VM or server is needed to install Remote logging server.
Remote logging SDK should be available in the server

++++++++++
Test Steps
++++++++++
1. FTP the SDK module for Kibana log collection tool to Ubunthu os machine.
2. tar xfv wrs-install-log-server-1.0.0.tgz
3. Follow instructions from README file which is given in example for
   installing udp transport.
   code::
   cd install-log-server
   sudo ./install-log-server.sh -i <Sever IP> -u
   ...

4. Open a web browser and open kibana website to connect to log server

   code::
   http://<log server ip address>:5601
   ...

+++++++++++++++++
Expected Behavior
+++++++++++++++++
Able launch kibana log collection tool using web browser
http://<log server ip address>:5601


```````````````````````````````
FM_Enhanced_Log_Management_02
```````````````````````````````
:Test ID: FM_Enhanced_Log_Management_02
:Test Title: test_verify_configure_TIS_for_external_log_collection_using_udp
:Tags: P2,FM,Enhanced log management,regression

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++
system should be installed with load that has this feature.
External VM or server is needed to install Remote logging server.
Remote logging SDK should be available in the server

+++++++++++++++++++
Testcase Objective:
+++++++++++++++++++

This is to test the Configuration of External logging on TIS with UDP option
and verify logs collected
on server.

++++++++++
Test Steps
++++++++++
1. After setting log server as per test case 1
2. Configure TIS server with to collected logs  below cli show udp
   connection option as sdk install
   code::
   system remote logging-modify --ip_address 128.224.186.92 --transport udp
   --enabled True
   ...
3. verify the logs are collected and seen over the time period of 10 min.
   http://<log server ip address>:5601


+++++++++++++++++
Expected Behavior
+++++++++++++++++
Able launch kibana log collection tool using web browser and see the logs
getting collected http://<log server ip address>:5601

```````````````````````````````
FM_Enhanced_Log_Management_03
```````````````````````````````
:Test ID: FM_Enhanced_Log_Management_03
:Test Title: test_verify_remote_logging_disable_and_enable
:Tags: P2,FM,Enhanced log management,regression

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++
system should be installed with load that has this feature.
External VM or server is needed to install Remote logging server.
Remote logging SDK should be available in the server

+++++++++++++++++++
Testcase Objective:
+++++++++++++++++++

This is to test the Configuration of External logging on TIS with UDP option
and verify logs collected
on server.

++++++++++
Test Steps
++++++++++
1. After setting log server as per test case 2
2. Disable SDK by below cli on TIS

   code ::
   system remotelogging-modify --ip_address 128.224.186.92 \
   --transport udp --enabled false
   ...

3. Verify the logs not collected and seen over the time period of 5 min or
   more http://<log server ip address>:5601. There won't be any logs
   during this disable
4. Enable SDK by below cli on TIS

   code ::
   system remotelogging-modify --ip_address 128.224.186.92 \
   --transport udp --enabled True
   ...

5. Verify the logs are collected and seen over the time period of 5 min or
   more. http://<log server ip address>:5601

+++++++++++++++++
Expected Behavior
+++++++++++++++++
Able launch kibana log collection tool using web browser and see the logs
when enhanced logging is enabled and not seen when it is disabled

``````````
FM_SNMP_04
``````````
:Test ID: FM_SNMP_04
:Test Title: test_creating_new community_string_from_cli
:Tags: P2,FM,SNMP,regression

+++++++++++++++++++
Testcase Objective:
+++++++++++++++++++
Able to create community string

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++
system should be installed with load that has this feature.

++++++++++
Test Steps
++++++++++
1. Create community string using below cli

   code::
   system snmp-comm-add -c <comunity>
   ...

2. Verify that created community using below cli .

   code::
   system snmp-comm-list
   ...

+++++++++++++++++
Expected Behavior
+++++++++++++++++
Able to create SNMP community string and display.

``````````
FM_SNMP_05
``````````
:Test ID: FM_SNMP_05
:Test Title: SNMP_cli_trap_dest_can_be_deleted
:Tags: P2,FM,SNMP,regression

+++++++++++++++++++
Testcase Objective:
+++++++++++++++++++
To verify trap delete and trap is no long received.

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++
system should be installed with load that has this feature.
SNMP trap receiver is installed to receive the trap.

++++++++++
Test Steps
++++++++++
1. Create community string using below cli

   code::
   system snmp-comm-add -c <comunity>

2. Create trapdest using below cli.Use  ip address of client and community
   string that was already created.

   code::
   system snmp-trapdest-add -i <ip_address> -c <comunity>
   ...

3. Verify that created trapdest displayed

   code::
   system snmp-trapdest-list
   ...
4. Restart snmp using below cli

   code::
   snmpd /etc/init.d/snmpd restart)
   ...

5. Verify that trap is received by the trap listener.By seeing messages
   in SNMP viewer
6. Delete trapdest using cli below

   code::
   system snmp-trapdest-delete <ip_address>)
   ...

7. Verify that trapdest deleted

   code::
   system snmp-trapdest-list
   ...

8. Verify that trap is no longer received by the trap listener.

+++++++++++++++++
Expected Behavior
+++++++++++++++++
When trap is available messages are seen after trap was deleted there was no
messages on trap listener.

----------
References
----------
https://wiki.openstack.org/wiki/StarlingX/Containers/Installation

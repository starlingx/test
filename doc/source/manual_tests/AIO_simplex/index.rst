=======
Simplex
=======


--------------------
Overall Requirements
--------------------

StarlingX Environemnt setup

----------
Test Cases
----------


.. contents::
   :local:
   :depth: 1

~~~~~~~~~~
Simplex_01
~~~~~~~~~~

:Test ID: Simplex_01
:Test Title: Admin Password change on AIO Simplex 1
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

This is to verify that the admin password can be changed successfully on AIO system.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++


1. To Update admin password:

 ::

  $ source /etc/nova/openrc
  $ openstack user set --password <new_password> <user>


+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Verify services are working as expected.
2. Verify if password changed by log in into StarlingX Horizon

Notes:
Each time the password is updated, should exit from 'keyston_admin' authentication and enter again.

~~~~~~~~~~
Simplex_02
~~~~~~~~~~

:Test ID: Simplex_02
:Test Title: Alarm Suppression
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Verify alarms are cleared

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++


For simplex, lock the controller-0

 ::

   $ source /etc/platform/openrc

1. On controller that is StandBy execute below command

 ::

   $ sudo timedatectl set-ntp 0

2. Verify that controller locked alarm displayed:

 ::

   $ fm alarm-list --uuid

3. Verify that entity-instance-id and suppression are included:

 ::

   $ fm alarm-show <alarm_uuid>

4. Lock inactive/standby controller:

 ::

   $ system host-lock controller-1
   $ fm alarm-list --uuid

4. Unlock controller:

 ::

   $ system host-unlock controller-1

5. Verify that alarm is cleared:

 ::

 $ fm alarm-list --uuid"


+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Verify that below alarm is generated:

 ::

   [wrsroot@controller-0 ~(keystone_admin)]$ fm alarm-list --uuid
   controller-1 'ntpd' process has failed. Manual     | host=controller-1 .....

2. Verify below values:

 ::

   | entity-instance-id | host=<hostname>
   | suppression           | True

3. After controller is locked, several alarms should be showed. Verify that the alarm displayed on step 2 is not displayed anymore.

4. When unlock controller, a reboot is expected.

5. When controller boot, alarms should be gone after the problem is solved.

~~~~~~~~~~
Simplex_03
~~~~~~~~~~

:Test ID: Simplex_03
:Test Title: Verify migration is rejected on Simplex
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Migration is rejected

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

You should have at least to VM up and running and a Cirros vm can be created

1. Authentification $ source /etc/platform/openrc

2. Create a flavor

 ::

   $openstack flavor create --ram 512 --disk 1 --vcpus 1 --public m1.tiny

3. Create an image:

 ::

   $openstack image create --file cirros.img --disk-format qcow2 cirros

4. Create a network:

 ::

   $openstack network create net-1

5. Create a subnet:

 ::

   $openstack subnet create --network net-1 --subnet-range 192.168.0.0/24 --ip-version 4 --dhcp subnet-1

6. Create a vm:

 ::

   $openstack server create --flavor m1.tiny --image cirros --network net-1 cirros-vm

7. Show the vm created:

 ::

   $openstack server list

8. Verify which host (compute) the vm was attached:

 ::

   $openstack server show cirros-vm | grep ""host""

9. Try to migrate vm:

 ::

   $openstack server migrate --live <target_host> <server_name>

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Flavor created successfully
2. Image created successfully
3. Network created successfully
4. Subnet created successfully
5. Verify migration is rejected: "no valid host was found. There are not enough hosts available"

~~~~~~~~~~
Simplex_04
~~~~~~~~~~

:Test ID: Simplex_04
:Test Title: Installation and Commissioning AIO Simplex
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Verify simplex setup and launching and deleting vms are succesful


+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1.Install the AIO simplex with standard compute

2.Launch/delete VMs

 ::

   $nova delete <instance_name>

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Verify the installation is successful.
2. Verify launching and deleting vms are successful.


~~~~~~~~~~
Simplex_05
~~~~~~~~~~

:Test ID: Simplex_05
:Test Title: Validate the 2nd controller cannot be added
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++



+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Install the AIO simplex with standard compute

2. Once AIO Simplex system is up, try to add a second controller

 ::

   $ system host-update 2 personality=controller


+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Verify the installation is successful.
2. Verify command is rejected.

~~~~~~~~~~
Simplex_06
~~~~~~~~~~

:Test ID: Simplex_06
:Test Title: Lock unlock AIO Simplex
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Lock-Unlock Active controller, no matter that the name says AIO , this test can be done on all configurations with at least 2 VM's up and running

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Source

 ::

  $ source /etc/platform/openrc

2. Unlock active controller:

 ::

  $ system host-unlock controller-0

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Verify all vms are up and running.


~~~~~~~~~~
Simplex_07
~~~~~~~~~~

:Test ID: Simplex_07
:Test Title: Verify installation with HTTPS
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Verify endpoint list https


+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Install the AIO simplex with standard compute

2. Use the command to validate https endpoints

 ::

  $openstack endpoint list

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Validation Installation is successfully completed
2. Validate all services have https enabled


~~~~~~~~~~
Simplex_08
~~~~~~~~~~

:Test ID: Simplex_08
:Test Title: Verify VMs lauch/delete via Heat
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Launch and instance and delete instance by heat

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

a) An image with the name of cirros available

 ::

  i.e.
  Export openstack_helm authentication
     $ export OS_CLOUD=openstack_helm
     REMARK: go to [0] for details.

  $ wget http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img

  $ openstack image create --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2 --public cirros

b) A flavor with the name flavor_name.type available.

 ::

  i.e.
  $ openstack flavor create --public --id 1 --ram 512 --vcpus 1 --disk 4 flavor_name.type
      REMARK: go to [1] for type of flavors.

c) A network available

 ::

  i.e.
  $ openstack network create net

  $ openstack subnet create --network net --ip-version 4 --subnet-range 192.168.0.0/24 --dhcp net-subnet1

d) Execute the following command to take the network id

 ::

  $ export NET_ID=$(openstack network list | awk '/ net / { print $2 }')



++++++++++
Test Steps
++++++++++

1. Create Heat stack using nova_server.yaml by typing:

 ::

  $ openstack stack create --template nova_server.yaml stack_demo --parameter "NetID=$NET_ID"

2. Delete the stack

 ::

  $ openstack stack delete stack_demo

+++++++++++++++++
Expected Behavior
+++++++++++++++++
1. Verify Stack is successfully created and new nova instance is created.

.. code:: bash

       $ openstack stack list

 ::

  i.e.
  +--------------------------------------+------------+----------------------------------+-----------------+----------------------+----------------------+
  | ID | Stack Name | Project | Stack Status | Creation Time | Updated Time                                                                              |
  +======================================+============+==================================+=================+======================+======================+
  |380bb224-4c41-4b25-b4e8-7291bb1f3129 | stack_demo | 3cfea8788a9c4323937e730e1a7cbf18 | CREATE_COMPLETE | 2019-02-22T11:36:17Z | 2019-02-22T11:36:25Z |
  +--------------------------------------+------------+----------------------------------+-----------------+----------------------+----------------------+

2. Verify the STACK and the resources is deleted $ openstack stack list


nova_server.yaml


 ::

  heat_template_version: 2015-10-15
  description: Launch a basic instance with CirrOS image using the ``demo1.tiny`` flavor, ``mykey`` key,  and one network.
  parameters:
    NetID:
      type: string
      description: Network ID to use for the instance.

  resources:
    server:
      type: OS::Nova::Server
      properties:
        image: cirros
        flavor: demo1.tiny
        key_name:
        networks:
        - network: { get_param: NetID }

  outputs:
    instance_name:
	 description: Name of the instance
      value: { get_attr: [ server, name ] }
    instance_ip:
      description: IP address of the instance.
      value: { get_attr: [ server, first_address ] }

~~~~~~~~~~
Simplex_09
~~~~~~~~~~

:Test ID: Simplex_09
:Test Title: Pmon monitored process
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Get the list of process monitored by pmon (/etc/pmond.d)

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Get the list of process

 ::

   $ source /etc/nova/openrc

2. To check all process:

 ::

   $ ls /etc/pmon.d/


+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. File should be available
2. File should contain a list of process

~~~~~~~~~~
Simplex_10
~~~~~~~~~~

:Test ID: Simplex_10
:Test Title: SM monitored process
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Monitor process by SM

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. On the active controller, one service or process at a time do the following

 ::

  $sudo sm-dump --pid
  $sudo kill -9 <process id>

2. Wait for up to 60 or more seconds.

 ::

   Note:
    To see the process ID of the service:
    $ sudo sm-dump --pid     or    $ sudo sm-dump -pid | grep <proc_name>

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Process should be restarted within 60 seconds or so. (Wait up to 2 minutes.)
SM may or may not move the service to disabled for a short amount of time.
SM will set the current state of the service back to enabled-active if it changed the state to disabled when the process was killed.

2. Verify that the PID has changed form the previous one

Note: This test case is easy to execute with Horizon PID becasue web page goes down and the back  "

~~~~~~~~~~
Simplex_11
~~~~~~~~~~

:Test ID: Simplex_11
:Test Title: Unsupported sysInv Commands
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Verify unsupported sysInv commands

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

Try to swact Simplex, this test is juts for Simplex.
1. Go to horizon, Admin, Platform, Host Inventory
or via CLI "swact controller-0"

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Instruction should be rejected

 ::

   Swact action not allowed for a simplex system

~~~~~~~~~~
Simplex_12
~~~~~~~~~~

:Test ID: Simplex_12
:Test Title: Validate all host profiles are blocked
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Validate that profile are blocked and rejected

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Create interface profile for a node

 ::

  by cli: system ifprofile-add
  by gui: Admin > Platform > Host Inventory > Interfaces > Create Interface Profile

2. Lock the node to test

3. Delete interfaces of the node

4. Apply the interface profile, from Horizon:

  Host Inventory > edit Host > Interface Profile > apply the one that you saved

5. Unlock the node

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Verify the profile created successfully
2. Verify the node locked successfully
3. Verify the interfaces are deleted

Note:

- cannot delete interface of 'ethernet' type, change its type to 'none' instead
- leave mgmt interface unchanged
- verify the interfaces are recreated successfully

4. Verify the node can be unlocked and get into unlocked, enabled and available states.
5. Interfaces are working without any issue


~~~~~~~~~~
Simplex_13
~~~~~~~~~~

:Test ID: Simplex_13
:Test Title: Validate service parameters on AIO Simplex
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

This is to verify that the service parameters can be set on AIO Simplex system

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Try to add amd modify some service parameters, for example:

 ::

  system service-parameter-add identity config token_expiration=6000
  system service-parameter-apply identity
  date; openstack token issue

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Verify system service parameters can be applied successfully.

~~~~~~~~~~
Simplex_14
~~~~~~~~~~

:Test ID: Simplex_14
:Test Title: Verify branding on AIO Simplex
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Branding Verified

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++


1. Display System information via cli and GUI

 ::

  In Horizon: Admin > System > System Information


2. To display System Information via CLI:

 ::

  $ source /etc/nova/openrc
  $ system service-list



+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. In system information you should look and see

 ::

   Services
   Compute Services
   Block Storage Services
   Network Agent

2. *This can be different in Starling-X*:

 ::

  ceilometer
  cinder
  glance
  horizon
  neutron
  nova
  oam
  platform
  pxeboot
  vim


~~~~~~~~~~
Simplex_15
~~~~~~~~~~

:Test ID: Simplex_15
:Test Title: Verify memory assignment on AIO Simplex
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

This is to verify the memory assignment in AIO Simplex

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Lock the system
2. From GUI, Click locked host name to open the settings
3. In memory tab, click update memory
4. Update memory with IG
5. Click save, and unlock host
6. Launch an instance.
7. Repeat the test for 2M and 4K memory size


+++++++++++++++++
Expected Behavior
+++++++++++++++++

System Memory should be able to perform lock using system memory

- A host can be locked if a vm is up and running on it.
- The vm should be migrated of host if the host is locked.
- When unlock, a reboot is expected.

~~~~~~~~~~
Simplex_16
~~~~~~~~~~

:Test ID: Simplex_16
:Test Title: Verify mgmt/infra interfaces config
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

This is to verify that the mgmt interface can't be deleted on AIO simplex system.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Lock the system
2. Try to delete mgmt interface from Horizon

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Verify the system is locked successfully.
2. Verify the action is rejected.
3. Verify the command is rejected.


~~~~~~~~~~
Simplex_17
~~~~~~~~~~

:Test ID: Simplex_17
:Test Title: Verify Reconfiguration of mgmt interface on AIO Simplex
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Pull Management Cable on Active Controller and check that still works

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++


1. Pull the management cable on the active controller node, disable port in the environmet by typing

  ::

   $sudo ip link set <port_interface> down.

2. REMARK: once the active controller is SWACTED turn up the port interface by typing

 ::

  $sudo ip link set <port_interface> up

3. Re-connect the cable again and check that controller is rebooted and back online as StandBy
4. Do a swact and verify that is done correctly


+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Ensure the active controller is automatically swacted and alarms are generated for MGMT interface is down.

~~~~~~~~~~
Simplex_18
~~~~~~~~~~

:Test ID: Simplex_18
:Test Title: Verify Reconfiguration of OAM port on AIO Simplex
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Verify ethernet OAM interface is updated successfully on controller

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Ensure that ethernet type is configured on OAM interface
2. Lock inactive controller.

 ::

   $system host-lock <controller>

3. Change MTU value for OAM interface by

 ::

   $system host-if-modify controller-0 <oam_interface> -m9000

4. Unlock inactive controller and swact

 ::

   $system host-swact <active-host>

5. Verify that /opt/platform/puppet/<release>/hieradata/<IP>.yaml is updated correctly. Search for interface name

 ::

   $system host-if-show

6. Verify that 'ifconfig' shows new value of MTU for OAM.
7. Verify that destination host could be pinged via OAM interface


+++++++++++++++++
Expected Behavior
+++++++++++++++++

5. FIle is updated with mtu=9000
6. Ifconfigr shows MTU 9000
7. Destination host  pingable via OAM interface

~~~~~~~~~~
Simplex_19
~~~~~~~~~~

:Test ID: Simplex_19
:Test Title: Kill an Instance
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Verify that a VM is killed by it's process

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

REMARK: Find the compute where the instance you are going to kill resides.


1. Check the process that is runing the VM

 ::

  $ps aux |grep qemu

2. Kill the proccess

 ::

  $sudo kill -9 <pid>


+++++++++++++++++
Expected Behavior
+++++++++++++++++

1.Verify that the VM (instance) goes to Hard Reboot and the get recovered and running


~~~~~~~~~~
Simplex_20
~~~~~~~~~~

:Test ID: Simplex_20
:Test Title: Verify resize and rebuild on AIO
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Server actions-rebuild interaction, resize and rebuild on AIO

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. You need to have a vm up and running in order to be resized with a new flavor. Use the vm created during last test case.

 ::

  $source /etc/nova/openrc

2. Create a new flavor:

 ::

  $openstack flavor create --ram 2048 --disk 10 --vcpus 1 m1.small

3. Resize a vm running:

 ::

   $openstack server resize --flavor m1.small cirros-vm

4. Check status for the Resize confirmation, wait until Verify_resize Status Appear under

 ::

   $openstack server list


5. To confirm resize (when Status field is VERIFY_RESIZE):

 ::

   $openstack server resize --confirm cirros-vm

6. Check new flavor used for vm:

 ::

  $openstack server list (Flavor field)

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. When resizing, the vm status should be: RESIZE
2. Should be able to confirme the resize of VM
3. Wait for vm status: ACTIVE
4. Verify the resize operation is successful in Flavor field of VM table.
5. VM should be up and running

~~~~~~~~~~
Simplex_21
~~~~~~~~~~

:Test ID: Simplex_21
:Test Title: Verify that the retention period can be changed on AIO Simplex
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Retention perdiod should be changed

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Enter the following command

 ::

  system pm-modify retention_secs=nnnn


+++++++++++++++++
Expected Behavior
+++++++++++++++++

Verify:
1. No error message
2. Return code is 0
3. New value is populated to DB and can be verified with system pm-show
4. Configuration file is also updated
5. Alarms 250.001 Config out-of-date are raised and cleared shortly automatically


~~~~~~~~~~
Simplex_22
~~~~~~~~~~

:Test ID: Simplex_22
:Test Title: Reboot system 10 times
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Verify that system still works after reboot

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Note

 ::

   This action can be performed on active controller, forcing reboot from vm, on bare metal should be pressing the reset button
   Cannot reboot an unlocked host. Need to lock the host first.
   Cannot 'lock' nor 'reboot' an active controller in Multinode via CLI nor via Horizon, please check if it is possible on Simplex and Duplex.

2. Authentication

 ::

  $source /etc/nova/openrc

3. Show hosts to reboot

 ::

   $system host-list

4. Lock a host

 ::

   $system host-lock <hostname>

5. Reboot a host

 ::

   $system host-reboot <hostname>

Unlock host:

 ::

   $system host-unlock <hostname>

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. System should be able to recover from reboot, no need for instances
2. When unlock, a host reboot is expected.
3. All hosts must be  'unlocked', 'enabled' and 'available'.
4. If the active controller is rebooted, the second controller turns ""Active"" and the rebooted turns ""Standby""  when boot."

~~~~~~~~~~
Simplex_23
~~~~~~~~~~

:Test ID: Simplex_23
:Test Title: CLI command system show displays All-in-one instead of CPE
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

System command should displays All-in-one instead of CPE


+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Using a system with only controller(s). The old name was CPE and the new name is All-in-one. Check system show output.

 ::

   $ system show


+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. The system_type parameter is All-in-one


~~~~~~~~~~
Simplex_24
~~~~~~~~~~

:Test ID: Simplex_24
:Test Title: Horizon login screen displays StarlingX
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Branding is correct

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Open the Horizon GUI and ensure that StarlingX Logo is displayed

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. StarlingX logo is displayed

~~~~~~~~~~
Simplex_25
~~~~~~~~~~

:Test ID: Simplex_25
:Test Title: Horizon system type shows All-in-one
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Ensure the values are correct for Simplex All in One


+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

This option can be reached in Horizon or CLI

1. To check system type via Horizon:

 ::

   Admin -> Platform -> System Configuration
   System Type, each configuration should have different value, standard, all in one and go on

2. To check system type via CLI:

 ::

   $ system show | grep "system"

+++++++++++++++++
Expected Behavior
+++++++++++++++++

system_mode refers to number of controllers:
        - simplex (one controller)
        - duplex (two controllers)
system_type refers to configuration and number of additional servers:
        - All-in-one (services onto de controller)
        - Standard (services onto additional servers, it means onto computes)"

~~~~~~~~~~
Simplex_26
~~~~~~~~~~

:Test ID: Simplex_26
:Test Title: Installer screens were changed to use All-in-one instead of CPE
:Tags: Simplex

++++++++++++++
Test Objective
++++++++++++++

Setup screens were changed to All-in-one

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX Environment setup

++++++++++
Test Steps
++++++++++

1. Grab the latest bootimage.iso
2. Boot a controller node using the bootimage.iso
3. Ensure all references to CPE were changed to All-in-one

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. References to CPE were changed to All-in-One

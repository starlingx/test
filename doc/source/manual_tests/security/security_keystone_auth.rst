=======================
Keystone Authentication
=======================

.. contents::
   :local:
   :depth: 1

-----------------------------------
SECURITY_keystone_authentication_01
-----------------------------------

:Test ID: SECURITY_keystone_authentication_01
:Test Title: Nova user Passwords are protected.
:Tags: keystone

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

The objective of this test is to verify that CGCS admin password is not stored
in clear text.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 2 Controllers + 1 compute.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Login to controller-0. At the prompt, type:

.. code:: bash

  $ keyring get CGCS admin

2. On controller-0 node enter as admin user

.. code:: bash

  $ source /etc/nova/openrc

3- Make sure that a file and a directory are  created in the following path:

.. code:: bash

  /opt/platform/.keyring/.CREDENTIAL

  /opt/platform/.keyring/(keyring specific directory with encrypted passwords)

4- Type:

.. code:: bash

  $ more /etc/nova/openrc

Something similar to the next plain text should be displayed:

.. code:: bash

  controller-0:~$ more /etc/nova/openrc
  unset OS_SERVICE_TOKEN

  export OS_ENDPOINT_TYPE=internalURL
  export CINDER_ENDPOINT_TYPE=internalURL

  export OS_USERNAME=admin
  export OS_PASSWORD=`TERM=linux /opt/platform/.keyring/18.03/.C
  REDENTIAL 2>/dev/null`
  export OS_AUTH_URL=http://192.168.204.2:5000/v3

  export OS_PROJECT_NAME=admin
  export OS_USER_DOMAIN_NAME=Default
  export OS_PROJECT_DOMAIN_NAME=Default
  export OS_IDENTITY_API_VERSION=3
  export OS_REGION_NAME=RegionOne
  export OS_INTERFACE=internal

  if [ ! -z """"${OS_PASSWORD}"""" ]; then
  export PS1='[\u@\h \W(keystone_$OS_USERNAME)]\$ '
  else
  echo 'Openstack Admin credentials can only be loaded from the active controller.'
   export PS1='\h:\w\$ ' fi

5- Go to horizon > admin > platform > host inventory - and swact host 0.

6- On controller-1 node enter as admin user:

.. code:: bash

  $ source /etc/nova/openrc

you should found the same /etc/nova/openrc content.

7- After sourcing the openrc, type:

.. code:: bash

  $ env

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* It should return, the Horizon admin password.

* Logged in as an admin successfully.

* Files and directories created successfully.

* Admin does not have the password stored in clear text.

* Logged in as an admin successfully and content should be the same as Ctr-0.

.. code:: bash

  You should be able to find;
  OS_PASSWORD=<your admin password>

-----------------------------------
SECURITY_keystone_authentication_02
-----------------------------------

:Test ID: SECURITY_keystone_authentication_02
:Test Title: Change admin password.
:Tags: keystone

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify admin password change in different scenarios (SWACT/lock/unlock standby
controller, in Active controller and empty password).

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 2 Controllers + 1 compute.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* Change admin password via cli:

.. code:: bash

  $ openstack user password set

* SWACT to standby controller and make sure the controller come up fine.

At the prompt, type:

.. code:: bash

  $ keyring get CGCS admin

* Lock standby controller (system host-lock controller-1)

* Change admin password via cli:

.. code:: bash

  $ openstack user password set

* At the prompt, type:

.. code:: bash

  $ keyring get CGCS admin""

* Unlock standby controller (system host-unlock controller-1)

* Change admin password via cli:

.. code:: bash

  $ openstack user password set

* Reboot standby controller.

* To recover from reboot loop lock/unlock standby controller.

* At the prompt, type:

.. code:: bash

  $ keyring get CGCS admin

* Change admin password via cli on Active controller:

.. code:: bash

  $ openstack user password set

* Logg in/out from active controller.

Try to change admin password via cli on Active controller with empty string:

.. code:: bash

  $ openstack user password set
    Current password: <type current pass>
    New Password: <Empty>
    Repeat New Password: <Empty>

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Admin password is changed successfully.

* After SWACT the standby controller became active.

* It should return, the Horizon admin password.

* Verify standby controller is locked.

* Admin password is changed successfully.

* Verify the password is changed (keyring get CGCS)

* Verify the standby controller comes up fine.

* Admin password is changed successfully.

* Verify that the standby controller goes into reboot loop.

* Verify after lock/unlock it recovers.

* Verify the password is changed (keyring get CGCS)

* Admin password is changed successfully.

* You are able to logged in/out to active controller successfully.

* Verify empty string is not accepted for keystone admin password and controller get back with following message:

.. code:: bash

  No password was supplied, authentication will fail when a suer does not have a pasword.
  Specify both the current password and a ne password

-----------------------------------
SECURITY_keystone_authentication_03
-----------------------------------

:Test ID: SECURITY_keystone_authentication_03
:Test Title: Adding users to keystone user list via horizon.
:Tags: keystone

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Go through Horizon Adding users to keystone user list via horizon.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 2 Controllers + 1 compute.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* From horizon as admin user go to identity tab -> users.

* Hit ""+ Create User"" button.

* Enter at least required fields:

::

  User Name:
  Password:
  Confirm Password:
  Primary Project.""
  Enter ""Create User"" button.
  Refresh Identity --> Users List and make sure the new user is displayed.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Identity /Users "" Frame is displayed successfully.

* Create user pop up window is displayed.

* Required fields were entered successfully.

* Horizon got back with message saying the new user is created successfully.

* The new user is displayed successfully in identity --> User list.

-----------------------------------
SECURITY_keystone_authentication_04
-----------------------------------

:Test ID: SECURITY_keystone_authentication_04
:Test Title: Token expiration default 3600.
:Tags: keystone

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify that token_expiration system service-parameter default is set 3600
value.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 1 Controller.

b) Set token_expiration value for users.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* Login to controller-0. At the prompt, type:

.. code:: bash

  $ sudo su

* On controller-0 node enter as super user

.. code:: bash

  $ /etc/keystone/keyston.cof

* Make sure that file exists and verify the expiration field, from Token should be: 3600

* Type:

.. code:: bash

  $ cat /etc/keystone/keystone.conf | grep ""expiration="" and check the result
  Something similar to the next plain text should be displayed:
  controller-0:~# cat /etc/keystone/keystone.conf | grep ""expiration=""
  expiration=3600"

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Verify file that keyston.conf

* Verify that expiration is the value of 3600

-----------------------------------
SECURITY_keystone_authentication_05
-----------------------------------

:Test ID: SECURITY_keystone_authentication_05
:Test Title: keystone fernet path and file.
:Tags: keystone

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify proper keystone path and file.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 1 Controller.

b) See documentation on [0]

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. In order to verify the Fernet path and file. Login to controller-0. At the
prompt, type:

.. code:: bash

  $ sudo su

2. On controller-0 node enter as super user to check the information inside
keyston.con under /etc/keystone/"" look for the fernet_tokens section and the
key_repository path"" the key_repository could be not always in the same path

In this case key_repository coul be verify at:

.. code:: bash

  $ controller-0:/opt/cgcs/keystone/fernet-keys

3. Then Verify that fernet keys exist:

.. code:: bash

  $controller-0:/opt/cgcs/keystone/fernet-keys #ls

4. Verify the fernet keys format:

.. code:: bash

  controller-0:/opt/cgcs/keystone/fernet-keys #cat 0
    G4bR3-2CoQGiKLDBWPwL0ZriLTYFEbLeSSFLNv5p30=

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Verify file that keyston.conf.

* Verify fernet path for fernet-keys.

* Verify Fernet Keys are generated and with the format.

-----------------------------------
SECURITY_keystone_authentication_06
-----------------------------------

:Test ID: SECURITY_keystone_authentication_0
:Test Title: Fernet tokens after controller SWACT.
:Tags: keystone

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Fernet tokens must be available on the system after SWACT (active/inactive
Controller).

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 1 Controller.

b) See documentation on [0]

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* Before SWACT verify Fernet Tokens and formats.

* Login to controller-0. At the prompt, type:

.. code:: bash

  $ sudo su""

* On controller-0 node enter as super user to check the information inside keyston.con under /etc/keystone/ look for the kernet_tokens section and the key_repository path the key_repository could be not always in the same path.

In this case key_repository coul be verify at:

.. code:: bash

  $controller-0:/opt/cgcs/keystone/fernet-keys

* Then Verify that fernet keys exist:

.. code:: bash

  $controller-0:/opt/cgcs/keystone/fernet-keys# ls
    0 1

* Verify the fernet keys format:

.. code:: bash

  controller-0:/opt/cgcs/keystone/fernet-keys# cat 0
    -G4bR3-2CoQGiKLDBWPwL0ZriLTYFEbLeSSFLNv5p30=

* SWACT the controllers, from the active controller Verify the Fernet path, files and format.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Fernet Tokens should remain after SWACT controllers.

-----------------------------------
SECURITY_keystone_authentication_07
-----------------------------------

:Test ID: SECURITY_keystone_authentication_07
:Test Title: Fernet instead of UUID.
:Tags: keystone

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Fernet instead of UUID.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 1 Controller.

b) See documentation on [0]

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* Login to controller-0. At the prompt:

1. Type

.. code:: bash

  $ sudo su""

On controller-0 node enter as super user
2- type:

.. code:: bash

  $ /etc/keystone/keyston.conf

Make sure that file exists and verify the Token provider should be: fernet""

3- Type:

.. code:: bash

  $ cat /etc/keystone/keystone.conf | grep ""provider"" and check the result

Something similar to the next plain text should be displayed:

.. code:: bash

  controller-0:/etc/keystone# cat /etc/keystone/keystone.conf | grep provider" provider=fernet

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Verify file that keyston.conf.

* Verify the provider is set to fernet and not UUID.

-----------------------------------
SECURITY_keystone_authentication_08
-----------------------------------

:Test ID: SECURITY_keystone_authentication_08
:Test Title: Key Rotation Test.
:Tags: keystone

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

The key rotation is performed.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 1 Controller.

b) See documentation on [0]

~~~~~~~~~~
Test Steps
~~~~~~~~~~

::

  Login to controller-0. At the prompt, type:
  1- $ sudo su"
  On Active controller-0 node enter as super user
  2- $ /etc/keystone/keyston.conf
  3-  Add to this keystone.conf file under fernet_tokens section:
    token_expiration=24
    rotation_frequency=6
    max_active_keys=4
  4.- Initialize fernet key repositories:
    # keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone
  5.- Initialize Credential repo:
    # keystone-manage credential_setup --keystone-user keystone --keystone-group keystone
  6.- Check for actual existing fernet keys in this path:
    /opt/cgcs/keystone/fernet-keys
  7.- Rotate the fernet keys:
    # keystone-manage fernet_rotate  --keystone-user keystone --keystone-group keystone
  8.- Check that a new fernet key has been added, you can compare the actual time when you have executed the cmd in order to know if already was created:
    #sudo timedatectl status

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Verifye that Key Rotation has been assigned another key in the path:

.. code:: bash

  /opt/cgcs/keystone/fernet-keys"

-----------------------------------
SECURITY_keystone_authentication_09
-----------------------------------

:Test ID: SECURITY_keystone_authentication_09
:Test Title: Verify log under /var/log/horizon.log that all passwords are masked.
:Tags: keystone

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify log under /var/log/horizon.log that all passwords are masked.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 1 Controller + 1 compute.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* Login to controller-0 using system admin user

* Verify all the passwords from horizon.log inside /var/log/horizon.log are masked or ( ********** )

.. code:: bash

  $cat /var/log/horizon.log

* Look for passwords and should be masked

.. code:: bash

  "password": ********"
  "fake_password": ********"

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Confirm that passwords are masked ( ***** ) in the logs from horizon.log

-----------------------------------
SECURITY_keystone_authentication_10
-----------------------------------

:Test ID: SECURITY_keystone_authentication_10
:Test Title: Encryption on Management network communication.
:Tags: MITM_Virtual

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify that communication over Starlingx Management network is encrypted and
not showing any sensitive information in plain text.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 1 VM Controller + 1 VM Compute.

b) Kali Security OS installed on libvirt Virtual Machine having access to the
MGMT network (Kali will act as a MITM Virtual Machine).

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* In your HOST where the Virtual nodes resides type "ifconfig" and identified what network interfaces are up and running.

.. code:: bash

  $ ifconfig

  e.g.
  ...
  rename4   Link encap:Ethernet  HWaddr a0:36:9f:f7:be:a0
          inet addr:10.219.128.122  Bcast:10.219.128.255  Mask:255.255.255.0
          inet6 addr: fe80::6b2:8085:4bf2:da74/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:3067876 errors:0 dropped:14209 overruns:0 frame:0
          TX packets:9113396 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000
          RX bytes:233256569 (233.2 MB)  TX bytes:10462546810 (10.4 GB)

  virbr0    Link encap:Ethernet  HWaddr 00:00:00:00:00:00
          inet addr:192.168.122.1  Bcast:192.168.122.255  Mask:255.255.255.0
          UP BROADCAST MULTICAST  MTU:1500  Metric:1
          RX packets:0 errors:0 dropped:0 overruns:0 frame:0
          TX packets:0 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000
          RX bytes:0 (0.0 B)  TX bytes:0 (0.0 B)

  virbr1    Link encap:Ethernet  HWaddr fe:54:00:21:c0:24
          inet addr:10.10.10.1  Bcast:10.10.10.255  Mask:255.255.255.0
          inet6 addr: fe80::848f:cdff:fe4c:fb59/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:298794 errors:0 dropped:0 overruns:0 frame:0
          TX packets:606395 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000
          RX bytes:61810994 (61.8 MB)  TX bytes:2124955052 (2.1 GB)

  virbr2    Link encap:Ethernet  HWaddr fe:54:00:6e:a7:90
          inet addr:192.168.204.1  Bcast:192.168.204.255  Mask:255.255.255.0
          inet6 addr: fe80::4403:aaff:fe5f:63ff/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:3858083 errors:0 dropped:6 overruns:0 frame:0
          TX packets:980 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000
          RX bytes:2071553276 (2.0 GB)  TX bytes:85710 (85.7 KB)

* (Double check network interfaces up)

* Create in your Kali Virtual Machine a NIC with the same "Bridge name" and "device model" used by the 2 nodes that you are going to connect.

**Brief explanation:**

* Use Case When Kali is going to be MITM machine between Controller-0 and compute-0 (see previous step for interfaces list):

* Configure Kali VM NIC with "Bridge name: virbr2", "Device model: e1000" (where virbr2 is the interface used by Compute-0 and Controller-0 MGMT network)

* Controller-0 node configured with "virbr2 bridge" "Ethernet", "IP: 192.168.204.3", MAC: 52:54:00:6e:a7:90. (Once Controller-0 is up, virbr2 interface will be used, however, when prompting ifconfig the Controller-0 will assign an interface with another name; something like Interface ens7)

* Compute-0 node configured with "Bridge name:ens7" "Ethernet", "IP: 192.168.204.90", MAC: 52:54:00:11:d0:6b.  (Once Compute-0 is up, virbr2 interface will be used, however, when prompting ifconfig the Compute-0 will assign an interface with another name; something like ens7)

* Set interface IP for Kali MITM attack.

* Login to your Kali VM.

* Check network interfaces up by typing:

.. code:: bash

  $ ifconfig

or

.. code:: bash

  $ ip link show""

* Assign an IP to the network interface where Controller-0 and Compute-0 are using:

.. code:: bash

  $ sudo ifconfig <interface name> <IPv4> netmask 255.255.255.0

  e.g.

  $ sudo ifconfig eth2 192.168.204.200 netmask 255.255.255.0

* Make sure connectivity between Kai and nodes by pinging Controller-0 and Compute-0 nodes.

.. code:: bash

  e.g.
  Ping Controller-0: 192.168.204.3
  Ping Compute-0: 192.168.204.90""

* Once you create connectivity between Kali Virtual machine and Starlingx nodes go to Kali VM --> Applications --> 09 - Sniffing & Spoofing -->Ettercap.

* Go to Menu banner --> Sniff --> Unified Sniffing.

* Select Network interface to sniff.

.. code:: bash

  e.g.
  Network interface : eth2""

* Go to Menu Banner --> MITM --> ARP Poisoning, and select the "Sniff remote connections" checkbox.

* Go to Menu Banner --> Hosts --> Scan for hosts option.

* Go to Menu Banner --> Hosts --> Hosts list.

* On Host list tab, highlight the server IP that you want to monitor and hit under "Add to Target 1" button.

.. code:: bash

  e.g.
  Following with the example the Server ip would be the Controller-0: 192.168.204.3.""

* On Host list tab, highlight the client IP that you want to monitor and hit under "Add to Target 2" button.

* Go to Menu Banner --> Targets --> Current Targets.

* Go to Applications -->  09 - Sniffing & Spoofing --> netsniff-ng.

* Type following command:

.. code:: bash

  $ netsniff-ng --in <interface name> --out <name of the file>.pcap
  e.g.
  $ netsniff-ng --in eth2 --out pickup-ctl0-cmp0.pcap""

** DO YOUR intended commands/actions in order to exercise your network **

* Once you executed the intended commands in order to exercise the network go to the terminal where the netsniff-ng app is running and stop the process.

* Go to Applications -->  09 - Sniffing & Spoofing --> Wireshark.

* Once the Wireshark application is opened, go to File and open the .pcap file generated by your sniffing command.

* Go to Wireshark menu banner and select Analyze --> Display Filters.

* Work with filters in order to analyze the security of protocols/Ports/IP version you are looking for.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Network interfaces were displayed successfully.

.. code:: bash

  i.e.
  Where:
   - rename4 interface is Intel network.
   - virbr1 interface used to connect Host with Controler-0 interface (OAM)
   - virbr2 interface used to connect to the MGMT network (controller-0 with Compute-0).

* Interface that is going to be used by the Controller-0 and the Compute-0 are up and running, as well as the one who will act as a MITM in Kali VM.

* Interfaces are shown in Kali VM successfully.

* IP network interface assigned successfully in Kali VM.

* Connectivity between Kali Virtual machine and nodes was successfully.

* Ettercap application is opened successfully.

* A pop Up window asking for Network interface to used should be opened successfully.

* The Kali VM started to monitor and sniffing the proper interface successfully.

* ARP spoofing should be done successfully where the MAC address from the Server and Client are set in Kali acting as a MITM attacker.

* Ettercap application should scan their hosts who has connectivity.

* A list of hosts with IP, MAC Address should be displayed.

* Server IP address should be marked as a Target 1 successfully.

Client IP address should be marked as a Target 2 successfully.

* Target 1/2 should be displayed successfully.

* netsniff-ng command prompt should be displayed.

* The command should be executed successfully and you would be monitoring the targets.

* MGMT Network is excercised successfully.

* The netsniff-ng program should be stopped and you would be seeing a message saying:

.. code:: bash

  [1]+ Stopped netsniff-ng --in eth2 --out pickup-ctl0-cmp0.pcap

* Wireshark should be opened successfully.

* .pcap file should be opened by Wireshark successfully.

* You were able to analyze Secure connectivity between Client and Server communications. If there is unsecure communications open a defect.

~~~~~~~~~~~
References:
~~~~~~~~~~~

[0] - https://docs.openstack.org/keystone/pike/admin/identity-fernet-token-faq.html

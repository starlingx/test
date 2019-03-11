=============
OAM Interface
=============

.. contents::
   :local:
   :depth: 1

-------------------------
SECURITY_OAM_interface_01
-------------------------

:Test ID: SECURITY_OAM_interface_01
:Test Title: Set up OAM interface Firewall
:Tags: port_services

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Use Netfilter/IpTables to set default firewall for OAM Interface.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) Starlingx uses Netfilter framework for firewall setup. Make sure
"iptables" and "iptables-config" files exist in /etc/sysconfig path.

b) On Active Controller, execute following commands to enable 443 https port:

.. code:: bash

  $ system modify -p true
  $ system modify --https_enabled true

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Once Starlingx product installed, go to Active controller,
/etc/sysconfig/iptables and check following protocol/ports are accepted:

::

  Protocol Port Service Name
  tcp 22 ssh
  tcp 80 horizon (http only)
  tcp 443 horizon (https only)
  tcp 4545 nfv-vim-api
  tcp 5000 keystone-api
  tcp 6080 nova-nonvc-proxy
  tcp 6385 sysinv-api
  tcp 8000 heat-cfn
  tcp 8003 heat-cloudwatch-api
  tcp 8004 heat-api
  tcp 8042 aodh-api
  tcp 8776 cinder-api
  tcp 8774 nova-api
  tcp 9292 glance-api
  tcp 9696 neutron-api
  tcp 15491 patching-api
  udp 123 ntp
  udp 161 snmp
  udp 2222 service manager
  udp 2223 service manager


2. Use netstat command to verify that ports are up and listening by typing:

.. code:: bash

  Controller-0 $ sudo netstat -plant | grep <port>

REMARK: Please repeat netstat command for every single port listed in above
step.

or

.. code:: bash

  Controller-0 $ sudo netstat -plant | grep LISTEN

REMARK: you should get the full list of listening ports with all available
IPs.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Once you open the /etc/sysconfig/iptables file you should be able to see
following rules listed:

::

  -A INPUT -p tcp -m multiport --dports 22 -m comment --comment """"011 platform accept ssh ipv4"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 80 -m comment --comment """"500 horizon incoming dashboard"""" -j ACCEP
  -A INPUT -p tcp -m multiport --dports 4545 -m comment --comment """"500 nfv-vim incoming nfv-vim-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 5000 -m comment --comment """"500 keystone incoming keystone-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 6080 -m comment --comment """"500 nova-novnc incoming nova-novnc"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 6385 -m comment --comment """"500 sysinv incoming sysinv-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8000 -m comment --comment """"500 heat-cfn incoming heat-cfn"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8003 -m comment --comment """"500 heat-cloudwatch incoming heat-cloudwatch"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8004 -m comment --comment """"500 heat incoming heat-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8042 -m comment --comment """"500 aodh incoming aodh-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8776 -m comment --comment """"500 cinder incoming cinder-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8774 -m comment --comment """"500 nova incoming nova-api-rules"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 9292 -m comment --comment """"500 glance incoming glance-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 9696 -m comment --comment """"500 neutron incoming neutron-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 15491 -m comment --comment """"500 patching incoming patching-api"""" -j ACCEPT
  -A INPUT -p udp -m multiport --dports 123 -m comment --comment """"201 platform accept ntp ipv4"""" -j ACCEPT
  -A INPUT -p udp -m multiport --dports 161 -m comment --comment """"202 platform accept snmp ipv4"""" -j ACCEPT
  -A INPUT -p udp -m multiport --dports 2222,2223 -m comment --comment """"010 platform accept sm ipv4"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 443 -m comment --comment """"500 horizon incoming dashboard"""" -j ACCEPT

REMARK: Per Ken Young(Windriver): we no longer need to open 8777 for the
cellometer-api, nor 8773 for nova-ec2.

2. All ports listed in the iptable file should be displayed successfully.

::

  e.g. [wrsroot@controller-0 syslog-ng(keystone_admin)]$ sudo netstat -plant | grep 8080
  tcp        0      0 127.0.0.1:8080          0.0.0.0:*               LISTEN      3733/gunicorn: work
  tcp        0      0 10.10.10.2:8080         0.0.0.0:*               LISTEN      27240/haproxy

-------------------------
SECURITY_OAM_interface_02
-------------------------

:Test ID: SECURITY_OAM_interface_02
:Test Title: Validate that services respond over https
:Tags: API

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

From and external host, browse HTTPS REST API for each service.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) On Active Controller, execute following commands to enable 443 https port:

.. code:: bash

  $ system modify -p true

  $ system modify --https_enabled true

b) Obtain a CA-Signed Certificate. Steps to create your own CA certificate.

1. Generate your own server private key (can be used on multiple servers)
by typing:

.. code:: bash

  $ openssl genrsa -out server-key.pem 2048

2. Generate the public certificate for the server private key (""commonName"" attribute must match the floating IP of the servers) For more reference go to [0]

.. code:: bash

  $ openssl req -new -key server-key.pem -out /home/user/server.csr -batch -subj ""/countryName=CN/stateOrProvinceName=<your state>/localityName=<city>/organizationName=<Your Company>/organizationalUnitName=<Your Org>/commonName=10.10.10.2""

  e.g.

  $ openssl req -new -key server-key.pem -out /home/fhernan2/server.csr -batch subj ""/countryName=MX/stateOrProvinceName=Jalisco/localityName=Guadalajara/organizationName=intel/organizationalUnitName=SSG/commonName=10.10.10.2""

3. Generate CA private key by typing:

.. code:: bash

  $ openssl genrsa -out ca-key.pem 2048

4. Generate CA public certificate (to be installed on the client browser)
by typing:

.. code:: bash

  $ openssl req -x509 -new -nodes -key ca-key.pem -days 3650 -out ca-cert.pem -outform PEM -subj ""/countryName=CN/stateOrProvinceName=<your state>/localityName=Ottawa/organizationName=<your Company>/organizationalUnitName=<Your gruo>/commonName=<Your Common Name>"" -text batch

  :e.g.
  $openssl req -x509 -new -nodes -key ca-key.pem -days 3650 -out ca-cert.pem -outform PEM -subj ""/countryName=MX/stateOrProvinceName=Jalisco/localityName=Guadalajara/organizationName=intel/organizationalUnitName=SSG/commonName=10.10.10.2""

5. Signing the server public certificate with CA private key by typing:

.. code:: bash

  $ openssl x509 -req -in ../vbox/server.csr -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial -out ../vbox/server.pem -days 3650

  :e.g.

  $ openssl x509 -req -in /home/fhernan2/CA_certificate/server.csr -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial -out /home/fhernan2/CA_certificate/server.pem -days 3650  
    Signature ok
    subject=/C=MX/ST=Jalisco/L=Guadalajara/O=intel/OU=SSG/CN=10.10.10.2
    Getting CA Private Key

6. Move the server-key.pem, server.pem, files from the host where you create
them to Active Controller by typing:

.. code:: bash

  $ scp server* wrsroot@10.10.10.3:~

7. Create a server key file by concatenating the server private key and the
CA-signed server certificate in a key file. Generate key file for installation
on controller node by typing

.. code:: bash

  $ cat server-key.pem /home/wrsroot/server.pem > /home/wrsroot/server-with-key.pem

8. Install the server key file on the controllers by typing:

.. code:: bash

  $ system certificate-install server-with-key.pem

9. Install the CA certificate on you browser (this will allow the browser to
recognize the server).

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Browse Horizon with HTTPS.

.. code:: bash

  e.g.
  https://10.10.10.3

2. Go to Project --> API Access.

3. Browse every single service available and male sure in add the exception by
importing the certificate from the browser.

e.g.

a)Browse --> https://10.10.10.2:8

b)Browser should come with following message:

::

  Your connection is not secure.
  The owner of 10.10.10.2 has configured their website improperly.
  To protect your information from being stolen, Firefox has not
  connected to this website....

c)Hit "Advanced" button.

d)Following message should be displayed:

.. code:: bash

  10.10.10.2:8977 uses an invalid security certificate.
  The certificate is not trusted because it is self-signed.
  The certificate is only valid for .
  Error code: MOZILLA_PKIX_ERROR_SELF_SIGNED_CERT

e) Hit "Add Exception..." button.

f) "Add Security Exception" pop up window should be displayed explaining that
"You are about to override how Firefox identifies this site..."

g) Hit "View" button in order to display Details of CA-certificate and make
sure it is the one you created.

h) Hit over """"Get certificate"""" or "Confirm Security Exception" button to
accept the certificate.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~


1. Horizon should be opened successufly with https browser connection.

2. A list of services and service ponts should be displayed.

.. code:: bash

  e.g.
  Service | Service Endpoint
  Alarming | https://10.10.10.2:8042
  Cloudformation | https://10.10.10.2:8000/v1/a52d40232ea64352b522b113ddc41d05
  Compute | https://10.10.10.2:8774/v2.1/a52d40232ea64352b522b113ddc41d05
  Event | https://10.10.10.2:8977
  Faultmanagement | https://10.10.10.2:18002
  Identity | https://10.10.10.2:5000/v3
  Image | https://10.10.10.2:9292
  Metering  -
  Metric | https://10.10.10.2:8041
  Network | https://10.10.10.2:9696
  Nfv | https://10.10.10.2:4545
  Orchestration | https://10.10.10.2:8004/v1/a52d40232ea64352b522b113ddc41d05
  Patching | https://10.10.10.2:15491
  Placement | https://10.10.10.2:8778
  Platform | https://10.10.10.2:6385/v1
  Smapi | https://10.10.10.2:7777

3. You should be able to get a response from the Service.

::

  e.g.

  versions
     values
        0
           status """"stable""""
           updated """"2013-02-13T00:00:00Z""""
           media-types 
              0
                 base """"application/json""""
                 type """"application/vnd.openstack.telemetry-v2+json""""
              1
                 base """"application/xml""""
                 type """"application/vnd.openstack.telemetry-v2+xml""""
        id """"v2""""
     links
        0
           href """"https://10.10.10.2:8977/v2""""
           rel """"self""""
        1
           href """"http://docs.openstack.org/""""
           type """"text/html""""
           rel """"describedby"""""

-------------------------
SECURITY_OAM_interface_03
-------------------------

:Test ID: SECURITY_OAM_interface_03
:Test Title: Backup and restore with OAM Firewall configuration file.
:Tags: Security config

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

The goal of this test is to confirm the port configration is preserved by the
backup and restore procedure.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Starlingx uses Netfilter framework for firewall setup. Make sure "iptables"
and "iptables-config" files exist in /etc/sysconfig path.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Install the Starlingx configuration with a custom configuration file.

2. Ensure there are no unexpected alarms post-install.

3. Use netstat command to verify that ports are up and listening by typing:

.. code:: bash

  Controller-0 $ sudo netstat -plant | grep <port>

REMARK: Please repeat netstat command for every single port listed in above
step.

or

.. code:: bash

  Controller-0 $ sudo netstat -plant | grep LISTEN

REMARK: you should get the full list of listening ports with all available
ips, save the list in order to compare it once the you do the restore in
further steps. Verify this on both controllers as well as the OAM float port.

or

.. code:: bash

  Controller-0 $ source /etc/nova/openrc

  Controller-0 $ openstack endpoint list

4. Pre-requisites to do  a BACKUP.

To ensure recovery from backup files during a restore procedure, VMs must be
in the active state when performing the backup. VMs that are in a shutdown or
paused state at the time of the backup will not be recovered after a
subsequent restore procedure.

.. code:: bash

  execute "sudo config_controller --backup <backup_name>"

5. Pre-requisites to do RESTORE.

All cluster hosts must be prepared for network boot and then powered down.
(Means for virtual you should power on wait for PXE messages and then
Power-down)

The restore procedure requires all hosts but controller-0 to boot over the
internal management network using the PXE protocol. Ideally, the old boot
images are no longer present, so that the hosts boot from the network when
powered on. If this is not the case, you must configure each host manually
for network boot immediately after powering it on.

Note: Save the backups previously created in a clean environment, perform
sudo config_controller --restore-system /home/$user/<backup_name_system.tgz>

6. Pre-requisites to do RESTORE.

All cluster hosts must be prepared for network boot and then powered down.
(Means for virtual you should power on wait for PXE messages and then
Power-down)

The restore procedure requires all hosts but controller-0 to boot over the
internal management network using the PXE protocol. Ideally, the old boot
images are no longer present, so that the hosts boot from the network when
powered on. If this is not the case, you must configure each host manually
for network boot immediately after powering it on.

Note: Save the backups previously created in a clean environment, perform
sudo config_controller --restore-images /home/$user/<backup_name_images.tgz>

7. Once the system is restored ensure the expected ports are still open. Use
netstat command to verify that ports are up and listening by typing:

.. code:: bash

  Controller-0 $ sudo netstat -plant | grep <port>

REMARK: Please repeat netstat command for every single port listed in above
step.

or

.. code:: bash

  Controller-0 $ sudo netstat -plant | grep LISTEN

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Starlingx configuration should be installed successfully.

2. No unexpected alarms were displayed in post-install.

3. The list of available ports should be displayed and saved it successfully.

4. After execute the sudo config_controller --backup <backupname> command
system.tgz and image.tgz files should be created successfully.

.. code:: bash

  e.g.
  Performing backup (this might take several minutes):
  Step 16 of 16 [#############################################] [100%]
  System backup file created: /opt/backups/<backupname>_system.tgz
  Images backup file created: /opt/backups/backupname_images.tgz""

5. system should be in the same way that the files were generated before

6. images shoule be in the same way that the files were generated before

7. Once the system is restore expected ports are open post-restored

-------------------------
SECURITY_OAM_interface_04
-------------------------

:Test ID: SECURITY_OAM_interface_04
:Test Title: Default system install without configuration file iptables rules.
:Tags: IPtable_rule

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

The goal of this test is to default system install without configuration file
iptables rules making sure when installing with/without Firewall ip tables
the installation is successfull.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Netfilter framework installed on Starlingx configuration.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Go to Virtual Dedicated Storage Installation Guide [1]

2. Go one step before "sudo config_controller" installation step - (one step
before ""Configuring Controller-0"" section)

3. Go to active controller and make sure in remove "iptables",
"iptables-config", "iptables.save",  "ip6tables", "ip6tables-config",
"ip6tables.save" from /etc/sysconfig path by typing rm -rf <file>

4. On active controller type:

.. code:: bash

   Controller-0 $ sudo config_controller and accept all default values

   or

   Controller-0 $ sudo config_controller --config-file <cfg_file_name>
   If you have created a specific configuration file for your cluster.

5. After "config_controller" bootstrap configuration Starlingx firewall is
enabled, make sure the ipfirewall rules are set by typing:

.. code:: bash

  Controller-0 $ sudo iptables --list-rules

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Steps for Virtual Dedicated Storage Installation Guide should be displayed.

2. Went one step before "sudo config_controller" installation step
successfully.

3. "iptables", "iptables-config", "iptables.save",  "ip6tables",
"ip6tables-config", "ip6tables.save" files removed from /etc/sysconfig path
successfully.

4. "config_controller" bootstrap configuration command executed successfully.

5. Following rules should be listed:

::

  -A INPUT -p tcp -m multiport --dports 22 -m comment --comment """"011 platform accept ssh ipv4"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 80 -m comment --comment """"500 horizon incoming dashboard"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 4545 -m comment --comment """"500 nfv-vim incoming nfv-vim-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 5000 -m comment --comment """"500 keystone incoming keystone-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 6080 -m comment --comment """"500 nova-novnc incoming nova-novnc"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 6385 -m comment --comment """"500 sysinv incoming sysinv-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8000 -m comment --comment """"500 heat-cfn incoming heat-cfn"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8003 -m comment --comment """"500 heat-cloudwatch incoming heat-cloudwatch"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8004 -m comment --comment """"500 heat incoming heat-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8042 -m comment --comment """"500 aodh incoming aodh-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8776 -m comment --comment """"500 cinder incoming cinder-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 8774 -m comment --comment """"500 nova incoming nova-api-rules"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 9292 -m comment --comment """"500 glance incoming glance-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 9696 -m comment --comment """"500 neutron incoming neutron-api"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 15491 -m comment --comment """"500 patching incoming patching-api"""" -j ACCEPT
  -A INPUT -p udp -m multiport --dports 123 -m comment --comment """"201 platform accept ntp ipv4"""" -j ACCEPT
  -A INPUT -p udp -m multiport --dports 161 -m comment --comment """"202 platform accept snmp ipv4"""" -j ACCEPT
  -A INPUT -p udp -m multiport --dports 2222,2223 -m comment --comment """"010 platform accept sm ipv4"""" -j ACCEPT
  -A INPUT -p tcp -m multiport --dports 443 -m comment --comment """"500 horizon incoming dashboard"""" -j ACCEPT

:REMARK Per Ken Young(Windriver): we no longer need to open 8777 for the cellometer-api, nor 8773 for nova-ec2.

-------------------------
SECURITY_OAM_interface_05
-------------------------

:Test ID: SECURITY_OAM_interface_05
:Test Title: SSH root access sshd config file changed, Connection rejected.
:Tags: SSH

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

Verify SSH root access to the regular lab is rejected after the change to sshd
config.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 1 Active Controller.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Generate an SSH key-pair.

.. code:: bash

  $ ssh-keygen -t rsa""

2. Copy the Public key over the Lab controller.

.. code:: bash

  $ scp ~/.ssh/<id_rsa.pub> wrsroot@<lab.ip>""

3. Copy the publick key from your wrsroot account into the "authorized_keys"
file of the "root" account.

Steps for adding ssh key:
  a) login to controller
  b) do sudo su to get to root
  c) create folder/file: /root/.ssh/authorized_keys if they do not exist
  d) cat /home/wrsroot/<id_rsa.pub/ >> /root/.ssh/authorized_keys""

4. Now login from your desktop using.

.. code:: bash

  $ ssh -I <id_rsa.pub> root@<lab.ip>"

On attempting to ssh with root(with/without password). The user will now
get "Permission denied" Error. Even if user try ssh -l <key> he should not be
prompt for password at all. The Denial output should be shown before any
password prompt.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

This generates a set of keys (private key and pub key. The pub one has the
.pub extention.

This adds your key into the roots authorized_ssh key.

-------------------------
SECURITY_OAM_interface_06
-------------------------

:Test ID: SECURITY_OAM_interface_06
:Test Title: Firewall rule removal function remove rules from both controllers
:Tags: firewall_rules

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

Verify firewall rule removal function correctly from both controllers.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) Starlingx uses Netfilter framework for firewall setup. Make sure "iptables"
and "iptables-config" files exist in /etc/sysconfig path.

b) Make sure in add at least one custom IP firewall. Check detail in how to do
it in "CLI firewall rules install function" Test Case.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. On active Controller, create an empty file to remove all firewall rules.

.. code:: bash

  $ touch /home/wrstoot/empty.rules

2. Install empty rule file to remove all the firewall rules by typing:

.. code:: bash

  $ system firewall-rules-install /home/wrsroot/empty.rules

3. After installed is completed make sure the firewall rules were removed by
typing:

.. code:: bash

  $ sudo iptables -L

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. "empty.rules" file is created successfully.

2. System firewall installed command is executed successfully.

3. Custom firewall rules should be removed successfully.

-------------------------
SECURITY_OAM_interface_07
-------------------------

:Test ID: SECURITY_OAM_interface_07
:Test Title: CLI firewall rules install function.
:Tags: firewall_rules

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

Verify that firewall-rules-install CLI command function works properly.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Starlingx uses Netfilter framework for firewall setup. Make sure "iptables"
and "iptables-config" files exist in /etc/sysconfig path.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create a ""iptables.rules"" file with custom firewall rule.

.. code:: bash

  $ iptables-save > iptables.rules

2. Create new rule by adding port 9000

.. code:: bash

  e.g.

  $ sudo vim iptables.rules

  -A INPUT -p tcp -m multiport --dports 9000 -m comment --comment "your rule" -j ACCEPT

3. Validate the file by typing the following command

.. code:: bash

  $ sudo iptables-restore --noflush --test < <iptable_rule_file>

  e.g.

  $ sudo iptables-restore --noflush --test < iptables.rules

4. Install custom firewall by typing: source /etc/nova/openrc

.. code:: bash

  $ system firewall-rules-install <iptable_rule_file>

  e.g.

  $ system firewall-rules-install iptables.rules

5. Make sure the custom firewall rule was applied successfully by typing:

.. code:: bash

  $ sudo iptables -L -n | grep <added_port>

  e.g.

  $ sudo iptables -L -n | grep 9000

:MAKE SURE THE PORT WAS ADDED SUCCESSFULLY BY USING IT FOR SSH COMMANDS.

6. Run the following command:

.. code:: bash

  $ sudo vim /etc/ssh/sshd_config

7. Locate the following line:

.. code:: bash

  # Port 22

8. Remove the # and change '22' to your desired port number. <9000>

9. Restart the sshd service by running the following command: $sudo su

.. code:: bash

  $ service sshd restart

10. Establish a ssh to the new port by typing:

.. code:: bash

  $ ssh <user>@<OAM_IP> - <specific_port>

  e.g.

  $ ssh wrsroot@10.10.10.4 -p 9000

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. "iptables.rules" file created successfully with custome firewall rule.

.. code:: bash

  e.g.
     *filter
     :INPUT DROP [0:0]
     :FORWARD DROP [0:0]
     :OUTPUT ACCEPT [2:312]
     :INPUT-custom-post - [0:0]
     :INPUT-custom-pre - [0:0]
     -A INPUT -p tcp -m multiport --dports 9000 -m comment --comment ""custome 9000 firewall rule"" -j ACCEPT
     COMMIT

2. The validation should be done successfully and no error message should be
shown.

3. The custom firewall was applied successfully and message logged.

.. code:: bash

   +--------------+--------------------------------------+
   | Property     | Value                                |
   +--------------+--------------------------------------+
   | uuid         | 183cb3a5-1085-49e0-b4c3-0970bb784fde |
   | firewall_sig | ab9dd4976d1d1d404df4e6fcda26e0dd     |
   | updated_at   | 2018-12-03 14:59:39.425337+00:00     |
   +--------------+--------------------------------------+

4. Custom firewall rule applied successfully.

.. code:: bash

  e.g.

  [wrsroot@controller-1 ~(keystone_admin)]$ sudo iptables -L -n |grep 9000
      ACCEPT     tcp  --  0.0.0.0/0            0.0.0.0/0            multiport dports 9000 /* custome 9000 firewall rule */

MAKE SURE THE PORT WAS ADDED SUCCESSFULLY BY USING IT FOR SSH COMMANDS.

5. sshd_config file is able to edit.

6. Proper line with # Port 22 was identified.

7. Line was edited successfully with port 9000.

8. sshd service was restarted successfully.

9. ssh connection made with port 9000.

-------------------------
SECURITY_OAM_interface_08
-------------------------

:Test ID: SECURITY_OAM_interface_08
:Test Title: Apply firewall rule on contr-1 and modifying it on contr-0.
:Tags: firewall_rules

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

Verify that by using the firewall-rules-install CLI command you can add a
firewall rule on Controller-1 and then modified that rule on Controller-0.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Starlingx uses Netfilter framework for firewall setup. Make sure "iptables"
and "iptables-config" files exist in /etc/sysconfig path.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Go to Active Controller-0 and execute the "CLI firewall rules install
function" test case.

2. swact controller-0 to controoler-1.

3. $sudo vim /etc/ssh/sshd_config

.. code:: bash

  change port 22 to port 9000

4. sudo service sshd restart

5. ssh wrsroot@ip-controller-1 -p 9000

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. On Controller-1 custome firewall rule was installed successfully.

2. On Controller-0 custome firewall rule was updated sucessfully.

3. Custome Firewall rule modifcation from step 2 taken in both controllers.

-------------------------
SECURITY_OAM_interface_09
-------------------------

:Test ID: SECURITY_OAM_interface_09
:Test Title: Custom firewall rule persistance after backup/restore.
:Tags: firewall_rules

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

Verify that once "System firewall-rules-install" CLI is executed the new
custom firewall rule persist after backup/restore.


~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Starlingx uses Netfilter framework for firewall setup. Make sure "iptables"
and "iptables-config" files exist in /etc/sysconfig path.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Go to Active Controller and execute the "CLI firewall rules install
function" test case.

2. Once the custome firewall rule is applied do a backup of your cluster.

**Pre-requisites to do  a BACKUP.**

To ensure recovery from backup files during a restore procedure, VMs must be
in the active state when performing the backup. VMs that are in a shutdown or
paused state at the time of the backup will not be recovered after a
subsequent restore procedure.

.. code:: bash

  execute "sudo config_controller --backup <backup_name>"

3. Make a System Restore expecting to see the custome firewall rule.

**Pre-requisites to do RESTORE.**

All cluster hosts must be prepared for network boot and then powered down.
(Means for virtual you should power on wait for PXE messages and then
Power-down)

The restore procedure requires all hosts but controller-0 to boot over the
internal management network using the PXE protocol. Ideally, the old boot
images are no longer present, so that the hosts boot from the network when
powered on. If this is not the case, you must configure each host manually for
network boot immediately after powering it on.

Note: Save the backups previously created in a clean environment, perform:

.. code:: bash

  sudo config_controller --restore-system /home/$user/<backup_name_system.tgz>"

4. Make a Image restore.

**Pre-requisites to do RESTORE.**

All cluster hosts must be prepared for network boot and then powered down.
(Means for virtual you should power on wait for PXE messages and then
Power-down)

The restore procedure requires all hosts but controller-0 to boot over the
internal management network using the PXE protocol. Ideally, the old boot
images are no longer present, so that the hosts boot from the network when
powered on. If this is not the case, you must configure each host manually for
network boot immediately after powering it on.

**Note:** Save the backups previously created in a clean environment, perform:

.. code:: bash

  sudo config_controller --restore-images /home/$user/<backup_name_images.tgz>"

5. Once the system is restored ensure the expected ports are still open. Use
netstat command to verify that ports are up and listening by typing:

.. code:: bash

  Controller-0 $ sudo netstat -plant | grep <port>

**REMARK:** Please repeat netstat command for every single port listed in above
step.

or

.. code:: bash

  Controller-0 $ sudo netstat -plant | grep LISTEN"

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. On Controller-1 custome firewall rule was installed successfully.

2. After execute the sudo config_controller --backup <backupname> command
system.tgz and image.tgz files should be created successfully.

.. code:: bash

  e.g.
  Performing backup (this might take several minutes):
  Step 16 of 16 [#############################################] [100%]
  System backup file created: /opt/backups/<backupname>_system.tgz
  Images backup file created: /opt/backups/backupname_images.tgz

3. system should be in the same way that the files were generated before

4. images shoule be in the same way that the files were generated before

5. Once the system is restore expected ports are open post-restored

-------------------------
SECURITY_OAM_interface_10
-------------------------

:Test ID: SECURITY_OAM_interface_10
:Test Title: "iptables.rules" file with wrong format used with "firewall-rules-install" command.
:Tags: firewall_rules

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

Verify when using an "iptables.rules" file with wrong format, the system
firewall install CLI command get a gracefully error output.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Starlingx uses Netfilter framework for firewall setup. Make sure "iptables"
and "iptables-config" files exist in /etc/sysconfig path.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create a "wrongiptables" file with wrong format.

2. Install custom firewall by typing:

.. code:: bash

  $ system firewall-rules-install <wrong_iptable_rule_file>

  e.g.

  $ system firewall-rules-install wrongiptables

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. "wrongiptables" file with wrong format created successfully.

2. Firewall rule install command executed should display an error message when
"wrongiptables" wrong format file was used.

.. code:: bash

  e.g.

  controller-1 ~(keystone_admin)]$ system firewall-rules-install wrongiptables
      Error in custom firewall rule file"

-------------------------
SECURITY_OAM_interface_11
-------------------------

:Test ID: SECURITY_OAM_interface_11
:Test Title: NFV (port 32323) software debug access removed.
:Tags: api

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

Verify that NFV (port 32323) software debug access is removed by using curl
command request and "openstack endpoint list" command. The reason of this test
case is to comply with intel security debug access removal in all intel
products. By default the port "32323" and the IP assigned to the network
interface card (NIC) which connect to external orchestration, administration
and operation (OAM) network it is used only for debugging purposes by the
design team.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) Add Service Endpoing IP into no_proxy .bashrc file.

::

  - Go to Horizon --> Project --> API Access and identify what Service Endpoint has your Starlingx cluster.
  - Open a terminal in the Host where your Starlingx cluster resides.
  - Add the Service Endpoint IP into your no_proxy .bashrc

.. code:: bash

  e.g.

  export no_proxy=intel.com,10.10.10.2
  Authenticate 10.10.10.2

- Open a terminal and make sure you can ssh to the Service Endpoint IP

.. code:: bash

  $ ssh wrsroot@10.10.10.2. (submit proper password)

b) Get token from keystone.

::

  - In the ssh 10.10.10.2 session send the following curl command to get the proper token from keystone where <PASSWORD> is your Horizon admin password.

.. code:: bash

  $ curl -i -X POST http://10.10.10.2:5000/v2.0/tokens -H ""Content-Type: application/json"" -H ""User-Agent: python-keystoneclient"" -d '{""auth"": {""tenantName"": ""admin"", ""passwordCredentials"": {""username"": ""admin"", ""password"": ""<PASSWORD>""}}}' | tail -n 1

  e.g.
  You would be expecting an output similar like this:

  {""access"": {""token"": {""issued_at"": ""2018-12-07T10:52:27.000000Z"", ""expires"": ""2018-12-07T11:52:27.000000Z"", ""id"": ""gAAAAABcClDrLoF7_W03l8uhrPQ9dn4tkuvbd9pfsgIo6-PkObg3imG4HTGT2IQLGkBOszjcS1jOC7g0ZqKByoZ3cEax7LKAiEgC_fkPEnB_mpSjqd5ACzc20VLZaklQfFLXiU4b-w_pZeMPHF09FsP8P4j-ixqx9IgYEEc-4Zmb9cjZ5phNQfA"",

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Open a terminal in the Host where your Starlingx cluster resides. From pre-
requisites make sure you did ssh to the Service Endpoint IP.

2. Make a curl request to nfv port 32323 using the "token" gotten from Pre-
requisites steps.

.. code:: bash

  e.g.

  $ curl -i http://10.10.10.2:32323 -X GET -H ""Contenpe: application/json"" -H ""Accept: application/json"" -H ""X-Auth-Token:""gAAAAABcCnq_pXb57FKTwP0VI8Ry5kuDTHzRWTgcAXfS9ir-HiBN14BSVuXKwIsqDU0SWoztk4sBj0U912AEdU1GawOdniI1yC3-VY_I7BwWSXSlPDccojU7GMdB3KAwXoUWVPELrshGwkBSu2RSLsbZhjSZarxH1CNgeUgPsj5fSMdq81R4qzw"""" | tail -n 1

3. Go to Active controller and make sure no NFV (port 32323) Service exist by
typing:

.. code:: bash

      $ openstack endpoint list | grep 32323

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Open terminal and validate ssh connection to the Service Endpoint IP
successfully.

2. Curl command will get a failure message "Failed to connect to 10.10.10.2
port 32323: Connection timed out"

::

  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:-
  0     0    0     0    0     0      0      0 --:--:--  0:00:02 --:-
  0     0    0     0    0     0      0      0 --:--:--  0:01:39 --:-
  0     0    0     0    0     0      0      0 --:--:--  0:01:40 --:-
  0     0    0     0    0     0      0      0 --:--:--  0:02:09 --:-
  curl: (7) Failed to connect to 10.10.10.2 port 32323: Connection timed out
  100    90  100    90    0     0    183      0 --:--:-- --:--:-- --:--:--   548

3. No NFV (port 32323) service exist.

-------------------------
SECURITY_OAM_interface_12
-------------------------

:Test ID: SECURITY_OAM_interface_12
:Test Title: NFV (port 4545) API Service
:Tags: API

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

Verify that NFV (port 4545) Service is LISTENING by using curl command request
and "openstack endpoint list" command.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Verify that NFV (port 4545) Service is LISTENING by using curl command request
and "openstack endpoint list" command.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Open a terminal in the Host where your Starlingx cluster resides. From pre-
requisites make sure you did ssh to the Service Endpoint IP.

2. Make a curl request to nfv port 4545 using the "token" gotten from Pre-
requisites steps.

.. code:: bash

  e.g.
  $ curl -i http://10.10.10.2:4545 -X GET -H ""Contenpe: application/json"" -H ""Accept: application/json"" -H ""X-Auth-Token:""gAAAAABcCnq_pXb57FKTwP0VI8Ry5kuDTHzRWTgcAXfS9ir-HiBN14BSVuXKwIsqDU0SWoztk4sBj0U912AEdU1GawOdniI1yC3-VY_I7BwWSXSlPDccojU7GMdB3KAwXoUWVPELrshGwkBSu2RSLsbZhjSZarxH1CNgeUgPsj5fSMdq81R4qzw"""" | tail -n 1

3.  Go to Active controller and make sure no NFV (port 4545) Service exist by typing:

.. code:: bash

  $ openstack endpoint list | grep 4545

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Open terminal and validate ssh connection to the Service Endpoint IP
successfully.

2. Curl command will succed.

3. The NFV (port 4545) service exist and is in LISTENING status.

~~~~~~~~~~~
References:
~~~~~~~~~~~
[0] - https://www.sslshopper.com/what-is-a-csr-certificate-signing-request.html"

[1] - https://docs.starlingx.io/installation_guide/dedicated_storage.html#dedicated-storage

=====
https
=====

.. contents::
   :local:
   :depth: 1

-----------------
SECURITY_https_01
-----------------

:Test ID: SECURITY_https_01
:Test Title: System install with badly formed configuration file scenario1.
:Tags: config

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify the system can handle a badly formed configuration file and has the
ability to continue with the installation after correcting the errors in the
"config_controller.ini" file, without having to reinstall the system.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) A bootable USB with Stx...iso file.

b) To run the playbook, you need to first set up external connectivity [1] 
and wrong "localhost.yml" file created.

.. code:: bash

  # Mandatory
  system_mode: duplexx # double 'x'

  # Optional
  external_oam_subnet: 10.10.10.0/260 # Wrong subnet
  external_oam_gateway_address: 10.10.10.1
  external_oam_floating_address: 10.10.10.1 # IP duplicated
  external_oam_node_0_address: 10.10.10.4
  external_oam_node_1_address: 10.10.10.5
  management_subnet: 192.168.204.0/24
  dns_servers:
    - 8.8.4.4 # wrong DNS server
  admin_password: St4rlingX*
  ansible_become_pass: St4rlingX*

c) For Bare Metal, make sure the Management, OAM and data networks are planned
set up, and connected.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

**Starlingx**

1. Power on the host to be configured as controller-0.

2. Configure the host BIOS boot sequence to boot from a USB removable storage
device.

3. Insert the USB flash drive and boot the host.

4. Select "All-in-one Controller Configuration".

5. Select "Graphical Console" for installation.

6. Select "STANDARD Security Boot Profile" Security profile.

7. login into the hsot as sysadmin, with proper password configured.

**Copying the localhost.yml File to Controller-0**

8. Connected the controller-0 to the OAM network:

.. code:: bash

  ip address add 10.10.10.3/24 dev <interface_name>

  ip link set up dev <interface_name>

  ip route add default via 10.10.10.1 dev <interface_name>

9. Copy the "localhost.yml" file from your machine to the controller-0

10. Install the system using that malformed configuration file by applying
the ansible-playbook bootstrap command.

.. code:: bash

  $ ansible-playbook /usr/share/ansible/stx-ansible/playbooks/bootstrap/bootstrap.yml

11. Ensure the user can re-run the install after correcting the errors,
**i.e.** they should not have to wipedisk and then re-install.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

**Starlingx**

1. Host to be configured as a controller-0 powered on.

2. Host BIOS boot sequence configured to USB removable storage device.

3. The installer is loaded, and the "Select kernel options and boot kernel
installer welcome screen appears".

4. "All-in-one Controller Configuration" selected.

5. "Graphical Console" for installation selected.

6. "STANDARD Security Boot Profile" Security profile selected. Monitor the
initialization until is completed and remove the USB flash drive from the host
to ensure the host reboots from the hard drive.

7. First time you log in as wrsroot you will be asked to change the password.

**Copying the Configuration Input File to Controller-0**

8. Controller-0 is connected to the OAM network.

9. "localhost.yml" file copied successfully on Controller-0.

10. ansible-playbook bootstrap command failed. The user is presented with an error
message describing the nature of the provisioning failure. (Add several typos
into the file and solve one by one)

11. After all errors are corrected the user can re-run and installed the
product.

This test passes if the formatting issue is detected by the system and an
error message is returned to the user. Also required is the ability to
continue with the installation after correcting errors with the file,
without having to reinstall the system.

-----------------
SECURITY_https_02
-----------------

:Test ID: SECURITY_https_02
:Test Title: On IPv6 lab Verify SSH **root** access to the lab is rejected.
:Tags: config

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify ssh root access is rejected even if the id_rsa.pub public key is provided.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 1 Controller over IPV6.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Generate an SSH key-pair on your linux (client).

.. code:: bash

  $ ssh-keygen -t rsa

**REMARK:** This generates a set of keys (private key and pub key. The pub one
has the .pub extention)

2. Copy the Public key over the IPv6 Lab controller

.. code:: bash

  $ scp ~/.ssh/<id_rsa.pub> wrsroot@<lab.ip>

3. Copy the <id_rsa.pub> publick key into the "authorized_keys" file of the
"root" account

::

  a) Login to controller

  b) Do sudo su to get to root

  c) Validate you got root by typing:

    $ whoami

  d) Create folder/file: /root/.ssh/authorized_keys if they do not exist

  e) Copy <id_rsa.pub> into <authorized_keys>
    $ cat /home/wrsroot/<id_rsa.pub> >> /root/.ssh/authorized_keys

4. Now login from your desktop using:

.. code:: bash

  $ ssh -I <public_key> root@<lab.ip>"

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. ssh key-pair generated successfully.

2. Public key successfully copied on Controller-0.

3. This adds your key into the roots authorized_ssh key.

4. You should not be able to ssh as root user to the lab, waiting for a
message saying something like the following:

::

  root@<ipv6lab>: Permission denied (publickey).

-----------------
SECURITY_https_03
-----------------

:Test ID: SECURITY_https_03
:Test Title: Negative test case, https-certificate-install unsuccessful when --https_enabled flag on Controller-0 is "False"
:Tags: https

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test verifies that if https_enabled=False installing signed certificate
is rejected.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) On Active Controller, execute following command to disable https port:

.. code:: bash

  $ system modify --https_enabled false

b) Make sure the --https_enabled flag is set "false" by typing:

.. code:: bash

  controller-0 $ system show

c) Obtain a CA-Signed Certificate. Steps to create your own CA certificate
(go to pre-condition of "Validate that services respond over https" Test Case
for create the certifiacte)

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Once you got the certificate (check your precondition) move the certificate
to your controller-0 and try to install the certificate by typing:

.. code:: bash

  $ system certificate-install server-with-key.pem

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. The certtificate should not be installed and you should get an erro message
similar to:

**WARNING:** For security reasons, the original certificate, containing the
private key, will be removed, once the private key is processed. Certificate
server-with-key.pem not installed: Error decryption PEM file: Could not
unserialize key data.

-----------------
SECURITY_https_04
-----------------

:Test ID: SECURITY_https_04
:Test Title: https enable post-install AIO-DX lab.
:Tags: https

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test verifies that https can successfully be enabled on AIO-DX syste
post-install.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) All in One AIO - Duplex DX configuration.

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

  execute ""sudo config_controller --backup <backup_name>""

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

**Note:** Save the backups previously created in a clean environment, perform
sudo config_controller --restore-system /home/$user/<backup_name_system.tgz>

4. Make a Image restore.

**Pre-requisites to do RESTORE.**

All cluster hosts must be prepared for network boot and then powered down.
(Means for virtual you should power on wait for PXE messages and then
Power-down)

The restore procedure requires all hosts but controller-0 to boot over the
internal management network using the PXE protocol. Ideally, the old boot
images are no longer present, so that the hosts boot from the network when
powered on. If this is not the case, you must configure each host manually
for network boot immediately after powering it on.

**Note:** Save the backups previously created in a clean environment, perform
sudo config_controller --restore-images /home/$user/<backup_name_images.tgz>

5. Once the system is restored ensure the expected ports are still open. Use
netstat command to verify that ports are up and listening by typing:

.. code:: bash

  Controller-0 $ sudo iptables -L -n | grep 9000

**REMARK:** Please repeat netstat command for every single port listed in
above step.

or

.. code:: bash

  Controller-0 $ sudo netstat -plant | grep LISTEN

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. AIO-DX lab installed successfully and https enabled in port 443
successfully.

2. CA-singed certificate installed on Controller-0 successfully.

3. Before proceeding to the next step, out-of-date alarms should be cleared.

4. All public endpoints should be changed to https successfully.

5. Horizon Web browser is accessible just via https and correct certificate is
presented.

6. SWACT made successfully.

7. Horizon Web browser is accessible just via https and correct certificate is
presented after SWACT.

-----------------
SECURITY_https_05
-----------------

:Test ID: SECURITY_https_05
:Test Title: https IPv6 enable post-install standard system
:Tags: https

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This tests verifies that https can be successfully enabled on Starlingx in
IPv6 mode.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) Make sure in have proper IPV6 Infrastructure ready for Starlingx and once
the Infrastructure of IPv6 is set install the Starlingx product. Take note of
the Controller-0,1 and floating IPv6 Addresses.

**REMARK:** 2_12 OAM was set with IPv6 and Management with IPV4. currently we
are not able to set Management with IPv6.

.. code:: bash

  i.e.
  fd62:2b07:a9f1:7222::84 - controller-0
  fd62:2b07:a9f1:7222::85 - controller-1
  fd62:2b07:a9f1:7222::202 - FloatingIP

b) On Active Controller, execute following commands to enable 443 https port:

.. code:: bash

  $ system modify -p true

  $ system modify --https_enabled true

c) Obtain a CA-Signed Certificate. Steps to create your own CA certificate.

1. Generate your own server private key (can be used on multiple servers) by
typing:

.. code:: bash

  $ openssl genrsa -out server-key.pem 2048

2. Generate the public certificate for the server private key ("commonName"
attribute must match the floating IP of the servers).
For more reference go to [0].

.. code:: bash

  $ openssl req -new -key server-key.pem -out /home/user/server.csr -batch -subj ""/countryName=CN/stateOrProvinceName=<your state>/localityName=<city>/organizationName=<Your Company>/organizationalUnitName=<Your Org>/commonName=<Controller-0_IPV6>"

  e.g.
  $ openssl req -new -key server-key.pem -out /home/fhernan2/server.csr -batch -subj ""/countryName=MX/stateOrProvinceName=Jalisco/localityName=Guadalajara/organizationName=intel/organizationalUnitName=SSG/commonName=<Controller-0_IPV6>""

3. Generate CA private key by typing:

.. code:: bash

  $ openssl genrsa -out ca-key.pem 2048

4. Generate CA public certificate (to be installed on the client browser) by
typing:

.. code:: bash

  $ openssl req -x509 -new -nodes -key ca-key.pem -days 3650 -out ca-cert.pem -outform PEM -subj ""/countryName=CN/stateOrProvinceName=<your state>/localityName=Ottawa/organizationName=<your Company>/organizationalUnitName=<Your gruo>/commonName=<Your Common Name>"" -text -batch
  e.g.
  $openssl req -x509 -new -nodes -key ca-key.pem -days 3650 -out ca-cert.pem -outform PEM -subj ""/countryName=MX/stateOrProvinceName=Jalisco/localityName=Guadalajara/organizationName=intel/organizationalUnitName=SSG/commonName=<Controller-0_IPV6>""

5. Signing the server public certificate with CA private key by typing:

.. code:: bash

  $ openssl x509 -req -in ../vbox/server.csr -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial -out ../vbox/server.pem -days 3650
  e.g.
  $ openssl x509 -req -in /home/fhernan2/CA_certificate/server.csr -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial -out /home/fhernan2/CA_certificate/server.pem -days 3650
    Signature ok
    subject=/C=MX/ST=Jalisco/L=Guadalajara/O=intel/OU=SSG/CN=<Controller-0_IPV6>
    Getting CA Private Key

6. Move the server-key.pem, server.pem, files from the host where you create
them to Active Controller by typing:

.. code:: bash

  $ scp server* wrsroot@<Controller-0_IPV6>:~

7. Create a server key file by concatenating the server private key and the
CA-signed server certificate in a key file. Generate key file for installation
on controller node by typing:

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

1. Browse Horizon with Floating IPv6 HTTPS.

.. code:: bash

  e.g.

  https://[fd62:2b07:a9f1:7222::202]

**REMARK:** You will recieve a warning "NET::ERR_CERT_AUTHORITY_INVALID"" on
your browser, make sure is the Certificate you created and accept it -(you can
go to your browser settings and add the certificate manually)

2. Login Horizon and go to Project --> API Access.

3. Browse services randomly.

.. code:: bash

  e.g.
  a)Browse --> https://[fd62:2b07:a9f1:7222::202]
  b)Browser should come with following message:
    Your connection is not private. Attackers might be trying to steal your information... ""NET::ERR_CERT_AUTHORITY_INVALID"" on your browser...
  c)Hit """"Advanced"""" button.
  d)Following message (or something similar) would be displayed:
    This server could not proe that it is [fd62:2b07:a9f1:7222::202]...
  e)Hit ""Proceed to [fd62:2b07:a9f1:7222::202](unsage)"" link."

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Horizon should be opened successufly with IPv6 https browser connection.

2. A list of services and service ponts should be displayed.

.. code:: bash

  e.g.
  Service        | Service Endpoint
  Alarming       | https://[fd62:2b07:a9f1:7222::202]:8042
  Cloudformation |

3. You should be able to get a response from the Service.

.. code:: bash

  i.e.
  {""version"": {""status"": ""stable"", ""updated"": ""2017-02-22T00:00:00Z"", ""media-types"": [{""base"": ""application/json"", ""type"": ""application/vnd.openstack.identity-v3+json""}], ""id"": ""v3.8"", ""links"": [{""href"": ""https://[fd62:2b07:a9f1:7222::202]:5000/v3/"", ""rel"": ""self""}]}}
  {""versions"": [{""status"": ""CURRENT"", ""id"": ""v2.0"", ""links"": [{""href"": ""https://[fd62:2b07:a9f1:7222::202]:9696/v2.0/"", ""rel"": ""self""}]}]}"

~~~~~~~~~~~
References:
~~~~~~~~~~~

[0] - https://www.sslshopper.com/what-is-a-csr-certificate-signing-request.html

[1] - https://wiki.openstack.org/wiki/StarlingX/

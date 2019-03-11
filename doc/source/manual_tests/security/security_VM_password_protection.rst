======================
VM password protection
======================

.. contents::
   :local:
   :depth: 1

----------------------------------
SECURITY_VM_password_protection_01
----------------------------------

:Test ID: SECURITY_VM_password_protection_01
:Test Title: wrsroot Password expiration.
:Tags: Security psswd

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test verifies that once the linux wrsroot user password expires a user is
forced to change it on next login.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 2 Controllers + 1 compute.

b) Disable NTP automatic time synchronization in your system.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Go to controller-0 node terminal and login as admin user. e.g. "wrsroot"

2. Type the following command to disable ntp automatic time synchronization.

.. code:: bash

  $ sudo timedatectl set-ntp 0

3. Type following command and check ""NTP enabled: no"".

.. code:: bash

  $ sudo timedatectl status

4. Take a snapshoot of the time-date.

5. Set password maximum number during which a password is valid to 1 day by
typing:

.. code:: bash

  $ sudo chage -M 1 wrsroot

6. Type below command and make sure the Maximum number of days between
password change is set to 1.

.. code:: bash

  $ sudo chage -l wrosroot

7. Wait 24 hours OR change the date-time of the system 1 day ahead by typing:

.. code:: bash

  $ sudo timedatectl set-time 'YYYY-MM-DD'

  <where DD is one day ahead of the real time-date.>

8. Type below command and check the time-date is 1 day ahead of the real time.

.. code:: bash

  $ sudo timedatectl status

9. From your host Attempt to ssh to the controller-0 after the password ages
out by typing:

.. code:: bash

  $ ssh -q wrsroot@###.###.###.###""""

10. Do not change the password and CLOSE your wrsroot ssh connection.

11. From your host Attempt to ssh wrsroot user again to the controller-0:

.. code:: bash

  $ ssh -q <wrsroot>@###.###.###.###

12. Change your wrsroot aged password.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Admin logged in successfully.

2. NTP Automatic time synchronization should be disabled successfully.

3. "NTP enabled: no" should be displayed.

4. Time-date snapshot taken.

5. Maximum number of days between password change should be set to 1.

6. Maximum number of days between password change should be displayed '1'.

7. You waited 24 hours or you changed the date of the system one day ahead
successfully.

8. Time of the system should be displayed with 1 day ahead.

9. Once you create ssh connection you would get a following message:

::

    "" You are required to change your password immediately (password aged) ""
    "" Changing password for wrsroot""
    "" (current) UNIX password: ""
    "" New password:

10. wrsroot ssh connection closed successfully.

11. "wrsroot" SSH connection established successfully even if the wrsroot was
aged out.

12. Once you re-tried a wrsroot ssh connection you would get a following
message:

::

  "" You are required to change your password immediately (password aged) ""
  "" Changing password for wrsroot""
  "" (current) UNIX password: ""
  "" New password: ""
  ""wrsroot"" user changed its password successfully.

----------------------------------
SECURITY_VM_password_protection_02
----------------------------------

:Test ID: SECURITY_VM_password_protection_02
:Test Title: Backup and restore with different password.
:Tags: backup_restore

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify Starlingx backup and restore cluster with different password and run a
basic tet sanity after.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 2 Controllers + 1 compute.

b) Backup and restore find where password has to be changed.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Run test case "wrsroot Password expiration" and change the wrsroot Password

OR

install your Starlingx configuration and use "passwd wrsroot" command as a
"root user" to change its password.

**BACKUP**

2. Pre-requisites to do a BACKUP.

To ensure recovery from backup files during a restore procedure, VMs must be
in the active state when performing the backup. VMs that are in a shutdown or
paused state at the time of the backup will not be recovered after a
subsequent restore procedure.

3. Execute

.. code:: bash

  "sudo config_controller --backup <backup_name>"

4. Transfer the backup files to an external storage resource.

You can use a command such as scp to transfer the backup files to a server
reachable over the OAM network. You can also copy them to a locally attached
storage device, such as an external USB drive.

**RESTORE**

5. Pre-requisites to do RESTORE.

Create the same infrastructure from where you made the backup until one step
before "config_controller" command - that means that you should get you are

a) "rMMYYY.iso" installed, b) your controller-0 active, and c) all your nodes
should be up and running (If you are restoring in a virtual lab, make sure ALL
cluster hosts must be prepared for network boot - means you should power-on
your nodes and wait for PXE messages)

**REMARK:** The restore procedure requires all hosts but controller-0 to boot
over the internal management network using the PXE protocol. Ideally, the old
boot images are no longer present, so that the hosts boot from the network
when powered on. If this is not the case, you must configure each host
manually for network boot immediately after powering it on.

6. Make a restore in a clean environment, perform

.. code:: bash

  $ sudo config_controller --restore-system /home/user/<backup_name_system.tgz>

7. Verify all nodes are locked.

a) Check the current lock status for the nodes.

.. code:: bash

  i.e.

  $ system host-list

b) Lock any unlocked nodes.

.. code:: bash

  $ system host-update # action=force-lock

8. Transfer <Backupname_images.tgz> file to master controller-0.

**All nodes where waiting on PXE boot network.**

9. Execute restore images command by typing:

.. code:: bash

  $sudo confirg_controller --restore-image /home/<user>/<backupname.tgz>

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. "wrsroot" password changed successfully.

.. code:: bash

  i.e.
  "Starlingx1!"

2. Backup prerequisite set and all VMs were on active state successfully.

3. Backup created successfully.

.. code:: bash

  i.e.
  Backup output
    Step 16 of 16
    System backup file created: /opt/backups/<backupname>_system.tgz
    Images backup file created: /opt/backups/<backupname>_images.tgz

4. <backupname>_sytem.tgz, <backupname>_images.tgz, were transferred
successfully to an external storage for further restore steps.

5. The same Lab infrastructure was created from where the backup was made.
Your a) "rMMYYY.iso" should be installed successfully, b) your controller-0
should be active, and c) all your nodes should be up, running, locked and able
to boot over the internal management network.

6. Restore the system was 100% complete. Meanwhile the restore command was in
progress all nodes where "Forced reset" constantly.

**REMARK:** At this point PXE boot blue screen was displayed in every single
node.

7. All nodes were locked successfully.

8. <Backupname_images.tgz>  file was transferred to master controller-0.

9. Your Starlingx configuration lab should be restore successfully with proper
password changed on step 1.

----------------------------------
SECURITY_VM_password_protection_03
----------------------------------

:Test ID: SECURITY_VM_password_protection_03
:Test Title: Automatic logout of inactive ssh session.
:Tags: Security

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test verified automatic logout of inactive ssh session.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 2 Controllers + 1 compute.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Go to controller-0 node terminal and login as admin user. e.g. "wrsroot"

2. Take a snapshoot of the time-date.

.. code:: bash

  "Keep the session inactive along "n" minutes until the session is automatically logout.

**REMARK:** "n" minutes is described in the configuration user session.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Admin logged in successfully.

2. Time-date snapshot taken.

3. The session should be logged out successfully after "n" minutes of inactive
session.

----------------------------------
SECURITY_VM_password_protection_04
----------------------------------

:Test ID: SECURITY_VM_password_protection_04
:Test Title: MAX time for login enforced.
:Tags: psswd

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test verifies that maximum time for login is enforced. If a user does not
login within previously configured time - login is aborted.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 1 Controller.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Establish a ssh connection to controller-0 terminal.

.. code:: bash

  e.g.

  $ ssh wrsroot@10.10.10.3""

2. DO NOT ENTER PASSWORD and wait 60 seconds in order to login.

3. Try to enter password for ssh connection."

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Controller-0 should go back with "wrsroot@10.10.10.3's password:" message
successfuly.

2. Password is not entered and session wait for more than 60 seconds
successfully.

3. Login password request is timeout and session login is lost successfully.

.. code:: bash

  e.g.

  expected message on CentOS:

  Connection to 10.10.10.3 closed by remote host.

  Connection to 10.10.10.3 closed.

----------------------------------
SECURITY_VM_password_protection_05
----------------------------------

:Test ID: SECURITY_VM_password_protection_05
:Test Title: wrsroot aging and swact.
:Tags: psswd

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify wrsroot aging and swact.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 2 Controllers + 1 compute.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Go to controller-0 node terminal and login as admin user. e.g. ""wrsroot""

2. Type

.. code:: bash

  $ sudo timedatectl set-ntp 0 to disable ntp automatic time synchronization.""

3. Type following command and check NTP enabled: no"

.. code:: bash

  $ sudo timedatectl status

4. Take a snapshoot of the time-date.

5. Set wrsroot password maximum number during which a password is valid to 1
day by typing:

.. code:: bash

  $ sudo chage -M 1 wrsroot""

6. Type following command and make sure the Maximum number of days between
password change is set to 1 and SWACT.

.. code:: bash

  $ sudo chage -l wrosroot

7. Wait 24 hours or change the date-time of the system 1 day ahead by typing:

.. code:: bash

  $ sudo timedatectl set-time 'YYYY-MM-DD'

  where DD is one day ahead of the real time-date.
  Go to horizon and do a SWACT.
  Right after the SWACT is completed try to login using wrsroot user and correct password on controller-1.
  Change your wrsroot aged out password.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Admin logged in successfully.

2. NTP Automatic time synchronization should be disabled successfully.

3. NTP enabled: no should be displayed.

4. Time-date snapshot taken.

5. Maximum number of days between wrsroot password change should be set to 1.

6 Maximum number of days between password change should be displayed '1'. The
command should be executed successfully. SWACT is completed successfully. The
Controller-1 should got back with a message saying

::

  ** WARNING: Your password has expired **
  ** You must change your password now and login again!...**""

7. Password changed successfully.

----------------------------------
SECURITY_VM_password_protection_06
----------------------------------

:Test ID: SECURITY_VM_password_protection_06
:Test Title: swact wrsroot aging on controller-1
:Tags: psswd

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify wrsroot aging can be set on controller-1.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 2 Controllers + 1 compute.

b) Disable NTP automatic time synchronization in your system.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. With controller-0 "Active", go to horizon and do a SWACT.

2. Go to controller-1 node terminal and login as admin user. e.g. ""wrsroot""

3. Type

.. code:: bash

  $ sudo timedatectl set-ntp 0 to disable ntp automatic time synchronization.""

4. Type and check "NTP enabled: no"

.. code:: bash

  $ sudo timedatectl status

5. Take a snapshoot of the time-date.

6. Set wrsroot password maximum number during which a password is valid to 1
day by typing:

.. code:: bash

  $ sudo chage -M 1 wrsroot""

7. Type following command and make sure the Maximum number of days between
password change is set to 1.

.. code:: bash

  $ sudo chage -l wrosroot

8. Wait 24 hours or change the date-time of the system 1 day ahead by typing:

.. code:: bash

   $ sudo timedatectl set-time 'YYYY-MM-DD'
   where DD is one day ahead of the real time-date.

9. Change your wrsroot aged out password.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. SWACT is completed successfully.

2. Admin logged in successfully.

3. NTP Automatic time synchronization should be disabled successfully.

4. NTP enabled: no should be displayed.

5. Time-date snapshot taken.

6. Maximum number of days between wrsroot password change should be set to 1.

7. Maximum number of days between password change should be displayed '1'.

8. The command should be executed successfully.

9. Password changed successfully.

~~~~~~~~~~~
References:
~~~~~~~~~~~

===================
Password rule setup
===================

.. contents::
   :local:
   :depth: 1

-------------------------------
SECURITY_password_rule_setup_01
-------------------------------

:Test ID: SECURITY_password_rule_setup_01
:Test Title: System admin user is capable of changing password quality.
:Tags: psswd

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify that system admin user is capable of changing password quality.

Password quality configuration is validated using "pam_pwquality" library.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 1 Controllers + 1 compute.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* Login to controller-0 using system admin user, source /etc/nova/openrc

* To change password quality configuration on the controller, edit ``/etc/pam.d/common-password.``

* The password quality validation is configured via the first non-comment line

.. code :: bash

  password    required                        pam_pwquality.so try_first_pass retry=3 authtok_type=    difok=3 minlen=7 lcredit=-1 ucredit=-1 ocredit=-1 dcredit=-1 enforce_for_root debug

* Change the minimum password length by changing the 'minlen' parameter to 9.

* Change the minimum number of characters that must change between subseqent passwords by editing the ""difok"" parameter to 3.

* Change least one uppercase character in the password by adding 'ucredit=-1'

* Change the password on behalf a user. Sign on to "root" or "su" the "root" account. Type:

.. code :: bash

  $ sudo su

* Make sure you are "root" by typing:

.. code :: bash

  $ whoami

* Change the password on behalf a user by typing "passwd <user>"

* Enter a password with 8 characters, 1 uppercase letter and 1 non-alphanumeric character.

* Enter a password with 8 characters, none uppercase letter and 1 non-alphanumeric character.

* Enter same old password and add characters until the lenght reach 9 characters, 1 uppercase letter and 1 non-alphanumeric character.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Logged in to controller-0 successfully.

* minlen parameter = 9 changed successfully.

* difok parameter = 3 changed successfully that password must have at least three bytes that are not present in the old password.

* ucredit parameter = -1 changed successfully.

* Signed on to ""root"" or ""su"" successfully.

* By typing whoami the system should get back with ""root"" successfully.

* The system should get back with "New Password:" prompt request successfully.

* The system should get back with "BAD PASSWORD: The password is shorter than 9 characters"" message successfully.

* The system should get back with "BAD PASSWORD: The password contains less than 1 upper case letters"" message successfully.

* The system should get back with "BAD PASSWORD"

::
  e.g.
  Radawa$ka1
  RRRapava$ka1
  RRRRapava$ka1
  RRRRRapava$ka1
  RRRRRapava$ka122222
  RRRRRapava$ka1222222"""

-------------------------------
SECURITY_password_rule_setup_02
-------------------------------

:Test ID: SECURITY_password_rule_setup_02
:Test Title: wrsroot changed password and propagated.
:Tags: psswd

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify that wrsroot password can be changed it and propagate it in every
single node.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 1 Controllers + 1 compute.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* Login to controller-0 using system admin user.

... code :: bash

  Change the password on behalf wrsroot. Sign on to "root" or "su" the "root" account. Type:
    $ sudo su

* Make sure you are """"root"""" by typing:

... code :: bash

  $ whoami

* Change the password on behalf wrsroot by typing "passwd wrsroot"

* Go through every single node into your cluster and make sure the new wrsroot password is propageted.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Logged in to controller-0 successfully.

* Signed on to "root" or "su" successfully.

* By typing whoami the system should get back with ""root"" successfully.

* The system should get back with "New Password:" prompt request successfully.

* wrsroot new password is propagated."

-------------------------------
SECURITY_password_rule_setup_03
-------------------------------

:Test ID: SECURITY_password_rule_setup_03
:Test Title: password rule locked out.
:Tags: psswd

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify after setting rule where after 6 consecutive failes the user should be
locked out for 5 minutes.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) At least 1 Controllers + 1 compute.

b) Setup hydra or any other tool to perform password brute force against the
Starlingx product.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* Login to controller-0 using system admin user, source /etc/nova/openrc

* Change tu SU user

* Please modify this 2 files with the following structure

::

	Files to be modified:
		#/etc/pam.d/system-auth
		#/etc/pam.d/password-auth

	lines to add:
		Below the auth section please add following the Structure as shown in the example:

		auth        required      pam_faillock.so preauth silent audit deny=3 unlock_time=300
		auth        [default=die]  pam_faillock.so  authfail  audit  deny=3  unlock_time=300

		Example: The structure sholud be like this in both files:

		auth        required      pam_env.so
		auth        required      pam_faillock.so preauth silent audit deny=3 unlock_time=300
		auth        sufficient    pam_fprintd.so
		auth        sufficient    pam_unix.so nullok try_first_pass
		auth        [default=die]  pam_faillock.so  authfail  audit  deny=3  unlock_time=300
		auth        requisite     pam_succeed_if.so uid >= 1000 quiet
		auth        required      pam_deny.so

		Below the account section please add:

		account     required      pam_faillock.so

		Example: The structure sholud be like this in both files:

		account     required      pam_unix.so
		account     sufficient    pam_localuser.so
		account     sufficient    pam_succeed_if.so uid < 500 quiet
		account     required      pam_permit.so
		account     required      pam_faillock.so

* Open other terminal and change to SU user monitor the attemps where faillock will be called

... code :: bash

  $ faillock

**Note** that faillock should not have any user locked

* Open other terminal and try to change to SU with bad authentification password

* Monitor each attempt, you should be able to see the wrong password on the Terminal where you have faillock cmd

* Monitor that after 3 attempts the SU account is locked, after 2 min is unlocked, you can use date command to check time.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* After 3 attempts the account is locked, after 2 min the account is unlocked.

-------------------------------
SECURITY_password_rule_setup_04
-------------------------------

:Test ID: SECURITY_password_rule_setup_04
:Test Title: account stays locked after swact.
:Tags: psswd

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify account stays locked after swact.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 2 Controllers + 1 compute

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. On Controller-0 console try to login more than 5 times with same user and
wrong password.

2. Open another Controller-0 prompt console or establish a ssh connection to
the controller-0 and this time use the correct password to login.

... code :: bash

  $ ssh <user>@<IP>

3. Go to horizon and do a SWACT.

4. Right after the SWACT is completed try to login using same user and correct
password on controller-1.

5. Right after the SWACT is completed try to login using another NOT locked
user controller-1.

6. Wait for more than 5 minutes and this time try to login using same user and
correct password on controller-1.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. More than 5 login with wrong password attempted.

2. The Controller-0 should not allowed you to login since the user is locked
out.

3. SWACT is completed successfully.

4. The Controller-1 should not allowed you to login since the user is still
locked out.

5. The Controller-1 should allowed you to login with NOT locked user and you
can verify only one user account is locked.

6. After 5 minutes the Controller-1 should  allowed you to login.

-------------------------------
SECURITY_password_rule_setup_05
-------------------------------

:Test ID: SECURITY_password_rule_setup_05
:Test Title: relogin after timed out horizon session.
:Tags: psswd

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify that you can relogin to a timed out Horizon session with only one
attempt.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 1 Controllers + 1 compute.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* From horizon as admin user go to identity tab -> users.

* Wait 'n' minutes until Horizon session expires.

* Once the Horizon session expires make sure you can re-login using same user/password."

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Identity /Users Frame is displayed successfully.

* Session is expired successfully.

* User is able to re-loged in using same credentials.

-------------------------------
SECURITY_password_rule_setup_06
-------------------------------

:Test ID: SECURITY_password_rule_setup_06
:Test Title: login to active controller horizon is blocked for locked account.
:Tags: psswd

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify login to active controller horizon is blocked for locked account.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 1 Controllers + 1 compute.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

* Go to Horizon Web page, try to login more than 5 times with same user and wrong password.

* Right after is locked out try to login using same user and correct password on Horizon.

* Wait for more than 5 minutes and this time try to login using same user and correct passw

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* More than 5 login with same user and wrong password attempted and Horizon get back with ""user currently locked out"" message successfully.

* Horizon should not allowed you to login since the user is still locked out.

* After 5 minutes the Horizon should  allowed you to login to Horizon.

~~~~~~~~~~~
References:
~~~~~~~~~~~

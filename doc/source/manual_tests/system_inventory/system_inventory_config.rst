=======================
System Inventory/Config
=======================

.. contents::
   :local:
   :depth: 1

-----------------------
sysinv_conf_01
-----------------------

:Test ID: sysinv_conf_01
:Test Title: change the dns server ip addresses using gui
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Modify the DNS servers list after installation using Horizon

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

System up and running
a DNS server

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Login to platform horizon with the user 'admin'

2. Go to admin / platform / system configuration / dns / edit DNS

3. In the dialog box,  edit the IP addresses and click Save

4. Check the DNS are set and the order is preserved

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

- DNS servers listed in the same order they were entered.

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_conf_03
-----------------------

:Test ID: sysinv_conf_03
:Test Title: change the ntp server ip addresses using gui
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Modify the NTP server using Horizon

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

A system up and running
a Valid NTP server

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Login to platform horizon with the user 'admin'

2. Go to admin / platform / system configuration / NTP / edit NTP

3. In the dialog box, edit the domain names or IP addresses  and click Save.

4. Lock and unlock the standby controller.

5. Perform a swact

6. Lock and unlock the original controller.


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

3.
   - NTP servers are changed
   - alarms 250.001 (configuration is out-of-date) are created

4.
   - alarm is cleared on standby controller

6.
   - alarm is cleared on original controller

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_conf_04
-----------------------

:Test ID: sysinv_conf_04
:Test Title: change the ntp server ip addresses using cli
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Modify the NTP server using CLI

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

A system up and running
a Valid NTP server

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Authenticate with platform keystone

2. Change the NTP IP with the ntp-modify command.

.. code:: bash

  system ntp-modify ntpservers=server1[, server2, server3]

3. Check the list

.. code:: bash

  system ntp-show

4. Lock and unlock the standby controller.

5. Perform a swact

6. Lock and unlock the original controller.


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

2.
   - NTP servers are changed
   - alarms 250.001 (configuration is out-of-date) are created

4.
   - alarm is cleared on standby controller

6.
   - alarm is cleared on original controller

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_conf_05
-----------------------

:Test ID: sysinv_conf_05
:Test Title: Enable the ptp service using cli
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Enable the PTP service using CLI

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Disable NTP service

.. code:: bash

  system ntp-modify –enabled=false

2. Enable PTP service as legacy

.. code:: bash

  system ptp-modify –mode=legacy –enabled=true

3. lock and unlock all the hosts to clear out of config alarms.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

3. Hosts should be recoverded correclty

- Verify that host keep alive and there are not constant reboots


~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_conf_06
-----------------------

:Test ID: sysinv_conf_06
:Test Title: Enable the ptp service using gui
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Enable the PTP service  using Horizon

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Login to platform horizon with the user 'admin'

2. Go to admin / platform / system configuration / PTP / edit PTP

3. In the dialog box, click on the "Enabled" button and click Save.

4. Lock and unlock the standby controller.

5. Perform a swact

6. Lock and unlock the original controller.



~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

2.
   - PTP service is enabled
   - alarms 250.001 (configuration is out-of-date) are created

4.
   - alarm is cleared on standby controller

6.
   - alarm is cleared on original controller

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_conf_07
-----------------------

:Test ID: sysinv_conf_07
:Test Title: change the oam ip addresses using cli
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Modify the OAM IP address using CLI

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Authenticate with platform keystone

2. Check there are no system alarms

3. Change the IP address on controller-1

.. code:: bash

  system oam-modify key=value

4. Lock and unlock standby controller

5. Perform a swact

6. Lock and unlock the original controller.

7. Check IPs are correctly set

.. code:: bash

  system oam-show

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

3.
   - IP address is changed
   - alarms 250.001 (configuration is out-of-date) are raised

4.
   - alarm is cleared on standby controller

6.
   - alarm is cleared on original controller

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_conf_08
-----------------------

:Test ID: sysinv_conf_08
:Test Title: change the oam ip addresses using gui
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Modify the OAM IP address using Horizon

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Login to platform horizon with the user 'admin'

2. Go to admin / platform / system configuration / OAM IP / edit OAM IP

3. In the dialog box, edit the IP address of Controller-1 and click Save.

4. Lock and unlock the standby controller.

5. Perform a swact

6. Lock and unlock the original controller.


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

3.
   - controller-1 IP address is changed
   - alarms 250.001 (configuration is out-of-date) are raised

4.
   - alarm is cleared on standby controller

6.
   - alarm is cleared on original controller

~~~~~~~~~~
References
~~~~~~~~~~

N/A



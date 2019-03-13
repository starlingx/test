============================
Networking Regression Manual
============================

The intention for this set of tests is to replicate common networking
scenarios on the day on day operation. This subdomain can help system admins
in order to verify network sanity. All this tests are created in order to
check how your network is working.


.. contents::
   :local:
   :depth: 1

--------------------
NET_REG_MAN_105
--------------------

:Test ID: NET_REG_MAN_105
:Test Title: Verify that the system name can be modified via CLI and GUI
:Tags: Regression

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

The objective for this test case is to verify that we can change system
properties in different ways. In this case we are just working with the system
name.


~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) Any configuration up and running.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Obtain system name and description with the following command lines:

   ::

     $ system show
     $ system host-lock <system>

2. Change system name and description through the following command line:

   ::

     $ system modify --name <new name>  --description "Change reasons"

3. Log into Horizon and navigate to Admin System Configuration section.

4. Click on the "Edit System" button and change name and description back to
   original values.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. System name and description should be according with tested configurarion.

2. Changing the System name and description should be accepted through command
   line.

3. Returning original values for name and description should be accepted
   through Horizon interface.

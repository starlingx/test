===========================
System Inventory/Containers
===========================

.. contents::
   :local:
   :depth: 1

-----------------------
sysinv_cont_01
-----------------------

:Test ID: sysinv_cont_01
:Test Title: Bring down services (uninstall the application)
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Use sysinv to uninstall the application.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

A system up and running with a container application running

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Uninstall the application

.. code:: bash

  system application-remove stx-openstack

2. check the status

.. code:: bash

  system application-list

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

2. the application is removed


~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_cont_02
-----------------------

:Test ID: sysinv_cont_02
:Test Title: Delete services (delete application definition)
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Use sysinv to delete the application definition.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Application has been previosly removed

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Delete the aplication definition

.. code:: bash

  system application-delete stx-openstack

2. check the status

.. code:: bash

  system application-list

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

2. Once finished, the command returns no output.

~~~~~~~~~~
References
~~~~~~~~~~

N/A


-----------------------
sysinv_cont_03
-----------------------

:Test ID: sysinv_cont_03
:Test Title: update and delete a helm chart
:Tags: sysinv

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify overriding a value is accepted on a helm chart

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

N/A

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Choose a helm chart to be updated

.. code:: bash

  system helm-override-list

2. Show current values

.. code:: bash

  system helm-override-show horizon openstack

3. Change a setting

.. code:: bash

  system helm-override-update --set lockout_retries_num=5 horizon openstack

4. verify value has been updated (added as user_overrides)

.. code:: bash

  system helm-override-show horizon openstack

5. Verify the change is working

6. Delete the overrides and get the chart back to it's original values

.. code:: bash

  system helm-override-delete horizon openstack

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. The list of all the present helm charts with its corresponding namespaces

2. Property and values are shown

3. change is accepted

4. New Value is added as user_overrides

5. Setting works as expected

6. override changed is not longer appearing


~~~~~~~~~~
References
~~~~~~~~~~

N/A



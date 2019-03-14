==================
HORIZON Responsive
==================


.. contents::
   :local:
   :depth: 1

---------------------
HORIZON_responsive_01
---------------------

:Test ID: HORIZON_responsive_01
:Test Title: Platform and containerized horizon UI response.
:Tags: responsive

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify that after installation of the second controller the platform and
containerized horizon UI do not stop working.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~


~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Open your web browser and type ``http://<external OAM IP>:8080`` in order
to get the login of the platform horizon UI.

2. Open your web browser and type ``http://<external OAM IP>:31000`` in order
to get the login of the containerized horizon UI.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Successfully logged in into the platform horizon.

::

  UI - http://<external OAM IP>:8080``

2. Successfully logged in into the containerized horizon.

::

  UI - http://<external OAM IP>:31000

---------------------
HORIZON_responsive_02
---------------------

:Test ID: HORIZON_responsive_02
:Test Title: Horizon login responsive.
:Tags: responsive

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Horizon login time using All-in-one.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Starlingx cluster set up.

**REMARK:** A good suggestion is running this test case in all lab configs.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Open your web browser and type ``http://<external OAM IP>:8080`` in order
to get the login of the platform horizon UI.

2. Open your web browser and type ``http://<external OAM IP>:31000`` in order
to get the login of the containerized horizon UI.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Make sure the login of the platform horizon UI time takes less than 5
minutes.

2. Make sure the login of the containerized horizon UI time takes less than 5
minutes.

~~~~~~~~~~~
References:
~~~~~~~~~~~

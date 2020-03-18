===================================
Detection of failed virtual machine
===================================


.. contents::
   :local:
   :depth: 1

-----------------------
detection_fail_VM_01
-----------------------

:Test ID: detection_fail_VM_01
:Test Title: Detection of failed virtual machine
:Tags: performance

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

The objective of this test is to verify how much time is cosumed StarlingX to
detect when a Virtual Machine has failed.


~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

The StarlingX configuration deployed for this is the Standard Controller
(2 controllers + 2 computes) in order to review the behavior in a multinode
environment.


~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Launch a VM with the features described below, this section includes an
script which could help to do that (Another alternative is to use the
OpenStack dashboard).

::

    | Feature    | Description            |
    |------------|------------------------|
    | RAM        | 2GB                    |
    | Disk       | 20GB                   |
    | VCPUS      | 1                      |
    | Properties | hw:mem_page_size=large |
    | Image      | [Debian]               |

* Detect the compute where that VM was deployed and kill the QEMU process,
  immediately after this, the initial time must be taken.
* Make a constant of pull request of the VM status and stop the test when it
  changes.
* Finally take the end time and calculate the delta.


~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

Result being around 500ms

~~~~~~~~~~
References
~~~~~~~~~~

N/A



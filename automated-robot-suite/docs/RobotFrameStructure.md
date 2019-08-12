
# Edge Compute Framework Structure documentation

Table of Contents

- [Introduction](#introduction)
- [Edge Compute Folder Structure](#edge-compute-folder-structure)
  - [1. Libraries](#1-libraries)
  - [2. Resources](#2-resources)
  - [3. Variables](#3-variables)
  - [4. Utils](#4-utils)
  - [5. Tests](#5-test)
    - [5.1 Horizon](#51-horizon)
    - [5.2 Keystone](#52-keystone)
    - [5.3 Nova](#53-nova)
    - [5.4 Glance](#54-glance)
    - [5.5 Swift](#55-swift)
    - [5.6 Neutron](#56-cinder)
    - [5.7 Cinder](#57-neutron)
    - [5.8 Heat](#58-heat)
    - [5.9 Ceilometer](#59-ceilometer)
  - [6. Results](#6-results)
  - [7. Latest-result](#7-latest-result)


## Introduction
This structure tries to fit Robot Framework User Guide good practices.<br>
For more detailed information please check the following :link:
[Link](http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#documentation-formatting)

## Edge Compute Folder Structure

```text
stx-test-suite/
|--Libraries
|--Resources
    |--MyResources file
|--Variables
    |--global.py file
|--Utils
|--Tests
    |--Horizon component
       |--Tests.robot file

            *** Settings ***
            [Documentation]
            [Tags]
            imports...
            Resources
            Test Setup
            Test Teardown

            *** Test Cases
            ...
        |--__init__.robot file

            ***Settings***
            imports
            Suite Setup
            Suite Teardown

            ***keywords***
            ...
    |--Keystone
    |--Nova
    |--Glance
    |--Swift
    |--Neutron
    |--Cinder
    |--Heat
    |--Ceilometer
|--Results
    |--YYYYMMDDHHMMSS<test_suite_name>
|--Latest-results
```

### 1. Libraries
Any test library that is **NOT** one of the standard libraries would be here.

### 2. Resources
Resource files contain user keywords used in test case files and test suite
initialization files providing a mechanism for sharing them.<br>
Since the resource file structure is very close to test case files,
it is easy to create them.

Resource files are imported using the _Resource setting_ in the settings table.
The path to the resource file is given in the cell after the setting name.

**e.g.**<br>
TEST CASE TEMPLATE <br>
```text
*** Settings ***
Resource    my_resources.html
Resource    ../data/resources.html
Resource    ${RESOURCES}/common.tsv

*** Keywords ***
...
```

### 3. Variables
This folder should contain scripts declaring global variables, environmental
variables, or any special variable used in the Edge Computing framework.

**e.g.**<br>

  - global.py
```text
CONTROLLER_IP='10.10.10.10'
CONTROLLER_USERNAME='root'
CONTROLLER_PASSWORD='linux'
```

  - virtual_machine_variables.py
```text
-  MEMDisk1=200GB
-  MEMDisk2=100GB
```

### 4. Utils
This folder should contain generic functions that perform actions across the
Edge Computing execution.

**e.g.**

  - common_reports.py
```text
- check_results_dir(...)
- create_output_dir(...)
- link_latest_run(...)
```

### 5. Test
Contains the Robot Automated Test scenarios per Edge Computing Component.

#### 5.1 Horizon
Horizon folder should contain test cases focused on exercise the Horizon GUI
where every tenant or application user can launch up/manage their own instances.

**COMPONENT FOLDER STRUCTURE**

#### Tests.robot file
```text
*** Settings ***
[Documentation] tag specifying brief description of the Test case.
[Tags] keywords specifying what is being tested.

Imports...
# Import Order Template

# {{stdlib imports in human alphabetical order}}
# {{third-party lib imports in human alphabetical order}}
# {{project imports in human alphabetical order}}

# Import Order Example
import httplib
import logging
import random

import eventlet
import webob.exc

import nova.api.ec2
from nova.api import manager
from nova.api import openstack

Resources...
Test Setup
Test Teardown

*** Test Cases ***
...

```

#### __init__.robot file
The **__ init__ file** is a special test suite initialization file.<br>
It is a test suite **created from a directory** that can have the same
structure and syntax as test case files, except that **they cannot have test
case tables** and **not** all settings are supported.

```text
*** Settings ***
 Imports ...
 Suite Setup
 Suite Teardown

*** Keywords ***
```

#### 5.2 Keystone
Keystone folder should contain test cases focused on exercise the authorization
or authentication related to every layer of services in OpenStack.<br>

**e.g.** Tokens, Catalog, Policy, and Assignment Service role.


#### 5.3 Nova
Nova folder should contain test cases focused on exercise compute domain.

**e.g.** When you launch a instance is where all the computing and all the
processing actually happens.

#### 5.4 Glance
Glance folder should contain test cases focused on exercise services for
launching the instances. Glance has all the disk images contained in them
different versions of OS such as Linux, CentOS, Ubuntu, Windows.


#### 5.5 Swift
Swift folder should contain test cases focused on exercise databases as a
Object Storage Services where you can store all kind of files `as objects`.

**REMARK:** Everything is converted to an object and saved in the Storage File
System.


#### 5.6 Cinder
Cinder folder should contain test cases focused on exercise databases as a
`Block storage` services where the database is seen like a pluggable storage
which is very similar to the disk storage system in a computer.


#### 5.7 Neutron
Neutron folder should contain test cases focused on exercise the `networking`
service associated with all OpenStack Services.

#### 5.8 Heat
Heat folder should contain test cases focused on exercise Orchestration.

#### 5.9 Ceilometer
Ceilometer folder should contain tests cases focused on exercise metering and
billing. It checks availability of the services for how much time is an instance
active or running.

### 6. Results
Test execution results are keep in folders following the next format when the
execution was ran:
```text
%Y%m%d%H%M%S_<test_suite_name>
Where
   %Y -- Year
   %m -- Month
   %d -- Day
   %H%M%S -- Hour Minute Second
```

### 7. Latest-result
<br>...

Hope this can help you good look :+1:
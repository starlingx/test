*** Settings ***
Documentation    Add hosts and perform swacts to test host management.
...    Author(s):
...     - Hector Ivan Ramos Escobar <ramos.escobarx.hector.ivan@intel.com>
...     - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Resource          Resources/Provisioning.robot
Resource          Resources/Utils.robot
Resource          Resources/HostManagement.robot
Resource          Resources/OpenStack.robot
Suite Setup       Utils.Stx Suite Setup
Suite TearDown    Run Keywords
...    Utils.Stx Suite TearDown

*** Variables ***
${controller_0}       controller-0
${controller_1}       controller-1
${add_error_msg}      Host-add Rejected: Adding a host on a simplex system
...    is not allowed.
${swact_error_msg}    Swact action not allowed for a simplex system.
${lock_error_msg}     Rejected: Can not lock an active controller.

*** Test Cases ***
Add Controller Host Simplex
    [Tags]    Simplex
    [Documentation]    Try to add a new controller on a Simplex
    ...    configuration, expect to fail.
    &{result}    Run Command    system host-add -n ${controller_1}
    ${output}    Get From Dictionary    ${result}    stderr
    Should Contain    ${output}    ${add_error_msg}

Swact Controller Host Simplex
    [Tags]    Simplex
    [Documentation]    Try to perform a swact controller on a Simplex
    ...    configuration, expect to fail.
    &{result}    Run Command    system host-swact ${controller_0}
    ${output}    Get From Dictionary    ${result}    stderr
    Should Contain    ${output}    ${swact_error_msg}

Lock Active Controller
    [Tags]    Duplex    MN-Local    MN-External
    [Documentation]    Try to perform a lock to the Active controller
    ${system_cmd}    Catenate    SEPARATOR=|    system host-show ${controller_0}
    ...    grep capabilities    awk -F"'" '{print$8}'
    &{result}    Run Command    ${system_cmd}
    ${personality}    Get From Dictionary    ${result}    stdout
    ${active_controller}    Set Variable If
    ...    '${personality}'=='Controller-Active'    controller-0    controller-1
    &{result}    Run Command    system host-lock ${active_controller}
    ${output}    Get From Dictionary    ${result}    stderr
    Should Contain    ${output}    ${lock_error_msg}

Lock Unlock Standby Controller
    [Tags]    Duplex    MN-Local    MN-External
    [Documentation]    Perform a lock/unlock to the Standby controller
    ${system_cmd}    Catenate    SEPARATOR=|    system host-show ${controller_0}
    ...    grep capabilities    awk -F"'" '{print$8}'
    &{result}    Run Command    ${system_cmd}
    ${personality}    Get From Dictionary    ${result}    stdout
    ${standby_controller}    Set Variable If
    ...    '${personality}'=='Controller-Standby'    controller-0    controller-1
    Lock Node    ${standby_controller}
    Unlock Controller    ${standby_controller}

Lock Unlock Compute Hosts
    [Tags]    MN-Local    MN-External
    [Documentation]    Perform a lock/unlock to the compute nodes
    ${computes} =    Get Compute Nodes
    Sort List    ${computes}
    : FOR    ${compute}    IN    @{computes}
    \    Lock Node    ${compute}
    \    Unlock Compute    ${compute}

Lock Unlock Storage Hosts
    [Tags]    MN-External
    [Documentation]    Perform a lock/unlock to the storage nodes
    ${storages} =    Get Storage Nodes
    Sort List    ${storages}
    : FOR    ${storage}    IN    @{storages}
    \    Lock Node    ${storage}
    \    Unlock Storage    ${storage}

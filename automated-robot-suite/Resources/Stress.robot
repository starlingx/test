*** Settings ***
Documentation    This file contains Keywords to execute Stress test.
...    Author(s):
...     - Jose Perez Carranza <jose.perez.carranza@intel.com>
...     - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Library      Collections
Library      SSHLibrary
Library      String
Resource     Resources/Utils.robot
Variables    Variables/Global.py

*** Keywords ***
Stress Suspend Resume Instance
    [Arguments]    ${vm}
    [Documentation]    Perform a VM suspend/resume to a VM 10 times.
    : FOR    ${i}    IN RANGE    1    11
    \    Suspend Instance    ${vm}
    \    Resume Instance    ${vm}

Stress Set Error Active Instance
    [Arguments]    ${vm}
    [Documentation]    Set 'Error' and 'Active' flags to VM 10 times.
    : FOR    ${i}    IN RANGE    1    11
    \    Set Error State Instance    ${vm}    error
    \    Set Active State Instance    ${vm}    active

Stress Pause Unpause Instance
    [Arguments]    ${vm}
    [Documentation]    Perform pause/unpause to a VM 10 times.
    : FOR    ${i}    IN RANGE    1    11
    \    Pause Instance    ${vm}
    \    Unpause Instance    ${vm}

Stress Stop Start Instance
    [Arguments]    ${vm}
    [Documentation]    Perform stop/start to a VM 10 times.
    : FOR    ${i}    IN RANGE    1    11
    \    Stop Instance    ${vm}
    \    Start Instance    ${vm}

Stress Lock Unlock Instance
    [Arguments]    ${vm}
    [Documentation]    Perform lock/unlock to a VM 10 times.
    : FOR    ${i}    IN RANGE    1    11
    \    Lock Instance    ${vm}
    \    Unlock Instance    ${vm}

Stress Reboot Instance
    [Arguments]    ${vm}
    [Documentation]    Perfrom a reboot to a VM 10 times.
    : FOR    ${i}    IN RANGE    1    11
    \    Reboot Instance    ${vm}

Stress Rebuild Instance
    [Arguments]    ${vm}
    [Documentation]    Perform a rebuild to a VM 10 times.
    : FOR    ${i}    IN RANGE    1    11
    \    Rebuild Instance    ${vm}

Stress Rebuild Instance From Volume
    [Arguments]    ${vm}    ${image}
    [Documentation]    Perform a rebuild from a volume to a VM 10 times.
    : FOR    ${i}    IN RANGE    1    11
    \    Rebuild Instance From Volume    ${vm}    ${image}

Stress Resize Instance
    [Arguments]    ${vm}    ${flavor_1}    ${flavor_2}
    [Documentation]    Perform a resize to a VM 10 times.
    : FOR    ${i}    IN RANGE    1    11
    \    Resize Instance    ${vm}    ${flavor_2}
    \    Resize Instance    ${vm}    ${flavor_1}

Stress Set Property Instance
    [Arguments]    ${vm}    ${properties_1}    ${properties_2}
    [Documentation]    Set/unset properties to a VM 10 times.
    : FOR    ${i}    IN RANGE    1    11
    \    Set Instance Property    ${vm}    ${properties_1}
    \    Unset Instance Property    ${vm}    ${properties_2}

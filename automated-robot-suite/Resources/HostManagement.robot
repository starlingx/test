*** Settings ***
Documentation    Lock and Unlock compute and storage hosts. Swact a controller.
...    Author(s):
...     - Jose Perez Carranza <jose.perez.carranza@intel.com>
...     - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Library      SSHLibrary
Library      Collections
Library      OperatingSystem
Library      Libraries/common.py
Library      String
Variables    Variables/Global.py
Variables    Variables/config_init.py    Config
...    %{PYTHONPATH}/Config/config.ini

*** Keywords ***
Unlock Controller
    [Arguments]    ${controller_name}
    [Documentation]    Unlocks specified controller.
    Wait Until Keyword Succeeds    15 min     10 sec    Check Property Value
    ...    ${controller_name}    availability    online
    ${result}    Run Command    system host-unlock ${controller_name}    True
    ...    60
    Wait Until Keyword Succeeds    20 min    5 sec    Check Property Value
    ...    ${controller_name}    administrative    unlocked
    [Return]    ${result}

Unlock Compute
    [Arguments]    ${compute}
    [Documentation]  Unlock specified compute.
    Wait Until Keyword Succeeds    30 min     5 sec
    ...    Check System Application Status   platform-integ-apps    applied
    Run Command    system host-unlock ${compute}    True    60 sec
    Check Host Readiness    ${compute}

Lock Node
    [Documentation]    Locks specified node.
    [Arguments]    ${controller_name}
    Wait Until Keyword Succeeds    5 min     10 sec    Check Property Value
    ...    ${controller_name}    availability    available
    ${result}    Run Command    system host-lock ${controller_name}    True
    Wait Until Keyword Succeeds    5 min     10 sec    Check Property Value
    ...    ${controller_name}    administrative    locked
    [Return]    ${result}

Swact Controller
    [Arguments]    ${controller}
    [Documentation]    Swact the active controller and activates the SSH
    ...    connection with the new active controller
    ${result}    Run Command    system host-swact ${controller}    True
    ${new_act_cont}    Set Variable If
    ...    '${controller}'=='controller -0'    controller-1    controller-0
    Wait Until Keyword Succeeds    10 min     2 sec    Check Host Task
    ...    ${controller}    Swact: Complete
    Check Host Readiness    ${new_act_cont}    1
    # - Switch SSH connection to the Active Controller
    Switch Controller Connection    ${secondary_controller_connection}
    ...    ${master_controller_connection}

Unlock Storage
    [Arguments]    ${storage}
    [Documentation]  Unlock specified storage node.
    Run Command    system host-unlock ${storage}    True    60 sec
    Check Host Readiness    ${storage}

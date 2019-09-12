*** Settings ***
Documentation    General Utils library. This library has broad scope, it can
...    be used by any robot system tests.
...
...    This program and the accompanying materials are made available under the
...    terms of the Eclipse Public License v1.0 which accompanies this distribution,
...    and is available at http://www.eclipse.org/legal/epl-v10.html
...
...    Contributor(s):
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
Set Env Vars From Openrc
    [Documentation]    Sources the openrc form /etc/nova/ to have the admin
    ...    variables exported on the controller.
    Run Command    source /etc/platform/openrc    True

Run Command On Remote System
    [Arguments]    ${system_ip}    ${cmd}    ${user}    ${password}
    ...    ${prompt}    ${prompt_timeout}=30    ${return_stdout}=True
    ...    ${return_stderr}=False
    [Documentation]    Reduces the common work of running a command on a remote
    ...    system to a single higher level robot keyword, taking care to log in
    ...    with a public key and. The command given is written and the return
    ...    value depends on the passed argument values of return_stdout
    ...    (default: True) and return_stderr (default: False).
    ...    At least one should be True, or the keyword will exit and FAIL.
    ...    If both are True, the resulting return value will be a two element
    ...    list containing both. Otherwise the resulting return value is a
    ...    string.
    ...    No test conditions are checked.
    Run Keyword If    "${return_stdout}"!="True" and "${return_stderr}"!="True"
    ...    Fail    At least one of {return_stdout} or {return_stderr} args
    ...    should be set to True
    ${current_ssh_connection}    SSHLibrary.Get Connection
    BuiltIn.Log
    ...    Attempting to execute command "${cmd}" on remote system
    ...    "${system_ip}" by user "${user}" with prompt "${prompt}" and
    ...    password "${password}"
    ${conn_id}    SSHLibrary.Open Connection    ${system_ip}
    ...    prompt=${prompt}    timeout=${prompt_timeout}
    Flexible SSH Login    ${user}    ${password}
    ${stdout}    ${stderr}    SSHLibrary.Execute Command    ${cmd}
    ...    return_stderr=True
    SSHLibrary.Close Connection
    Log    ${stderr}
    Run Keyword If    "${return_stdout}"!="True"    Return From Keyword
    ...    ${stderr}
    Run Keyword If    "${return_stderr}"!="True"    Return From Keyword
    ...    ${stdout}
    [Return]    ${stdout}    ${stderr}

Run Command
    [Arguments]    ${cmd}    ${fail_if_error}=False    ${timeout}=${TIMEOUT+170}
    ...    ${prompt}=$
    [Documentation]    Execute a command on controller over ssh connection
    ...    keeping environment visible to the subsequent keywords.Also allows
    ...    the keyword to fail if there is an error, by default this keyword
    ...    will not fail and will return the stderr.
    Set Client Configuration    timeout=${timeout}    prompt=${prompt}
    &{result}    Create Empty Result Dictionary
    Read
    Write    ${cmd}
    ${output}    Read Until Prompt
    ${output}    Remove Prompt Line    ${output}
    ${rc}    Get Return Code
    Run Keyword If    ${rc} == 0    Set To Dictionary    ${result}    stdout=${output.strip()}
    ...    ELSE IF   ${fail_if_error} == True    FAIL    ${output}
    ...    ELSE   Set To Dictionary    ${result}    stderr=${output}
    Set To Dictionary    ${result}    rc=${rc}
    Log Dictionary    ${result}
    [Return]    ${result}

Execute Sudo Command
    [Arguments]    ${cmd}    ${timeout}=${TIMEOUT+50}
    [Documentation]    Execute a sudo on controller over ssh connection keeping
    ...    environment visible to the subsequent keywords that will ask for
    ...    password everytime it is run. It is recommended to run sudo commands
    ...    manually using -k option (sudo -k) to find if password is required.
    ...    If password is not required after verify the command manually,
    ...    please use Run Command.
    Set Client Configuration    timeout=${timeout}    prompt=:
    Read
    Write    sudo -k ${cmd}
    ${output}    Read Until Prompt
    ${output}    Run Command    ${CLI_USER_PASS}
    [Return]     ${output}

Stx Suite Setup
    [Documentation]    Wrapper to setup the environment needed for exercise
    ...    StarlingX features
    Open Master Controller Connection
    Set Env Vars From Openrc

Stx Suite TearDown
    [Documentation]    Wrapper to clean up activities on the suite.
    Close All Connections

Get Qemu VM MAC Address
    [Arguments]    ${qemu_vm_name}    ${source}
    [Documentation]    Returns the MAC address of specific source form a
    ...    qemu VM
    ${qemu_cmd}    Catenate    SEPARATOR=|
    ...    virsh -c qemu:///system domiflist ${qemu_vm_name}    grep ${source}
    ...    awk '{print $5}'
    ${mac_Adress}    Run    ${qemu_cmd}
    [Return]    ${mac_Adress}

Get Return Code
    [Documentation]    Wrapper to return the code number of last executed
    ...    command
    Write    echo $?
    ${rc}    Read Until Regexp  [0-9]+
    Log     ${rc}
    [Return]    ${rc}

Get Compute Nodes
    [Documentation]    Get the compute nodes and return them in a list.
    ${system_cmd}    Catenate    SEPARATOR=|    system host-list --nowrap
    ...    grep compute-    cut -d '|' -f 3
    &{result}    Run Command    ${system_cmd}    True
    @{list}    Convert Response To List    ${result}
    [Return]    @{list}

Get Storage Nodes
    [Documentation]    Get the storage nodes and return them in a list.
    ${system_cmd}    Catenate    SEPARATOR=|    system host-list --nowrap
    ...    grep storage-    cut -d '|' -f 3
    &{result}    Run Command    ${system_cmd}    True
    @{list}    Convert Response To List    ${result}
    [Return]    @{list}

Get Compute Interfaces Names
    [Arguments]    ${host}    ${pattern}=[A-Z]
    [Documentation]    Get all the interfaces names of the given pattern, if
    ...    no pattern is  given all the interfaces are retireved in the list.
    ${system_cmd}    Catenate    SEPARATOR=|
    ...    system host-if-list --nowrap -a ${host}    grep ${pattern}
    ...    cut -d '|' -f 3
    &{result}    Run Command     ${system_cmd}    True
    @{list}    Convert Response To List    ${result}
    [Return]    @{list}

Get Disk List UID
    [Arguments]    ${host}    ${device_node}
    [Documentation]    Returns the UID of the disk given the device node and
    ...    host
    ${system_cmd}    Catenate    SEPARATOR=|    system host-disk-list ${host}
    ...    grep ${device_node}    awk '{print $2}'
    &{result}    Run Command    ${system_cmd}    True
    ${uid}     Get From Dictionary    ${result}    stdout
    [Return]    ${uid}

Get Partition UID
    [Arguments]    ${host}    ${device_node}
    [Documentation]    Returns the UID of the partition given the device node
    ...    and host
    ${system_cmd}    Catenate    SEPARATOR=|
    ...    system host-disk-partition-list ${host}    grep ${device_node}
    ...    awk '{print $2}'
    &{result}    Run Command    ${system_cmd}    True
    ${uid}     Get From Dictionary    ${result}    stdout
    [Return]    ${uid}

Get Property Value Of Command
    [Arguments]    ${cmd}    ${property}
    [Documentation]    Given a command that returns a a table, this command
    ...    returns the specific value of the property specified.
    ${result}    Run Command    ${cmd} | grep -w ${property} | awk '{print$4}'
    ${value}     Get From Dictionary    ${result}    stdout
    [Return]    ${value.strip()}

Get LVM Storage Backend UID
    [Arguments]    ${backend}
    [Documentation]    Returns the UID of the specified Backend.
    ${result}    Run Command
    ...    system storage-backend-list | grep ${backend} | awk '{print $2}'
    ${value}     Get From Dictionary    ${result}    stdout
    [Return]    ${value.strip()}

Get Property From Result
    [Arguments]     ${result}    ${property}
    [Documentation]
    ${dict}    String To Dict    ${result}
    ${dict}    Get From Dictionary    ${dict}    Property
    ${dict}    Get From Dictionary    ${dict}    ${property}
    ${dict}    Get From Dictionary    ${dict}    Value
    [Return]    ${dict}

Get Release Version
    [Documentation]    Returns the version of the release under validation.
    ${cmd_current_version}    Catenate    cat /etc/build.info |
    ...    grep SW_VERSION | awk '{ split($1, v, "="); print v[2]}'
    &{result}     Run Command    ${cmd_current_version}    True
    ${current_version}    Get From Dictionary    ${result}    stdout
    [Return]    ${current_version.strip('"')}

Get Tier UUID
    [Arguments]    ${tier_name}
    [Documentation]    Returns the TIER uuid
    ${name}    Set Variable    storage
    ${cmd}    Catenate    system storage-tier-list    ${tier_name}
    ...    |grep ${name}    |awk '{print $2}'
    ${uuid}    Run Command    ${cmd}
    [Return]    ${uuid.stdout.strip()}

Get All Vms List
    [Documentation]    Get a list of all the VM’s created by the suite.
    ${cmd}    Catenate    virsh -c qemu:///system list --all |
    ...    awk '/-[0-9]/{print $2}'
    ${result}    Run    ${cmd}
    @{vms}     Split String    ${result}
    [Return]    @{vms}

Get Root Disk Device
    [Arguments]    ${host}
    [Documentation]    Get the root disk partition assigned to the specified
    ...    node
    ${cmd}    Catenate  SEPARATOR=|    system host-show ${host}
    ...    grep rootfs    awk '{print $4}'
    ${result}    Run Command    ${cmd}
    ${root_disk}    Set Variable    ${result.stdout.strip()}
    ${cmd}    Catenate  SEPARATOR=|
    ...    system host-disk-list ${host} --nowrap
    ...    grep ${root_disk}     awk '{print $4}'
    ${root_disk_device}    Run Command    ${cmd}
    [Return]    ${root_disk_device.stdout.strip()}

Get Interface UUID
    [Arguments]    ${host}    ${port_name}
    [Documentation]    Get Interface id of the specified host and port
    ${cmd}    Catenate    SEPARATOR=|    system host-if-list -a ${host}
    ...    grep ${port_name}    awk '{print $2}'
    ${uuid}    Run Command    ${cmd}
    [Return]    ${uuid.stdout.strip()}

Get Interface Information
    [Arguments]    ${host}    ${interface}
    [Documentation]    Returns a dictionary with the values of the spcecified
    ...    interface.
    ${cmd}    Catenate    SEPARATOR=|    system host-port-list ${host} --nowrap
    ...    grep ${interface}    awk '{ print $2,$4,$8}'
    ${info}    Run Command    ${cmd}
    ${info}    Convert Response To List    ${info}
    [Return]    ${info}

Get Ceph Monitor UID
    [Arguments]    ${host}
    [Documentation]    Get id of the CEPH  monitor of the specified node.
    ${result}    Run Command
    ...    system ceph-mon-list | grep ${host} | awk '{print $2}'
    ${value}    Get From Dictionary    ${result}    stdout
    [Return]    ${value.strip()}

Get Net Id
    [Arguments]    ${network_name}
    [Documentation]    Retrieve the net id for the given network name
    ${openstack_cmd}    Set Variable    openstack network list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}
    ...    grep "${network_name}"    awk '{print$2}'
    &{result}    Run OS Command    ${cmd}
    ${output}    Get From Dictionary    ${result}    stdout
    ${splitted_output}   Split String    ${output}    ${EMPTY}
    ${net_id}    Get from List    ${splitted_output}    0
    [Return]    ${net_id}

Get Snapshot ID
    [Arguments]    ${snapshot}
    [Documentation]    Retrieve the snapshot id for the given snapshot name
    ${openstack_cmd}    Set Variable    openstack volume snapshot list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}
    ...    grep "${snapshot}"    awk '{print$2}'
    &{result}    Run OS Command    ${cmd}
    ${output}    Get From Dictionary    ${result}    stdout
    ${splitted_output}    Split String    ${output}    ${EMPTY}
    ${snapshot_id}    Get from List    ${splitted_output}    0
    [Return]    ${snapshot_id}

Check Property Value
    [Arguments]    ${host}    ${property}    ${expected_value}
    [Documentation]    Validates that property is set correctly to the expected
    ...    value
    ${current_value}    Retrieve Host Property    ${host}    ${property}
    Should Be Equal As Strings    ${current_value}    ${expected_value}

Check Controller Is Unlocked
    [Arguments]    ${controller_name}
    [Documentation]    Validates that controller is successfully unlocked.
    Set Env Vars From Openrc
    Check Property Value    ${controller_name}    administrative    unlocked

Check Property Value Of Command
    [Arguments]    ${cmd}    ${property}    ${expected_value}
    [Documentation]    Validates that property is set correctly to the expected
    ...    value on the repsonse of command given.
    ${current_value}    Get Property Value Of Command    ${cmd}    ${property}
    Should Be Equal As Strings    ${current_value}    ${expected_value}

Check If Host Is In Degraded Mode
    [Arguments]    ${host}    ${timeout}
    [Documentation]    Verify if host fall in a degraded mode during a period
    ...    of specified time.
    Wait Until Keyword Succeeds    ${timeout} min     10 sec
    ...    Check Property Value    ${host}    availability    degraded

Check Host Task
    [Arguments]    ${host}    ${expected_result}
    [Documentation]    Get actual task status from given host
    ${output}    Run Command
    ...    system host-show ${host} | grep task | awk -F '|' '{print$3}'
    Should Contain    ${output.stdout}    ${expected_result}

Check System Application Status
    [Arguments]    ${application}    ${status}
    [Documentation]    Check if openstack applications were applied.
    ${cmd}    Catenate    SEPARATOR=|    system application-list
    ...    grep ${application}    awk '{print $10}'
    &{result}    Run Command    ${cmd}
    ${value}     Get From Dictionary    ${result}    stdout
    Run Keyword If    '${value}' == 'apply-failed'    System Application Apply    ${application}
    ...    ELSE    Should Be Equal As Strings    ${value}    ${status}

Check Field Value
    [Arguments]    ${component}    ${component_name}    ${property}
    ...    ${expected_value}
    [Documentation]    Validates that property is set correctly to the
    ...    expected value.
    ${current_value}    Retrieve Field Property    ${component}
    ...    ${component_name}    ${property}
    Should Be Equal As Strings    ${current_value}    ${expected_value}

Check Compute Service Property
    [Arguments]    ${compute}    ${expected_value}
    [Documentation]    Check status instance.
    ${current_value}    Retrieve Field Property Compute    ${compute}
    Should Be Equal As Strings    ${current_value}    ${expected_value}

Retrieve Field Property
    [Arguments]    ${component}    ${component_name}    ${property}
    [Documentation]    Returns the spceified value of the property.
    ${openstack_cmd}    Set Variable
    ...    openstack ${component} show ${component_name}
    ${cmd}=    Catenate    SEPARATOR=|    ${openstack_cmd}
    ...    grep -w ${property}    tail -1    awk '{print$4}'
    ${result}    Run OS Command    ${cmd}
    ${value}     Get From Dictionary    ${result}    stdout
    [Return]    ${value.strip()}

Retrieve Field Property Compute
    [Arguments]    ${compute}
    ${openstack_cmd}    Set Variable
    ...    openstack compute service list --service nova-compute
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}
    ...    grep ${compute}    awk '{print$10}'
    ${result}    Run OS Command    ${cmd}
    ${value}     Get From Dictionary    ${result}    stdout
    [Return]    ${value.strip()}

Retrieve Host Property
    [Arguments]        ${hostname}    ${property}
    [Documentation]    Returns the spceified value of the property on the
    ...    system host.
    ${system_cmd}    Catenate    SEPARATOR=|    system host-show ${hostname}
    ...    grep -w ${property}    awk '{print$4}'
    ${result}    Run Command    ${system_cmd}
    ${value}    Get From Dictionary    ${result}    stdout
    [Return]    ${value.strip()}

Modify Host Interface
    [Arguments]    ${net_type}    ${class}    ${host}    ${interface}
    [Documentation]    Modify interface attributes according to given options.
    ${system_cmd}    Catenate    system host-if-modify
    ...    -n oam0 -c ${class}    ${host}    ${interface}
    Run Command    ${system_cmd}    True
    Run Command
    ...    system interface-network-assign ${host} oam0 ${net_type}

Stage Application Deployment
    [Arguments]    ${application}    ${app_tarball}
    [Documentation]    Use sysinv to upload the application tarball.
    Wait Until Keyword Succeeds    30 min     5 sec
    ...    Check System Application Status   platform-integ-apps    applied
    Run Command    system application-upload ${app_tarball}    True
    Wait Until Keyword Succeeds    30 min     5 sec
    ...    Check System Application Status   ${application}    uploaded

System Application Apply
    [Arguments]    ${application}
    [Documentation]    Run the system aplication apply
    Run Command    system application-apply ${application}    True
    Wait Until Keyword Succeeds    90 min     5 min
    ...    Check System Application Status   ${application}    applied

System Application Remove
    [Arguments]    ${application}
    [Documentation]    Run the system aplication remove.
    Run Command    system application-remove ${application}    True
    Wait Until Keyword Succeeds    90 min     5 sec
    ...    Check System Application Status   ${application}    uploaded

System Application Delete
    [Arguments]    ${application}
    [Documentation]    Run the system aplication delete.
    Run Command    system application-delete ${application}    True
    ${cmd}    Catenate    SEPARATOR=|    system application-list
    ...    grep ${application}
    &{result}    Run Command    ${cmd}
    ${value}     Get From Dictionary    ${result}    stdout
    Should Be Empty    ${value}

Flexible SSH Login
    [Arguments]    ${user}    ${password}=${EMPTY}    ${delay}=0.5s
    [Documentation]    On active SSH session: if given non-empty password,
    ...    do Login, else do Login With Public Key.
    ${pwd_length}    BuiltIn.Get Length    ${password}
    # ${pwd_length} is guaranteed to be an integer, so we are safe to evaluate
    # it as Python expression.
    BuiltIn.Run Keyword And Return If    ${pwd_length} > 0    SSHLibrary.Login
    ...    ${user}    ${password}    delay=${delay}
    BuiltIn.Run Keyword And Return    SSHLibrary.Login With Public Key
    ...    ${user}    ${USER_HOME}/.ssh/${SSH_KEY}    ${KEYFILE_PASS}
    ...    delay=${delay}

Connect to Controller Node
    [Arguments]    ${user}    ${password}    ${ip_address}    ${prompt}=$
    ...    ${timeout}=10s
    [Documentation]    Stablish a SSH connection to the controller and return
    ...    the connection id
    ${controller_connection}    SSHLibrary.Open_Connection
    ...    ${ip_address}    prompt=${prompt}    timeout=${timeout}
    Flexible SSH Login    ${user}    ${password}
    [Return]    ${controller_connection}

Open Master Controller Connection
    [Documentation]    Establish a SSH connection with the master controller
    ...    to start executing the the suite.
    ${master_controller_connection}    Connect to Controller Node
    ...    ${CONFIG.credentials.STX_DEPLOY_USER_NAME}
    ...    ${CONFIG.credentials.STX_DEPLOY_USER_PSWD}
    ...    ${CONFIG.general.IP_UNIT_0_ADDRESS}
    Set Suite Variable    ${master_controller_connection}
    log    ${master_controller_connection}

Generate Secondary Controller Connection
    [Arguments]    ${controller}
    [Documentation]    Establish a SSH connection with the secondary controller
    ...    to have it alive.
    ${controller_ip}    Set Variable If    '${controller}'=='controller-0'
    ...    ${CONFIG.general.IP_UNIT_0_ADDRESS}
    ...    ${CONFIG.general.IP_UNIT_1_ADDRESS}
    ${secondary_controller_connection}    Connect to Controller Node
    ...    ${CONFIG.credentials.STX_DEPLOY_USER_NAME}
    ...    ${CONFIG.credentials.STX_DEPLOY_USER_PSWD}
    ...    ${controller_ip}
    Set Suite Variable    ${secondary_controller_connection}
    log    ${secondary_controller_connection}
    # - Set Active connection back to master controller
    Run Keyword And Return If    ${secondary_controller_connection} is not None
    ...    Switch Controller Connection    ${master_controller_connection}
    ...    ${secondary_controller_connection}

Switch Controller Connection
    [Arguments]    ${new_idx}    ${old_idx}
    [Documentation]   Enable a SSH connection to the new active controller and
    ...    source proper variables.
    Switch Connection    ${new_idx}
    Get Connection    ${new_idx}
    Run Command    whoami
    Wait Until Keyword Succeeds    5 min     5 sec     Set Env Vars From Openrc
    Set Suite Variable    ${secondary_controller_connection}
    ...   ${old_idx}
    Set Suite Variable    ${master_controller_connection}    ${new_idx}

Generate SSH Key On Current Host
    [Arguments]    ${key_path}    ${key_name}
    [Documentation]    Generates a SSH key on the current hots to be used as
    ...    the base for keypair generation.
    Run Command    ssh-keygen -f ${key_path}/${key_name} -t rsa -P ''    True

Create Empty Result Dictionary
    [Documentation]    Creates an Empty Dictionary with the required structure
    ...    for a response of executed command.
    &{result_dict}    Create Dictionary    stdout=${EMPTY}
    Set To Dictionary    ${result_dict}    stderr=${EMPTY}
    Set To Dictionary    ${result_dict}    rc=${EMPTY}
    [Return]     ${result_dict}

Remove Prompt Line
    [Arguments]    ${output}
    [Documentation]    On the response of the command execution is also
    ...    retrieved the prompt line (because the use of Read until prompt)
    ...    this keyword delete that last line and returns a clean output.
    ${line_to_remove}    Get Line    ${output}    -1
    ${clean_out}    Remove String    ${output}    ${line_to_remove}
    [Return]    ${clean_out}

Wait Until Keyword Fails
    [Arguments]    ${timeout}    ${retry}    ${error}    ${keyword}    @{args}
    [Documentation]    Waits until executed keyword returns the expected error.
    Wait Until Keyword Succeeds    ${timeout}    ${retry}
    ...    Run Keyword And Expect Error    ${error}    ${keyword}    @{args}

Convert Response To List
    [Arguments]    ${result}
    [Documentation]    Given a response dictionary, gets the stdout and split
    ...    it by spaces and return it as a list.
    ${response}     Get From Dictionary    ${result}    stdout
    @{res_in_list}    Split String    ${response}
    [Return]    @{res_in_list}

Create Directory On Current Host
    [Arguments]    ${dir_name}    ${dir_path}
    [Documentation]    Create a directory on specified location inside of host
    ...    that is currently active on ssh connection.
    Run Command    mkdir ${dir_path}/${dir_name}
    [Return]    ${dir_path}/${dir_name}

Start Nodes Virtual
    [Documentation]    Start VM’s that will serve as the Nodes of the system.
    @{vms_list}   Get All Vms List
    : FOR    ${vm}    IN    @{vms_list}
    \    Run    virsh -c qemu:///system start ${vm}
    \    Run    virt-manager -c qemu:///system --show-domain-console ${vm}

*** Settings ***
Documentation    Establish a SSH connection with the master controller to
...    execute openstack commands to create networks, subnetworks, flavors,
...    images, volumes, snapshots, instances, etc.
...    Author(s):
...     - Jose Perez Carranza <jose.perez.carranza@intel.com>
...     - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Library      Collections
Library      SSHLibrary
Library      String
Resource     Resources/Utils.robot
Variables    Variables/Global.py

*** Keywords ***
Run OS Command
    [Arguments]    ${cmd}    ${fail_if_error}=False    ${timeout}=${TIMEOUT+20}
    [Documentation]    Keyword to execute exclusively commands for OpenStack as
    ...    it uses the proper token for OS authentication.
    ${load_os_token}    Set Variable    export OS_CLOUD=openstack_helm
    ${stdout}    ${stderr}    ${rc}    Execute Command
    ...    ${load_os_token} && ${cmd}    return_stdout=True
    ...    return_stderr=True    return_rc=True    timeout=${timeout}
    ${res}    Create dictionary    stdout=${stdout}    stderr=${stderr}
    ...    rc=${rc}
    Run Keyword If    ${rc} != 0 and ${fail_if_error} == True    FAIL
    ...    ${stderr}
    [Return]    ${res}

Create Network
    [Arguments]    ${network_name}    ${additional_args}=${EMPTY}
    ...    ${verbose}=TRUE
    [Documentation]    Create Network with openstack request.
    ${openstack_cmd}    Set Variable    openstack network create
    ${cmd}    Catenate     ${openstack_cmd}    ${network_name}
    ...    ${additional_args}
    Run OS Command    ${cmd}    True    30 sec

Create Subnet
    [Arguments]    ${network_name}    ${range_ip}
    ...    ${additional_args}=${EMPTY}
    [Documentation]    Create SubNet for the Network with neutron request.
    ${openstack_cmd}    Set Variable    openstack subnet create
    ${cmd}    Catenate    ${openstack_cmd}    --network ${network_name}
    ...    --subnet-range ${range_ip} ${additional_args}
    Run OS Command    ${cmd}    True    30 sec

Create Flavor
    [Arguments]    ${ram}    ${vcpus}    ${disk}    ${name}
    ...    ${extra_args}=${EMPTY}
    [Documentation]    Create a flavor with specified values.
    ${openstack_cmd}    Set Variable    openstack flavor create
    ${cmd}    Catenate     ${openstack_cmd}    --ram ${ram}    --disk ${disk}
    ...    --vcpus ${vcpus}    --public    --id auto     ${extra_args}
    ...    ${name}
    Run OS Command    ${cmd}    True    3 min

Create Image
    [Arguments]    ${file_path}  ${disk_format}  ${name}
    [Documentation]    Create image from a given .img file.
    SSHLibrary.File Should Exist    ${file_path}
    ${openstack_cmd}    Set Variable    openstack image create
    ${cmd}    Catenate    ${openstack_cmd}    --file ${file_path}
    ...    --disk-format ${disk_format}    --public    ${name}
    Run OS Command    ${cmd}    True    3 min
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    image    ${name}    status    active

Create Volume
    [Arguments]    ${size}    ${image}    ${bootable}    ${name}
    [Documentation]    Create Volume.
    ${openstack_cmd}    Set Variable    openstack volume create
    ${cmd}    Catenate    ${openstack_cmd}    --size ${size}
    ...    --image ${image}    ${bootable}    ${name}
    Run OS Command    ${cmd}    True    30 sec
    Wait Until Keyword Succeeds    10 min    10 sec    Check Field Value
    ...     volume    ${name}    status    available

Create Snapshot
    [Arguments]    ${volume}    ${name}
    [Documentation]    Create Snapshot.
    Run OS Command
    ...    openstack volume snapshot create --volume ${volume} ${name}
    ...    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    volume snapshot    ${name}    status    available

Create Stack
    [Arguments]    ${stack_name}    ${stack_template}    ${net_id}
    [Documentation]    Create Stack
    ${openstack_cmd}    Set Variable    openstack stack create --template
    ${cmd}    Catenate    ${openstack_cmd}    ${stack_template}
    ...    ${stack_name}    --parameter "NetID=${net_id}"
    ${output}    Run OS Command   ${cmd}
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    stack    ${stack_name}    stack_status    CREATE_COMPLETE
    ${openstack_cmd}    Set Variable    openstack server list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True    30 sec
    @{vm_list}    Convert Response To List    ${result}
    : FOR    ${vm}    IN    @{vm_list}
    \    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm}    status    ACTIVE
    \    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm}    power_state    Running

Create Instance
    [Arguments]    ${net_name}    ${vm_name}    ${image}    ${flavor}
    [Documentation]    Create a VM Instances with the net id of the Netowrk
    ...    flavor and image
    ${net_id}    Get Net Id    ${net_name}
    ${openstack_cmd}    Set Variable    openstack server create
    ${cmd}    Catenate    ${openstack_cmd}    --image ${image}
    ...    --flavor ${flavor}    --nic net-id=${net_id}    ${vm_name}
    Run OS Command    ${cmd}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    power_state    Running

Create Instance From Volume
    [Arguments]    ${net_name}    ${vm_name}    ${volume}    ${flavor}
    [Documentation]    Create a VM Instances with the net id of the Netowrk
    ...    flavor and volume
    ${net_id}    Get Net Id    ${net_name}
    ${openstack_cmd}    Set Variable    openstack server create
    ${cmd}    Catenate    ${openstack_cmd}    --volume ${volume}
    ...    --flavor ${flavor}    --nic net-id=${net_id}    ${vm_name}
    Run OS Command    ${cmd}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    power_state    Running

Create Instance From Snapshot
    [Arguments]    ${net_name}    ${image}    ${vm_name}    ${snapshot}
    ...    ${size}    ${flavor}
    [Documentation]    Create a VM Instances with the net id of the Netowrk
    ...    flavor and snapshot
    ${net_id}    Get Net Id    ${net_name}
    ${snapshot_id}    Get Snapshot ID    ${snapshot}
    ${openstack_cmd}    Set Variable    openstack server create
    ${mapping}    Catenate    SEPARATOR=:    ${snapshot_id}    snapshot
    ...    ${size}
    ${cmd}    Catenate    ${openstack_cmd}    --flavor ${flavor}
    ...    --image ${image}    --nic net-id=${net_id}
    ...    --block-device-mapping    vdb=${mapping}    ${vm_name}
    Run OS Command    ${cmd}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    power_state    Running

Create Instance With Keypair
    [Arguments]    ${net_name}    ${vm_name}    ${image}    ${flavor}
    ...    ${key_name}
    [Documentation]    Create a VM Instances with the net id of the
    ...    Netowrk flavor and image and a keypair
    ${net_id}    Get Net Id    ${net_name}
    ${openstack_cmd}    Set Variable    openstack server create
    ${cmd}    Catenate    ${openstack_cmd}    --image ${image}
    ...    --flavor ${flavor}    --nic net-id=${net_id}
    ...    --key-name ${key_name}    ${vm_name}
    Run OS Command    ${cmd}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    power_state    Running

Create KeyPair
    [Arguments]    ${key_name}
    [Documentation]    Create new public or private key for server ssh access.
    ${key_dir}    Create Directory On Current Host    .ssh
    ...    /home/${CLI_USER_NAME}
    ${result}    Run Keyword And Ignore Error
    ...    SSHLibrary.File Should Exist    ${key_dir}/${key_name}
    ${key_exist}    Get From List    ${result}    0
    Run Keyword If    '${key_exist}' == 'FAIL'
    ...    Generate SSH Key On Current Host    /home/${CLI_USER_NAME}/.ssh
    ...    ${key_name}
    ${openstack_cmd}    Set Variable    openstack keypair create
    ${cmd}    Catenate    ${openstack_cmd}
    ...    --public-key ${key_dir}/${key_name}.pub    ${key_name}
    Run OS Command    ${cmd}    True    30 sec

Suspend Instance
    [Arguments]    ${vm_name}
    [Documentation]    Suspend the corresponding VM
    Run OS Command    openstack server suspend ${vm_name}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    SUSPENDED

Resume Instance
    [Arguments]    ${vm_name}
    [Documentation]    Resume the corresponding VM
    Run OS Command    openstack server resume ${vm_name}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE

Set Error State Instance
    [Arguments]    ${vm_name}    ${value}
    [Documentation]    Set 'Error' value to the corresponding VM
    Run OS Command    openstack server set --state ${value} ${vm_name}
    ...    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ERROR

Set Active State Instance
    [Arguments]    ${vm_name}    ${value}
    [Documentation]    Set 'Active' value to the corresponding VM
    Run OS Command    openstack server set --state ${value} ${vm_name}
    ...    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE

Pause Instance
    [Arguments]    ${vm_name}
    [Documentation]    Pause an instance.
    Run OS Command    openstack server pause ${vm_name}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    PAUSED

Unpause Instance
    [Arguments]    ${vm_name}
    [Documentation]    Unpause an instance.
    Run OS Command    openstack server unpause ${vm_name}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE

Stop Instance
    [Arguments]    ${vm_name}
    [Documentation]    Stop an instance.
    Run OS Command    openstack server stop ${vm_name}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    SHUTOFF

Start Instance
    [Arguments]    ${vm_name}
    [Documentation]    Start an instance.
    Run OS Command    openstack server start ${vm_name}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE

Lock Instance
    [Arguments]    ${vm_name}
    [Documentation]    Lock an instance.
    Run OS Command    openstack server lock ${vm_name}    True    30 sec

Unlock Instance
    [Arguments]    ${vm_name}
    [Documentation]    Unlock an instance.
    Run OS Command    openstack server unlock ${vm_name}    True    30 sec

Reboot Instance
    [Arguments]    ${vm_name}
    [Documentation]    Reboot an instance.
    Run OS Command    openstack server reboot ${vm_name}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    REBOOT
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE

Rebuild Instance
    [Arguments]    ${vm_name}
    [Documentation]    Rebuild an instance.
    Run OS Command    openstack server rebuild ${vm_name}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    REBUILD
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE

Rebuild Instance From Volume
    [Arguments]    ${vm_name}    ${image}
    [Documentation]    Rebuild an instance from volume
    Run OS Command    openstack server rebuild --image ${image} ${vm_name}
    ...    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    REBUILD
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE

Resize Instance
    [Arguments]    ${vm_name}    ${flavor}
    [Documentation]    Resize an instance.
    Run OS Command    openstack server resize --flavor ${flavor} ${vm_name}
    ...    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    RESIZE
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    VERIFY_RESIZE
    Run OS Command    openstack server resize --confirm ${vm_name}
    ...    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec    Check Field Value
    ...    server    ${vm_name}    status    ACTIVE

Set Instance Property
    [Arguments]    ${vm_name}    ${key}
    [Documentation]    Set properties of an instance.
    Run OS Command    openstack server set ${key} ${vm_name}    True
    ...    30 sec

Unset Instance Property
    [Arguments]    ${vm_name}    ${key}
    [Documentation]    Unset properties of an instance.
    Run OS Command    openstack server unset ${key} ${vm_name}    True
    ...    30 sec

Evacuate Instances
    [Arguments]    ${host}
    [Documentation]    Evacuate all VMs from computes or from controllers.
    ${openstack_cmd}    Set Variable    openstack compute service set
    ${cmd}    Catenate    ${openstack_cmd}    --disable
    ...    --disable-reason test-evacuate    ${host}    nova-compute
    Run OS Command    ${cmd}    True    30 sec
    Wait Until Keyword Succeeds    5 min    10 sec
    ...    Check Compute Service Property    ${host}    disabled
    Wait Until Keyword Succeeds    5 min    10 sec
    ...    Check Compute Service Property    ${host}    enabled

Delete Stack
    [Arguments]    ${stack}
    [Documentation]    Delete an specific stack.
    ${openstack_cmd}    Set Variable    openstack stack delete
    ${cmd}    Catenate    ${openstack_cmd}    ${stack}    -y
    Run OS Command    ${cmd}    True    30 sec

Delete Snapshot
    [Arguments]    ${snapshot}
    [Documentation]    Delete an specific snapshot.
    ${openstack_cmd}    Set Variable    openstack volume snapshot delete
    ${cmd}    Catenate    ${openstack_cmd}    ${snapshot}
    Run OS Command    ${cmd}    True    30 sec

Delete Volume
    [Arguments]    ${volume}
    [Documentation]    Delete an specific volume.
    ${openstack_cmd}    Set Variable    openstack volume delete
    ${cmd}    Catenate    ${openstack_cmd}    ${volume}
    Run OS Command    ${cmd}    True    30 sec

Delete Flavor
    [Arguments]    ${flavor}
    [Documentation]    Delete an specific flavor.
    ${openstack_cmd}    Set Variable    openstack flavor delete
    ${cmd}    Catenate    ${openstack_cmd}    ${flavor}
    Run OS Command    ${cmd}    True    30 sec

Delete Image
    [Arguments]    ${image}
    [Documentation]    Delete an specific image.
    ${openstack_cmd}    Set Variable    openstack image delete
    ${cmd}    Catenate    ${openstack_cmd}    ${image}
    Run OS Command    ${cmd}    True    30 sec

Delete Instance
    [Arguments]    ${vm}
    [Documentation]    Delete an specific instance.
    ${openstack_cmd}    Set Variable    openstack server delete
    ${cmd}    Catenate    ${openstack_cmd}    ${vm}
    Run OS Command    ${cmd}    True    30 sec

Delete Network
    [Arguments]    ${network}
    [Documentation]    Delete an specific network.
    ${openstack_cmd}    Set Variable    openstack network delete
    ${cmd}    Catenate    ${openstack_cmd}    ${network}
    Run OS Command    ${cmd}    True    30 sec

Delete KeyPair
    [Arguments]    ${keypair}
    [Documentation]    Delete an specific keypair.
    ${openstack_cmd}    Set Variable    openstack keypair delete
    ${cmd}    Catenate    ${openstack_cmd}    ${keypair}
    Run OS Command    ${cmd}    True    30 sec

Delete All Stacks
    [Documentation]    Get a list of all existing stacks to delete them one
    ...    by one.
    ${openstack_cmd}    Set Variable    openstack stack list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Stack"
    &{result}    Run OS Command    ${cmd}    True    30 sec
    @{stack_list}    Convert Response To List    ${result}
    : FOR    ${stack}    IN    @{stack_list}
    \    Delete Stack    ${stack}

Delete All Snapshots
    [Documentation]    Get a list of all existing snapshots to delete them one
    ...    by one.
    ${openstack_cmd}    Set Variable    openstack volume snapshot list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True    30 sec
    @{snapshot_list}    Convert Response To List    ${result}
    : FOR    ${snapshot}    IN    @{snapshot_list}
    \    Delete Snapshot    ${snapshot}

Delete All Volumes
    [Documentation]    Get a list of all existing volumes to delete them one
    ...    by one.
    ${openstack_cmd}    Set Variable    openstack volume list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$2}'
    ...    grep -v "ID"
    &{result}    Run OS Command    ${cmd}    True    30 sec
    @{volume_list}    Convert Response To List    ${result}
    : FOR    ${volume}    IN    @{volume_list}
    \    Delete Volume    ${volume}

Delete All Flavors
    [Documentation]    Get a list of all existing flavors to delete them one
    ...    by one.
    ${openstack_cmd}    Set Variable    openstack flavor list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"    grep -v "m1"
    &{result}    Run OS Command    ${cmd}    True
    @{flavor_list}    Convert Response To List    ${result}
    : FOR    ${flavor}    IN    @{flavor_list}
    \    Delete Flavor    ${flavor}

Delete All Images
    [Documentation]    Get a list of all existing images to delete them one
    ...    by one.
    ${openstack_cmd}    Set Variable    openstack image list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"    grep -v "Cirros"
    &{result}    Run OS Command    ${cmd}    True
    @{image_list}    Convert Response To List    ${result}
    : FOR    ${image}    IN    @{image_list}
    \    Delete Image    ${image}

Delete All Instances
    [Documentation]    Get a list of all existing instances to delete them one
    ...    by one.
    ${openstack_cmd}    Set Variable    openstack server list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{vm_list}    Convert Response To List    ${result}
    : FOR    ${vm}    IN    @{vm_list}
    \    Delete Instance    ${vm}

Delete All Networks
    [Documentation]    Get a list of all existing networks to delete them one
    ...    by one.
    ${openstack_cmd}    Set Variable    openstack network list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"    grep -v "private"    grep -v "public"
    ...    grep -v "external"    grep -v "internal"
    &{result}    Run OS Command    ${cmd}    True
    @{network_list}    Convert Response To List    ${result}
    : FOR    ${network}    IN    @{network_list}
    \    Delete Network    ${network}

Delete All KeyPairs
    [Documentation]    Get a list of all existing keypais to delete them one
    ...    by one.
    ${openstack_cmd}    Set Variable    openstack keypair list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$2}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{key_list}    Convert Response To List    ${result}
    : FOR    ${key}    IN    @{key_list}
    \    Delete KeyPair    ${key}

Openstack Cleanup All
    [Documentation]    Delete all instances, images, flavors, networks and
    ...    keypairs generated during tests.
    Delete All Instances
    Delete All Images
    Delete All Flavors
    Delete All Networks
    Delete All KeyPairs
    Run Keyword And Ignore Error    Delete All Volumes
    Delete All Snapshots
    Delete All Volumes
    Delete All Stacks

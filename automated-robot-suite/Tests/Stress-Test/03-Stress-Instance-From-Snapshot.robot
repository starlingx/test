*** Settings ***
Documentation    Tests to create and stress instances from an snapshot, perform
...    different power status and set properties, using Cirros OS.
...    Author(s):
...     - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Library           SSHLibrary
Resource          Resources/Utils.robot
Resource          Resources/OpenStack.robot
Resource          Resources/Stress.robot
Suite Setup       Utils.Stx Suite Setup
Suite TearDown    Run Keywords
...    OpenStack.Openstack Cleanup All
...    Utils.Stx Suite TearDown

*** Variables ***
${cirros_image}            ${CIRROS_FILE}
${cirros_image_name}       cirros
${cirros_flavor_name}      f1.small
${cirros_flavor_name_2}    f2.small
${cirros_flavor_ram}       2048
${cirros_flavor_disk}      20
${cirros_flavor_vcpus}     1
${cirros_instance_name}    vm-cirros
${cirros_volume_size}      20
${cirros_volume_name}      vol-cirros
${cirros_snapshot_name}    snap-cirros
${cirros_snapshot_size}      20
${network_name}            network-1
${subnet_name}             subnet-1
${disk_format}             qcow2
${subnet_range}            192.168.0.0/24
${subnet_extras}           --ip-version 4 --dhcp ${subnet_name}
${flavor_property_1}       --property sw:wrs:guest:heartbeat='false'
${flavor_property_2}       --property hw:cpu_policy='shared'
${instance_property_1}     --property sw:wrs:auto_recovery
${instance_property_2}     --property hw:wrs:live_migration_max_downtime
${instance_property_3}     --property hw:wrs:live_migration_timeout
${host_image_path}         /home/${CLI_USER_NAME}/

*** Test Cases ***
Create Flavor for Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create flavor with or without properties to be used
    ...    to launch Cirros instances.
    ${properties}    Catenate    ${flavor_property_1}    ${flavor_property_2}
    Create Flavor    ${cirros_flavor_ram}    ${cirros_flavor_vcpus}
    ...    ${cirros_flavor_disk}    ${cirros_flavor_name}

Create Image for Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create image with or without properties to be used
    ...    to launch Cirros instances.
    Put File    %{PYTHONPATH}/${cirros_image}
    ...    ${host_image_path}/${cirros_image}
    Create Image    ${host_image_path}/${cirros_image}    ${disk_format}
    ...    ${cirros_image_name}

Create Network for Instance
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create network to be used to launch Cirros instances.
    Create Network    ${network_name}
    Create Subnet    ${network_name}    ${subnet_range}    ${subnet_extras}

Create Volume for Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create volume with or without properties to be used
    ...    to launch Cirros instances.
    Create Volume    ${cirros_volume_size}    ${cirros_image_name}
    ...    --bootable    ${cirros_volume_name}

Create Snapshots for Instance
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create snapshots with or without properties to be used
    ...    to launch Cirros instances.
    :FOR    ${i}    IN RANGE    1    10
    \    Create Snapshot    ${cirros_volume_name}
    ...    ${cirros_snapshot_name}-${i}

Launch Instances From Snapshots
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Launch 9 Cirros instances from snapshots.
    ${i}    Set Variable    1
    ${openstack_cmd}    Set Variable    openstack volume snapshot list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{snap_list}    Convert Response To List    ${result}
    : FOR    ${snap}    IN    @{snap_list}
    \    Create Instance From Snapshot    ${network_name}
    ...    ${cirros_image_name}    ${cirros_instance_name}-${i}    ${snap}
    ...    ${cirros_snapshot_size}    ${cirros_flavor_name}
    \    ${i}    Evaluate    ${i} + 1

Suspend Resume Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Suspend and Resume all Cirros instances 10 times.
    ${openstack_cmd}    Set Variable    openstack server list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{vm_list}    Convert Response To List    ${result}
    : FOR    ${vm}    IN    @{vm_list}
    \    Stress Suspend Resume Instance    ${vm}

Set Error Active Flags Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Set 'Error' and 'Active' flags all Cirros instances
    ...    10 times.
    ${openstack_cmd}    Set Variable    openstack server list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{vm_list}    Convert Response To List    ${result}
    : FOR    ${vm}    IN    @{vm_list}
    \    Stress Set Error Active Instance    ${vm}

Pause Unpause Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Pause and Unpause all Cirros instances 10 times.
    ${openstack_cmd}    Set Variable    openstack server list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{vm_list}    Convert Response To List    ${result}
    : FOR    ${vm}    IN    @{vm_list}
    \    Stress Suspend Resume Instance    ${vm}

Stop Start Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Stop and Start all Cirros instances 10 times.
    ${openstack_cmd}    Set Variable    openstack server list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{vm_list}    Convert Response To List    ${result}
    : FOR    ${vm}    IN    @{vm_list}
    \    Stress Stop Start Instance    ${vm}

Lock Unlock Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Lock and Unlock all Cirros instances 10 times.
    ${openstack_cmd}    Set Variable    openstack server list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{vm_list}    Convert Response To List    ${result}
    : FOR    ${vm}    IN    @{vm_list}
    \    Stress Lock Unlock Instance    ${vm}

Reboot Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Reboot all Cirros instances 10 times.
    ${openstack_cmd}    Set Variable    openstack server list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{vm_list}    Convert Response To List    ${result}
    : FOR    ${vm}    IN    @{vm_list}
    \    Stress Reboot Instance    ${vm}

Rebuild Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Rebuild all Cirros instances 10 times.
    ${openstack_cmd}    Set Variable    openstack server list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{vm_list}    Convert Response To List    ${result}
    : FOR    ${vm}    IN    @{vm_list}
    \    Stress Rebuild Instance From Volume    ${vm}    ${cirros_image_name}

Resize Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Resize all Cirros instances 10 times.
    Create Flavor    ${cirros_flavor_ram}    ${cirros_flavor_vcpus}
    ...    ${cirros_flavor_disk}    ${cirros_flavor_name_2}
    ${openstack_cmd}    Set Variable    openstack server list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{vm_list}    Convert Response To List    ${result}
    : FOR    ${vm}    IN    @{vm_list}
    \    Stress Resize Instance    ${vm}    ${cirros_flavor_name}
    ...    ${cirros_flavor_name_2}

Set Unset Properties Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Set Unset properties of all Cirros instances 10 times.
    ${properties}    Catenate    ${instance_property_1}='true'
    ...    ${instance_property_2}='500'    ${instance_property_3}='180'
    ${properties_2}    Catenate    ${instance_property_1}
    ...    ${instance_property_2}    ${instance_property_3}
    ${openstack_cmd}=    Set Variable    openstack server list
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    awk '{print$4}'
    ...    grep -v "Name"
    &{result}    Run OS Command    ${cmd}    True
    @{vm_list}    Convert Response To List    ${result}
    : FOR    ${vm}    IN    @{vm_list}
    \    Stress Set Property Instance    ${vm}    ${properties}
    ...    ${properties_2}

Evacuate Instances From Hosts
    [Tags]    Duplex    MN-Local    MN-External
    [Documentation]    Evacuate all Cirros instances from computes or
    ...    controllers 10 times.
    Run Keyword If    '${CONFIGURATION_TYPE}' == 'Duplex'
    ...    Run Keywords    Evacuate Instances    controller-0    AND
    ...    Evacuate Instances     controller-1
    ...    ELSE IF    '${CONFIGURATION_TYPE}' == 'MN-Local' or '${CONFIGURATION_TYPE}' == 'MN-External'
    ...    Run Keywords    Evacuate Instances    compute-0    AND
    ...    Evacuate Instances    compute-1

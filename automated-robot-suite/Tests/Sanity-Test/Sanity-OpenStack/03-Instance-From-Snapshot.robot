*** Settings ***
Documentation    Create instances from snapshot, perform different
...    power status and set properties, using Cirros OS.
...    Author(s):
...     - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Library           SSHLibrary
Resource          Resources/Utils.robot
Resource          Resources/OpenStack.robot
Suite Setup       Utils.Stx Suite Setup
Suite TearDown    Run Keywords
...    OpenStack.Openstack Cleanup All
...    Utils.Stx Suite TearDown

*** Variables ***
${cirros_image}              ${CIRROS_FILE}
${cirros_image_name}         cirros
${cirros_flavor_name_1}      f1.small
${cirros_flavor_name_2}      f2.small
${cirros_flavor_ram}         2048
${cirros_flavor_disk}        20
${cirros_flavor_vcpus}       1
${cirros_instance_name_1}    vm-cirros-1
${cirros_instance_name_2}    vm-cirros-2
${cirros_volume_size}        20
${cirros_volume_name}        vol-cirros-1
${cirros_snapshot_name_1}    snap-cirros-1
${cirros_snapshot_name_2}    snap-cirros-2
${cirros_snapshot_size}      20
${network_name}              network-1
${subnet_name}               subnet-1
${disk_format}               qcow2
${subnet_range}              192.168.0.0/24
${subnet_extras}             --ip-version 4 --dhcp ${subnet_name}
${flavor_property_1}         --property sw:wrs:guest:heartbeat='false'
${flavor_property_2}         --property hw:cpu_policy='shared'
${instance_property_1}       --property sw:wrs:auto_recovery
${instance_property_2}       --property hw:wrs:live_migration_max_downtime
${instance_property_3}       --property hw:wrs:live_migration_timeout
${host_image_path}           /home/${CLI_USER_NAME}/

*** Test Cases ***
Create Flavors For Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create flavors with or without properties to be used
    ...    to launch Cirros instances.
    ${properties}    Catenate    ${flavor_property_1}    ${flavor_property_2}
    Create Flavor    ${cirros_flavor_ram}    ${cirros_flavor_vcpus}
    ...    ${cirros_flavor_disk}    ${cirros_flavor_name_1}

Create Images For Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create images with or without properties to be used
    ...    to launch Cirros instances.
    Put File    %{PYTHONPATH}/${cirros_image}
    ...    ${host_image_path}/${cirros_image}
    Create Image    ${host_image_path}/${cirros_image}    ${disk_format}
    ...    ${cirros_image_name}

Create Networks For Instance
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create networks to be used to launch Cirros and Centos
    ...    instances.
    Create Network    ${network_name}
    Create Subnet    ${network_name}    ${subnet_range}    ${subnet_extras}

Create Volume For Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create volumes with or without properties to be used
    ...    to launch Cirros instances.
    Create Volume    ${cirros_volume_size}    ${cirros_image_name}
    ...    --bootable    ${cirros_volume_name}

Create Snapshot For Instance
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create snapshots with or without properties to be used
    ...    to launch Cirros instances.
    Create Snapshot    ${cirros_volume_name}    ${cirros_snapshot_name_1}
    Create Snapshot    ${cirros_volume_name}    ${cirros_snapshot_name_2}

Launch Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Launch Cirros instances from snapshot.
    Create Instance From Snapshot    ${network_name}    ${cirros_image_name}
    ...    ${cirros_instance_name_1}    ${cirros_snapshot_name_1}
    ...    ${cirros_snapshot_size}    ${cirros_flavor_name_1}
    Create Instance From Snapshot    ${network_name}    ${cirros_image_name}
    ...    ${cirros_instance_name_2}    ${cirros_snapshot_name_2}
    ...    ${cirros_snapshot_size}    ${cirros_flavor_name_1}

Suspend Resume Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Suspend and Resume Cirros instances.
    Suspend Instance    ${cirros_instance_name_1}
    Resume Instance    ${cirros_instance_name_1}
    Suspend Instance    ${cirros_instance_name_2}
    Resume Instance    ${cirros_instance_name_2}

Set Error Active Flags Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Set 'Error' and 'Active' flags to Cirros instances.
    Set Error State Instance    ${cirros_instance_name_1}    error
    Set Active State Instance    ${cirros_instance_name_1}    active
    Set Error State Instance    ${cirros_instance_name_2}    error
    Set Active State Instance    ${cirros_instance_name_2}    active

Pause Unpause Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Pause and Unpause Cirros instances.
    Pause Instance    ${cirros_instance_name_1}
    Pause Instance    ${cirros_instance_name_2}
    Unpause Instance    ${cirros_instance_name_1}
    Unpause Instance    ${cirros_instance_name_2}

Stop Start Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Stop and Start Cirros instances.
    Stop Instance    ${cirros_instance_name_1}
    Stop Instance    ${cirros_instance_name_2}
    Start Instance    ${cirros_instance_name_1}
    Start Instance    ${cirros_instance_name_2}

Lock Unlock Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Lock and Unlock Cirros instances.
    Lock Instance    ${cirros_instance_name_1}
    Lock Instance    ${cirros_instance_name_2}
    Unlock Instance    ${cirros_instance_name_1}
    Unlock Instance    ${cirros_instance_name_2}

Reboot Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Reboot Cirros instances.
    Reboot Instance    ${cirros_instance_name_1}
    Reboot Instance    ${cirros_instance_name_2}

Rebuild Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Rebuild Cirros instances.
    Rebuild Instance From Volume    ${cirros_instance_name_1}
    ...    ${cirros_image_name}
    Rebuild Instance From Volume    ${cirros_instance_name_2}
    ...    ${cirros_image_name}

Resize Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Resize Cirros instances.
    Create Flavor    ${cirros_flavor_ram}    ${cirros_flavor_vcpus}
    ...    ${cirros_flavor_disk}    ${cirros_flavor_name_2}
    Resize Instance    ${cirros_instance_name_1}    ${cirros_flavor_name_2}
    Resize Instance    ${cirros_instance_name_1}    ${cirros_flavor_name_1}

Set Unset Properties Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Set Unset properties of Cirros instances.
    ${properties}    Catenate    ${instance_property_1}='true'
    ...    ${instance_property_2}='500'    ${instance_property_3}='180'
    Set Instance Property    ${cirros_instance_name_1}    ${properties}
    Set Instance Property    ${cirros_instance_name_2}    ${properties}
    ${properties}    Catenate    ${instance_property_1}
    ...    ${instance_property_2}    ${instance_property_3}
    Unset Instance Property    ${cirros_instance_name_1}    ${properties}
    Unset Instance Property    ${cirros_instance_name_2}    ${properties}

Evacuate Instances From Hosts
    [Tags]    Duplex    MN-Local    MN-External
    [Documentation]    Evacuate all instances from computes or
    ...    controllers.
    Run Keyword If    '${CONFIGURATION_TYPE}' == 'Duplex'
    ...    Run Keywords    Evacuate Instances    controller-0    AND
    ...    Evacuate Instances     controller-1
    ...    ELSE IF    '${CONFIGURATION_TYPE}' == 'MN-Local' or '${CONFIGURATION_TYPE}' == 'MN-External'
    ...    Run Keywords    Evacuate Instances    compute-0    AND
    ...    Evacuate Instances    compute-1

*** Settings ***
Documentation    Create instances from image, perform different
...    power status and set properties, using Cirros OS and Centos OS.
...    Author(s):
...     - Juan Carlos Alonso juan.carlos.alonso@intel.com

Resource          Resources/Utils.robot
Resource          Resources/OpenStack.robot
Suite Setup       Utils.Stx Suite Setup
Suite TearDown    Run Keywords
...    OpenStack.Openstack Cleanup All
...    Utils.Stx Suite TearDown

*** Variables ***
${cirros_image}            ${CIRROS_FILE}
${cirros_image_name}       cirros
${cirros_flavor_name_1}    f1.small
${cirros_flavor_name_2}    f2.small
${cirros_flavor_ram}       2048
${cirros_flavor_disk}      20
${cirros_flavor_vcpus}     1
${cirros_instance_name}    vm-cirros-1
${centos_image}            ${CENTOS_FILE}
${centos_image_name}       centos
${centos_flavor_name}      f1.medium
${centos_flavor_ram}       4096
${centos_flavor_disk}      40
${centos_flavor_vcpus}     2
${centos_instance_name}    vm-centos-1
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
Create Flavors For Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create flavors with or without properties to be used
    ...    to launch Cirros and Centos instances.
    ${properties}    Catenate    ${flavor_property_1}    ${flavor_property_2}
    Create Flavor    ${cirros_flavor_ram}    ${cirros_flavor_vcpus}
    ...    ${cirros_flavor_disk}    ${cirros_flavor_name_1}
    Create Flavor    ${centos_flavor_ram}    ${centos_flavor_vcpus}
    ...    ${centos_flavor_disk}    ${properties}    ${centos_flavor_name}

Create Images For Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create images with or without properties to be used
    ...    to launch Cirros and Centos instances.
    Put File    %{PYTHONPATH}/${cirros_image}
    ...    ${host_image_path}/${cirros_image}
    Put File    %{PYTHONPATH}/${centos_image}
    ...    ${host_image_path}/${centos_image}
    Create Image    ${host_image_path}/${cirros_image}    ${disk_format}
    ...    ${cirros_image_name}
    Create Image    ${host_image_path}/${centos_image}    ${disk_format}
    ...    ${centos_image_name}

Create Networks For Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create networks to be used to launch Cirros and Centos
    ...    instances.
    Create Network    ${network_name}
    Create Subnet    ${network_name}    ${subnet_range}    ${subnet_extras}

Launch Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Launch Cirros and Centos instances.
    Create Instance    ${network_name}    ${cirros_instance_name}
    ...    ${cirros_image_name}    ${cirros_flavor_name_1}
    Create Instance    ${network_name}    ${centos_instance_name}
    ...    ${centos_image_name}    ${centos_flavor_name}

Suspend Resume Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Suspend and Resume Cirros and Centos instances.
    Suspend Instance    ${cirros_instance_name}
    Resume Instance    ${cirros_instance_name}
    Suspend Instance    ${centos_instance_name}
    Resume Instance    ${centos_instance_name}

Set Error Active Flags Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Set 'Error' and 'Active' flags to Cirros and Centos
    ...    instances.
    Set Error State Instance    ${cirros_instance_name}    error
    Set Active State Instance    ${cirros_instance_name}    active
    Set Error State Instance    ${centos_instance_name}    error
    Set Active State Instance    ${centos_instance_name}    active

Pause Unpause Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Pause and Unpause Cirros and Centos instances.
    Pause Instance    ${cirros_instance_name}
    Pause Instance    ${centos_instance_name}
    Unpause Instance    ${cirros_instance_name}
    Unpause Instance    ${centos_instance_name}

Stop Start Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Stop and Start Cirros and Centos instances.
    Stop Instance    ${cirros_instance_name}
    Stop Instance    ${centos_instance_name}
    Start Instance    ${cirros_instance_name}
    Start Instance    ${centos_instance_name}

Lock Unlock Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Lock and Unlock Cirros and Centos instances.
    Lock Instance    ${cirros_instance_name}
    Lock Instance    ${centos_instance_name}
    Unlock Instance    ${cirros_instance_name}
    Unlock Instance    ${centos_instance_name}

Reboot Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Reboot Cirros and Centos instances.
    Reboot Instance    ${cirros_instance_name}
    Reboot Instance    ${centos_instance_name}

Rebuild Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Rebuild Cirros and Centos instances.
    Rebuild Instance    ${cirros_instance_name}
    Rebuild Instance    ${centos_instance_name}

Resize Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Resize Cirros instance.
    Create Flavor    ${cirros_flavor_ram}    ${cirros_flavor_vcpus}
    ...    ${cirros_flavor_disk}    ${cirros_flavor_name_2}
    Resize Instance    ${cirros_instance_name}    ${cirros_flavor_name_2}
    Resize Instance    ${cirros_instance_name}    ${cirros_flavor_name_1}

Set Unset Properties Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Set Unset properties of Cirros and Centos instances.
    ${properties}    Catenate    ${instance_property_1}='true'
    ...    ${instance_property_2}='500'    ${instance_property_3}='180'
    Set Instance Property    ${cirros_instance_name}    ${properties}
    Set Instance Property    ${centos_instance_name}    ${properties}
    ${properties}    Catenate    ${instance_property_1}
    ...    ${instance_property_2}    ${instance_property_3}
    Unset Instance Property    ${cirros_instance_name}    ${properties}
    Unset Instance Property    ${centos_instance_name}    ${properties}

Evacuate Instances From Hosts
    [Tags]    Duplex    MN-Local    MN-External
    [Documentation]    Evacuate all Cirros and Centos instances from computes
    ...    or controllers.
    Run Keyword If    '${CONFIGURATION_TYPE}' == 'Duplex'
    ...    Run Keywords    Evacuate Instances    controller-0    AND
    ...    Evacuate Instances     controller-1
    ...    ELSE IF    '${CONFIGURATION_TYPE}' == 'MN-Local' or '${CONFIGURATION_TYPE}' == 'MN-External'
    ...    Run Keywords    Evacuate Instances    compute-0    AND
    ...    Evacuate Instances    compute-1

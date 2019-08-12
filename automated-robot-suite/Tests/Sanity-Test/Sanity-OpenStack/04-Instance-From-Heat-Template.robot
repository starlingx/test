***Settings ***
Documentation    Test to launch instance through a heat template.
...    Author(s):
...      - Hector Ivan Ramos Escobar <ramos.escobarx.hector.ivan@intel.com>
...      - Juan Carlos Alonso Sanchez <juan.carlos.alonso@intel.com>

Resource          Resources/Utils.robot
Resource          Resources/OpenStack.robot
Suite Setup       Utils.Stx Suite Setup
Suite TearDown    Run Keywords
...    OpenStack.Openstack Cleanup All
...    Utils.Stx Suite TearDown

*** Variables ***
${stack_template}          Utils/stack_template.yml
${stack_name_1}            stack-cirros-1
${stack_name_2}            stack-cirros-2
${cirros_image}            ${CIRROS_FILE}
${cirros_image_name}       cirros
${cirros_flavor_name}      f1.small
${cirros_flavor_ram}       2048
${cirros_flavor_disk}      20
${cirros_flavor_vcpus}     1
${network_name}            network-1
${subnet_name}             subnet-1
${disk_format}             qcow2
${subnet_range}            192.168.0.0/24
${subnet_extras}           --ip-version 4 --dhcp ${subnet_name}
${host_image_path}         /home/${CLI_USER_NAME}/

*** Test Cases ***
Create Flavors for Instance
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create flavors with or without properties to be used
    ...    to launch Cirros  instances.
    Create Flavor    ${cirros_flavor_ram}    ${cirros_flavor_vcpus}
    ...    ${cirros_flavor_disk}    ${cirros_flavor_name}

Create Images for Instances
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create images with or without properties to be used
    ...    to launch Cirros  instances.
    Put File    %{PYTHONPATH}/${cirros_image}
    ...    ${host_image_path}/${cirros_image}
    Create Image    ${host_image_path}/${cirros_image}    ${disk_format}
    ...    ${cirros_image_name}

Create Networks for Instance
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create networks to be used to launch Cirros
    ...    instances.
    Create Network    ${network_name}
    Create Subnet    ${network_name}    ${subnet_range}    ${subnet_extras}

Create Instance Trough Stack
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create a Cirros instance using a heat template
    Put File    %{PYTHONPATH}/${stack_template}
    ...    ${host_image_path}/${stack_template}
    ${net_id}    Get Net Id    ${network_name}
    Create Stack    ${stack_name_1}    ${stack_template}    ${net_id}
    Create Stack    ${stack_name_2}    ${stack_template}    ${net_id}

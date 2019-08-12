*** Settings ***
Documentation    Test to create an instance with Cirros.
...    Author(s):
...     - Hector Ivan Ramos Escobar <ramos.escobarx.hector.ivan@intel.com>
...     - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Resource          Resources/Utils.robot
Resource          Resources/OpenStack.robot
Suite Setup       Utils.Stx Suite Setup
Suite TearDown    Run Keywords
...    OpenStack.Openstack Cleanup All
...    Utils.Stx Suite TearDown

*** Variables ***
${cirros_image}             ${CIRROS_FILE}
${cirros_image_name}        cirros
${cirros_image_name_tmp}    cirros-tmp
${disk_format}              qcow2
${host_image_path}          /home/${CLI_USER_NAME}/
${image_disk_size}          10
${image_ram_size}           20

*** Test Cases ***
Create Image For Metrics
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Create images with or without properties to be used
    ...    to launch Cirros  instances.
    Put File    %{PYTHONPATH}/${cirros_image}
    ...    ${host_image_path}/${cirros_image}
    Create Image    ${host_image_path}/${cirros_image}    ${disk_format}
    ...    ${cirros_image_name}

Update Image Name
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Update image name.
    ${openstack_cmd}    Catenate    openstack image show
    ...    ${cirros_image_name}
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    grep "created_at"
    ...    awk '{print $4}'
    &{result}    Run OS Command    ${cmd}
    ${created_at}    Get From Dictionary    ${result}    stdout
    ${openstack_cmd}    Set Variable    openstack image set
    ${cmd}    Catenate    ${openstack_cmd}    --name ${cirros_image_name_tmp}
    ...    ${cirros_image_name}
    Run OS Command    ${cmd}    True
    ${openstack_cmd}    Catenate    openstack image show
    ...    ${cirros_image_name_tmp}
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    grep "updated_at"
    ...    awk '{print $4}'
    &{result}    Run OS Command    ${cmd}
    ${first_update}    Get From Dictionary    ${result}    stdout
    Should Not Be Equal    ${created_at}    ${first_update}
    ${openstack_cmd}    Set Variable    openstack image set
    ${cmd}    Catenate    ${openstack_cmd}    --name ${cirros_image_name}
    ...    ${cirros_image_name_tmp}
    Run OS Command    ${cmd}    True
    ${openstack_cmd}    Catenate    openstack image show
    ...    ${cirros_image_name}
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    grep "updated_at"
    ...    awk '{print $4}'
    &{result}    Run OS Command    ${cmd}
    ${second_update}    Get From Dictionary    ${result}    stdout
    Should Not Be Equal    ${first_update}    ${second_update}

Update Image Disk Ram Size
    [Tags]    Simplex    Duplex    MN-Local    MN-External
    [Documentation]    Update image disk size and ram size.
    ${openstack_cmd}    Catenate    openstack image show
    ...    ${cirros_image_name}
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    grep "updated_at"
    ...    awk '{print $4}'
    &{result}    Run OS Command    ${cmd}
    ${updated_at}    Get From Dictionary    ${result}    stdout
    ${openstack_cmd}    Set Variable    openstack image set
    ${cmd}    Catenate    ${openstack_cmd}    --min-disk ${image_disk_size}
    ...    ${cirros_image_name}
    Run OS Command    ${cmd}    True
    ${openstack_cmd}    Catenate    openstack image show
    ...    ${cirros_image_name}
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    grep "updated_at"
    ...    awk '{print $4}'
    &{result}    Run OS Command    ${cmd}
    ${first_update}    Get From Dictionary    ${result}    stdout
    Should Not Be Equal    ${updated_at}    ${first_update}
    ${openstack_cmd}    Set Variable    openstack image set
    ${cmd}    Catenate    ${openstack_cmd}    --min-ram ${image_ram_size}
    ...    ${cirros_image_name}
    Run OS Command    ${cmd}    True
    ${openstack_cmd}    Catenate    openstack image show
    ...    ${cirros_image_name}
    ${cmd}    Catenate    SEPARATOR=|    ${openstack_cmd}    grep "updated_at"
    ...    awk '{print $4}'
    &{result}    Run OS Command    ${cmd}
    ${second_update}    Get From Dictionary    ${result}    stdout
    Should Not Be Equal    ${first_update}    ${second_update}

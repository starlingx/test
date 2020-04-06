*** Settings ***
Documentation   Tests for provisioning and unlocking controllers, computes and
...    storage hosts.
...    Author(s):
...      - Jose Perez Carranza <jose.perez.carranza@intel.com>
...      - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Variables      Variables/Global.py
Resource       Resources/HostManagement.robot
Resource       Resources/Utils.robot
Resource       Resources/OpenStack.robot
Resource       Resources/Provisioning.robot
Library        Libraries/common.py
Library        Collections
Suite Setup    Run Keywords    Utils.Stx Suite Setup
...            provisioning.Assign Data Interfaces

*** Variables ***
${master_controller}    controller-0
${second_controller}    controller-1
${backend_type}         ceph
${physnet0}             physnet0
${physnet1}             physnet1
${mtu}                  1500
${publicnet}            public-net0
${privatenet}           private-net0
${internalnet}          internal-net0
${externalnet}          external-net0
${publicsubnet}         public-subnet0
${privatesubnet}        private-subnet0
${internalsubnet}       internal-subnet0
${externalsubnet}       external-subnet0
${publicrouter}         public-router0
${privaterouter}        private-router0
${lgv_name}             nova-local
${nova_size}            100
${nova_size_comp}       True
${cgts_part_size}       20
${app_tarball}          ${APP_TARBALL_FILE}
${host_image_path}      /home/${CLI_USER_NAME}/
${clouds_yml}           clouds.yml
${password}             ${Config.credentials.STX_DEPLOY_USER_PSWD}

*** Test Cases ***
Provisioning Simplex System
    [Tags]    Simplex
    [Documentation]     Validates provisioning of a simplex configuration
    ...    according to steps defined at
    ...    "https://wiki.openstack.org/wiki/StarlingX/Containers/Installation"
    Configure OAM Interface    ${master_controller}
    Run Keyword If   '${ENVIRONMENT}'=='baremetal'    Run Keywords
    ...    Set NTP Server    AND    Configure Vswitch Type
    Configure Backend Ceph
    Configure Data Interfaces    ${master_controller}    ${data0if}
    ...    ${data1if}    ${physnet0}    ${physnet1}    ${mtu}
    Enable Containerized Services    ${master_controller}
    Setup Partitions    ${master_controller}    ${lgv_name}    ${nova_size}
    ...    ${cgts_part_size}
    Configure Ceph    ${master_controller}    ${backend_type}
    Run Keyword If   '${ENVIRONMENT}'=='baremetal'
    ...    Configure Huge Page Size    ${master_controller}
    Unlock Master Controller    ${master_controller}
    Set Ceph Pool Replication
    Wait Until Keyword Succeeds    5 min    5 sec
    ...    Check Ceph Status
    Put File    %{PYTHONPATH}/${app_tarball}
    ...    ${host_image_path}/${app_tarball}
    Stage Application Deployment    stx-openstack    ${app_tarball}
    Bring Up Services    stx-openstack
    Set Ceph Pool Replication
    Put File    %{PYTHONPATH}/Utils/${clouds_yml}
    ...    ${host_image_path}/${clouds_yml}
    ${sed_cmd}    Catenate
    ...    sed -i 's/PASS/${password}/'    ${host_image_path}/${clouds_yml}
    Run Command    ${sed_cmd}
    Set Cluster Endpoints    ${clouds_yml}
    Provider Network Setup    ${physnet0}    ${physnet1}
    Tenant Networking Setup    ${physnet0}    ${physnet1}    ${externalnet}
    ...    ${publicnet}    ${privatenet}    ${internalnet}    ${publicsubnet}
    ...    ${privatesubnet}    ${internalsubnet}    ${externalsubnet}
    ...    ${publicrouter}    ${privaterouter}

Provisioning Duplex System
    [Tags]    Duplex
    [Documentation]    Validates provisioning of a duplex configuration
    ...    according to steps defined at
    ...    "https://wiki.openstack.org/wiki/StarlingX/Containers/
    ...    InstallationOnAIODX"
    Configure OAM Interface    ${master_controller}
    Configure MGMT Interface    ${master_controller}
    Run Keyword If   '${ENVIRONMENT}'=='baremetal'    Run Keywords
    ...    Set NTP Server    AND    Configure Vswitch Type
    Configure Backend Ceph
    Configure Data Interfaces    ${master_controller}    ${data0if}
    ...    ${data1if}    ${physnet0}    ${physnet1}    ${mtu}
    Enable Containerized Services    ${master_controller}
    Setup Partitions    ${master_controller}    ${lgv_name}    ${nova_size}
    ...    ${cgts_part_size}
    Configure Ceph    ${master_controller}    ${backend_type}
    Run Keyword If   '${ENVIRONMENT}'=='baremetal'
    ...    Configure Huge Page Size    ${master_controller}
    Unlock Master Controller    ${master_controller}
    Wait Until Keyword Succeeds    5 min    5 sec
    ...    Check Ceph Status
    # --- Installing Remaining Nodes ---
    Run Keyword IF   '${ENVIRONMENT}'=='virtual'
    ...    Install Remaining Nodes Virtual
    ...    ELSE    Install Remaining Nodes Baremetal
    # --- Controller-1 ---
    Configure Data Interfaces    ${second_controller}   ${data0if}
    ...    ${data1if}    ${physnet0}    ${physnet1}    ${mtu}
    Enable Containerized Services    ${second_controller}
    Setup Partitions    ${second_controller}    ${lgv_name}    ${nova_size}
    ...    ${cgts_part_size}
    Configure Ceph    ${second_controller}    ${backend_type}
    Run Keyword If   '${ENVIRONMENT}'=='baremetal'
    ...    Configure Huge Page Size    ${second_controller}
    Unlock Second Controller    ${second_controller}
    Check Host Readiness    ${second_controller}
    Wait Until Keyword Succeeds    5 min    5 sec
    ...    Check Ceph Status
    Put File    %{PYTHONPATH}/${app_tarball}
    ...    ${host_image_path}/${app_tarball}
    Stage Application Deployment    stx-openstack    ${app_tarball}
    Bring Up Services    stx-openstack
    Set Ceph Pool Replication
    Put File    %{PYTHONPATH}/Utils/${clouds_yml}
    ...    ${host_image_path}/${clouds_yml}
    ${sed_cmd}    Catenate
    ...    sed -i 's/PASS/${password}/'    ${host_image_path}/${clouds_yml}
    Run Command    ${sed_cmd}
    Set Cluster Endpoints    ${clouds_yml}
    Provider Network Setup    ${physnet0}    ${physnet1}
    Tenant Networking Setup    ${physnet0}    ${physnet1}    ${externalnet}
    ...    ${publicnet}    ${privatenet}    ${internalnet}    ${publicsubnet}
    ...    ${privatesubnet}    ${internalsubnet}    ${externalsubnet}
    ...    ${publicrouter}    ${privaterouter}

Provisioning Standard Non-Storage System
    [Tags]    MN-Local
    [Documentation]    Validates provisioning of a standard non storage
    ...    configuration according to steps defined at
    ...    "https://wiki.openstack.org/wiki/StarlingX/Containers/
    ...    InstallationOnStandard"
    # --- Controller-0 ---
    Configure OAM Interface    ${master_controller}
    Configure MGMT Interface    ${master_controller}
    Run Keyword If   '${ENVIRONMENT}'=='baremetal'    Run Keywords
    ...    Set NTP Server    AND    Configure Vswitch Type
    Configure Backend Ceph
    Enable Containerized Services    ${master_controller}
    Unlock Master Controller    ${master_controller}
    # --- Installing Remaining Nodes ---
    Run Keyword IF   '${ENVIRONMENT}'=='virtual'
    ...    Install Remaining Nodes Virtual
    ...    ELSE    Install Remaining Nodes Baremetal
    # --- Controller-1 ---
    Enable Containerized Services    ${second_controller}
    Provide OAM Network Interface    ${second_controller}
    Setup Cluster Host Interfaces    ${second_controller}
    Unlock Second Controller    ${second_controller}
    Check Host Readiness    ${second_controller}
    ## TO DO : HERE KEYWORD TO CHECK QUORUM ON CEPH
    # --- Computes  ---
    ${computes} =    Get Compute Nodes
    Sort List    ${computes}
    : FOR    ${compute}    IN    @{computes}
    \    Enable Containerized Services    ${compute}
    \    Run Keyword If    '${compute}'=='compute-0'
    \    ...    Add Ceph Monitor    ${compute}
    \    Setup Partitions    ${compute}    ${lgv_name}    ${nova_size_comp}
    ...    ${cgts_part_size}
    \    Configure Data Interfaces    ${compute}   ${data0if}
    ...    ${data1if}    ${physnet0}    ${physnet1}    ${mtu}
    \    Setup Cluster Host Interfaces    ${compute}
    \    Run Keyword If   '${ENVIRONMENT}'=='baremetal'
    ...    Configure Huge Page Size    ${compute}
    \    Unlock Compute    ${compute}
    \    Check Host Readiness    ${compute}
    ## TO DO : HERE KEYWORD TO CHECK QUORUM ON CEPH
    # - Enable ODS on Controllers
    ${controllers}    Create List    controller-0    controller-1
    : FOR    ${controller}    IN    @{controllers}
    \    Add ODS To Tier   ${controller}
    #  HERE KEYWORD TO CHECK QUORUM AND STATUS CEPH
    Put File    %{PYTHONPATH}/${app_tarball}
    ...    ${host_image_path}/${app_tarball}
    Stage Application Deployment    stx-openstack    ${app_tarball}
    Bring Up Services    stx-openstack
    Set Ceph Pool Replication
    Put File    %{PYTHONPATH}/Utils/${clouds_yml}
    ...    ${host_image_path}/${clouds_yml}
    ${sed_cmd}    Catenate
    ...    sed -i 's/PASS/${password}/'    ${host_image_path}/${clouds_yml}
    Run Command    ${sed_cmd}
    Set Cluster Endpoints    ${clouds_yml}
    Provider Network Setup    ${physnet0}    ${physnet1}
    Tenant Networking Setup    ${physnet0}    ${physnet1}    ${externalnet}
    ...    ${publicnet}    ${privatenet}    ${internalnet}    ${publicsubnet}
    ...    ${privatesubnet}    ${internalsubnet}    ${externalsubnet}
    ...    ${publicrouter}    ${privaterouter}

Provisioning Standard Storage System
    [Tags]    MN-External
    [Documentation]    Validates provisioning of a standard storage
    ...    configuration according to steps defined at
    ...    "https://wiki.openstack.org/wiki/StarlingX/Containers/
    ...    InstallationOnStandardStorage"
    # --- Controller-0 ---
    Configure OAM Interface    ${master_controller}
    Configure MGMT Interface    ${master_controller}
    Run Keyword If   '${ENVIRONMENT}'=='baremetal'    Run Keywords
    ...    Set NTP Server    AND    Configure Vswitch Type
    Configure Backend Ceph
    Enable Containerized Services    ${master_controller}
    Unlock Master Controller    ${master_controller}
    # --- Installing Remaining Nodes ---
    Run Keyword IF   '${ENVIRONMENT}'=='virtual'
    ...    Install Remaining Nodes Virtual
    ...    ELSE    Install Remaining Nodes Baremetal
    # --- Controller-1 ---
    Enable Containerized Services    ${second_controller}
    Provide OAM Network Interface    ${second_controller}
    Setup Cluster Host Interfaces    ${second_controller}
    Unlock Second Controller    ${second_controller}
    Check Host Readiness    ${second_controller}
    ## TO DO : HERE KEYWORD TO CHECK QUORUM ON CEPH
    # --- Storage Nodes ---
    # HERE CONTAINERIZED SERVICES
    ${storages} =    Get Storage Nodes
    Sort List    ${storages}
    : FOR    ${storage}    IN    @{storages}
    \    Setup Cluster Host Interfaces Storage Node    ${storage}
    \    Add Storage OSD    ${storage}    /dev/sdb
    \    Unlock Storage    ${storage}
    \    Check Host Readiness    ${storage}
    ## TO DO : HERE KEYWORD TO CHECK QUORUM ON CEPH
    # --- Compute Nodes ---
    ${computes} =    Get Compute Nodes
    Sort List    ${computes}
    : FOR    ${compute}    IN    @{computes}
    \    Enable Containerized Services    ${compute}
    \    Label Remote Storage    ${compute}
    ## TODO : According to the wiki comment "Why is this step different
    ##        than Standard?", so using storage keyword meanwhile
    \    Setup Cluster Host Interfaces Storage Node    ${compute}
    \    Configure Data Interfaces    ${compute}   ${data0if}
    ...    ${data1if}    ${physnet0}    ${physnet1}    ${mtu}
    \    Setup Partitions    ${compute}    ${lgv_name}    ${nova_size_comp}
    ...    ${cgts_part_size}    True
    \    Run Keyword If   '${ENVIRONMENT}'=='baremetal'
    ...    Configure Huge Page Size    ${compute}
    \    Unlock Compute    ${compute}
    \    Check Host Readiness    ${compute}    1
    ## TO DO : HERE KEYWORD TO CHECK QUORUM ON CEPH
    Put File    %{PYTHONPATH}/${app_tarball}
    ...    ${host_image_path}/${app_tarball}
    Stage Application Deployment    stx-openstack    ${app_tarball}
    Bring Up Services    stx-openstack
    Set Ceph Pool Replication
    Put File    %{PYTHONPATH}/Utils/${clouds_yml}
    ...    ${host_image_path}/${clouds_yml}
    ${sed_cmd}    Catenate
    ...    sed -i 's/PASS/${password}/'    ${host_image_path}/${clouds_yml}
    Run Command    ${sed_cmd}
    Set Cluster Endpoints    ${clouds_yml}
    Provider Network Setup    ${physnet0}    ${physnet1}
    Tenant Networking Setup    ${physnet0}    ${physnet1}    ${externalnet}
    ...    ${publicnet}    ${privatenet}    ${internalnet}    ${publicsubnet}
    ...    ${privatesubnet}    ${internalsubnet}    ${externalsubnet}
    ...    ${publicrouter}    ${privaterouter}

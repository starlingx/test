*** Settings ***
Documentation    Library with keywords to be used during provisioning of
...    StarlingX deployment.
...    Author(s):
...     - Jose Perez Carranza <jose.perez.carranza@intel.com>
...     - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Variables      Variables/Global.py
Variables      Variables/config_init.py    Config
...    %{PYTHONPATH}/Config/config.ini
Variables      ${ENV_YAML}
Resource       Resources/Utils.robot
Resource       Resources/OpenStack.robot
Resource       Resources/HostManagement.robot
Library        Libraries/common.py
Library        Collections
Library        String

*** Keywords ***
Set NTP Server
    [Documentation]   Setup the NTP servers for the system.
    ${ntp_servers}    Set Variable    0.pool.ntp.org,1.pool.ntp.org
    Run Command    system ntp-modify ntpservers=${ntp_servers}

Configure Data Interfaces
    [Arguments]    ${host}    ${data0if}    ${data1if}    ${physnet0}
    ...    ${physnet1}    ${mtu}
    [Documentation]    Configure data interfaces with proper values.
    # - Configuring OAM Network and Cluster Host Interface for controller-1
    Run Keyword IF    '${host}'=='controller-1'    Run Keywords
    ...    Provide OAM Network Interface    ${host}
    ...    AND
    ...    Setup Cluster Host Interfaces    ${host}
    ${iface_info}    Get Interface Information    ${host}    ${data0if}
    ${data0portuuid}    Get From List    ${iface_info}    0
    ${data0portname}    Get From List    ${iface_info}    1
    ${data0pciaddr}    Get From List    ${iface_info}    2
    ${iface_info}    Get Interface Information    ${host}    ${data1if}
    ${data1portuuid}    Get From List    ${iface_info}    0
    ${data1portname}    Get From List    ${iface_info}    1
    ${data1pciaddr}    Get From List    ${iface_info}    2
    ${data0ifuuid}    Get Interface UUID    ${host}    ${data0portname}
    ${data1ifuuid}    Get Interface UUID    ${host}    ${data1portname}
    # - Configure the datanetworks in sysinv, prior to referencing it in
    # - the 'system host-if-modify' command
    Run Keyword If    '${host}'=='controller-0' or '${host}'=='compute-0'
    ...    Run Keywords
    ...    Run Command    system datanetwork-add ${physnet0} vlan     True
    ...    AND
    ...    Run Command    system datanetwork-add ${physnet1} vlan     True
    Add Interface To Data Network    ${mtu}   data0    ${physnet0}
    ...    ${host}    ${data0ifuuid}
    Add Interface To Data Network    ${mtu}   data1    ${physnet1}
    ...    ${host}    ${data1ifuuid}

Enable Containerized Services
    [Arguments]    ${host}
    [Documentation]    apply all the node labels for each controller
    ...    and compute functions.
    ${is_controller}    Evaluate    "controller" in """${host}"""
    Run Keyword If    ${is_controller}==True    Run Command
    ...    system host-label-assign ${host} openstack-control-plane=enabled
    ...    True
    Run Keyword If
    ...    '${CONFIGURATION_TYPE}'=='Simplex' or '${CONFIGURATION_TYPE}'=='Duplex' or ${is_controller}==False
    ...    Run Keywords    Run Command
    ...    system host-label-assign ${host} openstack-compute-node=enabled
    ...    True
    ...    AND
    ...    Run Command    system host-label-assign ${host} openvswitch=enabled
    ...    True
    ...    AND
    ...    Run Command    system host-label-assign ${host} sriov=enabled
    ...    True

Setup Partitions
    [Arguments]    ${host}    ${lgv_name}    ${nova_size}    ${cgts_part_size}
    ...    ${setup_cgts}=False
    [Documentation]    Setup required partition on specified host.
    ${root_disk_device}    Get Root Disk Device    ${host}
    ${root_disk_uuid}    Get Disk List UID    ${host}   ${root_disk_device}
    ${part_status}    Set Variable If
    ...    '${host}'=='controller-0'    Ready    Creating
    ${is_controller}    Evaluate    "controller" in """${host}"""
    # --- Configuring nova-local ---
    ${nova_size}    Run Keyword If     ${nova_size}==True
    ...    Calcultae Nova Partition Size For Computes    ${host}
    ...    ${root_disk_uuid}    ${cgts_part_size}
    ...    ELSE
    ...    Set Variable    ${nova_size}
    ${nova_partition_uuid}    Add Disk Partition    ${host}
    ...    ${root_disk_uuid}    ${nova_size}    ${part_status}
    Add Local Volume Group    ${host}    ${lgv_name}
    Add Physical Volume    ${host}    ${lgv_name}    ${nova_partition_uuid}
    Run Keyword If    ${is_controller}==False    Modify LVG Attributes
    ...    -b image    ${host}    ${lgv_name}
    # --- Extending cgts-vg ---
    ${cgts_partition_uuid}    Run Keyword If    ${is_controller}==True or ${setup_cgts}==True
    ...    Add Disk Partition    ${host}
    ...    ${root_disk_uuid}    ${cgts_part_size}    ${part_status}
    Run Keyword If    ${is_controller}==True or ${setup_cgts}==True
    ...    Add Physical Volume    ${host}    ${lgv_name}
    ...    ${cgts_partition_uuid}

Configure Backend Ceph
    [Documentation]    Configure Ceph to be used as storage backend
    Run Command    system storage-backend-add ceph --confirmed    True

Configure Ceph
    [Arguments]    ${host}    ${backend_type}
    [Documentation]   Enable CEPH partition on the specified node
    Add ODS To Tier    ${host}

Configure Huge Page Size
    [Arguments]    ${host}
    [Documentation]    Configure single huge page size for openstack worker
    ...    node.
    Run Command    system host-memory-modify -f vswitch -1G 1 ${host} 0
    ...    True
    Run Command    system host-memory-modify -f vswitch -1G 1 ${host} 1
    ...    True
    Run Command    system host-memory-modify -1G 10 ${host} 0    True
    Run Command    system host-memory-modify -1G 10 ${host} 1    True

Unlock Master Controller
    [Arguments]    ${controller}
    [Documentation]    Verify that controller with ACTIVE ssh connection
    ...    is unlocked and reestablish the ssh connection on the suite.
    ${error_expected}    Set Variable   *Socket is closed*
    Unlock Controller    ${controller}
    Wait Until Keyword Fails    20 min      20 sec    ${error_expected}
    ...    Run Command    whoami
    Close Connection
    Sleep    10 min
    Wait Until Keyword Succeeds    15 min      30 sec
    ...    Open Master Controller Connection
    Wait Until Keyword Succeeds    15 min     30 sec
    ...    Check Controller Is Unlocked    ${controller}
    Check Host Readiness    ${controller}

Unlock Second Controller
    [Arguments]    ${controller}
    [Documentation]    Verify second controller is unlocked.
    Unlock Controller    ${controller}
    Wait Until Keyword Succeeds   40 min     30 sec
    ...    Check Controller Is Unlocked    ${controller}
    # - Generate a new secondary connection due lost of comunication
    Wait Until Keyword Succeeds    50 min      20 sec    Check Property Value
    ...    ${controller}    availability    available
    Generate Secondary Controller Connection    ${controller}

Set Ceph Pool Replication
    [Documentation]    Set Ceph pool replication to get HEALTH_OK
    Run Command    ceph osd pool ls | xargs -i ceph osd pool set {} size 1
    ...    True

Check Ceph Status
    [Arguments]    ${status_1}=HEALTH_OK    ${status_2}=HEALTH_WARN
    [Documentation]    Verifies the status of the CEPH feature.
    ${result}    Run Command    ceph -s
    Should Contain Any    ${result.stdout}    ${status_1}    ${status_2}
    Run Keyword If    '${CONFIGURATION_TYPE}'!='Simplex'
    ...    Run Command      ceph osd tree    True

Bring Up Services
    [Arguments]    ${application}
    [Documentation]    Use sysinv to apply the application.
    System Application Apply    ${application}
    Wait Until Keyword Succeeds    60 min     5 sec
    ...    Check System Application Status    ${application}    applied

Set Cluster Endpoints
    [Arguments]    ${clouds_yml}
    [Documentation]    Set and verify the cluster endpoints.
    Execute Sudo Command    mkdir -p /etc/openstack
    Execute Sudo Command    mv ${clouds_yml} /etc/openstack/.

Provider Network Setup
    [Arguments]    ${physnet0}    ${physnet1}
    [Documentation]    Create the network segment ranges.
    &{output}    Run OS Command
    ...    openstack project list | grep admin | awk '{print $2}'    True
    ${adminid}    Get From Dictionary    ${output}    stdout
    ${openstack_cmd}    Set Variable    openstack network segment range create
    ${cmd}     Catenate    ${openstack_cmd}    ${physnet0}-a
    ...    --network-type vlan    --physical-network ${physnet0}
    ...    --minimum 400    --maximum 499    --private    --project ${adminid}
    Run OS Command    ${cmd}    True
    ${cmd}     Catenate    ${openstack_cmd}    ${physnet0}-b
    ...    --network-type vlan    --physical-network ${physnet0}
    ...    --minimum 10    --maximum 10
    Run OS Command   ${cmd}    True
    ${cmd}     Catenate    ${openstack_cmd}    ${physnet1}-a
    ...    --network-type vlan    --physical-network ${physnet1}
    ...    --minimum 500    --maximum 599    --private    --project ${adminid}
    Run OS Command   ${cmd}    True

Tenant Networking Setup
    [Arguments]    ${physnet0}    ${physnet1}    ${externalnet}    ${publicnet}
    ...    ${privatenet}    ${internalnet}    ${publicsubnet}
    ...    ${privatesubnet}    ${internalsubnet}    ${externalsubnet}
    ...    ${publicrouter}    ${privaterouter}
    [Documentation]    Setup tenant networking
    &{output}    Run OS Command
    ...    openstack project list | grep admin | awk '{print $2}'    True
    ${adminid}    Get From Dictionary    ${output}    stdout
    ${openstack_cmd}    Set Variable    openstack network create
    ${cmd}    Catenate    ${openstack_cmd}    --project ${adminid}
    ...    --provider-network-type=vlan
    ...    --provider-physical-network=${physnet0}    --provider-segment=10
    ...    --share     --external    ${externalnet}
    Run OS Command    ${cmd}    True
    ${cmd}    Catenate    ${openstack_cmd}    --project ${adminid}
    ...    --provider-network-type=vlan
    ...    --provider-physical-network=${physnet0}    --provider-segment=400
    ...    ${publicnet}
    Run OS Command    ${cmd}    True
    ${cmd}    Catenate    ${openstack_cmd}    --project ${adminid}
    ...    --provider-network-type=vlan
    ...    --provider-physical-network=${physnet1}    --provider-segment=500
    ...    ${privatenet}
    Run OS Command    ${cmd}    True
    ${cmd}    Catenate    ${openstack_cmd}    --project ${adminid}
    ...    ${internalnet}
    Run OS Command    ${cmd}    True
    &{output}    Run OS Command
    ...    openstack network list | grep ${publicnet} | awk '{print $2}'
    ${publicnetid}    Get From Dictionary    ${output}    stdout
    &{output}    Run OS Command
    ...    openstack network list | grep ${privatenet} | awk '{print $2}'
    ${privatenetid}    Get From Dictionary    ${output}    stdout
    &{output}    Run OS Command
    ...    openstack network list | grep ${internalnet} | awk '{print $2}'
    ${internalnetid}    Get From Dictionary    ${output}    stdout
    &{output}    Run OS Command
    ...    openstack network list | grep ${externalnet} | awk '{print $2}'
    ${externalnetid}    Get From Dictionary    ${output}    stdout
    ${openstack_cmd}    Set Variable    openstack subnet create
    ${cmd}    Catenate    ${openstack_cmd}    --project ${adminid}
    ...    ${publicsubnet}    --network ${publicnet}
    ...    --subnet-range 192.168.101.0/24
    Run OS Command    ${cmd}    True
    ${cmd}    Catenate    ${openstack_cmd}    --project ${adminid}
    ...    ${privatesubnet}    --network ${privatenet}
    ...    --subnet-range 192.168.201.0/24
    Run OS Command    ${cmd}    True
    ${cmd}    Catenate    ${openstack_cmd}    --project ${adminid}
    ...    ${internalsubnet}    --gateway none    --network ${internalnet}
    ...    --subnet-range 10.1.1.0/24
    Run OS Command    ${cmd}    True

    ${cmd}    Catenate    ${openstack_cmd}    --project ${adminid}
    ...    ${externalsubnet}    --gateway 192.168.1.1
    ...    --network ${externalnet}    --subnet-range 192.168.1.0/24
    ...    --ip-version 4
    Run OS Command    ${cmd}    True
    Run OS Command    openstack router create ${publicrouter}    True
    Run OS Command    openstack router create ${privaterouter}    True
    &{output}    Run OS Command
    ...    openstack router list | grep ${privaterouter} | awk '{print $2}'
    ${privaterouterid}    Get From Dictionary    ${output}    stdout
    &{output}    Run OS Command
    ...    openstack router list | grep ${publicrouter} | awk '{print $2}'
    ${publicrouterid}    Get From Dictionary    ${output}    stdout
    ${cmd}    Catenate    openstack router set     ${publicrouterid}
    ...   --external-gateway ${externalnetid}    --disable-snat
    Run OS Command    ${cmd}    True
    ${cmd}    Catenate    openstack router set    ${privaterouterid}
    ...    --external-gateway ${externalnetid}    --disable-snat
    Run OS Command    ${cmd}    True
    Run OS Command
    ...    openstack router add subnet ${publicrouter} ${publicsubnet}
    ...    True
    Run OS Command
    ...    openstack router add subnet ${privaterouter} ${privatesubnet}
    ...    True

Install Remaining Nodes Virtual
    [Documentation]    Install rest of the nodes according to the configuration
    ...    selected.
    Start Nodes Virtual
    Second Controller Installation Virtual    ${second_controller}
    ${vm_computes}    Get Compute List To Install Virtual
    ${vm_storages}    Get Storage List To Install Virtual
    Run Keyword If    '${CONFIGURATION_TYPE}'!='Duplex'    Run Keywords
    ...    Install Compute Nodes Virtual     ${vm_computes}
    ...    AND
    ...    Run Keyword If    '${CONFIGURATION_TYPE}'=='MN-External'
    ...    Install Storage Nodes Virtual     ${vm_storages}

Second Controller Installation Virtual
    [Arguments]    ${controller}
    [Documentation]    Validates that second controller is installed correctly.
    ...    for virtual environments.
    ${mac_address}    Get Qemu VM MAC Address    ${controller}    stxbr2
    # Workaround for launchpad 1822657
    Run Command
    ...    system host-add -n ${controller} -p controller -m ${mac_address}
    ${listed}    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Run Command    system host-show ${controller}
    # Try To Add it again, if not possible fail
    Run Keyword If    ${listed.rc}!=0    Run Command
    ...    system host-add -n ${controller} -p controller -m ${mac_address}
    ...    True
    Wait Until Keyword Succeeds    50 min      20 sec    Check Property Value
    ...    ${second_controller}    install_state    completed

Get Compute List To Install Virtual
    [Documentation]    Get a list of computes that will be installed, in this
    ...    case are the name of the VM’s created on the host machine.
    ${cmd}    Catenate    virsh -c qemu:///system list --all |
    ...    awk '/compute/{print $2}'
    ${result}    Run    ${cmd}
    @{computes}    Split String    ${result}
    [Return]    @{computes}

Get Storage List To Install Virtual
    [Documentation]    Get a list of storage nodes that will be installed, in
    ...    this case are the name of the VM’s created on the host machine.
    ${cmd}    Catenate    virsh -c qemu:///system list --all |
    ...    awk '/storage/{print $2}'
    ${result}    Run    ${cmd}
    @{storages}    Split String    ${result}
    [Return]    @{storages}

Install Compute Nodes Virtual
    [Arguments]    ${computes}
    [Documentation]    Install the compute nodes of the system with given
    ...    computes list.
    Set Test Variable    ${counter}    ${0}
    : FOR    ${vm}    IN    @{computes}
    \    ${mac_address}    Get Qemu VM MAC Address    ${vm}    stxbr2
    \    Run Command
    ...   system host-add -n compute-${counter} -p worker -m ${mac_address}
    \    ${listed}    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Run Command    system host-show compute-${counter}
    \    Run Keyword If    ${listed.rc}!=0    Run Command
    ...    system host-add -n compute-${counter} -p worker -m ${mac_address}
    ...    True
    \    ${counter}    Set Variable    ${counter+1}
    # The reason for a second loop is to add all computes on the first loop
    # and verify its installation on the second loop, hence a lot of time is
    # save on the test.
    Set Test Variable    ${counter}    ${0}
    : FOR    ${vm}    IN    @{computes}
    \    Wait Until Keyword Succeeds    20 min    20 sec    Check Property Value
    ...    compute-${counter}    install_state    completed
    \    ${counter}    Set Variable    ${counter+1}

Install Storage Nodes Virtual
    [Arguments]    ${storages}
    [Documentation]    Install the compute nodes of the system with given
    ...    storage nodes list.
    Set Test Variable    ${counter}    ${0}
    : FOR    ${vm}    IN    @{storages}
    \    ${mac_address}    Get Qemu VM MAC Address    ${vm}    stxbr2
    \    Run Command
    ...    system host-add -n storage-${counter} -p storage -m ${mac_address}
    \    ${listed}    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Run Command    system host-show storage-${counter}
    \    Run Keyword If    ${listed.rc}!=0    Run Command
    ...    system host-add -n storage-${counter} -p storage -m ${mac_address}
    ...    True
    \    ${counter}    Set Variable    ${counter+1}
    # The reason for a second loop is to add all computes on the first loop
    # and verify its installation on the second loop, hence a lot of time is
    # save on the test.
    Set Test Variable    ${counter}    ${0}
    : FOR    ${vm}    IN    @{storages}
    \    Wait Until Keyword Succeeds    20 min    20 sec    Check Property Value
    ...    storage-${counter}    install_state    completed
    \    ${counter}    Set Variable    ${counter+1}

Install Remaining Nodes Baremetal
    [Documentation]    Install rest of the nodes according to the info on the
    ...    installation yaml file.
    @{nodes_list}    Get List Of Installation Nodes
    # -- Turn On Nodes
    : FOR    ${node}   IN    @{nodes_list}
    \    &{node_data}    Set Variable    &{NODES}[${node}]
    \    ${bmc_ip}    Set Variable    &{node_data}[bmc_ip]
    \    ${bmc_user}    Set Variable     &{node_data}[bmc_user]
    \    ${pswd}    Set Variable     &{node_data}[bmc_pswd]
    \    ${set_pxe_boot_device}    Catenate    ipmitool -N 5 -H ${bmc_ip}
    ...    -U ${bmc_user} -P ${pswd}
    ...    -I lanplus chassis bootparam set bootflag pxe options=no-timeout
    \    ${turn_on_node}    Catenate    ipmitool -N 5 -H ${bmc_ip} -U ${bmc_user}
    ...    -P ${pswd} -I lanplus chassis power on
    \    Run   ${set_pxe_boot_device}
    \    Run   ${turn_on_node}
    # -- Start installation of nodes
    : FOR    ${node}   IN    @{nodes_list}
    \    &{node_data}    Set Variable    &{NODES}[${node}]
    \    ${name}    Set Variable     &{node_data}[name]
    \    ${personality}    Set Variable    &{node_data}[personality]
    \    ${mac_address}    Set Variable    &{node_data}[pxe_nic_mac]
    \    Run Command
    ...    system host-add -n ${name} -p ${personality} -m ${mac_address}
    \    ${listed}    Wait Until Keyword Succeeds    2 min    5 sec
    ...    Run Command    system host-show ${name}
    \    Run Keyword If    ${listed.rc}!=0    Run Command
    ...    system host-add -n ${name} -p ${personality} -m ${mac_address}
    ...    True
    # -- Monitor installation of nodes
    : FOR    ${node}   IN    @{nodes_list}
    \    &{node_data}    Set Variable    &{NODES}[${node}]
    \    ${name}    Set Variable    &{node_data}[name]
    \    Wait Until Keyword Succeeds    30 min    5 sec    Check Property Value
    \    ...    ${name}    install_state    completed

Get List Of Installation Nodes
    [Documentation]    Return a list of nodes candidate to be installed,
    ...    controller-0 is removed by default
    # NODES variable is actually the YAML file imported on variables
    ${nodes_list}    Get Dictionary Keys    ${NODES}
    Remove Values From List    ${nodes_list}    controller-0
    [Return]    @{nodes_list}

Assign Data Interfaces
    [Documentation]    Set variables for Data interfaces according to the
    ...    configuration selected
    @{data_interfaces}    Run Keyword IF   '${ENVIRONMENT}'=='virtual'
    ...    Create List   eth1000    eth1001
    ...    ELSE
    ...    Create List   enp24s0f0    enp24s0f1
    ${data0if}    Get From List    ${data_interfaces}    0
    ${data1if}    Get From List    ${data_interfaces}    1
    Set Suite Variable    ${data0if}
    Set Suite Variable    ${data1if}

Turn Off Installation Nodes
    [Documentation]    Turn off all the nodes that are candidate to be
    ...    installed to avoid them to be booted with already installed
    ...    StarlingX deployment.
    @{nodes_list}    Get List Of Installation Nodes
    : FOR    ${node}   IN    @{nodes_list}
    \    &{node_data}    Set Variable    &{NODES}[${node}]
    \    ${bmc_ip}    Set Variable    &{node_data}[bmc_ip]
    \    ${bmc_user}    Set Variable     &{node_data}[bmc_user]
    \    ${pswd}    Set Variable     &{node_data}[bmc_pswd]
    \    ${turn_off_node}    Catenate    ipmitool -N 5 -H ${bmc_ip} -U ${bmc_user}
    ...    -P ${pswd} -I lanplus chassis power off
    \    Run   ${turn_off_node}

Check Host Readiness
    [Arguments]    ${host}    ${wait_time}=5
    [Documentation]    Verify that host is unlocked, enabled and available.
    Wait Until Keyword Succeeds    40 min     5 sec    Check Property Value
    ...    ${host}    administrative    unlocked
    Wait Until Keyword Succeeds    20 min     5 sec    Check Property Value
    ...    ${host}    operational    enabled
    # Validate that host does not fall a degraded mode after was
    # available for some time.
    Run Keyword And Ignore Error    Check If Host Is In Degraded Mode
    ...    ${host}    ${wait_time}
    Wait Until Keyword Succeeds    60 min     5 sec    Check Property Value
    ...    ${host}    availability    available

Provide OAM Network Interface
    [Arguments]    ${controller}
    [Documentation]    Enables the OAM interface for second controller.
    ${net_type}    Set Variable    oam
    ${class}    Set Variable    platform
    ${oam_if}    Set Variable    ${Config.logical_interface.OAM}
    Modify Host Interface    ${net_type}    ${class}    ${controller}
    ...    ${oam_if}

Configure OAM Interface
    [Arguments]    ${controller}
    [Documentation]    Enables the OAM interface for master controller.
    ${oam_if}    Set Variable    ${Config.logical_interface.OAM}
    Run Keyword If    '${CONFIGURATION_TYPE}'!='Simplex'
    ...    Remove LO Interfaces    ${controller}
    ${system_cmd}    Catenate    system host-if-modify    ${controller}
    ...    ${oam_if}    -c platform
    Run Command    ${system_cmd}
    Run Command    system interface-network-assign ${controller} ${oam_if} oam

Remove LO Interfaces
    [Arguments]    ${controller}
    [Documentation]    Remove LO interfaces.
    Run Command    system host-if-modify ${controller} lo -c none
    ${system_cmd}    Catenate    SEPARATOR=|
    ...    system interface-network-list ${controller}    grep lo
    ...    awk '{print $4}'
    ${result}    Run Command    ${system_cmd}
    ${ifnet_uuids}    Convert Response To List    ${result}
    : FOR    ${uuid}    IN    @{ifnet_uuids}
    \    Run Command    system interface-network-remove ${uuid}

Configure MGMT Interface
    [Arguments]    ${controller}
    [Documentation]    Enables the MGMT interface for master controller.
    ${mgmt_if}    Set Variable    ${Config.logical_interface.MGMT}
    ${system_cmd}    Catenate    system host-if-modify    ${controller}
    ...    ${mgmt_if}    -c platform
    Run Command    ${system_cmd}
    ${system_cmd}    Catenate    system host-if-modify    ${controller}
    ...    ${mgmt_if}    -c platform
    Run Command    ${system_cmd}
    Run Command
    ...    system interface-network-assign ${controller} ${mgmt_if} mgmt
    Run Command
    ...    system interface-network-assign ${controller} ${mgmt_if} cluster-host

Setup Cluster Host Interfaces
    [Arguments]    ${host}
    [Documentation]    Setup mgmt network as a cluster-host network interface.
    Run Command    system host-if-modify ${host} mgmt0    True
    Run Command    system interface-network-assign ${host} mgmt0 cluster-host

Add Ceph Monitor
    [Arguments]    ${host}
    [Documentation]    Enable CEPH monitor to the specified host.
    Run Command    system ceph-mon-add ${host}    True
    #${mon_uid}    Get Ceph Monitor UID    ${host}
    Wait Until Keyword Succeeds    30 min     10 sec
    ...    Check Property Value Of Command
    ...    system ceph-mon-show ${host}    state    configured

Add ODS To Tier
    [Arguments]    ${host}
    [Documentation]    Enable the ODS on the specified node.
    ${device}    Set Variable    /dev/sdb
    ${tier_name}    Set Variable    ceph_cluster
    ${tier_opt}    Set Variable    ${SPACE}
    ${cmd}    Catenate    SEPARATOR=|    system host-disk-list ${host}
    ...   grep ${device}    awk '{print $2}'
    ${result}    Run Command    ${cmd}    True
    ${tier_uuid}    Run Keyword If    '${host}'=='controller-1'
    ...   Get Tier UUID    ${tier_name}
    ${tier_opt}    Set Variable If
    ...    '${host}'=='controller-1'    --tier-uuid ${tier_uuid}    ${EMPTY}
    Run Command
    ...    system host-stor-add ${host} ${result.stdout.strip()} ${tier_opt}
    ...    True

Setup Cluster Host Interfaces Storage Node
    [Arguments]    ${host}
    [Documentation]    Setup mgmt network as a cluster-host network interface
    ...    on storage nodes.
    ${if_uuid}    Get Interface UUID    ${host}    mgmt0
    Run Command
    ...    system interface-network-assign ${host} ${if_uuid} cluster-host
    ...    True

Add Storage OSD
    [Arguments]    ${storage}    ${device}
    [Documentation]    Enables the storage nodes as Object Storage Device (OSD)
    ${tier_name}    Set Variable    ceph_cluster
    ${uid}    Get Disk List UID    ${storage}    ${device}
    Run Command    system host-stor-add ${storage} ${uid}    True    60

Label Remote Storage
    [Arguments]    ${host}
    [Documentation]    Enable remote storage for root/ephemeral/swap disks in
    ...    standard storage configurations by labeling the worker nodes.
    Run Command    system host-label-assign ${host} remote-storage=enabled
    ...    True

Add Interface To Data Network
    [Arguments]    ${mtu}    ${if_name}    ${datanetwork}    ${host}    ${uuid}
    [Documentation]    Adds an interface to the specified data network.
    ${option}    Set Variable If
    ...    '${host}'=='controler-0'    -d    -p
    ${cmd}    Catenate    system host-if-modify    -m ${mtu}    -n ${if_name}
    ...    -c data    ${host}    ${uuid}
    Run Command    ${cmd}    True
    Run Command
    ...    system interface-datanetwork-assign ${host} ${uuid} ${datanetwork}
    ...    True

Calcultae Nova Partition Size For Computes
    [Arguments]    ${host}    ${uid}    ${cgs_size}
    [Documentation]     Return a calculated value for nova according to the
    ...    available space.
    ${disk_space}    Get Property Value Of Command
    ...    system host-disk-show ${host} ${uid}    available_gib
    ${disk_space}     Fetch From Left    ${disk_space}    .
    ${nova_space}    Evaluate    ${disk_space}-${cgs_size}
    [Return]    ${nova_space}

Add Disk Partition
    [Arguments]    ${host}    ${uid}    ${size}    ${status}
    [Documentation]    Add a partition for specified disk on the specified host
    ${result}    Run Command
    ...    system host-disk-partition-add ${host} ${uid} ${size} -t lvm_phys_vol
    ...    True
    ${new_uid}    Get Property From Result    ${result}    uuid
    Wait Until Keyword Succeeds    30 min     10 sec
    ...    Check Property Value Of Command
    ...    system host-disk-partition-show ${host} ${new_uid}    status
    ...    ${status}
    [Return]    ${new_uid}

Add Local Volume Group
    [Arguments]    ${host}    ${lvg_name}
    [Documentation]    Adds a local volume group according to given options.
    Run Command    system host-lvg-add ${host} ${lvg_name}    True

Add Physical Volume
    [Arguments]    ${host}    ${lvg name}    ${uid}
    [Documentation]    Adds a physical volume to the specified host.
    Run Command    system host-pv-add ${host} ${lvg name} ${uid}    True

Modify LVG Attributes
    [Arguments]    ${options}    ${host}    ${lvg name}
    [Documentation]    Modify the attributes of a Local Volume Group.
    Run Command    system host-lvg-modify ${options} ${host} ${lvg name}

Configure Vswitch Type
    [Documentation]    Deploy OVS-DPDK supported only on baremetal hardware
    Run Command    system modify --vswitch_type ovs-dpdk
    Run Command    system host-cpu-modify -f vswitch -p0 1 controller-0

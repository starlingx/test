*** Settings ***
Documentation    Install and configure StarlingX ISO.
...    Author(s):
...      - Jose Perez Carranza <jose.perez.carranza@intel.com>
...      - Humberto Perez Rodriguez <humberto.i.perez.rodriguez@intel.com>
...      - Juan Carlos Alonso <juan.carlos.alonso@intel.com>

Library           SSHLibrary
Library           Collections
Library           OperatingSystem
Library           Process
Library           String
Library           Qemu/qemu_setup.py
Library           Libraries/iso_setup.py
Library           Libraries/common.py
Library           Libraries/pxe_server.py
Resource          Resources/Utils.robot
Resource          Resources/Provisioning.robot
Variables         Variables/config_init.py    Config
...    %{PYTHONPATH}/Config/config.ini
Suite TearDown    Utils.Stx Suite TearDown

*** Variables ***
${destination}      /home/${CLI_USER_NAME}/localhost.yml
${source}           %{PYTHONPATH}/Config/${Config.general.CONFIGURATION_FILE}
${qemu_script}      %{PYTHONPATH}/Qemu/qemu_setup.py
${iso}              %{PYTHONPATH}/${STX_ISO_FILE}
${yaml}             %{PYTHONPATH}/${CONFIG.general.ENV_YAML_FILE}
${kernel_option}    ${CONFIG.iso_installer.KERNEL_OPTION}
${source_pkg}       /var/www/html/stx/bootimage/Packages
${source_repo}      /var/www/html/stx/bootimage/repodata
${password}         ${Config.credentials.STX_DEPLOY_USER_PSWD}

*** Test Cases ***
Qemu Libvirt VMs Setup Virtual
    [Tags]    Simplex    Duplex    MN-Local    MN-External    virtual
    [Documentation]    Qemu-Libvirt VMs setup and configuration for
    ...    StarlingX virtual deployment.
    # -- Install ISO on a VM
    ${result}    Run Process     python ${qemu_script} -i ${iso} -c ${yaml}
    ...    shell=True
    log    ${result.stdout}
    log    ${result.stderr}
    Log To Console    ${result.stderr}
    Should Be Equal As Integers  ${result.rc}  0

GRUB Checker For BIOS Virtual
    [Tags]    Simplex    Duplex    MN-Local    MN-External    virtual
    [Documentation]    Check grub cmd boot line against the ones in StarlingX
    ...    ISO file.
    ${grub_command_line}    Get Cmd Boot Line
    ${status}     Grub Checker    ${iso}    vbios    ${kernel_option}
    ...    ${grub_command_line}
    Should Be Equal As Strings    ${status}    match
    ...    msg="Kernel boot option does not match"    values=False

Install ISO Virtual
    [Tags]    Simplex    Duplex    MN-Local    MN-External    virtual
    [Documentation]    Installation of controller node and define the
    ...    connection to be used on other test cases.
    # -- Install ISO on a VM
    ${controller_connection}    Install Iso
    Set Suite Variable    ${controller_connection}

Check ISO Basic Mounting BareMetal
    [Tags]    Simplex    Duplex    MN-Local    MN-External    baremetal
    [Documentation]    Test basic ISO structure and funcntionality.
    Mount Iso On Pxe    ${iso}

Install ISO BareMetal
    [Tags]    Simplex    Duplex    MN-Local    MN-External    baremetal
    [Documentation]    Installation of controller node and define the
    ...    connection to be used on other test cases.
    ${master_controller}    Install Iso Master Controller
    Run Keyword If    '${CONFIGURATION_TYPE}'!='Simplex'
    ...    Turn Off Installation Nodes

Ansible Bootstrap Configuration
    [Tags]    Simplex    Duplex    MN-Local    MN-External    virtual    baremetal
    [Documentation]    Configure controller with local bootstrap playbook.
    # -- Copy localhost.yml file to controller
    Wait Until Keyword Succeeds    5 min    5 sec
    ...    Connect to Controller Node    ${CLI_USER_NAME}    ${CLI_USER_PASS}
    ...    ${CONFIG.general.IP_UNIT_0_ADDRESS}
    SSHLibrary.Put File    ${source}    ${destination}
    ${sed_cmd}    Catenate
    ...    sed -i 's/ANSIBLE_PASS/${password}/'    ${destination}
    Run Command    ${sed_cmd}
    ${sed_cmd}    Catenate
    ...    sed -i 's/ADMIN_PASS/${password}/'    ${destination}
    Run Command    ${sed_cmd}
    ${bootstrap}    Set Variable
    ...    /usr/share/ansible/stx-ansible/playbooks/bootstrap.yml
    Run Command    ansible-playbook ${bootstrap}    True    3600    ~$

Copy Install Packages
    [Tags]    Simplex    Duplex    MN-Local    MN-External    baremetal
    [Documentation]    Copy packages required to install secondary nodes.
    # -- Copy required packages post install --Workaround for pxe install--
    Wait Until Keyword Succeeds    5 min    5 sec
    ...    Connect to Controller Node    ${CLI_USER_NAME}    ${CLI_USER_PASS}
    ...    ${CONFIG.general.IP_UNIT_0_ADDRESS}
    # -- Get current release
    ${cmd_current_version}    Catenate    SEPARATOR=|    cat /etc/build.info
    ...    grep SW_VERSION    awk '{ split($1, v, "="); print v[2]}'
    &{result}    Run Command    ${cmd_current_version}    True
    ${current_version}    Get From Dictionary    ${result}    stdout
    # -- Transfer directories with packages
    ${destination_dir}    Set Variable    /home/${CLI_USER_NAME}/
    ${destination_move}    Set Variable
    ...    /www/pages/feed/rel-${${current_version.strip('"')}}
    SSHLibrary.Put Directory    ${source_pkg}    ${destination_dir}   mode=0755
    SSHLibrary.Put Directory    ${source_repo}    ${destination_dir}  mode=0755
    Execute Sudo Command
    ...    mv ${destination_dir}/Packages ${destination_move}/Packages
    Execute Sudo Command
    ...    mv ${destination_dir}/repodata ${destination_move}/repodata
    SSHLibrary.Close Connection

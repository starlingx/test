"""Provides the capability to setup a StarlingX iso with specific
configuration"""
from ast import literal_eval
from imp import reload
import os
import re
from shutil import copyfile
from shutil import copytree
from shutil import rmtree
import sys
import threading
import pexpect
import yaml

from bash import bash

from Config import config
from Utils import logger
from Utils import network
from Utils.utils import isdir

# reloading config.ini
reload(config)

# Global variables
THIS_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_PATH = os.path.dirname(THIS_PATH)
PROMPT = '$'

# Setup the logger
LOG_FILENAME = 'iso_setup_baremetal.log'
LOG_PATH = config.get('general', 'LOG_PATH')
LOG = logger.setup_logging('iso_setup_baremetal',
                            log_file='%s/%s'.format(LOG_PATH, LOG_FILENAME),
                            console_log=False)


class PxeServer(object):
    """Handle PXE services and mount ISO for Installation"""

    def __init__(self, iso_path):
        self.iso_path = iso_path
        self.iso_name = os.path.basename(self.iso_path).replace('.iso', '')
        self.tftp_dir = '/var/lib/tftpboot/uefi'

    def mount_iso(self):
        """Mounting ISO and grabbing shim, grub.efi and grub.cfg files"""

        # Mounting ISO on /mnt and on http server
        mount_point = '/mnt'
        http_mnt_point = '/var/www/html/stx'
        tmp_mnt_point = '/tmp'

        if os.listdir(mount_point):
            LOG.info('%s is busy umounting', mount_point)
            umounting_attempts = 3

            while umounting_attempts > 0:
                umounting = bash('sudo umount -l {}'.format(mount_point))

                if umounting.stderr and umounting_attempts:
                    LOG.info('Failed to umount %s, retrying...', mount_point)
                elif umounting.stderr and not umounting_attempts:
                    LOG.info('Max umounting attempts reached, leaving '
                             'installation')
                    sys.exit(1)
                else:
                    break

                umounting_attempts -= 1

        bash('sudo mount {0} {1}'.format(self.iso_path, mount_point))
        LOG.info('Mounting ISO on %s', mount_point)

        if isdir(os.path.join(http_mnt_point, self.iso_name)):
            LOG.info('Folder %s/%s already exists in http server, deleting '
                     'it.', http_mnt_point, self.iso_name)
            rmtree(os.path.join(http_mnt_point, self.iso_name))
        copytree(mount_point, os.path.join(http_mnt_point, self.iso_name))

        if isdir(os.path.join(tmp_mnt_point, self.iso_name)):
            LOG.info('Folder %s/%s already exists in http server, deleting '
                     'it.', tmp_mnt_point, self.iso_name)
            rmtree(os.path.join(tmp_mnt_point, self.iso_name))

        # Changing from RPM to CPIO format
        LOG.info('Uncompressing RPM necessary files')
        copytree(os.path.join(http_mnt_point, self.iso_name, 'Packages'),
                 os.path.join(tmp_mnt_point, self.iso_name, 'Packages'))
        grub2_regex = re.compile('grub2-efi-x64-[0-9]')
        os.chdir(os.path.join(tmp_mnt_point, self.iso_name, 'Packages'))

        for package in os.listdir(
                os.path.join(tmp_mnt_point, self.iso_name, 'Packages')):

            if 'shim' in package or grub2_regex.search(package):
                LOG.info('Found grub/shim file uncompressing it')
                bash('rpm2cpio {} | cpio -dimv'.format(package))

        # Copying shim, and grub files to tftpboot folder
        # fixme: handle condition to make sure tftp_dir exists
        if not os.path.isdir(self.tftp_dir):
            os.makedirs(self.tftp_dir)
        LOG.info('Copying grub and shim files to TFTP server')

        for root, _, files in os.walk('/tmp/{}/Packages'.format(
                self.iso_name)):

            for package in files:
                if any(boot_file in package for boot_file in ('shim.efi',
                                                              'grubx64.efi')):
                    copyfile(os.path.join(root, package),
                             os.path.join(self.tftp_dir, package))

                if 'grub.cfg' in package:
                    copyfile(os.path.join(root, package),
                             os.path.join(self.tftp_dir, package))
        copyfile(os.path.join(http_mnt_point, self.iso_name,
                              'EFI/BOOT/grub.cfg'),
                 os.path.join(self.tftp_dir, 'grub.cfg'))

        # Copying vmlinuz and initrd
        images_dir = os.path.join(self.tftp_dir, 'images')

        if isdir(images_dir):
            LOG.info('%s already exists, deleting directory.', images_dir)
            rmtree(images_dir)

        LOG.info('Copying vmlinuz and initrd files.')
        copytree(os.path.join(mount_point, 'images/pxeboot'),
                 os.path.join(self.tftp_dir, 'images'))

    @staticmethod
    def check_pxe_services():
        """This function is intended to restart DHCP service

        DHCP service needs to be restarted in order to grab the changes on the
        dhcp config file"""
        LOG.info('Checking PXE needed services')
        services = ['dhcpd', 'tftp', 'httpd']

        for service in services:
            active_service = bash('sudo systemctl is-active {}'
                                  .format(service))
            if 'active'.encode('utf-8') in active_service.stdout:
                LOG.info('%s service is active', service)
                continue
            else:
                LOG.info('%s service is not active, restarting', service)
                bash('sudo systemctl restart {}'.format(service))

    def get_efi_boot_line(self, grub_dict):
        """Get linuxefi command and initrdefi command from grub_dict

        Get linuxefi command and initrdefi command from grub_dict according to
        specified option on configuration argument while running runner.py
        """
        configuration_type = config.get('general', 'CONFIGURATION_TYPE')
        http_server_ip = config.get('baremetal', 'HTTP_SERVER')
        LOG.info('config_type')
        LOG.info(configuration_type)
        boot_lines = dict()

        if configuration_type == 'simplex':
            boot_lines = grub_dict['aio']['serial']['standard']
        elif configuration_type == 'duplex':
            boot_lines = grub_dict['aio']['serial']['standard']
        elif configuration_type == 'multinode_controller_storage':
            boot_lines = grub_dict['standard']['serial']['standard']
        elif configuration_type == 'multinode_dedicated_storage':
            boot_lines = grub_dict['standard']['serial']['standard']

        prefix = 'uefi/images'
        linuxefi_cmd = boot_lines['linuxefi']
        linuxefi_http_cmd = list()

        for parameter in linuxefi_cmd.split(' '):
            if 'inst.ks' in parameter:
                ks_file = parameter.split('/')[-1]
                parameter = 'inst.ks=http://{server}/stx/{iso}/{ks_file}' \
                    .format(server=http_server_ip, iso=self.iso_name,
                            ks_file=ks_file)
                linuxefi_http_cmd.append(parameter)
            elif 'inst.stage2' in parameter:
                parameter = 'inst.stage2=http://{server}/stx/{iso}' \
                    .format(server=http_server_ip, iso=self.iso_name)
                linuxefi_http_cmd.append(parameter)
            elif 'vmlinuz' in parameter:
                parameter = '{prefix}{parameter}'.format(prefix=prefix,
                                                         parameter=parameter)
                linuxefi_http_cmd.append(parameter)
            else:
                linuxefi_http_cmd.append(parameter)
        inst_repo = 'inst.repo=http://{server}/stx/{iso}'\
            .format(server=http_server_ip, iso=self.iso_name)
        linuxefi_http_cmd.append(inst_repo)
        boot_lines['linuxefi'] = ' '.join(linuxefi_http_cmd)

        initrd_cmd = boot_lines['initrdefi']
        initrd_prefix_cmd = list()

        for parameter in initrd_cmd.split(' '):
            if 'initrd.img' in parameter:
                parameter = '{prefix}{parameter}'.format(prefix=prefix,
                                                         parameter=parameter)
                initrd_prefix_cmd.append(parameter)
            else:
                initrd_prefix_cmd.append(parameter)
        boot_lines['initrdefi'] = ' '.join(initrd_prefix_cmd)
        return boot_lines

    def handle_grub(self):
        """Pointing source files to http server on grub"""

        installation_type = config.get('general', 'CONFIGURATION_TYPE')
        grub_dict = analyze_grub(
            os.path.join(self.tftp_dir, 'grub.cfg'))
        grub_lines = self.get_efi_boot_line(grub_dict)
        grub_entry = ("menuentry '{config}'{{\n{linuxefi}\n{initrdefi}\n}}"
                      .format(config=installation_type,
                              linuxefi=grub_lines['linuxefi'],
                              initrdefi=grub_lines['initrdefi']))
        grub_timeout = 'timeout=5\n'
        with open(os.path.join(self.tftp_dir, 'grub.cfg'), 'w') as grub_file:
            grub_file.writelines(grub_timeout)
            grub_file.write(grub_entry)


class Node(object):
    """Constructs a Node server that can be booted to pxe and also follow the
    installation of STX system
    """

    def __init__(self, node):
        self.name = node['name']
        self.personality = node['personality']
        self.pxe_nic_mac = node['pxe_nic_mac']
        self.bmc_ip = node['bmc_ip']
        self.bmc_user = node['bmc_user']
        self.bmc_pswd = node['bmc_pswd']
        if self.name == 'controller-0':
            self.installation_ip = node['installation_ip']

    def boot_server_to_pxe(self):
        """Boot the installation target server using PXE server"""

        LOG.info('Booting %s To PXE', self.name)
        LOG.info('Node %s : Setting PXE as first boot option', self.name)
        set_pxe = bash('ipmitool -I lanplus -H {node_bmc_ip} '
                       '-U {node_bmc_user} -P {node_bmc_pswd} '
                       'chassis bootdev pxe'.format(
                           node_bmc_ip=self.bmc_ip,
                           node_bmc_user=self.bmc_user,
                           node_bmc_pswd=self.bmc_pswd))
        if set_pxe.stderr:
            LOG.info(set_pxe.stderr)

        LOG.info('Node %s : Resetting target.', self.name)
        power_status = bash('ipmitool -I lanplus -H {node_bmc_ip} '
                            '-U {node_bmc_user} -P {node_bmc_pswd} '
                            'chassis power status'.format(
                                node_bmc_ip=self.bmc_ip,
                                node_bmc_user=self.bmc_user,
                                node_bmc_pswd=self.bmc_pswd))
        if power_status.stderr:
            LOG.info(set_pxe.stderr)

        if "Chassis Power is on" in str(power_status):
            power = bash('ipmitool -I lanplus -H {node_bmc_ip} '
                         '-U {node_bmc_user} -P {node_bmc_pswd} '
                         'chassis power reset'.format(
                             node_bmc_ip=self.bmc_ip,
                             node_bmc_user=self.bmc_user,
                             node_bmc_pswd=self.bmc_pswd))
        else:
            power = bash('ipmitool -I lanplus -H {node_bmc_ip} '
                         '-U {node_bmc_user} -P {node_bmc_pswd} '
                         'chassis power on'.format(
                             node_bmc_ip=self.bmc_ip,
                             node_bmc_user=self.bmc_user,
                             node_bmc_pswd=self.bmc_pswd))
        if power.stderr:
            LOG.info(power.stderr)

        LOG.info('Node %s: Deactivating sol sessions.', self.name)
        kill_sol = bash('ipmitool -I lanplus -H {node_bmc_ip} '
                        '-U {node_bmc_user} -P {node_bmc_pswd} sol '
                        'deactivate'.format(node_bmc_ip=self.bmc_ip,
                                            node_bmc_user=self.bmc_user,
                                            node_bmc_pswd=self.bmc_pswd))
        if kill_sol.stderr:
            LOG.info(kill_sol.stderr)

    def follow_node_installation(self):
        """This function is intended to follow nodes installation"""

        user_name = config.get('credentials', 'STX_DEPLOY_USER_NAME')
        password = config.get('credentials', 'STX_DEPLOY_USER_PSWD')

        LOG.info('Node %s: Following node installation.', self.name)
        installation = pexpect.spawn(('ipmitool -I lanplus -H {node_bmc_ip} '
                                      '-U {node_bmc_user} -P {node_bmc_pswd} '
                                      'sol activate')
                                     .format(node_bmc_ip=self.bmc_ip,
                                             node_bmc_user=self.bmc_user,
                                             node_bmc_pswd=self.bmc_pswd))
        installation.logfile = open('{}/iso_setup_installation.txt'.format(
            LOG_PATH), 'wb')
        installation.timeout = int(config.get('iso_installer', 'BOOT_TIMEOUT'))
        installation.expect('Start PXE over IPv4.')
        LOG.info('Node %s: Trying to boot using PXE', self.name)
        installation.expect('Linux version')
        LOG.info('Node %s: Loading Linux Kernel', self.name)
        installation.expect('Welcome to')
        LOG.info('Node %s: CentOS have been loaded', self.name)
        installation.expect('Starting installer, one moment...')
        LOG.info('Node %s: Starting installer ...', self.name)
        installation.expect('Performing post-installation setup tasks')
        LOG.info('Node %s: Performing post-installation setup tasks',
                 self.name)
        installation.expect('login:')
        LOG.info('Node %s: the system boot up correctly', self.name)
        LOG.info('Node %s: logging into the system', self.name)
        installation.sendline(user_name)
        installation.expect('Password:')
        installation.sendline(user_name)
        LOG.info('Node %s: setting a new password', self.name)
        installation.expect('UNIX password:')
        installation.sendline(user_name)
        installation.expect('New password:')
        installation.sendline(password)
        installation.expect('Retype new password:')
        installation.sendline(password)
        installation.expect('$')
        LOG.info('Node %s: the password was changed successfully', self.name)
        installation.close()
        LOG.info('Node %s: Closing SOL session after successfully '
                 'installation', self.name)
        deactivate_sol = bash(('ipmitool -I lanplus -H {node_bmc_ip} '
                               '-U {node_bmc_user} -P {node_bmc_pswd} '
                               'sol deactivate')
                              .format(node_bmc_ip=self.bmc_ip,
                                      node_bmc_user=self.bmc_user,
                                      node_bmc_pswd=self.bmc_pswd))
        if not deactivate_sol.stderr:
            LOG.info('Node %s: SOL session closed successfully', self.name)


def analyze_grub(grub_cfg_file):
    """Get linuxefi command and initrdefi command from grub_dict

    Get linuxefi command and initrdefi command from grub_dict according to
    selected option in config file
    """
    with open(grub_cfg_file, 'r') as grub:
        lines = grub.readlines()
        cmd_lines = list()

        for line in lines:

            if 'linuxefi' in line:
                line = line.strip()
                cmd_line = "'linuxefi': '{line}',".format(line=line)
                cmd_lines.append(cmd_line)
            elif 'initrdefi' in line:
                line = line.strip()
                cmd_line = "'initrdefi': '{line}'".format(line=line)
                cmd_lines.append(cmd_line)
            elif 'submenu' in line or 'menuentry' in line:
                if re.search('--id=(.*) {', line):
                    menu_name = re.search('--id=(.*) {', line)
                else:
                    menu_name = re.search("'(.*)'", line)
                menu_name = menu_name.group(1)
                line = "'{}': {{".format(menu_name)
                cmd_lines.append(line)
            elif '}' in line:
                cmd_lines.append('},')

        grub_menu = ''.join(cmd_lines)  # type: str
        grub_menu = '{{ {} }}'.format(grub_menu)
        grub_dict = literal_eval(grub_menu)
        return grub_dict


def mount_iso_on_pxe(iso):
    """"Manage and enable PXE services"""

    pxe_server = PxeServer(iso)
    pxe_server.mount_iso()
    pxe_server.handle_grub()
    pxe_server.check_pxe_services()


def install_iso_master_controller():
    """Launch ISO installation on controller-0"""

    nodes_file = os.path.join(os.environ['PYTHONPATH'], 'baremetal',
                              'baremetal_setup.yaml')
    nodes = yaml.safe_load(open(nodes_file))

    # Update config.ini with OAM and MGMT interfaces
    network_interfaces = []
    network_interfaces.insert(0, nodes['nodes']['controller-0']['oam_if'])
    network_interfaces.insert(1, nodes['nodes']['controller-0']['mgmt_if'])
    configuration_file = os.path.join(
        PROJECT_PATH, 'Config', 'config.ini')
    configuration_type = config.get('general', 'CONFIGURATION_TYPE')
    network.update_networks_config(
        network_interfaces, configuration_file, configuration_type)

    # Installing STX on main controller
    controller_0 = nodes['nodes']['controller-0']
    master_controller = Node(controller_0)
    master_controller.boot_server_to_pxe()
    master_controller.follow_node_installation()

    return master_controller


def get_controller0_ip():
    """Returns master controller IP"""

    nodes_file = os.path.join(THIS_PATH, '..', 'BareMetal',
                              'installation_setup.yaml')
    nodes = yaml.load(open(nodes_file))
    controller_0 = nodes['controller-0']
    master_controller = Node(controller_0)

    return master_controller.installation_ip


def config_controller(config_file):
    """Configures master controller using its corresponding init file"""

    config_controller_timeout = int(config.get(
        'iso_installer', 'CONFIG_CONTROLLER_TIMEOUT'))
    nodes_file = os.path.join(os.environ['PYTHONPATH'], 'baremetal',
                              'baremetal_setup.yaml')
    nodes = yaml.safe_load(open(nodes_file))
    controller_0 = nodes['nodes']['controller-0']
    master_controller = Node(controller_0)
    serial_cmd = ('ipmitool -I lanplus -H {node_bmc_ip} -U {node_bmc_user} '
                  '-P {node_bmc_pswd} sol activate'
                  .format(node_bmc_ip=master_controller.bmc_ip,
                          node_bmc_user=master_controller.bmc_user,
                          node_bmc_pswd=master_controller.bmc_pswd))

    configuring_controller = pexpect.spawn(serial_cmd)
    configuring_controller.logfile = open('{}/iso_setup_installation.txt'
                                          .format(LOG_PATH), 'wb')
    configuring_controller.sendline('\r')
    configuring_controller.expect(PROMPT)
    LOG.info('Applying configuration (this will take several minutes)')
    configuring_controller.sendline(
        'sudo config_controller --force --config-file {}'.format(config_file))
    configuring_controller.timeout = config_controller_timeout
    configuring_controller.expect('Configuration was applied')
    LOG.info(configuring_controller.before)
    configuring_controller.logfile.close()
    LOG.info('Closing the log')
    configuring_controller.close()
    closing_serial_connection = (
        bash('ipmitool  -I lanplus -H {node_bmc_ip} -U {node_bmc_user} '
             '-P {node_bmc_pswd} sol deactivate'
             .format(node_bmc_ip=master_controller.bmc_ip,
                     node_bmc_user=master_controller.bmc_user,
                     node_bmc_pswd=master_controller.bmc_pswd)))
    if closing_serial_connection.stderr:
        LOG.info(closing_serial_connection.stderr)


def install_secondary_nodes():
    """Installs STX on controller-1 and computes"""

    nodes_file = os.path.join(THIS_PATH, '..', 'BareMetal',
                              'installation_setup.yml')
    nodes = yaml.load(open(nodes_file))

    # Removing controller-0 from Nodes
    controller_0 = nodes.pop('controller-0')
    master_controller = Node(controller_0)
    serial_cmd = ('ipmitool -I lanplus -H {node_bmc_ip} -U {node_bmc_user} '
                  '-P {node_bmc_pswd} sol activate'
                  .format(node_bmc_ip=master_controller.bmc_ip,
                          node_bmc_user=master_controller.bmc_user,
                          node_bmc_pswd=master_controller.bmc_pswd))
    controller_0_serial = pexpect.spawn(serial_cmd)

    # Loading openrc
    controller_0_serial.sendline('source /etc/nova/openrc')

    # Adding nodes to master controller
    nodes_instances = list()
    node_names = nodes.keys()

    for node_name in node_names:
        node = Node(nodes[node_name])
        nodes_instances.append(node)
        controller_0_serial.sendline('system host-add -n {name} '
                                     '-p {personality} -m {mac_address}'
                                     .format(name=node.name,
                                             personality=node.personality,
                                             mac_address=node.pxe_nic_mac))
        node.boot_server_to_pxe()

    node_installation_threads = list()

    for nodes_instance in nodes_instances:
        thread = threading.Thread(
            target=nodes_instance.follow_node_installation())
        LOG.info('Starting installation on %s', nodes_instance.name)
        thread.start()
        node_installation_threads.append(thread)

    # Waiting for nodes to be installed
    LOG.info('Waiting for nodes to be installed')

    for node_installation_thread in node_installation_threads:
        node_installation_thread.join()

    LOG.info('All nodes have been installed successfully!')

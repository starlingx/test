"""Provides the capability to setup a StarlingX iso with specific
configuration"""

from imp import reload
import os
import getpass
import subprocess
import pexpect

import psutil

from Config import config
from Libraries import common
from Utils import logger
from Utils import network

# reloading config.ini
reload(config)

# Global variables
THIS_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_PATH = os.path.dirname(THIS_PATH)
CURRENT_USER = getpass.getuser()
PASSWORD = config.get('credentials', 'STX_DEPLOY_USER_PSWD')
PROMPT = '$'

# setup the logger
LOG_FILENAME = 'iso_setup.log'
LOG_PATH = config.get('general', 'LOG_PATH')
LOG = logger.setup_logging(
    'iso_setup', log_file='{path}/{filename}'.format(
        path=LOG_PATH, filename=LOG_FILENAME), console_log=False)


class Installer(object):
    """Install a StarlingX ISO though serial console"""

    def __init__(self):
        self.child = pexpect.spawn(config.get('iso_installer', 'VIRSH_CMD'))
        self.child.logfile = open('{}/iso_setup_console.txt'.format(
            LOG_PATH), 'wb')

    @staticmethod
    def open_xterm_console():
        """Open a xterm console to visualize logs from serial connection"""

        suite_path = os.path.dirname(THIS_PATH)
        terminal = 'xterm'
        terminal_title = '"controller-0 boot console"'
        geometry = '-0+0'  # upper right hand corner
        os.environ['DISPLAY'] = ':0'
        command = 'python {suite}/Utils/watcher.py {log_path}'.format(
            suite=suite_path, log_path=LOG_PATH)

        try:
            pid_list = subprocess.check_output(['pidof', terminal]).split()

            # killing all xterm active sessions
            for pid in pid_list:
                _pid = psutil.Process(int(pid))
                # terminate the process
                _pid.terminate()

                if _pid.is_running():
                    # forces the process to terminate
                    _pid.suspend()
                    _pid.resume()
        except subprocess.CalledProcessError:
            LOG.info('There is not process for : %s', terminal)

        os.system('{term} -geometry {geo} -T {title} -e {cmd} &'.format(
            term=terminal, geo=geometry, title=terminal_title, cmd=command))

    def boot_installer(self):
        """Interact with the installation process at boot time

        The aim of this function is send the appropriate arguments in order to
        boot the ISO
        """
        boot_timeout = int(config.get('iso_installer', 'BOOT_TIMEOUT'))
        self.child.expect('Escape character')
        LOG.info('connected to the VM (controller-0)')
        # send a escape character
        self.child.sendline('\x1b')
        self.child.expect('boot:')
        cmd_boot_line = common.get_cmd_boot_line()
        self.child.sendline(cmd_boot_line)
        LOG.info('kernel command line sent: %s', cmd_boot_line)
        # send a enter character
        self.child.sendline('\r')
        # setting a boot timeout
        self.child.timeout = boot_timeout
        self.child.expect('Loading vmlinuz')
        LOG.info('Loading vmlinuz')
        self.child.expect('Loading initrd.img')
        LOG.info('Loading initrd.img')
        self.child.expect('Starting installer, one moment...')
        LOG.info('Starting installer ...')
        self.child.expect('Performing post-installation setup tasks')
        LOG.info('Performing post-installation setup tasks')

    def first_login(self):
        """Change the password at first login"""

        user_name = config.get('credentials', 'STX_DEPLOY_USER_NAME')
        self.child.expect('localhost login:')
        LOG.info('the system boot up correctly')
        LOG.info('logging into the system')
        self.child.sendline(user_name)
        self.child.expect('Password:')
        self.child.sendline(user_name)
        LOG.info('setting a new password')
        self.child.expect('UNIX password:')
        self.child.sendline(user_name)
        self.child.expect('New password:')
        self.child.sendline(PASSWORD)
        self.child.expect('Retype new password:')
        self.child.sendline(PASSWORD)
        self.child.expect('$')
        LOG.info('the password was changed successfully')

    def configure_temp_network(self):
        """Setup a temporal controller IP"""

        controller_tmp_ip = config.get('iso_installer', 'CONTROLLER_TMP_IP')
        controller_tmp_gateway = config.get(
            'iso_installer', 'CONTROLLER_TMP_GATEWAY')
        LOG.info('Configuring temporal network')

        self.child.expect(PROMPT)

        # -----------------------------
        # getting OS network interfaces
        timeout_before = self.child.timeout
        self.child.timeout = 10
        self.child.sendline('ls /sys/class/net')
        cmd_stdout = []

        try:
            for stdout in self.child:
                cmd_stdout.append(stdout.strip())
        except pexpect.exceptions.TIMEOUT:
            LOG.info('custom timeout reached')

        network_interfaces = []
        network_interfaces.extend(''.join(cmd_stdout[-1:]).split())
        # returning to the original timeout value
        self.child.timeout = timeout_before
        controller_tmp_interface = network_interfaces[0]
        # -----------------------------

        self.child.sendline('sudo ip addr add {0}/24 dev {1}'.format(
            controller_tmp_ip, controller_tmp_interface))
        self.child.expect('Password:')
        self.child.sendline(PASSWORD)

        self.child.expect(PROMPT)

        self.child.sendline('sudo ip link set {} up'.format(
            controller_tmp_interface))

        self.child.expect(PROMPT)
        self.child.sendline('sudo ip route add default via {}'.format(
            controller_tmp_gateway))

        LOG.info('Network configured, testing ping')
        self.child.sendline('ping -c 1 127.0.0.1')
        self.child.expect('1 packets transmitted')
        LOG.info('Ping successful')

        # updating networks in the config.ini
        configuration_file = os.path.join(
            PROJECT_PATH, 'Config', 'config.ini')
        configuration_type = config.get('general', 'CONFIGURATION_TYPE')
        network.update_networks_config(
            network_interfaces, configuration_file, configuration_type)

    def config_controller(self, config_file):
        """Configure controller with provided configuration file

        :param config_file: which is the configuration file for
            config_controller
        """
        config_controller_timeout = int(config.get(
            'iso_installer', 'CONFIG_CONTROLLER_TIMEOUT'))
        self.child.expect(PROMPT)
        LOG.info('Applying configuration (this will take several minutes)')
        self.child.sendline(
            'sudo config_controller --force --config-file {}'
            .format(config_file))
        self.child.timeout = config_controller_timeout
        self.child.expect('Configuration was applied')
        LOG.info(self.child.before)

    def finish_logging(self):
        """Stop logging and close log file"""
        self.child.logfile.close()
        LOG.info('Closing the log')


def install_iso():
    """Start the process of installing a StarlingX ISO"""

    install_obj = Installer()
    install_obj.open_xterm_console()
    install_obj.boot_installer()
    install_obj.first_login()
    install_obj.configure_temp_network()
    return install_obj


def config_controller(controller_connection, config_file):
    """Start controller configuration with specified configuration file

    :param controller_connection: which is the connection stabilised through
    to the controller
    :param config_file: which is the configuration file for config_controller
    """
    controller_connection.config_controller(config_file)
    controller_connection.finish_logging()

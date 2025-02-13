from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_config import LabConfig
from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class LabConnectionKeywords(BaseKeyword):
    """
    Class to hold Lab connection keywords
    """

    def get_active_controller_ssh(self) -> SSHConnection:
        """
        Gets the active controller ssh
        Returns: the ssh for the active controller

        """
        lab_config = ConfigurationManager.get_lab_config()

        jump_host_config = None
        if lab_config.is_use_jump_server():
            jump_host_config = lab_config.get_jump_host_configuration()

        connection = SSHConnectionManager.create_ssh_connection(
            lab_config.get_floating_ip(),
            lab_config.get_admin_credentials().get_user_name(),
            lab_config.get_admin_credentials().get_password(),
            ssh_port=lab_config.get_ssh_port(),
            jump_host=jump_host_config,
        )

        return connection

    def get_standby_controller_ssh(self) -> SSHConnection:
        """
        Gets the standby controller ssh
        Returns: the ssh for the standby controller

        """
        lab_config = ConfigurationManager.get_lab_config()

        # get the standby controller
        standby_controller = SystemHostListKeywords(self.get_active_controller_ssh()).get_standby_controller()
        if not standby_controller:
            raise KeywordException('System does not have a standby controller')

        standby_host_name = standby_controller.get_host_name()

        standby_ip = lab_config.get_node(standby_host_name).get_ip()

        jump_host_config = None
        if lab_config.is_use_jump_server():
            jump_host_config = lab_config.get_jump_host_configuration()

        connection = SSHConnectionManager.create_ssh_connection(
            standby_ip,
            lab_config.get_admin_credentials().get_user_name(),
            lab_config.get_admin_credentials().get_password(),
            ssh_port=lab_config.get_ssh_port(),
            jump_host=jump_host_config,
        )

        return connection

    def get_compute_ssh(self, compute_name: str) -> SSHConnection:
        """
        Gets an SSH connection to the 'Compute' node whose name is specified by the argument 'compute_name'.
        Args:
             compute_name (string): The name of the 'Compute' node.

        Returns: the SSH connection to the 'Compute' node whose name is specified by the argument 'compute_name'.

        NOTE: this 'ssh connection' actually uses ssh_pass to make a call from the active controller connection.

        """
        connection = self.get_active_controller_ssh()
        lab_config = ConfigurationManager.get_lab_config()

        # setup this connection to use ssh pass
        connection.setup_ssh_pass(compute_name, lab_config.get_admin_credentials().get_user_name(), lab_config.get_admin_credentials().get_password())

        return connection

    def get_subcloud_ssh(self, subcloud_name: str) -> SSHConnection:
        """
        Gets an SSH connection to the 'Subcloud' node whose name is specified by the argument 'subcloud_name'.
        Args:
             subcloud_name (string): The name of the 'subcloud' node.

        Returns: the SSH connection to the 'subcloud' node whose name is specified by the argument 'subcloud_name'.

        """
        lab_config = ConfigurationManager.get_lab_config()
        subcloud_config: LabConfig = lab_config.get_subcloud(subcloud_name)

        if not subcloud_config:
            raise ValueError(f"There is no 'subcloud' node named {subcloud_name} defined in your config file.")

        jump_host_config = None
        if lab_config.is_use_jump_server():
            jump_host_config = lab_config.get_jump_host_configuration()

        connection = SSHConnectionManager.create_ssh_connection(
            subcloud_config.get_floating_ip(),
            lab_config.get_admin_credentials().get_user_name(),
            lab_config.get_admin_credentials().get_password(),
            ssh_port=lab_config.get_ssh_port(),
            jump_host=jump_host_config,
        )

        return connection

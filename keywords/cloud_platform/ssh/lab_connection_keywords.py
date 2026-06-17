from contextlib import contextmanager
from typing import Generator

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_config import LabConfig
from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.ssh.ssh_tunnel import SSHTunnel
from framework.ssh.ssh_tunnel_info import SSHTunnelInfo
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


class LabConnectionKeywords(BaseKeyword):
    """
    Class to hold Lab connection keywords
    """

    def get_active_controller_ssh(self) -> SSHConnection:
        """Gets the active controller ssh

        Returns:
            SSHConnection: the ssh for the active controller
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

        Returns:
            SSHConnection: the ssh for the standby controller
        """
        lab_config = ConfigurationManager.get_lab_config()

        # get the standby controller
        standby_controller = SystemHostListKeywords(self.get_active_controller_ssh()).get_standby_controller()
        if not standby_controller:
            raise KeywordException("System does not have a standby controller")

        standby_host_name = standby_controller.get_host_name()

        standby_ip = lab_config.get_node(standby_host_name).get_ip()

        jump_host_config = None
        if lab_config.is_use_jump_server():
            jump_host_config = lab_config.get_jump_host_configuration()

        connection = SSHConnectionManager.create_ssh_connection(
            standby_ip,
            lab_config.get_admin_credentials().get_user_name(),
            lab_config.get_admin_credentials().get_password(),
            name=standby_host_name,
            ssh_port=lab_config.get_ssh_port(standby_host_name),
            jump_host=jump_host_config,
        )

        return connection

    def get_ssh_for_hostname(self, hostname: str) -> SSHConnection:
        """
        Gets the ssh connection for the hostname

        Args:
             hostname (str): The name of the host

        Returns:
            SSHConnection: the ssh for the hostname

        """
        lab_config = ConfigurationManager.get_lab_config()

        host_node = lab_config.get_node(hostname)
        if not host_node:
            raise KeywordException(f"System does not have '{hostname}'")

        host_type = host_node.get_type()
        if any(node_type in host_type for node_type in ["worker", "storage"]):
            return self.get_ssh_pass(hostname)

        host_ip = host_node.get_ip()
        jump_host_config = None
        if lab_config.is_use_jump_server():
            jump_host_config = lab_config.get_jump_host_configuration()

        connection = SSHConnectionManager.create_ssh_connection(
            host_ip,
            lab_config.get_admin_credentials().get_user_name(),
            lab_config.get_admin_credentials().get_password(),
            name=hostname,
            ssh_port=lab_config.get_ssh_port(hostname),
            jump_host=jump_host_config,
        )
        return connection

    def get_compute_ssh(self, compute_name: str) -> SSHConnection:
        """
        Gets an SSH connection to the 'Compute' node whose name is specified by the argument 'compute_name'.

        Establishes a real SSH session to the compute node by using the controller
        as a proxy via ProxyCommand. This allows full SSH functionality including SFTP.

        Args:
            compute_name (str): The name of the 'Compute' node.

        Returns:
            SSHConnection: the SSH connection to the 'Compute' node.
        """
        return self._get_proxy_ssh(compute_name)

    def get_storage_ssh(self, storage_name: str) -> SSHConnection:
        """
        Gets an SSH connection to the 'Storage' node whose name is specified by the argument 'storage_name'.

        Establishes a real SSH session to the storage node by using the controller
        as a proxy via ProxyCommand. This allows full SSH functionality including SFTP.

        Args:
            storage_name (str): The name of the 'Storage' node.

        Returns:
            SSHConnection: the SSH connection to the 'Storage' node.
        """
        return self._get_proxy_ssh(storage_name)

    def _get_proxy_ssh(self, host_name: str) -> SSHConnection:
        """
        Gets a real SSH connection to a node by proxying through the active controller.

        Uses paramiko's ProxyCommand to establish a direct SSH session to the target
        node through the controller. This bypasses AllowTcpForwarding restrictions
        and provides full SSH functionality including SFTP.

        Args:
            host_name (str): The hostname of the target node (e.g. 'compute-0').

        Returns:
            SSHConnection: A real SSH connection to the target node.
        """
        lab_config = ConfigurationManager.get_lab_config()
        credentials = lab_config.get_admin_credentials()
        username = credentials.get_user_name()
        password = credentials.get_password()
        controller_ip = lab_config.get_floating_ip()

        jump_host_config = None
        if lab_config.is_use_jump_server():
            jump_host_config = lab_config.get_jump_host_configuration()

        connection = SSHConnectionManager.create_proxy_ssh_connection(
            target_host=host_name,
            target_username=username,
            target_password=password,
            first_jump_host=jump_host_config,
            second_jump_host=controller_ip,
            second_jump_username=username,
            second_jump_password=password,
        )

        return connection

    def get_ssh_pass(self, host_name: str) -> SSHConnection:
        """
        Gets an SSH connection to the node whose name is specified by the argument 'host_name'.

        Args:
            host_name (str): The name of the node.

        Returns:
            SSHConnection: the SSH connection to the node whose name is specified by the argument 'host_name'.

        """
        connection = self.get_active_controller_ssh()
        connection.set_name(host_name)
        lab_config = ConfigurationManager.get_lab_config()
        credentials = lab_config.get_admin_credentials()
        # setup this connection to use ssh pass
        connection.setup_ssh_pass(host_name, credentials.get_user_name(), credentials.get_password())

        return connection

    def get_subcloud_ssh(self, subcloud_name: str) -> SSHConnection:
        """Gets an SSH connection to the 'Subcloud' node whose name is specified by the argument 'subcloud_name'.

        Args:
             subcloud_name (str): The name of the 'subcloud' node.

        Returns:
            SSHConnection: the SSH connection to the 'subcloud' node whose name is specified by the argument 'subcloud_name'.

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

    def get_subcloud_factory_ssh(self, subcloud_name: str) -> SSHConnection:
        """Gets an SSH connection to the subcloud using its factory IP and factory credentials.

        Uses factory_credentials from the subcloud config. Falls back to admin_credentials if not set.
        Uses factory_ip from the subcloud config. Falls back to floating_ip if not set.

        Args:
            subcloud_name (str): The name of the 'subcloud' node.

        Returns:
            SSHConnection: the SSH connection to the subcloud at its factory IP.
        """
        lab_config = ConfigurationManager.get_lab_config()
        subcloud_config: LabConfig = lab_config.get_subcloud(subcloud_name)

        if not subcloud_config:
            raise ValueError(f"There is no 'subcloud' node named {subcloud_name} defined in your config file.")

        factory_creds = subcloud_config.get_factory_credentials()
        if factory_creds:
            username = factory_creds.get_user_name()
            password = factory_creds.get_password()
        else:
            username = subcloud_config.get_admin_credentials().get_user_name()
            password = subcloud_config.get_admin_credentials().get_password()

        jump_host_config = None
        if lab_config.is_use_jump_server():
            jump_host_config = lab_config.get_jump_host_configuration()

        connection = SSHConnectionManager.create_ssh_connection(
            subcloud_config.get_factory_ip(),
            username,
            password,
            ssh_port=lab_config.get_ssh_port(),
            jump_host=jump_host_config,
        )

        return connection

    def get_secondary_active_controller_ssh(self) -> SSHConnection:
        """Gets an SSH connection to the secondary active controller node.

        Returns:
            SSHConnection: the ssh for the secondary active controller
        """
        lab_config = ConfigurationManager.get_lab_config()
        secondary_lab_config = lab_config.get_secondary_system_controller_config()

        if not secondary_lab_config:
            raise ValueError(f"There is no {secondary_lab_config} defined in your config file.")

        jump_host_config = None
        if lab_config.is_use_jump_server():
            jump_host_config = lab_config.get_jump_host_configuration()

        connection = SSHConnectionManager.create_ssh_connection(
            secondary_lab_config.get_floating_ip(),
            secondary_lab_config.get_admin_credentials().get_user_name(),
            secondary_lab_config.get_admin_credentials().get_password(),
            ssh_port=secondary_lab_config.get_ssh_port(),
            jump_host=jump_host_config,
        )

        return connection

    def ping_host(self, hostname: str, count: int = 3) -> bool:
        """Ping a host by hostname or IP address.

        Args:
            hostname (str): The hostname or IP address to ping.
            count (int): Number of ping packets.

        Returns:
            bool: True if ping succeeds, False otherwise.
        """
        connection = self.get_active_controller_ssh()
        cmd = f"ping -c {count} {hostname}"
        connection.send(cmd)
        return connection.get_return_code() == 0

    def test_ssh_connectivity(self, hostname: str) -> bool:
        """Test SSH connectivity to a host using lab credentials.

        Args:
            hostname (str): The hostname to test SSH connectivity to.

        Returns:
            bool: True if SSH connection succeeds, False otherwise.
        """
        connection = self.get_active_controller_ssh()
        lab_config = ConfigurationManager.get_lab_config()
        connection.setup_ssh_pass(hostname, lab_config.get_admin_credentials().get_user_name(), lab_config.get_admin_credentials().get_password())
        connection.send("echo 'connection_test'")
        return connection.get_return_code() == 0

    @contextmanager
    def create_bmc_ssh_tunnel(self, host_name: str) -> Generator[SSHTunnel, None, None]:
        """Create an SSH tunnel to the bmc via the active controller.

        Use as a context manager to auto-close the tunnel:

            with keywords.create_bmc_ssh_tunnel("controller-0") as tunnel:
                # use tunnel
            # tunnel is automatically closed

             127.0.0.1:<local_port> <=> <bm_ip>:<bm_port>

        Args:
            host_name (str): The name of the bmc's host to create the tunnel to.

        Yields:
            SSHTunnel: ssh tunnel to bmc
        """
        lab_config = ConfigurationManager.get_lab_config()
        node = lab_config.get_node(lab_node_name=host_name)
        if not node:
            raise KeywordException(f"Node not found: '{host_name}'")

        remote_host, remote_port = node.get_bm_ip(), node.get_bm_port()
        if not remote_host:
            raise KeywordException(f"BMC ip is not configured for host {host_name}")

        tunnel_info = SSHTunnelInfo(remote_host, remote_port)
        jump_host_config = None
        if lab_config.is_use_jump_server():
            jump_host_config = lab_config.get_jump_host_configuration()

        ssh_tunnel = SSHTunnel(
            tunnel_info=tunnel_info,
            host=lab_config.get_floating_ip(),
            ssh_port=lab_config.get_ssh_port(),
            username=lab_config.get_admin_credentials().get_user_name(),
            password=lab_config.get_admin_credentials().get_password(),
            jump_host_config=jump_host_config,
        )

        with ssh_tunnel as tunnel:
            yield tunnel

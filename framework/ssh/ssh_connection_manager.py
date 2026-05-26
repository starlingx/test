import getpass
import socket
from datetime import datetime

from config.host.objects.host_configuration import HostConfiguration
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_info import SSHConnectionInfoClass


class SSHConnectionManagerClass:
    def __init__(self):
        self.ssh_connection_list = {}

    def create_ssh_connection(
        self,
        host: str,
        user: str,
        password: str,
        name: str = None,
        ssh_port: int = 22,
        timeout: int = 30,
        jump_host: HostConfiguration = None,
    ) -> SSHConnection:
        """
        Creates the ssh connection and connects using the host, user and password
        Adds the connection to the list to be managed
        Args:

            host: the host to connect with
            user: the user
            password: the password
            name: Name associated with the connection in the Manager.
            ssh_port: The port to use to establish an SSH connection.
            timeout: The maximum time in seconds the caller wants to wait for the SSH connection to be established.
            jump_host: jump host configuration if needed

        Returns: The ssh connection

        """
        if not name:
            name = host
        if self.ssh_connection_list.get(name):
            name = name + '_{}'.format(datetime.timestamp(datetime.now()))
        ssh_connection = SSHConnection(name, host, user, password, timeout=timeout, ssh_port=ssh_port, jump_host=jump_host)
        ssh_connection.connect()
        self.ssh_connection_list[name] = ssh_connection

        return ssh_connection

    def create_ssh_from_info(self, info: SSHConnectionInfoClass, name: str = None) -> SSHConnection:
        """
        Creates the ssh connection and connects using the SSH Connection Info
        Adds the connection to the list to be managed
        Args:
            info (SSHConnectionInfoClass): Connection information
            name (str): Name associated with the connection in the Manager.

        Returns: The ssh connection

        """
        return self.create_ssh_connection(info.get_host(), info.get_user(), info.get_password(), name)

    def create_local_ssh(self, name: str = None) -> SSHConnection:
        """
        Creates an ssh connection to the local host.
        Adds the connection to the list to be managed
        Args:
            name (str): Name associated with the connection in the Manager.

        Returns: The ssh connection

        """
        local_host = socket.gethostname()
        local_user = getpass.getuser()

        return self.create_ssh_connection(local_host, local_user, None, name)

    def create_proxy_ssh_connection(
        self,
        target_host: str,
        target_username: str,
        target_password: str,
        first_jump_host: HostConfiguration = None,
        second_jump_host: str = None,
        second_jump_username: str = None,
        second_jump_password: str = None,
        timeout: int = 30,
    ) -> SSHConnection:
        """
        Creates a real SSH connection to a target node by proxying through one or two jump hosts.

        Uses paramiko ProxyCommand to establish a direct SSH session to the target
        through intermediate hosts. This bypasses AllowTcpForwarding restrictions
        and provides full SSH functionality including SFTP.

        Connection order: RunAgent -> first_jump_host (optional) -> second_jump_host -> target

        Args:
            target_host: The hostname of the target node.
            target_username: The SSH username for the target node.
            target_password: The SSH password for the target node.
            first_jump_host: Optional configuration for the outer jump host (first hop from the run agent).
            second_jump_host: The IP or hostname of the jump host closest to the target (runs nc to reach it).
            second_jump_username: The SSH username for the second jump host.
            second_jump_password: The SSH password for the second jump host.
            timeout: The maximum time in seconds to wait for the connection.

        Returns:
            SSHConnection: A real SSH connection to the target node.
        """
        name = target_host
        if self.ssh_connection_list.get(name):
            name = name + '_{}'.format(datetime.timestamp(datetime.now()))

        if first_jump_host:
            first_jump_ip = first_jump_host.get_host()
            first_jump_user = first_jump_host.get_credentials().get_user_name()
            first_jump_password = first_jump_host.get_credentials().get_password()
            proxy_cmd = (
                f"sshpass -p '{first_jump_password}' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
                f"{first_jump_user}@{first_jump_ip} "
                f"sshpass -p '{second_jump_password}' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
                f"{second_jump_username}@{second_jump_host} nc {target_host} 22"
            )
        else:
            proxy_cmd = (
                f"sshpass -p '{second_jump_password}' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
                f"{second_jump_username}@{second_jump_host} nc {target_host} 22"
            )

        ssh_connection = SSHConnection(
            name,
            target_host,
            target_username,
            target_password,
            timeout=timeout,
            proxy_command=proxy_cmd,
        )
        ssh_connection.connect()
        self.ssh_connection_list[name] = ssh_connection

        return ssh_connection

    def get_ssh_connection(self, name) -> SSHConnection:
        """
        Getter for the ssh connection
        Args:
            name: the name of the ssh connection to get

        Returns: the ssh connection

        """
        return self.ssh_connection_list.get(name)

    def remove_ssh_connection(self, name):
        """
        Closes the ssh connection and removes it from the list of managed connections
        Args:
            name: the name of the connection

        Returns:

        """
        ssh_connection = self.ssh_connection_list.get(name)
        if ssh_connection:
            ssh_connection.close()
            self.ssh_connection_list.pop(name)

    def remove_all(self):
        """
        Cycles through all managed connections and closes them, then empties the dict
        Returns:

        """
        keys = self.ssh_connection_list.keys()
        for key in keys:
            connection = self.ssh_connection_list.get(key)
            connection.close()

        self.ssh_connection_list.clear()


SSHConnectionManager = SSHConnectionManagerClass()

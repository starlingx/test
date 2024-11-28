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

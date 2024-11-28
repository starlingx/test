from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.host.objects.system_host_if_output import SystemHostInterfaceOutput
from keywords.cloud_platform.system.host.objects.system_host_if_show_output import SystemHostIfShowOutput
from keywords.cloud_platform.system.host.objects.system_host_interface_object import SystemHostInterfaceObject


class SystemHostInterfaceKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system host-if-*' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_host_interface_list(self, hostname) -> SystemHostInterfaceOutput:
        """
        Gets the system host interface list

        Args:
            hostname: Name of the host for which we want to get the interface list.

        Returns:
            SystemHostInterfaceOutput object with the list of interfaces of this host.

        """
        output = self.ssh_connection.send(source_openrc(f'system host-if-list -a --nowrap {hostname}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_interface_output = SystemHostInterfaceOutput(output)

        return system_host_interface_output

    def system_host_interface_show(self, hostname: str, interface_name: str) -> SystemHostInterfaceObject:
        """
        Keyword to get the host interface show object
        Args:
            hostname (): the name of the host
            interface_name (): the interface name

        Returns:

        """
        output = self.ssh_connection.send(source_openrc(f'system host-if-show {hostname} {interface_name}'))
        self.validate_success_return_code(self.ssh_connection)
        system_host_interface_show_output = SystemHostIfShowOutput(output)

        return system_host_interface_show_output.get_system_host_interface_object()

    def system_host_interface_add(self, hostname: str, name: str, if_type: str, iface: str, vf_driver: str = None, ifclass: str = None, num_vfs: int = -1):
        """
        Adds the interface
        Args:
            hostname (): the hostname
            name (): the name of the new interface
            if_type (): the interface type
            iface (): the interface parent
            vf_driver (): the vf driver
            ifclass (): the interface class
            num_vfs (): the number of vfs

        Returns:

        """
        extra_args = ''
        if vf_driver:
            extra_args += f'--vf-driver {vf_driver} '
        if ifclass:
            extra_args += f'--ifclass {ifclass} '
        if num_vfs:
            extra_args += f'--num-vfs {num_vfs} '
        self.ssh_connection.send(source_openrc(f'system host-if-add {hostname} {name} {if_type} {iface} {extra_args}'))
        self.validate_success_return_code(self.ssh_connection)

    def system_interface_delete(self, hostname: str, interface_name: str):
        """
        System interface delete
        Args:
            hostname (): the hostname
            interface_name (): the interface name

        Returns:

        """
        self.ssh_connection.send(source_openrc(f'system host-if-delete {hostname} {interface_name}'))
        self.validate_success_return_code()

    def cleanup_interface(self, hostname: str, interface_name: str):
        """
        Used for teardowns
        Args:
            hostname (): the hostname
            interface_name (): the interface name

        Returns:

        """
        self.ssh_connection.send(source_openrc(f'system host-if-delete {hostname} {interface_name}'))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"interface {interface_name} failed to delete")
        return rc

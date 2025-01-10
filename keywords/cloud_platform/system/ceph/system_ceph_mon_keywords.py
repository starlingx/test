from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.ceph.objects.system_ceph_mon_output import SystemCephMonOutput
from keywords.cloud_platform.system.ceph.objects.system_ceph_mon_show_output import SystemCephMonShowOutput


class SystemCephMonKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system ceph-mon' commands.
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_system_ceph_mon_list(self) -> SystemCephMonOutput:
        """
        Gets the system ceph-mon-list

        Args:

        Returns:
            SystemCephMonOutput object with the list of ceph-mon.

        """
        command = source_openrc(f'system ceph-mon-list')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ceph_mon_output = SystemCephMonOutput(output)
        return system_ceph_mon_output

    def get_system_ceph_mon_show(self, host_id) -> SystemCephMonShowOutput:
        """
        Gets the system ceph-mon-show

        Args:
            host_id: name or id of the host

        Returns:
            SystemCephMonShowOutput object.

        """
        command = source_openrc(f'system ceph-mon-show {host_id}')
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        system_ceph_mon_show_output = SystemCephMonShowOutput(output)
        return system_ceph_mon_show_output
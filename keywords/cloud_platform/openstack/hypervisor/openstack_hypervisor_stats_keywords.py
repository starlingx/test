"""Keywords for openstack hypervisor stats show CLI command."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.hypervisor.object.openstack_hypervisor_stats_output import OpenStackHypervisorStatsOutput
from keywords.openstack.command_wrappers import source_admin_openrc


class OpenStackHypervisorStatsKeywords(BaseKeyword):
    """Class for OpenStack hypervisor stats keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize OpenStackHypervisorStatsKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_openstack_hypervisor_stats(self) -> OpenStackHypervisorStatsOutput:
        """
        Get a OpenstackHypervisorStatsOutput object related to the execution of the 'openstack hypervisor stats show' command.

        Returns:
             OpenstackHypervisorStatsOutput: an instance of the OpenstackHypervisorStatsOutput object representing the
             hypervisor stats on the host, as a result of the execution of the 'openstack hypervisor stats show' command.
        """
        output = self.ssh_connection.send(source_admin_openrc("openstack hypervisor stats show"))
        self.validate_success_return_code(self.ssh_connection)
        openstack_hypervisor_stats_output = OpenStackHypervisorStatsOutput(output)

        return openstack_hypervisor_stats_output

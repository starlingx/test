from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ceph.object.ceph_mgr_services_output import CephMgrServicesOutput


class CephMgrKeywords(BaseKeyword):
    """Keywords for the Ceph manager (mgr)."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to a host with Ceph CLI access.
        """
        self.ssh_connection = ssh_connection

    def get_mgr_services(self) -> CephMgrServicesOutput:
        """Get the services exposed by the active mgr and their URLs.

        Runs 'ceph mgr services'. A service is only listed when its mgr module
        is enabled and serving, so the presence of a service also confirms it
        is running.

        Returns:
            CephMgrServicesOutput: Parsed mapping of service name to URL.
        """
        output = self.ssh_connection.send("ceph mgr services")
        self.validate_success_return_code(self.ssh_connection)
        return CephMgrServicesOutput(output)

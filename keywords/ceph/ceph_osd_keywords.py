from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.ceph.object.ceph_osd_tree_output import CephOsdTreeOutput


class CephOsdKeywords(BaseKeyword):
    """Keywords for inspecting Ceph OSD runtime state via 'ceph osd tree'."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to a host with Ceph CLI access.
        """
        self.ssh_connection = ssh_connection

    def get_ceph_osd_tree(self) -> CephOsdTreeOutput:
        """Run 'ceph osd tree' and return the parsed output.

        Returns:
            CephOsdTreeOutput: Parsed OSD tree with per-OSD status and host.
        """
        output = self.ssh_connection.send("ceph osd tree")
        self.validate_success_return_code(self.ssh_connection)
        return CephOsdTreeOutput(output)

    def wait_for_osds_down_for_host(self, host: str, timeout: int = 120, polling_sleep_time: int = 5) -> None:
        """Wait until all OSDs on a host report down.

        Args:
            host (str): The host name whose OSDs should go down.
            timeout (int): Maximum time to wait in seconds.
            polling_sleep_time (int): Time between checks in seconds.
        """
        validate_equals_with_retry(
            function_to_execute=lambda: self.get_ceph_osd_tree().are_all_osds_down_for_host(host),
            expected_value=True,
            validation_description=f"All OSDs on host '{host}' are down",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

    def wait_for_osds_up_for_host(self, host: str, timeout: int = 300, polling_sleep_time: int = 10) -> None:
        """Wait until all OSDs on a host report up.

        Args:
            host (str): The host name whose OSDs should come up.
            timeout (int): Maximum time to wait in seconds.
            polling_sleep_time (int): Time between checks in seconds.
        """
        validate_equals_with_retry(
            function_to_execute=lambda: self.get_ceph_osd_tree().are_all_osds_up_for_host(host),
            expected_value=True,
            validation_description=f"All OSDs on host '{host}' are up",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

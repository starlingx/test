from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.ceph.object.ceph_status_output import CephStatusOutput


class CephStatusKeywords(BaseKeyword):
    """
    Class for ceph -s Keywords

    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def ceph_status(self) -> CephStatusOutput:
        """
        Run ceph -s command

        Args: None

        Returns: CephStatusOutput

        """
        output = self.ssh_connection.send("ceph -s")
        self.validate_success_return_code(self.ssh_connection)
        ceph_status_output = CephStatusOutput(output)
        return ceph_status_output

    def wait_for_ceph_health_status(self, expect_health_status: bool = None, timeout: int = 1800) -> bool:
        """
        Waits timeout amount of time for ceph to be in the given status

        Args:
            expect_health_status (bool): Ture (HEALTH_OK) or False (HEALTH_WARN)
            timeout (int): the timeout in secs

        Returns:
            bool: True: ceph health status match expect status
                  False: ceph health status not match expect status

        """
        if expect_health_status not in (True, False):
            raise ValueError(f"expect_health_status:{expect_health_status} is not valid.")

        def get_ceph_health_status():
            output = self.ssh_connection.send("ceph -s")
            ceph_status_output = CephStatusOutput(output)
            return ceph_status_output.is_ceph_healthy()

        msg = f"Current ceph health status should match expected status:{expect_health_status}"
        validate_equals_with_retry(get_ceph_health_status, expect_health_status, msg, timeout=timeout)

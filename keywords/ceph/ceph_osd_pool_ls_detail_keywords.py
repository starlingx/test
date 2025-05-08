import time

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ceph.object.ceph_osd_pool_ls_detail_object import CephOsdPoolLsDetailObject
from keywords.ceph.object.ceph_osd_pool_ls_detail_output import CephOsdPoolLsDetailOutput


class CephOsdPoolLsDetailKeywords(BaseKeyword):
    """
    Class for ceph osd pool ls detail keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): SSHConnection
        """
        self.ssh_connection = ssh_connection

    def get_ceph_osd_pool_ls_detail_list(self) -> list[CephOsdPoolLsDetailObject]:
        """
        Gets the "ceph osd pool ls detail" command as a list of `CephOsdPoolLsDetailObject` objects.

        Args: None

        Returns: list of 'CephOsdPoolLsDetailObject' objects.

        """
        output = self.ssh_connection.send("ceph osd pool ls detail")
        self.validate_success_return_code(self.ssh_connection)
        ceph_osd_pool_ls_detail_objects = CephOsdPoolLsDetailOutput(output).get_ceph_osd_pool_list()

        return ceph_osd_pool_ls_detail_objects

    def wait_for_ceph_osd_pool_replicated_size_update(self, pool_name: str, expected_replicated_size: int, timeout: int = 600) -> bool:
        """
        Waits timeout amount of time for "ceph osd pool ls detail" replicated size update

        Args:
            pool_name (str): the pool name
            expected_replicated_size (int): the expected replicated size value
            timeout (int): amount of timeout

        Returns:
            bool: True if the pool replicated size is updated as expected

        """
        output = self.ssh_connection.send("ceph osd pool ls detail")
        pool_object = CephOsdPoolLsDetailOutput(output).get_ceph_osd_pool(pool_name)
        replicated_update_timeout = time.time() + timeout

        while time.time() < replicated_update_timeout:
            ceph_osd_pool_replication_size = pool_object.get_replicated_size()
            if ceph_osd_pool_replication_size == expected_replicated_size:
                return True
            time.sleep(10)

        raise ValueError(f"replicated value is {ceph_osd_pool_replication_size}, not as expected value {expected_replicated_size}")

    def wait_for_ceph_osd_pool_min_size_update(self, pool_name: str, expected_min_size: int, timeout: int = 600) -> bool:
        """
        Waits timeout amount of time for "ceph osd pool ls detail" min_size update

        Args:
            pool_name (str): the pool name
            expected_min_size (int): the expected replicated size value
            timeout (int): amount of timeout

        Returns:
            bool: True if the pool min_size is updated as expected

        """
        output = self.ssh_connection.send("ceph osd pool ls detail")
        pool_object = CephOsdPoolLsDetailOutput(output).get_ceph_osd_pool(pool_name)
        mini_update_timeout = time.time() + timeout

        while time.time() < mini_update_timeout:
            ceph_osd_pool_min_size = pool_object.get_min_size()
            if ceph_osd_pool_min_size == expected_min_size:
                return True
            time.sleep(10)

        raise ValueError(f"replicated value is {ceph_osd_pool_min_size}, not as expected value {expected_min_size}")

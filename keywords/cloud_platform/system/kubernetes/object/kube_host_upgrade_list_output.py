from typing import Dict, List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.kubernetes.object.kube_host_upgrade_object import KubeHostUpgradeObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class KubeHostUpgradeListOutput:
    """Parses the output of 'system kube-host-upgrade-list' into a list of KubeHostUpgradeObject.

    Typical output:
    +----+--------------+-------------+----------------+-----------------------+-----------------+--------+
    | id | hostname     | personality | target_version | control_plane_version | kubelet_version | status |
    +----+--------------+-------------+----------------+-----------------------+-----------------+--------+
    | 1  | controller-0 | controller  | v1.31.5        | v1.31.5               | v1.31.5         | None   |
    | 2  | controller-1 | controller  | v1.32.2        | v1.32.2               | v1.31.5         | ...    |
    +----+--------------+-------------+----------------+-----------------------+-----------------+--------+
    """

    _REQUIRED_KEYS = ["id", "hostname", "personality", "target_version", "control_plane_version", "kubelet_version", "status"]

    def __init__(self, kube_host_upgrade_list_output: list) -> None:
        """Constructor.

        Args:
            kube_host_upgrade_list_output (list): Raw output of 'system kube-host-upgrade-list'.
        """
        self.kube_host_upgrade_list: List[KubeHostUpgradeObject] = []
        system_table_parser = SystemTableParser(kube_host_upgrade_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self._is_valid_output(value):
                host_upgrade = KubeHostUpgradeObject()
                host_upgrade.set_id(value["id"])
                host_upgrade.set_hostname(value["hostname"])
                host_upgrade.set_personality(value["personality"])
                host_upgrade.set_target_version(value["target_version"])
                host_upgrade.set_control_plane_version(value["control_plane_version"])
                host_upgrade.set_kubelet_version(value["kubelet_version"])
                host_upgrade.set_status(value["status"])
                self.kube_host_upgrade_list.append(host_upgrade)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_kube_host_upgrade_list(self) -> List[KubeHostUpgradeObject]:
        """Retrieves the list of parsed kube host upgrade objects.

        Returns:
            List[KubeHostUpgradeObject]: All host upgrade entries.
        """
        return self.kube_host_upgrade_list

    def get_host_upgrade_by_hostname(self, hostname: str) -> KubeHostUpgradeObject:
        """Retrieves a host upgrade entry by hostname.

        Args:
            hostname (str): The hostname to search for.

        Returns:
            KubeHostUpgradeObject: The matching host upgrade entry.

        Raises:
            KeywordException: If no entry is found for the given hostname.
        """
        for host_upgrade in self.kube_host_upgrade_list:
            if host_upgrade.get_hostname() == hostname:
                return host_upgrade
        raise KeywordException(f"No host upgrade entry found for hostname '{hostname}'.")

    def is_hostname_in_list(self, hostname: str) -> bool:
        """Checks if a hostname exists in the host upgrade list.

        Args:
            hostname (str): The hostname to check.

        Returns:
            bool: True if the hostname is found, False otherwise.
        """
        for host_upgrade in self.kube_host_upgrade_list:
            if host_upgrade.get_hostname() == hostname:
                return True
        return False

    @staticmethod
    def _is_valid_output(value: Dict[str, str]) -> bool:
        """Checks if the output contains all required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        for key in KubeHostUpgradeListOutput._REQUIRED_KEYS:
            if key not in value:
                get_logger().log_error(f"{key} is not in the output value: {value}")
                return False
        return True

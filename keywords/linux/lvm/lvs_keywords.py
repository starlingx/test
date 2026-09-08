"""Module for the 'lvs' command keywords."""

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_greater_than_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.linux.lvm.objects.lvs_output import LvsOutput


class LvsKeywords(BaseKeyword):
    """This class contains all the keywords related to the 'lvs' command."""

    SEPARATOR = "|"
    LVS_FIELDS = "lv_name,vg_name,lv_attr,lv_size,pool_lv,origin,data_percent,metadata_percent"

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize the LvsKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_lvs(self) -> LvsOutput:
        """
        Run 'lvs' and return the parsed output.

        Uses '--noheadings', an explicit '--separator' and a fixed column list
        so the output is stable and unambiguous to parse.

        Returns:
            LvsOutput: the parsed 'lvs' output.
        """
        cmd = f"lvs --noheadings --separator '{self.SEPARATOR}' -o {self.LVS_FIELDS}"
        output = self.ssh_connection.send_as_sudo(cmd)
        return LvsOutput(output, separator=self.SEPARATOR)

    def wait_for_lv_data_percent_above(self, lv_name: str, threshold: float = 0.0, timeout: int = 180, polling_interval: int = 10) -> None:
        """
        Wait for a logical volume's data usage percentage to exceed the given threshold.

        Args:
            lv_name (str): the name of the logical volume (e.g. 'lvmcsi-pool').
            threshold (float): the data usage percentage that must be exceeded.
            timeout (int): maximum time to wait in seconds.
            polling_interval (int): time between checks in seconds.

        Raises:
            TimeoutError: If the data usage does not exceed the threshold within the timeout.
        """

        def get_data_percent() -> float:
            return self.get_lvs().get_logical_volume(lv_name).get_data_percent()

        validate_greater_than_with_retry(get_data_percent, threshold, f"logical volume '{lv_name}' data usage to exceed {threshold}%", timeout=timeout, polling_sleep_time=polling_interval)

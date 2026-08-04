"""Software deploy precheck keywords."""

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.upgrade.objects.precheck_item import PrecheckItem
from keywords.cloud_platform.upgrade.objects.software_deploy_precheck_output import SoftwareDeployPrecheckOutput


class SoftwareDeployPrecheckKeywords(BaseKeyword):
    """
    Keywords for 'software deploy precheck' using the ACE object-output model.

    This class:
        - runs the 'software deploy precheck' command
        - wraps the CLI output into SoftwareDeployPrecheckOutput
        - performs additional cross-checks against system state
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Instance of the class.

        Args:
            ssh_connection (SSHConnection): An instance of SSH connection.
        """
        self.ssh_connection = ssh_connection
        self.usm_config = ConfigurationManager.get_usm_config()

    def _run_deploy_precheck(self, targets: str, sudo: bool = False) -> SoftwareDeployPrecheckOutput:
        """
        Run the 'software deploy precheck' command and return its parsed output.

        Args:
            targets (str): Arguments to pass to the command. Empty string runs with no arguments.
            sudo (bool): Option to pass the command with sudo.

        Returns:
            SoftwareDeployPrecheckOutput: Parsed precheck output.
        """
        get_logger().log_info(f"Prechecking deploy software: {targets or '(selected metapackages)'}")
        snapshot_flag = " --options snapshot=true" if self.usm_config.get_snapshot() else ""
        base_cmd = f"software deploy precheck{snapshot_flag} {targets}".strip()
        cmd = source_openrc(base_cmd)
        timeout = self.usm_config.get_precheck_timeout_sec()

        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, command_timeout=timeout, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, command_timeout=timeout, reconnect_timeout=timeout, get_pty=True)

        # Wrap the output into the object-output model.
        precheck_output = SoftwareDeployPrecheckOutput(output)
        return precheck_output

    def deploy_precheck(self, release_id: str | None = None, sudo: bool = False) -> SoftwareDeployPrecheckOutput:
        """
        Run the deploy precheck for a software release and validate its result.

        Target resolution from usm_config.get_metapackages():
            - "All": passes release_id (software deploy precheck <release_id>)
            - list: passes the listed metapackages (software deploy precheck <pkg1> <pkg2> ...)
            - "None" or release_id is None: no arguments (software deploy precheck)

        Args:
            release_id (str | None): Used when metapackages is "All". Ignored otherwise.
            sudo (bool): Option to pass the command with sudo.

        Returns:
            SoftwareDeployPrecheckOutput: Parsed and validated precheck output.

        Raises:
            Exception: If any health check fails or any metapackage is unhealthy.
        """
        metapackages = self.usm_config.get_metapackages()
        if isinstance(metapackages, list):
            targets = " ".join(metapackages)
        elif metapackages == "All" and release_id:
            targets = release_id
        else:
            targets = ""

        precheck_output = self._run_deploy_precheck(targets, sudo=sudo)

        failed_items = precheck_output.get_failed_items()
        validate_equals(failed_items, [], "Deploy precheck: no failed health checks")
        validate_equals(precheck_output.has_unhealthy_metapackages(), False, "Deploy precheck: no unhealthy metapackages")

        get_logger().log_info("Deploy precheck completed:\n" + "\n".join(precheck_output.get_raw_output()))

        return precheck_output

    def get_precheck_item_status(self, release_id: str, check: PrecheckItem, sudo: bool = False) -> bool | None:
        """
        Run 'software deploy precheck' and return the status of a specific check item.

        This method runs the precheck command and looks for the specified check
        item in the output. It uses partial matching to handle items with dynamic
        content (e.g., version numbers, release names).

        Args:
            release_id (str): Release to be prechecked.
            check (PrecheckItem): The specific precheck item to look for.
            sudo (bool): Option to pass the command with sudo.

        Returns:
            bool | True if the item status is [OK], False if the item exists
                but is not [OK], None if the item is not found in the output or
                the precheck command failed.

        Raises:
            KeywordException: If the release_id is missing.
        """
        if not release_id:
            raise KeywordException("Missing release ID for software deploy precheck")

        get_logger().log_info(f"Running deploy precheck to check '{check.value}' for release: {release_id}")
        base_cmd = f"software deploy precheck {release_id}"
        cmd = source_openrc(base_cmd)
        timeout = self.usm_config.get_precheck_timeout_sec()

        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, command_timeout=timeout, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, command_timeout=timeout, reconnect_timeout=timeout, get_pty=True)

        precheck_output = SoftwareDeployPrecheckOutput(output)

        # Use partial match since some precheck items have dynamic content
        # (e.g., version numbers, release names) appended to the static prefix.
        for item_name, item_status in precheck_output.get_status_dict().items():
            if check.value in item_name:
                is_ok = "[OK]" in item_status
                get_logger().log_info(f"Precheck item '{check.value}' status: {item_status}")
                return is_ok

        get_logger().log_info(f"Precheck item '{check.value}' not found in output")
        return None
        
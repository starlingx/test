from wrcp.keywords.cloud_platform.software.patch.software_patch_keywords import SwPatchQueryKeywords

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from starlingx.keywords.cloud_platform.ansible_playbook.object.software_state_output import SoftwareStateOutput
from starlingx.keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from starlingx.keywords.cloud_platform.version_info.cloud_platform_software_version import CloudPlatformSoftwareVersion
from starlingx.keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManager


class SoftwareStateKeywords(BaseKeyword):
    """Query and summarise the patch / software state of a StarlingX controller."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialise the helper.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
        """
        self.ssh_connection = ssh_connection
        self.patch_keywords = SwPatchQueryKeywords(ssh_connection)
        self.software_list_keywords = SoftwareListKeywords(ssh_connection)

    def get_patch_state(self) -> SoftwareStateOutput:
        """Return the current patch / software state."""
        sw_version = CloudPlatformVersionManager.get_sw_version()
        get_logger().log_info(f"sw_version: {sw_version}, name: {sw_version.get_name()}, id: {sw_version.get_id()}")

        if sw_version.is_after_or_equal_to(CloudPlatformSoftwareVersion.STARLINGX_10_0):
            patch_states = self._get_software_list_state()
        else:
            patch_states = self._get_sw_patch_query_state()

        return SoftwareStateOutput(patch_states)

    def _get_sw_patch_query_state(self) -> dict:
        """Fetch patch state by running ``sw-patch query``."""
        patch_query = self.patch_keywords.get_sw_patch_query()
        patches = patch_query.get_patches()
        if not patches:
            get_logger().log_info("No patches found")
            return {}

        states = {patch.patch_id: patch.state for patch in patches}
        return states

    def _get_software_list_state(self) -> dict:
        """Fetch patch state by running ``software list``."""
        software_list_output = self.software_list_keywords.get_software_list()
        states = {entry["Release"]: entry["State"] for entry in software_list_output.output_values}
        return states

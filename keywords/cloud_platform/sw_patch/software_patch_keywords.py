"""Module containing keyword functions for querying software patches."""

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_sudo_openrc
from keywords.cloud_platform.sw_patch.objects.query_output import SwPatchQueryOutput

class SwPatchQueryKeywords(BaseKeyword):
    """Provides keyword functions for software patch queries."""

    def __init__(self, ssh_connection):
        """Initializes SwPatchQueryKeywords with an SSH connection.

        Args:
            ssh_connection: SSH connection to the target system.
        """
        self.ssh_connection = ssh_connection

    def get_sw_patch_query(self) -> SwPatchQueryOutput:
        """Executes the `sw-patch query` command and returns the parsed output.

        Returns:
            SwPatchQueryOutput: Parsed output containing software patches.
        """
        cmd_out = self.ssh_connection.send('/usr/sbin/sw-patch query')
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("get_sw_patch_query")
        sw_query_output = SwPatchQueryOutput(cmd_out)
        return sw_query_output

    def sw_patch_upload(self, region_name, patch_file_path) -> str:
        """Uploads a software patch to the system.

            This function executes the `sw-patch upload` command to upload a patch
            file. If a region name is provided, the command includes the
            `--os-region-name` flag.

            Args:
                region_name (str, optional): The target system's region name.
                patch_file_path (str): The full path to the patch file to upload.

        Returns:
            str: The command output after attempting to upload the patch.
        """
        command = f'/usr/sbin/sw-patch upload {patch_file_path}'
        if region_name:
            command = f'/usr/sbin/sw-patch --os-region-name {region_name} upload {patch_file_path}'

        # command should run by sudo user
        get_logger().log_info(f"Executing patch upload: {command}")
        cmd_out = self.ssh_connection.send_as_sudo(source_sudo_openrc(command))
        get_logger().log_info(f"Patch upload command output: {cmd_out}")
        self.validate_success_return_code(self.ssh_connection)
        return cmd_out[0].strip('\n')

    def sw_patch_apply(self, patch_name) -> str:
        """Apply a software patch to the system.

        Args:
            patch_name: The patch file to apply.

        Returns:
            str: The command output after attempting to apply the patch.
        """
        command = f'/usr/sbin/sw-patch apply {patch_name}'

        # command should run by sudo user
        get_logger().log_info(f"Executing patch apply: {command}")
        cmd_out = self.ssh_connection.send_as_sudo(source_sudo_openrc(command))
        get_logger().log_info(f"Patch apply command output: {cmd_out}")
        self.validate_success_return_code(self.ssh_connection)
        return cmd_out[0].strip('\n')

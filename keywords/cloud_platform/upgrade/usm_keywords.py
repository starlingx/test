from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.upgrade.objects.software_upload_output import SoftwareUploadOutput
from keywords.cloud_platform.upgrade.software_show_keywords import SoftwareShowKeywords


class USMKeywords(BaseKeyword):
    """
    Keywords for USM software operations.

    Supports: commands for upgrade and patch management.
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def upload_patch_file(self, patch_file_path: str) -> SoftwareUploadOutput:
        """
        Upload a single patch file using 'software upload'.

        Args:
            patch_file_path (str): Absolute path to a .patch file.

        Raises:
            KeywordException: On failure to upload.

        Returns:
            SoftwareUploadOutput: Parsed output containing details of the uploaded patch.
        """
        get_logger().log_info(f"Uploading patch file: {patch_file_path}")
        output = self.ssh_connection.send_as_sudo(f"software upload {patch_file_path}")
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("Upload completed:\n" + "\n".join(output))
        return SoftwareUploadOutput(output)

    def upload_patch_dir(self, patch_dir_path: str) -> None:
        """
        Upload all patches in a directory using 'software upload-dir'.

        Args:
            patch_dir_path (str): Absolute path to a directory of .patch files.

        Raises:
            KeywordException: On failure to upload.
        """
        get_logger().log_info(f"Uploading patch directory: {patch_dir_path}")
        output = self.ssh_connection.send_as_sudo(f"software upload-dir {patch_dir_path}")
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("Upload directory completed:\n" + "\n".join(output))

    def show_software_release(self, release_id: str) -> list[str]:
        """
        Show info for a specific release using 'software show'.

        Args:
            release_id (str): ID of the release (e.g., "starlingx-10.0.0")

        Returns:
            list[str]: Raw output lines.

        Raises:
            KeywordException: If release_id is missing or the command fails.
        """
        if not release_id:
            raise KeywordException("Missing release ID for software show")

        get_logger().log_info(f"Showing software release: {release_id}")
        output = self.ssh_connection.send_as_sudo(f"software show {release_id}")
        self.validate_success_return_code(self.ssh_connection)
        return output

    def upload_release(self, iso_path: str, sig_path: str) -> None:
        """
        Upload a full software release using 'software upload'.

        Args:
            iso_path (str): Absolute path to the .iso file.
            sig_path (str): Absolute path to the corresponding .sig file.

        Raises:
            KeywordException: On failure to upload.
        """
        get_logger().log_info(f"Uploading software release: ISO={iso_path}, SIG={sig_path}")
        cmd = f"software upload {iso_path} {sig_path}"
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("Release upload completed:\n" + "\n".join(output))

    def upload_and_verify_patch_file(self, patch_file_path: str, expected_release_id: str, timeout: int, poll_interval: int) -> None:
        """Upload a patch and verify that it becomes available.

        This method is used for USM patching operations. It uploads a `.patch` file
        using `software upload` and polls for the corresponding release ID to appear
        with state "available" using `software show`.

        Args:
            patch_file_path (str): Absolute path to the `.patch` file.
            expected_release_id (str): Expected release ID after patch upload.
            timeout (int): Maximum number of seconds to wait for the release to appear.
            poll_interval (int): Interval (in seconds) between poll attempts.

        Raises:
            KeywordException: If upload fails or release does not become available in time.
        """
        self.upload_patch_file(patch_file_path)

        validate_equals_with_retry(
            function_to_execute=lambda: SoftwareShowKeywords(self.ssh_connection).get_release_state(expected_release_id),
            expected_value="available",
            validation_description=f"Wait for patch release {expected_release_id} to become available",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )

    def upload_and_verify_release(self, iso_path: str, sig_path: str, expected_release_id: str, timeout: int, poll_interval: int) -> None:
        """Upload a software release and verify that it becomes available.

        This method is used for USM upgrade operations. It uploads a `.iso` and `.sig`
        pair using `software upload` and waits for the release ID to appear with
        state "available" using `software show`.

        Args:
            iso_path (str): Absolute path to the `.iso` file.
            sig_path (str): Absolute path to the `.sig` signature file.
            expected_release_id (str): Expected release ID after upload.
            timeout (int): Maximum number of seconds to wait for the release to appear.
            poll_interval (int): Interval (in seconds) between poll attempts.

        Raises:
            KeywordException: If upload fails or release does not become available in time.
        """
        self.upload_release(iso_path, sig_path)

        validate_equals_with_retry(
            function_to_execute=lambda: SoftwareShowKeywords(self.ssh_connection).get_release_state(expected_release_id),
            expected_value="available",
            validation_description=f"Wait for release {expected_release_id} to become available",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )

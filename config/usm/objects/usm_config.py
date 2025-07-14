import json5


class USMConfig:
    """
    Encapsulates configuration for USM upgrade and patch operations.

    Call `validate_config()` after setting fields to ensure configuration consistency.
    """

    def __init__(self, config_path: str):
        """
        Load and parse the USM config file and validate contents.

        Args:
            config_path (str): Path to the JSON5 USM config file.

        Raises:
            FileNotFoundError: If the config file cannot be found.
            ValueError: If any required field is invalid.
        """
        try:
            with open(config_path) as f:
                usm_dict = json5.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not find USM config file: {config_path}")

        self.usm_operation_type = usm_dict.get("usm_operation_type")
        self.requires_reboot = usm_dict.get("requires_reboot")
        self.copy_from_remote = usm_dict.get("copy_from_remote")
        self.iso_path = usm_dict.get("iso_path")
        self.sig_path = usm_dict.get("sig_path")
        self.patch_path = usm_dict.get("patch_path")
        self.patch_dir = usm_dict.get("patch_dir")
        self.dest_dir = usm_dict.get("dest_dir")
        self.to_release_ids = usm_dict.get("to_release_ids")
        self.remote_server = usm_dict.get("remote_server")
        self.remote_server_username = usm_dict.get("remote_server_username")
        self.remote_server_password = usm_dict.get("remote_server_password")
        self.upgrade_arguments = usm_dict.get("upgrade_arguments")
        self.upload_poll_interval_sec = usm_dict.get("upload_poll_interval_sec")
        self.upload_timeout_sec = usm_dict.get("upload_timeout_sec")

        self.validate_config()

    def validate_config(self) -> None:
        """
        Validate config values for logical consistency.

        This includes:
        - Checking operation type is either 'upgrade' or 'patch'.
        - Ensuring expected release IDs are present.
        - Validating required fields for remote copy.
        - Confirming ISO/SIG or patch fields based on operation type.

        Raises:
            ValueError: If any config field is missing or inconsistent.
        """
        if self.usm_operation_type not in ("upgrade", "patch"):
            raise ValueError("Invalid usm_operation_type: must be 'upgrade' or 'patch'")

        if not isinstance(self.to_release_ids, list) or not self.to_release_ids:
            raise ValueError("to_release_ids must be a non-empty list")

        if self.copy_from_remote:
            if not (self.remote_server and self.remote_server_username and self.remote_server_password):
                raise ValueError("Remote server credentials required when copy_from_remote is true")

        if self.usm_operation_type == "upgrade":
            if not self.iso_path or not self.sig_path:
                raise ValueError("Upgrade requires source_iso_path and source_sig_path")

        if self.usm_operation_type == "patch":
            if not self.patch_path and not self.patch_dir:
                raise ValueError("Patch requires either patch_path or patch_dir")

    def get_usm_operation_type(self) -> str:
        """Get the USM operation type.

        Returns:
            str: Either "upgrade" or "patch".
        """
        return self.usm_operation_type

    def set_usm_operation_type(self, value: str) -> None:
        """Set the USM operation type.

        Args:
            value (str): Either "upgrade" or "patch".
        """
        self.usm_operation_type = value

    def get_requires_reboot(self) -> bool:
        """Get whether a reboot is required after operation.

        Returns:
            bool: True if a reboot is required.
        """
        return self.requires_reboot

    def set_requires_reboot(self, value: bool) -> None:
        """Set whether a reboot is required after operation.

        Args:
            value (bool): True if reboot is required.
        """
        self.requires_reboot = value

    def get_copy_from_remote(self) -> bool:
        """Check if files should be copied from a remote server.

        Returns:
            bool: True if ISO/SIG or patch files should be pulled from a remote build server.
        """
        return self.copy_from_remote

    def set_copy_from_remote(self, value: bool) -> None:
        """Specify whether to copy files from a remote build server.

        Args:
            value (bool): True to copy files from remote, False if they already exist on the controller.
        """
        self.copy_from_remote = value

    def get_iso_path(self) -> str:
        """Get the path to the ISO file.

        Returns:
            str: Absolute path to the ISO file for upgrade.
        """
        return self.iso_path

    def set_iso_path(self, value: str) -> None:
        """Set the path to the ISO file.

        Args:
            value (str): Absolute path to the ISO file.
        """
        self.iso_path = value

    def get_sig_path(self) -> str:
        """Get the path to the signature file.

        Returns:
            str: Absolute path to the SIG file.
        """
        return self.sig_path

    def set_sig_path(self, value: str) -> None:
        """Set the path to the signature file.

        Args:
            value (str): Absolute path to the SIG file.
        """
        self.sig_path = value

    def get_patch_path(self) -> str:
        """Get the path to a single patch file.

        Returns:
            str: Absolute path to a single .patch file.
        """
        return self.patch_path

    def set_patch_path(self, value: str) -> None:
        """Set the path to a single patch file.

        Args:
            value (str): Absolute path to a single .patch file.
        """
        self.patch_path = value

    def get_patch_dir(self) -> str:
        """Get the path to a patch directory.

        Returns:
            str: Directory containing multiple .patch files.
        """
        return self.patch_dir

    def set_patch_dir(self, value: str) -> None:
        """Set the path to a patch directory.

        Args:
            value (str): Directory containing multiple .patch files.
        """
        self.patch_dir = value

    def get_dest_dir(self) -> str:
        """Get the destination directory on the controller.

        Returns:
            str: Directory where ISO/SIG or patch files will be copied.
        """
        return self.dest_dir

    def set_dest_dir(self, value: str) -> None:
        """Set the destination directory on the controller.

        Args:
            value (str): Path on controller where files will be copied.
        """
        self.dest_dir = value

    def get_to_release_ids(self) -> list[str]:
        """Get the expected release IDs.

        Returns:
            list[str]: List of release versions used to validate success.
        """
        return self.to_release_ids

    def set_to_release_ids(self, value: list[str]) -> None:
        """Set the expected release IDs.

        Args:
            value (list[str]): One or more release version strings.
        """
        self.to_release_ids = value

    def get_remote_server(self) -> str:
        """Get the remote server address.

        Returns:
            str: Hostname or IP of the remote server.
        """
        return self.remote_server

    def set_remote_server(self, value: str) -> None:
        """Set the remote server address.

        Args:
            value (str): Hostname or IP of the remote server.
        """
        self.remote_server = value

    def get_remote_server_username(self) -> str:
        """Get the remote server username.

        Returns:
            str: Username for authenticating with the remote server.
        """
        return self.remote_server_username

    def set_remote_server_username(self, value: str) -> None:
        """Set the remote server username.

        Args:
            value (str): Username for authenticating with the remote server.
        """
        self.remote_server_username = value

    def get_remote_server_password(self) -> str:
        """Get the remote server password.

        Returns:
            str: Password for authenticating with the remote server.
        """
        return self.remote_server_password

    def set_remote_server_password(self, value: str) -> None:
        """Set the remote server password.

        Args:
            value (str): Password for authenticating with the remote server.
        """
        self.remote_server_password = value

    def get_upgrade_arguments(self) -> str:
        """Get optional CLI arguments for upload or upgrade.

        Returns:
            str: Extra CLI flags like "--force".
        """
        return self.upgrade_arguments

    def set_upgrade_arguments(self, value: str) -> None:
        """Set optional CLI arguments for upload or upgrade.

        Args:
            value (str): Extra CLI flags like "--force".
        """
        self.upgrade_arguments = value

    def get_upload_poll_interval_sec(self) -> int:
        """Get polling interval for upload progress.

        Returns:
            int: Number of seconds between upload status checks.
        """
        return self.upload_poll_interval_sec

    def set_upload_poll_interval_sec(self, value: int) -> None:
        """Set polling interval for upload progress.

        Args:
            value (int): Number of seconds between upload status checks.
        """
        self.upload_poll_interval_sec = value

    def get_upload_timeout_sec(self) -> int:
        """Get timeout duration for upload completion.

        Returns:
            int: Maximum seconds to wait for upload to complete.
        """
        return self.upload_timeout_sec

    def set_upload_timeout_sec(self, value: int) -> None:
        """Set timeout duration for upload completion.

        Args:
            value (int): Maximum seconds to wait for upload to complete.
        """
        self.upload_timeout_sec = value

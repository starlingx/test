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

        self.usm_operation_type = usm_dict.get("usm_operation_type", "upgrade")
        self.requires_reboot = usm_dict.get("requires_reboot", False)
        self.copy_from_remote = usm_dict.get("copy_from_remote", False)
        self.iso_path = usm_dict.get("iso_path", "")
        self.sig_path = usm_dict.get("sig_path", "")
        self.patch_path = usm_dict.get("patch_path", "")
        self.patch_dir = usm_dict.get("patch_dir", "")
        self.dest_dir = usm_dict.get("dest_dir", "/scratch/usm_files/")
        self.to_release_ids = usm_dict.get("to_release_ids", [])
        self.remote_server = usm_dict.get("remote_server", "")
        self.remote_username = usm_dict.get("remote_username", "")
        self.remote_password = usm_dict.get("remote_password", "")
        self.snapshot = usm_dict.get("snapshot", False)
        self.rollback = usm_dict.get("rollback", False)
        self.deploy_delete = usm_dict.get("deploy_delete", False)
        self.record_kpi = usm_dict.get("record_kpi", False)
        self.deployment_timeout_sec = usm_dict.get("deployment_timeout_sec", 7200)
        self.activation_timeout_sec = usm_dict.get("activation_timeout_sec", 3600)
        self.upgrade_arguments = usm_dict.get("upgrade_arguments", "")
        self.upload_poll_interval_sec = usm_dict.get("upload_poll_interval_sec", 30)
        self.upload_patch_timeout_sec = usm_dict.get("upload_patch_timeout_sec", 1800)
        self.upload_release_timeout_sec = usm_dict.get("upload_release_timeout_sec", 1800)
        self.precheck_timeout_sec = usm_dict.get("precheck_timeout_sec", 300)
        self.software_delete_timeout_sec = usm_dict.get("software_delete_timeout_sec", 300)
        self.deploy_delete_timeout_sec = usm_dict.get("deploy_delete_timeout_sec", 300)
        self.deploy_start_timeout_sec = usm_dict.get("deploy_start_timeout_sec", 1200)

    def validate_config(self) -> None:
        """
        Validate config values for logical consistency.

        This includes:
        - Checking operation type is either 'upgrade' or 'patch'.
        - Ensuring expected release IDs are present.
        - Validating required fields for remote copy.
        - Confirming ISO/SIG or patch fields based on operation type.
        - Validating timeout values are positive integers.

        Raises:
            ValueError: If any config field is missing or inconsistent.
        """
        if self.usm_operation_type not in ("upgrade", "patch"):
            raise ValueError("Invalid usm_operation_type: must be 'upgrade' or 'patch'")

        if not isinstance(self.to_release_ids, list) or not self.to_release_ids:
            raise ValueError("to_release_ids must be a non-empty list")

        if self.copy_from_remote:
            if not (self.remote_server and self.remote_username and self.remote_password):
                raise ValueError("Remote server credentials required when copy_from_remote is true")

        if self.usm_operation_type == "upgrade":
            if not self.iso_path or not self.sig_path:
                raise ValueError("Upgrade requires iso_path and sig_path")

        if self.usm_operation_type == "patch":
            if not self.patch_path and not self.patch_dir:
                raise ValueError("Patch requires either patch_path or patch_dir")

        # Validate timeout values
        if self.deployment_timeout_sec <= 0:
            raise ValueError("deployment_timeout_sec must be positive")
        if self.activation_timeout_sec <= 0:
            raise ValueError("activation_timeout_sec must be positive")
        if self.upload_patch_timeout_sec <= 0:
            raise ValueError("upload_patch_timeout_sec must be positive")
        if self.upload_release_timeout_sec <= 0:
            raise ValueError("upload_release_timeout_sec must be positive")
        if self.upload_poll_interval_sec <= 0:
            raise ValueError("upload_poll_interval_sec must be positive")

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

    def get_remote_username(self) -> str:
        """Get the remote username.

        Returns:
            str: Username for authenticating with the remote server.
        """
        return self.remote_username

    def set_remote_username(self, value: str) -> None:
        """Set the remote username.

        Args:
            value (str): Username for authenticating with the remote server.
        """
        self.remote_username = value

    def get_remote_password(self) -> str:
        """Get the remote password.

        Returns:
            str: Password for authenticating with the remote server.
        """
        return self.remote_password

    def set_remote_password(self, value: str) -> None:
        """Set the remote password.

        Args:
            value (str): Password for authenticating with the remote server.
        """
        self.remote_password = value

    def get_snapshot(self) -> bool:
        """Check if snapshot is enabled.

        Returns:
            bool: True if snapshot enabled, False otherwise.
        """
        return self.snapshot

    def set_snapshot(self, value: bool) -> None:
        """Set if snapshot is enabled.

        Args:
            value (bool): True if snapshot enabled, False otherwise.
        """
        self.snapshot = value

    def get_rollback(self) -> bool:
        """Check if rollback is enabled.

        Returns:
            bool: True if rollback enabled, False otherwise.
        """
        return self.rollback

    def set_rollback(self, value: bool) -> None:
        """Set if rollback is enabled.

        Args:
            value (bool): True if rollback enabled, False otherwise.
        """
        self.rollback = value

    def get_deploy_delete(self) -> bool:
        """Check if deploy delete flag is enabled.

        Returns:
            bool: True if deploy delete is enabled, False otherwise.
        """
        return self.deploy_delete

    def set_deploy_delete(self, value: bool) -> None:
        """Set if deploy delete flag is enabled.

        Args:
            value (bool): True if deploy delete is enabled, False otherwise.
        """
        self.deploy_delete = value

    def get_record_kpi(self) -> bool:
        """Check if KPI recording is enabled.

        Returns:
            bool: True if KPI recording is enabled, False otherwise.
        """
        return self.record_kpi

    def set_record_kpi(self, value: bool) -> None:
        """Set if KPI recording is enabled.

        Args:
            value (bool): True if KPI recording is enabled, False otherwise.
        """
        self.record_kpi = value

    def get_deployment_timeout_sec(self) -> int:
        """Get the deployment timeout in seconds.

        Returns:
            int: Deployment timeout in seconds.
        """
        return self.deployment_timeout_sec

    def set_deployment_timeout_sec(self, value: int) -> None:
        """Set the deployment timeout in seconds.

        Args:
            value (int): Deployment timeout in seconds.
        """
        self.deployment_timeout_sec = value

    def get_activation_timeout_sec(self) -> int:
        """Get the activation timeout in seconds.

        Returns:
            int: Activation timeout in seconds.
        """
        return self.activation_timeout_sec

    def set_activation_timeout_sec(self, value: int) -> None:
        """Set the activation timeout in seconds.

        Args:
            value (int): Activation timeout in seconds.
        """
        self.activation_timeout_sec = value

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

    def get_upload_patch_timeout_sec(self) -> int:
        """Get timeout duration for patch upload completion.

        Returns:
            int: Maximum seconds to wait for patch upload to complete.
        """
        return self.upload_patch_timeout_sec

    def set_upload_patch_timeout_sec(self, value: int) -> None:
        """Set timeout duration for patch upload completion.

        Args:
            value (int): Maximum seconds to wait for patch upload to complete.
        """
        self.upload_patch_timeout_sec = value

    def get_upload_release_timeout_sec(self) -> int:
        """Get timeout duration for release upload completion.

        Returns:
            int: Maximum seconds to wait for release upload to complete.
        """
        return self.upload_release_timeout_sec

    def set_upload_release_timeout_sec(self, value: int) -> None:
        """Set timeout duration for release upload completion.

        Args:
            value (int): Maximum seconds to wait for release upload to complete.
        """
        self.upload_release_timeout_sec = value

    def get_precheck_timeout_sec(self) -> int:
        """Get timeout duration for deploy precheck completion.

        Returns:
            int: Maximum seconds to wait for deploy precheck to complete.
        """
        return self.precheck_timeout_sec

    def set_precheck_timeout_sec(self, value: int) -> None:
        """Set timeout duration for release upload completion.

        Args:
            value (int): Maximum seconds to wait for release upload to complete.
        """
        self.precheck_timeout_sec = value

    def get_software_delete_timeout_sec(self) -> int:
        """Get timeout duration for software delete completion.

        Returns:
            int: Maximum seconds to wait for software delete to complete.
        """
        return self.software_delete_timeout_sec

    def set_software_delete_timeout_sec(self, value: int) -> None:
        """Set timeout duration for software delete completion.

        Args:
            value (int): Maximum seconds to wait for software delete to complete.
        """
        self.software_delete_timeout_sec = value

    def get_deploy_delete_timeout_sec(self) -> int:
        """Get timeout duration for software deploy delete completion.

        Returns:
            int: Maximum seconds to wait for software deploy delete to complete.
        """
        return self.deploy_delete_timeout_sec

    def set_deploy_delete_timeout_sec(self, value: int) -> None:
        """Set timeout duration for software deploy delete completion.

        Args:
            value (int): Maximum seconds to wait for software deploy delete to complete.
        """
        self.deploy_delete_timeout_sec = value

    def get_deploy_start_timeout_sec(self) -> int:
        """Get timeout duration for software deploy start completion.

        Returns:
            int: Maximum seconds to wait for software deploy start to complete.
        """
        return self.deploy_start_timeout_sec

    def set_deploy_start_timeout_sec(self, value: int) -> None:
        """Set timeout duration for software deploy start completion.

        Args:
            value (int): Maximum seconds to wait for software deploy start to complete.
        """
        self.deploy_start_timeout_sec = value

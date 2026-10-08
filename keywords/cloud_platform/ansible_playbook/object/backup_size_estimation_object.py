from typing import Optional


class BackupSizeEstimationObject:
    """Holds the individual values of a single platform backup size-estimation record.

    This is a plain data holder populated by ``BackupSizeEstimationOutput`` from the
    ansible ``-vv`` log. It carries the dc-vault ``du`` command and size, the cumulative
    platform size estimation, the available disk size, and whether the free-space
    pre-check gate passed.

    The getters raise when a value was never captured, so callers that need to probe for
    presence (e.g. to decide whether to re-parse from another source) should use
    ``has_dc_vault_size()`` / ``has_available_disk_size()`` or ``is_complete()`` instead.
    """

    def __init__(self, dc_vault_permdir: str = "/opt/dc-vault"):
        """Initialise an empty estimation record.

        Args:
            dc_vault_permdir (str): The dc-vault path the playbook measures. Defaults to "/opt/dc-vault".
        """
        self.dc_vault_permdir = dc_vault_permdir
        self.dc_vault_du_command: Optional[str] = None
        self.dc_vault_size_kib: Optional[int] = None
        self.total_platform_size_estimation: Optional[int] = None
        self.available_disk_size_kib: Optional[int] = None
        self.space_precheck_passed: Optional[bool] = None

    def set_dc_vault_du_command(self, dc_vault_du_command: str) -> None:
        """Set the dc-vault ``du`` command string.

        Args:
            dc_vault_du_command (str): The command string parsed from the log.
        """
        self.dc_vault_du_command = dc_vault_du_command

    def set_dc_vault_size_kib(self, dc_vault_size_kib: int) -> None:
        """Set the dc-vault size (KiB).

        Args:
            dc_vault_size_kib (int): dc-vault size in KiB.
        """
        self.dc_vault_size_kib = dc_vault_size_kib

    def set_total_platform_size_estimation(self, total_platform_size_estimation: int) -> None:
        """Set the cumulative platform size estimation (KiB).

        Args:
            total_platform_size_estimation (int): Estimated required disk size in KiB.
        """
        self.total_platform_size_estimation = total_platform_size_estimation

    def set_available_disk_size_kib(self, available_disk_size_kib: int) -> None:
        """Set the available disk size in the backup dir (KiB).

        Args:
            available_disk_size_kib (int): Available disk size in KiB.
        """
        self.available_disk_size_kib = available_disk_size_kib

    def set_space_precheck_passed(self, space_precheck_passed: bool) -> None:
        """Set whether the free-space pre-check gate passed (was skipped).

        Args:
            space_precheck_passed (bool): True if the "not enough free space" fail task was skipped.
        """
        self.space_precheck_passed = space_precheck_passed

    def get_dc_vault_du_command(self) -> str:
        """Return the dc-vault ``du`` command string parsed from the log.

        Returns:
            str: The command string.

        Raises:
            ValueError: If the dc-vault du command was not found in the log.
        """
        if self.dc_vault_du_command is None:
            raise ValueError("dc-vault du command was not found in the ansible log")
        return self.dc_vault_du_command

    def is_dc_vault_exclude_applied(self, excluded_dir: str) -> bool:
        """Return whether the dc-vault ``du`` applied ``--exclude`` for a directory.

        On a load that applies exclusions to the dc-vault size command, the command
        carries ``--exclude '<excluded_dir>'``; if it does not, the exclusion was not
        applied to the estimate.

        Args:
            excluded_dir (str): The excluded directory to look for (e.g. "/opt/dc-vault/backups").

        Returns:
            bool: True if the dc-vault du command excluded the directory.
        """
        if self.dc_vault_du_command is None:
            return False
        return f"--exclude '{excluded_dir}'" in self.dc_vault_du_command or f"--exclude {excluded_dir}" in self.dc_vault_du_command

    def get_dc_vault_size_kib(self) -> int:
        """Return the dc-vault size (KiB) the playbook computed after exclusions.

        Returns:
            int: dc-vault size in KiB.

        Raises:
            ValueError: If the dc-vault size was not found in the log.
        """
        if self.dc_vault_size_kib is None:
            raise ValueError("dc-vault size was not found in the ansible log")
        return self.dc_vault_size_kib

    def get_total_platform_size_estimation(self) -> int:
        """Return the final cumulative platform size estimation (KiB).

        Returns:
            int: Estimated required disk size in KiB.

        Raises:
            ValueError: If the estimate was not found in the log.
        """
        if self.total_platform_size_estimation is None:
            raise ValueError("total_platform_size_estimation was not found in the ansible log")
        return self.total_platform_size_estimation

    def get_available_disk_size_kib(self) -> int:
        """Return the available disk size in the backup dir (KiB) from the log.

        Returns:
            int: Available disk size in KiB.

        Raises:
            ValueError: If the available disk size was not found in the log.
        """
        if self.available_disk_size_kib is None:
            raise ValueError("available_disk_size was not found in the ansible log")
        return self.available_disk_size_kib

    def did_space_precheck_pass(self) -> bool:
        """Return whether the free-space pre-check gate passed (was skipped).

        Returns:
            bool: True if the "not enough free space" fail task was skipped.
        """
        return bool(self.space_precheck_passed)

    def has_dc_vault_size(self) -> bool:
        """Return whether the dc-vault size was captured.

        Returns:
            bool: True if the dc-vault size is present.
        """
        return self.dc_vault_size_kib is not None

    def has_available_disk_size(self) -> bool:
        """Return whether the available disk size was captured.

        Returns:
            bool: True if the available disk size is present.
        """
        return self.available_disk_size_kib is not None

    def is_complete(self) -> bool:
        """Return whether all values needed to assess the estimate were captured.

        Returns:
            bool: True if both the dc-vault size and the available disk size are present.
        """
        return self.has_dc_vault_size() and self.has_available_disk_size()

    def __str__(self) -> str:
        """Return a human-readable representation of the parsed estimation.

        Returns:
            str: Summary of the parsed size-estimation values.
        """
        return f"BackupSizeEstimationObject(dc_vault_size_kib={self.dc_vault_size_kib}, total_estimate_kib={self.total_platform_size_estimation}, available_kib={self.available_disk_size_kib}, precheck_passed={self.space_precheck_passed})"

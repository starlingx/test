"""Local-site GRUB factory-restore configuration module.

Holds the configuration for the "Local Factory Restore" via GRUB verification:
the auto-restore and restore-ansible log paths, the GRUB entry label to select,
and the auto-restore log success markers.
"""

from typing import List


class FactoryRestoreGrubConfig:
    """Configuration for the local-site GRUB factory-restore verification."""

    def __init__(self, factory_restore_grub_dict: dict):
        """Initialize from the 'factory_restore_grub' config section.

        Args:
            factory_restore_grub_dict (dict): The 'factory_restore_grub' section
                from the backup_restore JSON5 configuration.
        """
        self.auto_restore_log_path = factory_restore_grub_dict.get("auto_restore_log_path", "/var/log/auto-restore.log")
        self.restore_ansible_log_path = factory_restore_grub_dict.get("restore_ansible_log_path", "/home/sysadmin/ansible.log")
        self.grub_entry_label = factory_restore_grub_dict.get("grub_entry_label", "Local Factory Restore")
        self.success_markers = factory_restore_grub_dict.get(
            "success_markers",
            [
                "system restore-complete completed successfully",
                "Auto-restore script completed successfully",
                "Script exited with code 0.",
            ],
        )

    def get_auto_restore_log_path(self) -> str:
        """Get the auto-restore log path on the subcloud.

        Returns:
            str: Absolute path to the auto-restore log.
        """
        return self.auto_restore_log_path

    def get_restore_ansible_log_path(self) -> str:
        """Get the restore/bootstrap ansible log path on the subcloud.

        This is the ansible log the factory auto-restore drives (optimized
        restore playbook). Its PLAY RECAP line is polled to confirm the restore
        ansible actually finished before the auto-restore log is verified.

        Returns:
            str: Absolute path to the restore ansible log (e.g.
            "/home/sysadmin/ansible.log").
        """
        return self.restore_ansible_log_path

    def get_grub_entry_label(self) -> str:
        """Get the GRUB entry label to select for the local factory restore.

        Returns:
            str: The GRUB menu entry text (e.g. "Local Factory Restore").
        """
        return self.grub_entry_label

    def get_success_markers(self) -> List[str]:
        """Get the list of success markers expected in the auto-restore log.

        Returns:
            List[str]: Substrings that must all be present for a pass.
        """
        return self.success_markers

"""Keywords for handling subcloud config versioning across releases.

Subcloud config files for N-1/N-2 releases may be stored in release-specific
directories (e.g., /home/sysadmin/26.03/ or /home/sysadmin/25.09/) rather than
the default /home/sysadmin/subcloud-x/ path.

The deploy keywords always read configs from the default path. This keyword
class handles:
1. Detecting if release-specific config folders exist.
2. Backing up the current N-release configs (so they are not lost).
3. Copying N-1/N-2 configs into the default path for the deploy to use.

The backup is only created if the current files are confirmed to belong to the
N release by comparing the license content field in the deployment config YAML
against the system controller's deployment config.
"""

import os
from typing import List

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords


class SubcloudDeployConfigSyncKeywords(BaseKeyword):
    """Keywords for handling subcloud deploy config versioning.

    When deploying a subcloud with --release N-1 or N-2, the config files for
    that release may be stored in /home/sysadmin/<release_version>/ instead of
    the default /home/sysadmin/subcloud-x/ location. These keywords detect
    and swap config files so that deploy keywords pick up the correct release
    configs from their expected path.
    """

    SYSADMIN_HOME = "/home/sysadmin"

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self.file_kw = FileKeywords(ssh_connection)

    def release_config_folder_exists(self, release_version: str) -> bool:
        """Check if a release-specific config folder exists on the system controller.

        Args:
            release_version (str): Release version string (e.g., "26.03", "25.09").

        Returns:
            bool: True if /home/sysadmin/<release_version> directory exists.
        """
        release_dir = f"{self.SYSADMIN_HOME}/{release_version}"
        return self.file_kw.file_exists(release_dir)

    def get_release_config_files(self, release_version: str, subcloud_name: str) -> List[str]:
        """List config files in a release-specific subcloud folder.

        Release-specific files are stored in /home/sysadmin/<release>/<subcloud-dir>/
        mirroring the default structure.

        Args:
            release_version (str): Release version string (e.g., "26.03").
            subcloud_name (str): Subcloud name as used in deployment_assets config
                (e.g., "subcloud1").

        Returns:
            List[str]: File names found in the release-specific subcloud folder.
                Empty list if the folder does not exist.
        """
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        default_subcloud_dir = os.path.dirname(sc_assets.get_bootstrap_file())
        subcloud_folder_name = os.path.basename(default_subcloud_dir)

        release_subcloud_dir = f"{self.SYSADMIN_HOME}/{release_version}/{subcloud_folder_name}"

        if not self.file_kw.file_exists(release_subcloud_dir):
            get_logger().log_info(f"No release-specific folder found at '{release_subcloud_dir}'")
            return []

        files = self.file_kw.get_files_in_dir(release_subcloud_dir)
        get_logger().log_info(f"Found {len(files)} files in '{release_subcloud_dir}': {files}")
        return files

    def get_license_content_from_config(self, config_file_path: str) -> str:
        """Extract the license 'content' field from a deployment config YAML.

        Looks for a line matching 'content:' in the config file. This field
        identifies which release the config belongs to.

        Args:
            config_file_path (str): Remote path to the deployment config YAML file.

        Returns:
            str: The content value, or empty string if not found.
        """
        output = self.ssh_connection.send(f"grep -m1 'content:' {config_file_path} || true")
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        raw = raw.strip()
        if "content:" in raw:
            return raw.split("content:", 1)[1].strip()
        return ""

    def configs_belong_to_current_release(self, subcloud_name: str) -> bool:
        """Check if the current subcloud configs in default path belong to N release.

        Compares the license content field in the subcloud's deploy-config YAML
        against the system controller's deployment config. If they match, the
        configs are from the current (N) release.

        Args:
            subcloud_name (str): Subcloud name (e.g., "subcloud1").

        Returns:
            bool: True if the current configs match the system controller's
                license content (i.e., they belong to N release).
        """
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        controller_assets = deployment_assets_config.get_controller_deployment_assets()

        subcloud_deploy_config = sc_assets.get_deployment_config_file()
        controller_deploy_config = controller_assets.get_deployment_config_file()

        if not self.file_kw.file_exists(subcloud_deploy_config):
            get_logger().log_info(f"Subcloud deploy config does not exist: '{subcloud_deploy_config}'")
            return False

        sc_content = self.get_license_content_from_config(subcloud_deploy_config)
        ctrl_content = self.get_license_content_from_config(controller_deploy_config)

        if not sc_content or not ctrl_content:
            get_logger().log_info("Could not extract license content from one or both configs")
            return False

        match = sc_content == ctrl_content
        get_logger().log_info(f"License content match: {match} (subcloud='{sc_content}', controller='{ctrl_content}')")
        return match

    def backup_current_configs_to_n_release_folder(self, subcloud_name: str, n_release_version: str) -> None:
        """Backup current subcloud configs to an N-release-specific folder.

        Creates /home/sysadmin/<n_release_version>/<subcloud-dir>/ and copies
        all files from the default subcloud config directory there. Only
        performs the backup if:
        - The backup folder does not already exist (idempotent).
        - The current configs belong to the N release (license content check).
        - The default subcloud directory is not empty.

        Args:
            subcloud_name (str): Subcloud name (e.g., "subcloud1").
            n_release_version (str): Current system release version (e.g., "26.10").
        """
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        default_subcloud_dir = os.path.dirname(sc_assets.get_bootstrap_file())
        subcloud_folder_name = os.path.basename(default_subcloud_dir)

        backup_dir = f"{self.SYSADMIN_HOME}/{n_release_version}/{subcloud_folder_name}"

        if self.file_kw.file_exists(backup_dir):
            get_logger().log_info(f"Backup already exists at '{backup_dir}', skipping backup")
            return

        if not self.configs_belong_to_current_release(subcloud_name):
            get_logger().log_info(f"Current configs do not belong to N release ({n_release_version}), skipping backup")
            return

        files_to_backup = self.file_kw.get_files_in_dir(default_subcloud_dir)
        if not files_to_backup:
            get_logger().log_info(f"No files found in '{default_subcloud_dir}', skipping backup")
            return

        get_logger().log_info(f"Backing up current configs from '{default_subcloud_dir}' to '{backup_dir}'")
        self.file_kw.create_directory(f"{self.SYSADMIN_HOME}/{n_release_version}")
        self.file_kw.create_directory(backup_dir)
        for file_name in files_to_backup:
            self.file_kw.copy_file(f"{default_subcloud_dir}/{file_name}", f"{backup_dir}/{file_name}")
        get_logger().log_info(f"Backup complete: '{backup_dir}'")

    def copy_release_configs_to_default_path(self, release_version: str, subcloud_name: str) -> None:
        """Copy release-specific configs to the default subcloud config path.

        Copies all files from /home/sysadmin/<release_version>/<subcloud-dir>/
        into the default /home/sysadmin/<subcloud-dir>/ path, overwriting the
        existing files.

        Args:
            release_version (str): Release version whose configs to copy (e.g., "26.03").
            subcloud_name (str): Subcloud name (e.g., "subcloud1").
        """
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        default_subcloud_dir = os.path.dirname(sc_assets.get_bootstrap_file())
        subcloud_folder_name = os.path.basename(default_subcloud_dir)

        release_subcloud_dir = f"{self.SYSADMIN_HOME}/{release_version}/{subcloud_folder_name}"

        files_to_copy = self.file_kw.get_files_in_dir(release_subcloud_dir)
        if not files_to_copy:
            get_logger().log_info(f"No files in '{release_subcloud_dir}', nothing to copy")
            return

        get_logger().log_info(f"Copying configs from '{release_subcloud_dir}' to '{default_subcloud_dir}'")
        for file_name in files_to_copy:
            self.file_kw.copy_file(f"{release_subcloud_dir}/{file_name}", f"{default_subcloud_dir}/{file_name}")
        get_logger().log_info(f"Release {release_version} configs now in default path '{default_subcloud_dir}'")

    def restore_n_release_configs(self, subcloud_name: str, n_release_version: str) -> None:
        """Restore N-release configs from backup back to the default path.

        Copies files from /home/sysadmin/<n_release_version>/<subcloud-dir>/
        back to the default /home/sysadmin/<subcloud-dir>/ path, then removes
        the backup directory to prevent stale leftovers from affecting future runs.

        Args:
            subcloud_name (str): Subcloud name (e.g., "subcloud1").
            n_release_version (str): N release version (e.g., "26.10").
        """
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        default_subcloud_dir = os.path.dirname(sc_assets.get_bootstrap_file())
        subcloud_folder_name = os.path.basename(default_subcloud_dir)

        backup_dir = f"{self.SYSADMIN_HOME}/{n_release_version}/{subcloud_folder_name}"

        if not self.file_kw.file_exists(backup_dir):
            get_logger().log_info(f"No backup found at '{backup_dir}', cannot restore N-release configs")
            return

        files_to_restore = self.file_kw.get_files_in_dir(backup_dir)
        if not files_to_restore:
            get_logger().log_info(f"Backup dir '{backup_dir}' is empty, nothing to restore")
            return

        get_logger().log_info(f"Restoring N-release configs from '{backup_dir}' to '{default_subcloud_dir}'")
        for file_name in files_to_restore:
            self.file_kw.copy_file(f"{backup_dir}/{file_name}", f"{default_subcloud_dir}/{file_name}")
        get_logger().log_info(f"N-release ({n_release_version}) configs restored to '{default_subcloud_dir}'")

        get_logger().log_info(f"Removing backup directory '{backup_dir}'")
        self.file_kw.delete_directory(backup_dir)

    def sync_subcloud_configs_for_release(self, subcloud_name: str, target_release_version: str, n_release_version: str) -> bool:
        """Full workflow: backup N configs and swap in target release configs.

        This is the main entry point for tests deploying subclouds with N-1 or
        N-2 releases. It performs:
        1. Check if target release folder exists.
        2. If it does, backup current (N) configs if not already backed up.
        3. Copy target release configs to the default path.

        Args:
            subcloud_name (str): Subcloud name (e.g., "subcloud1").
            target_release_version (str): Release to deploy (e.g., "26.03" for N-1).
            n_release_version (str): Current system release (e.g., "26.10" for N).

        Returns:
            bool: True if configs were swapped, False if no release-specific
                folder was found (default configs will be used as-is).
        """
        if not self.release_config_folder_exists(target_release_version):
            get_logger().log_info(f"No release folder for '{target_release_version}', using default configs")
            return False

        release_files = self.get_release_config_files(target_release_version, subcloud_name)
        if not release_files:
            get_logger().log_info(f"Release folder for '{target_release_version}' has no configs for '{subcloud_name}'")
            return False

        self.backup_current_configs_to_n_release_folder(subcloud_name, n_release_version)
        self.copy_release_configs_to_default_path(target_release_version, subcloud_name)
        return True

    def sync_all_subclouds_configs_for_release(self, subcloud_names: List[str], target_release_version: str, n_release_version: str) -> List[str]:
        """Sync release configs for all subclouds in a batch.

        Iterates over a list of subclouds and swaps each one's config files
        to the target release version. Use this before batch deployments with
        --release N-1 or N-2.

        Args:
            subcloud_names (List[str]): List of subcloud names to sync.
            target_release_version (str): Release to deploy (e.g., "26.03").
            n_release_version (str): Current system release (e.g., "26.10").

        Returns:
            List[str]: Names of subclouds whose configs were actually swapped.
                Empty list if no release folder exists.
        """
        if not self.release_config_folder_exists(target_release_version):
            get_logger().log_info(f"No release folder for '{target_release_version}', using default configs for all subclouds")
            return []

        swapped_subclouds = []
        for subcloud_name in subcloud_names:
            swapped = self.sync_subcloud_configs_for_release(subcloud_name, target_release_version, n_release_version)
            if swapped:
                swapped_subclouds.append(subcloud_name)

        get_logger().log_info(f"Swapped configs for {len(swapped_subclouds)}/{len(subcloud_names)} subclouds: {swapped_subclouds}")
        return swapped_subclouds

    def restore_all_subclouds_n_release_configs(self, subcloud_names: List[str], n_release_version: str) -> None:
        """Restore N-release configs for all subclouds in a batch.

        Args:
            subcloud_names (List[str]): List of subcloud names to restore.
            n_release_version (str): N release version (e.g., "26.10").
        """
        for subcloud_name in subcloud_names:
            self.restore_n_release_configs(subcloud_name, n_release_version)

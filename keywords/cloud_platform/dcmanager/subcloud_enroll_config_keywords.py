"""Resolve the enroll config file paths for an N-1/N-2 subcloud enrollment.

For an N-1/N-2 enroll the release-specific configs use the same filenames as the
default configs but live under a release-named sub-directory, so only the
directory is redirected and the default configs are left unchanged.
"""

import os
from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.dcmanager.enroll_config import EnrollConfig
from keywords.files.file_keywords import FileKeywords


class SubcloudEnrollConfigKeywords(BaseKeyword):
    """Resolve enroll config file locations for the release (N-1/N-2) variants."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the system controller.
        """
        self.ssh_connection = ssh_connection

    def resolve_for_release(self, default_config: EnrollConfig, release: Optional[str]) -> EnrollConfig:
        """Resolve the enroll config paths for an N-1/N-2 release from the defaults.

        Redirects only the directory into the release-named folder, keeping the
        filenames, and drops the 'software_version' line from the release
        install-values (the enroll rejects a version mismatch). A None release
        returns the default paths unchanged.

        Args:
            default_config (EnrollConfig): The subcloud's default config paths.
            release (Optional[str]): Release segment to insert, or None.

        Returns:
            EnrollConfig: The resolved paths.
        """
        if not release:
            return default_config

        release_dir = self._release_config_dir(default_config.bootstrap_values, release)
        install_values = os.path.join(release_dir, os.path.basename(default_config.install_values))

        # Enroll adopts an already-installed subcloud and rejects an install-values
        # 'software_version' that differs from the system controller's version, so
        # drop that line for the N-1/N-2 enroll.
        self._strip_software_version(install_values)

        return EnrollConfig(
            bootstrap_values=os.path.join(release_dir, os.path.basename(default_config.bootstrap_values)),
            install_values=install_values,
            deploy_config_file=os.path.join(release_dir, os.path.basename(default_config.deploy_config_file)),
        )

    def _strip_software_version(self, install_values: str) -> None:
        """Remove the top-level 'software_version' line from an install-values file.

        Args:
            install_values (str): Path on the SC to the install-values file.

        Raises:
            FileNotFoundError: If the release install-values file is not staged on
                the system controller.
        """
        if not FileKeywords(self.ssh_connection).file_exists(install_values):
            raise FileNotFoundError(f"Release install-values not found on the system controller: '{install_values}'. Is the release config staged?")
        self.ssh_connection.send(f"sed -i '/^software_version:/d' {install_values}")

    @staticmethod
    def _release_config_dir(default_bootstrap_file: str, release: str) -> str:
        """Map a subcloud's default config directory to its release-specific one.

        Args:
            default_bootstrap_file (str): The subcloud's default bootstrap path.
            release (str): Release segment to insert.

        Returns:
            str: The release-specific config directory.
        """
        default_dir = os.path.dirname(default_bootstrap_file)
        parent = os.path.dirname(default_dir)
        subcloud_folder = os.path.basename(default_dir)
        return os.path.join(parent, release, subcloud_folder)

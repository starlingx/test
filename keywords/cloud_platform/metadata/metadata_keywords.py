"""Metadata keywords for StarlingX software release metadata operations."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords


class MetadataKeywords(BaseKeyword):
    """
    Keywords for manipulating StarlingX software release metadata files.

    These operations interact with /opt/software/metadata/ directories
    and are specific to the StarlingX Unified Software Management (USM) subsystem.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection
        self.file_keywords = FileKeywords(ssh_connection)

    def create_fake_release_metadata(self, source_release: str, fake_release: str, source_state: str = "deployed", target_state: str = "available") -> str:
        """
        Create a fake release metadata file by copying from an existing release and replacing the release ID.

        This is useful for testing prestage behavior with simulated release states when no release
        in the desired state exists on the system.

        Args:
            source_release (str): The release name to copy metadata from (e.g. "starlingx-24.09.0").
            fake_release (str): The new release name to use in the fake metadata (e.g. "starlingx-24.09.0-fake").
            source_state (str): The state directory of the source metadata (default: "deployed").
            target_state (str): The state directory where the fake metadata will be created (default: "available").

        Returns:
            str: The path to the created fake metadata file.
        """
        source_metadata = f"/opt/software/metadata/{source_state}/{source_release}-metadata.xml"
        fake_metadata = f"/opt/software/metadata/{target_state}/{fake_release}-metadata.xml"

        self.file_keywords.copy_file(source_metadata, fake_metadata, sudo=True)
        self.ssh_connection.send_as_sudo(f"sed -i 's|<id>{source_release}</id>|<id>{fake_release}</id>|g' {fake_metadata}")
        self.validate_success_return_code(self.ssh_connection)

        get_logger().log_info(f"Created fake release metadata: {fake_metadata}")
        return fake_metadata

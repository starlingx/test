from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.linux.dmi.object.dmi_bios_identity_object import DmiBiosIdentityObject
from keywords.linux.dmi.object.dmi_bios_identity_output import DmiBiosIdentityOutput


class DmiKeywords(BaseKeyword):
    """Keywords for the DMI/SMBIOS data the kernel exposes under ``/sys/class/dmi/id``."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Connection to the host to inspect.
        """
        self.ssh_connection = ssh_connection

    def get_bios_identity(self) -> DmiBiosIdentityObject:
        """Get the BIOS, system and board identity of the host.

        Only world-readable DMI files are read, so no serial numbers are collected.

        Returns:
            DmiBiosIdentityObject: BIOS, system and board identity.
        """
        head_files_output = FileKeywords(self.ssh_connection).read_file_patterns(DmiBiosIdentityOutput.get_file_paths())
        return DmiBiosIdentityOutput(head_files_output).get_dmi_bios_identity_object()

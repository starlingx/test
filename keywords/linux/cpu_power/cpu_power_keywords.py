from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.linux.cpu_power.object.cpu_power_settings_object import CpuPowerSettingsObject
from keywords.linux.cpu_power.object.cpu_power_settings_output import CpuPowerSettingsOutput


class CpuPowerKeywords(BaseKeyword):
    """Keywords for the CPU power settings the kernel exposes in sysfs."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Connection to the host to inspect.
        """
        self.ssh_connection = ssh_connection

    def get_cpu_power_settings(self) -> CpuPowerSettingsObject:
        """Get the effective P-state, C-state, turbo and SMT settings of the host.

        These reflect what the BIOS and kernel actually left in effect, so they
        are readable even when the BMC does not publish BIOS attributes.

        Returns:
            CpuPowerSettingsObject: Derived settings and their sysfs evidence.
        """
        head_files_output = FileKeywords(self.ssh_connection).read_file_patterns(CpuPowerSettingsOutput.FILE_PATTERNS, use_sudo=True)
        return CpuPowerSettingsOutput(head_files_output).get_cpu_power_settings_object()

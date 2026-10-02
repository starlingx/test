"""Keywords for inspecting the disable-nohz-full host label and its kernel nohz args.

On the standard kernel the `disable-nohz-full=enabled` host label removes the
`nohz` token from the `isolcpus=` boot arg and removes the `nohz_full=` grub arg
(keeping CPUs application-isolated); on the lowlatency/RT kernel the label has no
effect (nohz_full persists).

This class only provides reboot-free inspection helpers (read /proc/cmdline, query
whether the label is set). Mutating the label requires a controller lock/unlock
reboot, which the caller composes from the existing SystemHostLockKeywords and
SystemHostLabelKeywords so that a single lock/unlock wraps the change. Every method
uses the SSH connection passed to the constructor; after a reboot the caller must
re-acquire the active-controller SSH (via LabConnectionKeywords) and build a fresh
instance, because the floating OAM address can move.
"""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.host.objects.proc_cmdline_output import ProcCmdlineOutput
from keywords.files.file_keywords import FileKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords

# Label under test
DISABLE_NOHZ_LABEL_KEY = "disable-nohz-full"


class DisableNohzFullKeywords(BaseKeyword):
    """Reboot-free inspection helpers for the disable-nohz-full label effect."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
                A lock/unlock reboot can move the floating OAM address, so after an
                operation that reboots the host the caller should re-acquire the
                active-controller SSH and build a fresh instance.
        """
        self.ssh_connection = ssh_connection

    def get_proc_cmdline(self) -> ProcCmdlineOutput:
        """Return the parsed running kernel command line from /proc/cmdline.

        Reads the file via FileKeywords and returns a ProcCmdlineOutput so callers
        query fields (isolcpus, nohz_full) via getters rather than parsing text.

        Returns:
            ProcCmdlineOutput: Parsed /proc/cmdline.
        """
        lines = FileKeywords(self.ssh_connection).read_file("/proc/cmdline")
        return ProcCmdlineOutput("\n".join(lines))

    def is_label_present(self, host_name: str) -> bool:
        """Return True if the disable-nohz-full label is set on the host.

        Args:
            host_name (str): The host to query.

        Returns:
            bool: True if the disable-nohz-full label is present.
        """
        label_list = SystemHostLabelKeywords(self.ssh_connection).get_system_host_label_list(host_name)
        return label_list.get_label_value(DISABLE_NOHZ_LABEL_KEY) is not None

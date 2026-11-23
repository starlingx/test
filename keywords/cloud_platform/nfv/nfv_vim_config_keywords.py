"""Keywords to read and set values in the nfv-vim config.ini."""

import re
import shlex

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.nfv.objects.nfv_vim_config_section_output import NfvVimConfigSectionOutput

# nfv-vim reads this file when the vim service starts. It is per controller and
# is not replicated, so a value has to be set on each controller.
NFV_VIM_CONFIG_PATH = "/etc/nfv/vim/config.ini"

# Section names and keys in config.ini use only these characters (no regex
# metacharacters), so they can go in a sed address and substitution as-is.
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
# Values are plain numbers, words or booleans; '|' (the sed delimiter used here)
# and newlines are rejected.
_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9_.:/-]+$")


class NfvVimConfigKeywords(BaseKeyword):
    """Keywords to read and set values in the nfv-vim config.ini.

    The file is per controller: run these against each controller's own SSH
    connection. A change takes effect only after the vim service restarts on the
    active controller.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize NfvVimConfigKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller whose file is read or changed.
        """
        self.ssh_connection = ssh_connection

    @staticmethod
    def _validate_name(kind: str, name: str) -> None:
        """Check a section or key name is safe to use in a sed script.

        Args:
            kind (str): 'section' or 'key', for the error message.
            name (str): The name to check.

        Raises:
            ValueError: If the name has characters outside [A-Za-z0-9_-].
        """
        if not _NAME_PATTERN.match(name):
            raise ValueError(f"nfv-vim config {kind} '{name}' must match {_NAME_PATTERN.pattern}")

    def get_config_section(self, section: str) -> NfvVimConfigSectionOutput:
        """Read one section of the nfv-vim config.ini.

        Args:
            section (str): Section name without brackets, e.g. 'instance-configuration'.

        Returns:
            NfvVimConfigSectionOutput: The section's key=value pairs.
        """
        self._validate_name("section", section)
        sed_script = "/^\\[" + section + "\\]/,/^\\[/p"
        output = self.ssh_connection.send(f"sed -n {shlex.quote(sed_script)} {NFV_VIM_CONFIG_PATH}")
        self.validate_success_return_code(self.ssh_connection)
        return NfvVimConfigSectionOutput(output, section)

    def set_config_value(self, section: str, key: str, value: str) -> None:
        """Set an existing key in one section of the nfv-vim config.ini.

        Only a key already present in the section is changed; the section is not
        rewritten and other sections are not touched.

        Args:
            section (str): Section name without brackets, e.g. 'instance-configuration'.
            key (str): Option name, e.g. 'max_concurrent_migrates_per_host'.
            value (str): New value.

        Raises:
            ValueError: If a name or the value has unsupported characters, or the
                section does not already set the key.
        """
        self._validate_name("key", key)
        if not _VALUE_PATTERN.match(str(value)):
            raise ValueError(f"nfv-vim config value '{value}' for '{key}' must match {_VALUE_PATTERN.pattern}")
        if not self.get_config_section(section).has_key(key):
            raise ValueError(f"nfv-vim config section [{section}] on {self.ssh_connection.get_name()} has no key '{key}' to set")
        sed_script = "/^\\[" + section + "\\]/,/^\\[/ s|^" + key + "[[:space:]]*=.*|" + key + "=" + str(value) + "|"
        get_logger().log_info(f"Setting nfv-vim [{section}] {key}={value} in {NFV_VIM_CONFIG_PATH} on {self.ssh_connection.get_name()}")
        self.ssh_connection.send_as_sudo(f"sed -i {shlex.quote(sed_script)} {NFV_VIM_CONFIG_PATH}")
        self.validate_success_return_code(self.ssh_connection)

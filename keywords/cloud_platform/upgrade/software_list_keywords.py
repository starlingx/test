"""Software list keywords."""

import re

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.upgrade.objects.software_list_output import SoftwareListOutput


class SoftwareListKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the
    'software list' commands.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Instance of the class.

        Args:
            ssh_connection: An instance of an SSH connection.

        """
        self.ssh_connection = ssh_connection

    def get_software_list(self, sudo=False) -> SoftwareListOutput:
        """
        Get the software list.

        Args:
            sudo: True or False

        """
        if sudo:
            output = self.ssh_connection.send_as_sudo("software list")
        else:
            output = self.ssh_connection.send(source_openrc("software list"))
        self.validate_success_return_code(self.ssh_connection)
        software_list_output = SoftwareListOutput(output)

        return software_list_output

    def get_highest_deployed_version(self) -> str:
        """
        Get the highest version string among all deployed releases.

        Collects every release whose state is 'deployed' or 'deployed-partial'
        from 'software list', strips the product prefix (the leading
        letter-led token up to the first dash, e.g. 'starlingx-'), and returns
        the numerically highest dotted version, so '24.03.10' outranks
        '24.03.9' and '26.10.0' (r/stx.13.0) outranks '24.03.0' (r/stx.9.0).

        Returns:
            str: The highest deployed version (e.g. '24.03.0' on r/stx.9.0 or
                '26.10.0' on r/stx.13.0).

        Raises:
            RuntimeError: If no deployed release is found in 'software list'.

        """
        deployed = self.get_software_list().get_deployed_release_names()
        if not deployed:
            raise RuntimeError("No deployed release found in 'software list'. " "Check that a release is in 'deployed' or 'deployed-partial' state.")

        def _bare_version(release_name: str) -> str:
            """Strip the product prefix, leaving the dotted version segment."""
            match = re.match(r"[A-Za-z][A-Za-z0-9]*-(.+)", release_name)
            return match.group(1).strip() if match else release_name.strip()

        def _sort_key(version: str) -> tuple:
            """Build a numeric sort key so '24.03.10' > '24.03.9'."""
            return tuple(int(s) if s.isdigit() else 0 for s in version.split("."))

        versions = [_bare_version(name) for name in deployed]
        highest = max(versions, key=_sort_key)
        get_logger().log_info(f"Deployed releases {deployed} -> highest version '{highest}'")
        return highest

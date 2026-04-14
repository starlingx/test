"""OpenStack credentials retrieval from platform openrc."""

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class OpenStackCredentialsKeywords(BaseKeyword):
    """Retrieve OpenStack credentials from the platform openrc file."""

    def __init__(self, ssh_connection: object):
        """Initialize with SSH connection to a StarlingX controller.

        Args:
            ssh_connection (object): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection

    def get_openstack_password(self) -> str:
        """Get the OpenStack admin password from the platform keyring.

        Sources /etc/platform/openrc and reads OS_PASSWORD, which is
        retrieved from the platform keyring at runtime.

        Returns:
            str: The OpenStack admin password.
        """
        output = self.ssh_connection.send(source_openrc("echo $OS_PASSWORD"))
        self.validate_success_return_code(self.ssh_connection)
        return output[0].strip()

    def get_openstack_username(self) -> str:
        """Get the OpenStack admin username from openrc.

        Returns:
            str: The OpenStack admin username.
        """
        output = self.ssh_connection.send(source_openrc("echo $OS_USERNAME"))
        self.validate_success_return_code(self.ssh_connection)
        return output[0].strip()

"""OpenStack credentials manager for extracting credentials from lab."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.openstack.endpoint.openstack_endpoint_list_keywords import OpenStackEndpointListKeywords
from keywords.openstack.command_wrappers import source_admin_openrc

from keywords.openstack.connection.objects.openstack_credentials_object import OpenStackCredentialsObject

_APP_OPENRC = "/var/opt/openstack/admin-openrc"
_STX_OPENRC = "/etc/platform/openrc"


class OpenStackCredentialsManager:
    """Manager for extracting OpenStack credentials from lab environment.

    Supports both application (/var/opt/openstack/admin-openrc) and StarlingX
    (/etc/platform/openrc) OpenStack deployments. Auto-detects which
    openrc is available on the lab.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize credentials manager.

        Args:
            ssh_connection (SSHConnection): SSH connection to the lab.
        """
        self.ssh_connection = ssh_connection
        self._use_stx_openrc = self._detect_openrc_type()

    def _detect_openrc_type(self) -> bool:
        """Detect whether the lab uses StarlingX or application openrc.

        Returns:
            bool: True if StarlingX openrc, False if application openrc.

        Raises:
            FileNotFoundError: If neither openrc file is found.
        """
        output = self.ssh_connection.send(f"test -f {_APP_OPENRC} && echo APP || (test -f {_STX_OPENRC} && echo STX || echo NONE)")
        result = output.strip() if isinstance(output, str) else output[-1].strip()
        if result == "APP":
            get_logger().log_info(f"Detected application openrc: {_APP_OPENRC}")
            return False
        if result == "STX":
            get_logger().log_info(f"Detected StarlingX openrc: {_STX_OPENRC}")
            return True
        raise FileNotFoundError(f"No openrc found on lab (checked {_APP_OPENRC} and {_STX_OPENRC})")

    def _source_openrc(self, cmd: str) -> str:
        """Wrap command with the appropriate openrc source.

        Args:
            cmd (str): Command to wrap.

        Returns:
            str: Command prefixed with the correct openrc source.
        """
        if self._use_stx_openrc:
            return source_openrc(cmd)
        return source_admin_openrc(cmd)

    def get_admin_password(self) -> str:
        """Get admin password from openrc.

        Returns:
            str: Admin password.

        Raises:
            ValueError: If OS_PASSWORD is not set in the openrc.
        """
        output = self.ssh_connection.send(self._source_openrc("echo $OS_PASSWORD"))
        lines = output if isinstance(output, list) else output.splitlines()
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith("Unable"):
                return line
        raise ValueError("OS_PASSWORD is not set in admin openrc")

    def get_keystone_auth_url(self) -> str:
        """Get Keystone public URL using OpenStack endpoint list keyword.

        Returns:
            str: Keystone public URL.

        Raises:
            ValueError: If no Keystone public endpoint URL is found.
        """
        endpoint_keywords = OpenStackEndpointListKeywords(self.ssh_connection)
        if self._use_stx_openrc:
            endpoint_output = endpoint_keywords.endpoint_list()
        else:
            endpoint_output = endpoint_keywords.endpoint_list_admin_openrc()
        return endpoint_output.get_endpoint("keystone", "public").get_url()

    def get_openstack_credentials(self) -> OpenStackCredentialsObject:
        """Get OpenStack credentials for admin user.

        Returns:
            OpenStackCredentialsObject: OpenStack authentication credentials.

        Raises:
            ValueError: If OS_PASSWORD is not set or Keystone URL cannot be retrieved.
        """
        return OpenStackCredentialsObject(
            auth_url=self.get_keystone_auth_url(),
            username="admin",
            password=self.get_admin_password(),
            project_name="admin",
            user_domain_name="Default",
            project_domain_name="Default",
        )

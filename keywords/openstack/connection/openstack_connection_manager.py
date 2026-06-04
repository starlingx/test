"""Factory for creating ACEOpenStackConnection from lab credentials.

Centralizes the SSH → credentials → SDK connection chain so test files
and keywords don't duplicate this boilerplate.

Usage:
    from keywords.openstack.connection.openstack_connection_manager import create_ace_connection

    conn = create_ace_connection()  # uses active controller SSH
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.connection.openstack_connection import OpenStackConnection
from keywords.openstack.connection.openstack_credentials import OpenStackCredentialsManager


def create_ace_connection(ssh_connection: SSHConnection = None) -> ACEOpenStackConnection:
    """Create an ACEOpenStackConnection from lab credentials.

    If no SSH connection is provided, connects to the active controller
    automatically via LabConnectionKeywords.

    Args:
        ssh_connection (SSHConnection): Optional SSH connection. If None,
            connects to the active controller.

    Returns:
        ACEOpenStackConnection: Connected and logged OpenStack client.
    """
    if ssh_connection is None:
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    creds = OpenStackCredentialsManager(ssh_connection).get_openstack_credentials()
    raw_conn = OpenStackConnection(
        auth_url=creds.get_auth_url(),
        username=creds.get_username(),
        password=creds.get_password(),
        project_name=creds.get_project_name(),
        user_domain_name=creds.get_user_domain_name(),
        project_domain_name=creds.get_project_domain_name(),
        verify=False,
    )
    get_logger().log_info(f"OpenStack connection established: {creds.get_auth_url()}")
    return ACEOpenStackConnection(raw_conn)

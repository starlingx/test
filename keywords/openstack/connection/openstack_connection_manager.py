"""Factory for creating ACEOpenStackConnection from lab credentials.

Centralizes the SSH → credentials → SDK connection chain so test files
and keywords don't duplicate this boilerplate.

Usage:
    from keywords.openstack.connection.openstack_connection_manager import create_ace_connection

    conn = create_ace_connection()  # uses active controller SSH
"""

import socket
from urllib.parse import urlparse, urlunparse

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.connection.openstack_connection import OpenStackConnection
from keywords.openstack.connection.openstack_credentials import OpenStackCredentialsManager


def _resolve_auth_url(auth_url: str, ssh_connection: SSHConnection) -> str:
    """Ensure the auth URL is reachable from the local host.

    In DC environments, subcloud endpoints use hostnames that are only
    resolvable within the subcloud's cluster network. When running from
    a remote runagent, substitute the unresolvable hostname with the
    SSH connection's IP (which is known reachable).

    Args:
        auth_url (str): Original auth URL from endpoint list.
        ssh_connection (SSHConnection): SSH connection to the target host.

    Returns:
        str: Resolvable auth URL.
    """
    parsed = urlparse(auth_url)
    hostname = parsed.hostname

    try:
        socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_NUMERICHOST)
        return auth_url
    except socket.gaierror:
        pass

    try:
        socket.getaddrinfo(hostname, None)
        return auth_url
    except socket.gaierror:
        pass

    ssh_host = ssh_connection.host
    is_ipv6 = ":" in ssh_host
    new_host = f"[{ssh_host}]" if is_ipv6 else ssh_host
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    new_netloc = f"{new_host}:{port}"
    new_url = urlunparse((parsed.scheme, new_netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
    get_logger().log_info(f"Auth URL hostname '{hostname}' unresolvable — using SSH IP: {new_url}")
    return new_url


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
    auth_url = _resolve_auth_url(creds.get_auth_url(), ssh_connection)
    raw_conn = OpenStackConnection(
        auth_url=auth_url,
        username=creds.get_username(),
        password=creds.get_password(),
        project_name=creds.get_project_name(),
        user_domain_name=creds.get_user_domain_name(),
        project_domain_name=creds.get_project_domain_name(),
        verify=False,
    )
    get_logger().log_info(f"OpenStack connection established: {auth_url}")
    return ACEOpenStackConnection(raw_conn)

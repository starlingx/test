"""OpenStack connection manager using OpenStack SDK."""

from typing import Dict

from openstack import connection


class OpenStackConnection:
    """OpenStack connection wrapper using OpenStack SDK."""

    def __init__(self, auth_url: str, username: str, password: str, project_name: str, user_domain_name: str = "Default", project_domain_name: str = "Default", verify: bool = True):
        """Initialize OpenStack connection.

        Args:
            auth_url (str): Keystone authentication URL.
            username (str): Username for authentication.
            password (str): Password for authentication.
            project_name (str): Project name.
            user_domain_name (str): User domain name.
            project_domain_name (str): Project domain name.
            verify (bool): Enable SSL certificate verification.
        """
        # Ensure auth_url is not None or empty
        if not auth_url:
            raise ValueError("auth_url cannot be None or empty")

        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.project_name = project_name
        self.user_domain_name = user_domain_name
        self.project_domain_name = project_domain_name
        self.verify = verify
        self._conn = None

    def get_connection(self) -> connection.Connection:
        """Get OpenStack connection.

        Returns:
            connection.Connection: OpenStack connection object.
        """
        if self._conn is None:
            self._conn = connection.Connection(
                auth_url=self.auth_url,
                username=self.username,
                password=self.password,
                project_name=self.project_name,
                user_domain_name=self.user_domain_name,
                project_domain_name=self.project_domain_name,
                verify=self.verify,
            )
        return self._conn

    def get_auth_details(self) -> Dict[str, str]:
        """Get authentication details.

        Returns:
            Dict[str, str]: Authentication details including token, user_id, project_id, etc.
        """
        conn = self.get_connection()
        access = conn.session.auth.get_access(conn.session)

        return {
            "auth_token": access.auth_token,
            "user_id": access.user_id,
            "project_id": access.project_id,
            "project_name": access.project_name,
            "domain_id": access.domain_id,
            "expires_at": str(access.expires),
            "auth_url": self.auth_url,
        }

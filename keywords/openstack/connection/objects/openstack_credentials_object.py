"""OpenStack credentials object."""


class OpenStackCredentialsObject:
    """Holds OpenStack authentication credentials."""

    def __init__(self, auth_url: str, username: str, password: str, project_name: str, user_domain_name: str, project_domain_name: str):
        """Initialize OpenStack credentials.

        Args:
            auth_url (str): Keystone authentication URL.
            username (str): Username for authentication.
            password (str): Password for authentication.
            project_name (str): Project name.
            user_domain_name (str): User domain name.
            project_domain_name (str): Project domain name.
        """
        self._auth_url = auth_url
        self._username = username
        self._password = password
        self._project_name = project_name
        self._user_domain_name = user_domain_name
        self._project_domain_name = project_domain_name

    def get_auth_url(self) -> str:
        """Get Keystone authentication URL.

        Returns:
            str: Keystone authentication URL.
        """
        return self._auth_url

    def get_username(self) -> str:
        """Get username.

        Returns:
            str: Username.
        """
        return self._username

    def get_password(self) -> str:
        """Get password.

        Returns:
            str: Password.
        """
        return self._password

    def get_project_name(self) -> str:
        """Get project name.

        Returns:
            str: Project name.
        """
        return self._project_name

    def get_user_domain_name(self) -> str:
        """Get user domain name.

        Returns:
            str: User domain name.
        """
        return self._user_domain_name

    def get_project_domain_name(self) -> str:
        """Get project domain name.

        Returns:
            str: Project domain name.
        """
        return self._project_domain_name

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: Human-readable credentials summary.
        """
        return f"OpenStackCredentials(auth_url={self._auth_url}, username={self._username}, project={self._project_name})"

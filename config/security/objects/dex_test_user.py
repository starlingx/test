"""DexTestUser object for OIDC test user configuration."""


class DexTestUser:
    """Represents a test user for OIDC authentication testing."""

    def __init__(self, user_dict: dict):
        """Initialize test user from config dictionary.

        Args:
            user_dict (dict): User configuration dictionary.
        """
        self._username = user_dict.get("username", "")
        self._password = user_dict.get("password", "")
        self._email = user_dict.get("email", "")
        self._role = user_dict.get("role", "")
        self._crb_name = user_dict.get("crb_name", "")
        self._realm = user_dict.get("realm", "")

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

    def get_email(self) -> str:
        """Get email address.

        Returns:
            str: Email address.
        """
        return self._email

    def get_role(self) -> str:
        """Get user role.

        Returns:
            str: User role.
        """
        return self._role

    def get_crb_name(self) -> str:
        """Get ClusterRoleBinding name for this user.

        Returns:
            str: CRB name.
        """
        return self._crb_name

    def get_realm(self) -> str:
        """Get Keycloak realm.

        Returns:
            str: Realm name.
        """
        return self._realm

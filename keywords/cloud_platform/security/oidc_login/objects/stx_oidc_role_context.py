"""Context object holding the values needed to run a browser-based OIDC login for a role test."""


class StxOidcRoleContext:
    """Holds the values needed to run a browser-based OIDC login for a role test."""

    def __init__(self, test_user: object, login_url: str, oam_ip: str, connector_id: str, teardowns: list):
        """Constructor.

        Args:
            test_user (object): DEX test-user config object (username/password/crb_name).
            login_url (str): The oidc-login listener URL.
            oam_ip (str): Lab OAM IP (bare, no brackets).
            connector_id (str): DEX connector id to select (e.g. 'ldap-1').
            teardowns (list): Teardown callables in registration order —
                [role_bindings_teardown, cleanup]. The caller registers each with
                request.addfinalizer so (LIFO) cleanup runs first while keystone is
                up and the keystone-restarting role-bindings teardown runs last.
        """
        self.test_user = test_user
        self.login_url = login_url
        self.oam_ip = oam_ip
        self.connector_id = connector_id
        self.teardowns = teardowns

    def get_test_user(self) -> object:
        """Get the DEX test-user config object.

        Returns:
            object: The DEX test-user config object.
        """
        return self.test_user

    def get_login_url(self) -> str:
        """Get the oidc-login listener URL.

        Returns:
            str: The login URL.
        """
        return self.login_url

    def get_oam_ip(self) -> str:
        """Get the lab OAM IP (bare, no brackets).

        Returns:
            str: The OAM IP.
        """
        return self.oam_ip

    def get_connector_id(self) -> str:
        """Get the DEX connector id to select.

        Returns:
            str: The connector id (e.g. 'ldap-1').
        """
        return self.connector_id

    def get_teardowns(self) -> list:
        """Get the teardown callables in registration order.

        Returns:
            list: Teardown callables [role_bindings_teardown, cleanup].
        """
        return self.teardowns

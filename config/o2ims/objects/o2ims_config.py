import json5


class O2imsConfig:
    """
    Holds configuration for O2 IMS API testing.

    Manages the environment contract shared between the O2 bring-up and the O2
    IMS API tests: the OAuth2 token issuer's port, realm, client id and admin
    credentials, the directory holding the client certificate material on the
    test runner, and the port the O2 IMS API is served on.

    The client secret is intentionally NOT stored here. It is read live from the
    token issuer at run time, so it never appears in a committed configuration
    file.

    Configuration file format: JSON5 with required fields 'issuer_port',
    'realm', 'client_id', 'cert_dir', 'served_port', 'issuer_admin_user' and
    'issuer_admin_password'.
    """

    def __init__(self, config: str):
        """
        Initializes the O2imsConfig object by loading the specified config file.

        Args:
            config (str): Path to the O2 IMS configuration file (e.g., default.json5).

        Raises:
            FileNotFoundError: If the file is not found.
            ValueError: If the config is missing required fields.
        """
        try:
            with open(config) as f:
                self._config_dict = json5.load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Could not find the O2 IMS config file: {config}") from e

        for required_field in ("issuer_port", "realm", "client_id", "cert_dir", "served_port", "issuer_admin_user", "issuer_admin_password"):
            if required_field not in self._config_dict:
                raise ValueError(f"Config missing required field: '{required_field}'")

        self.issuer_port = self._config_dict["issuer_port"]
        self.realm = self._config_dict["realm"]
        self.client_id = self._config_dict["client_id"]
        self.cert_dir = self._config_dict["cert_dir"]
        self.served_port = self._config_dict["served_port"]
        self.issuer_admin_user = self._config_dict["issuer_admin_user"]
        self.issuer_admin_password = self._config_dict["issuer_admin_password"]

    def get_issuer_port(self) -> int:
        """
        Getter for the OAuth2 token issuer port.

        Returns:
            int: The port the token issuer listens on, as seen on the controller.
        """
        return self.issuer_port

    def get_realm(self) -> str:
        """
        Getter for the OAuth2 realm.

        Returns:
            str: The realm the client is configured in.
        """
        return self.realm

    def get_client_id(self) -> str:
        """
        Getter for the OAuth2 client id.

        Returns:
            str: The clientId used for the client_credentials grant.
        """
        return self.client_id

    def get_cert_dir(self) -> str:
        """
        Getter for the client certificate directory.

        Returns:
            str: The directory on the test runner holding the client certificate material.
        """
        return self.cert_dir

    def get_served_port(self) -> int:
        """
        Getter for the O2 IMS API served port.

        Returns:
            int: The port the O2 IMS API is served on.
        """
        return self.served_port

    def get_issuer_admin_user(self) -> str:
        """
        Getter for the OAuth2 issuer admin username.

        Returns:
            str: The admin username used to administer the token issuer.
        """
        return self.issuer_admin_user

    def get_issuer_admin_password(self) -> str:
        """
        Getter for the OAuth2 issuer admin password.

        Returns:
            str: The admin password used to administer the token issuer.
        """
        return self.issuer_admin_password

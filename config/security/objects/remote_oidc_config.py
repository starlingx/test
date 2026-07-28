"""RemoteOidcConfig object for remote OIDC (Keycloak) connector."""


class RemoteOidcConfig:
    """Remote OIDC (Keycloak) connector configuration."""

    def __init__(self, oidc_dict: dict):
        """Initialize remote OIDC config.

        Args:
            oidc_dict (dict): Remote OIDC configuration dictionary.
        """
        self._issuer_url = oidc_dict.get("issuer_url", "")
        self._client_id = oidc_dict.get("client_id", "")
        self._client_secret = oidc_dict.get("client_secret", "")
        self._claim_mapping = oidc_dict.get("claim_mapping", {})

    def get_issuer_url(self) -> str:
        """Get OIDC issuer URL.

        Returns:
            str: Issuer URL.
        """
        return self._issuer_url

    def get_client_id(self) -> str:
        """Get OIDC client ID.

        Returns:
            str: Client ID.
        """
        return self._client_id

    def get_client_secret(self) -> str:
        """Get OIDC client secret.

        Returns:
            str: Client secret.
        """
        return self._client_secret

    def get_claim_mapping(self) -> dict:
        """Get claim mapping dictionary.

        Returns:
            dict: Claim mapping (e.g. {'email': 'email', 'name': 'name'}).
        """
        return self._claim_mapping

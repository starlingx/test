"""OidcUsernameClaim object for OIDC username claim configuration."""


class OidcUsernameClaim:
    """OIDC username claim configuration."""

    def __init__(self, claim_dict: dict):
        """Initialize username claim config.

        Args:
            claim_dict (dict): Username claim configuration dictionary.
        """
        self._default = claim_dict.get("default", "preferred_username")
        self._alternative = claim_dict.get("alternative", "email")

    def get_default(self) -> str:
        """Get default username claim.

        Returns:
            str: Default claim name.
        """
        return self._default

    def get_alternative(self) -> str:
        """Get alternative username claim.

        Returns:
            str: Alternative claim name.
        """
        return self._alternative

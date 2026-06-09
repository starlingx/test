"""Structured object for parsed OIDC ID token claims.

Provides typed accessors for standard OIDC claims (email, name,
preferred_username) decoded from the cached ID token.
"""


class OidcTokenClaimsObject:
    """Parsed OIDC ID token claims with typed getter methods.

    Wraps the decoded JWT claims dictionary and provides accessor
    methods for standard OIDC claim fields (email, preferred_username,
    name, groups, email_verified).
    """

    def __init__(self, claims_dict: dict):
        """Initialize with decoded token claims.

        Args:
            claims_dict (dict): Decoded JWT payload as dictionary.
        """
        self._claims = claims_dict

    def get_email(self) -> str:
        """Get the email claim value.

        Returns:
            str: Email address, or empty string if not present.
        """
        return self._claims.get("email", "")

    def get_preferred_username(self) -> str:
        """Get the preferred_username claim value.

        Returns:
            str: Preferred username, or empty string if not present.
        """
        return self._claims.get("preferred_username", "")

    def get_name(self) -> str:
        """Get the name claim value.

        Returns:
            str: Display name, or empty string if not present.
        """
        return self._claims.get("name", "")

    def get_groups(self) -> list:
        """Get the groups claim value.

        Returns:
            list: List of group names, or empty list if not present.
        """
        return self._claims.get("groups", [])

    def get_subject(self) -> str:
        """Get the sub (subject) claim value.

        Returns:
            str: Subject identifier, or empty string if not present.
        """
        return self._claims.get("sub", "")

    def has_email(self) -> bool:
        """Check if email claim is present and non-empty.

        Returns:
            bool: True if email claim has a value.
        """
        return bool(self._claims.get("email"))

    def has_name(self) -> bool:
        """Check if name claim is present and non-empty.

        Returns:
            bool: True if name claim has a value.
        """
        return bool(self._claims.get("name"))

    def has_preferred_username(self) -> bool:
        """Check if preferred_username claim is present and non-empty.

        Returns:
            bool: True if preferred_username claim has a value.
        """
        return bool(self._claims.get("preferred_username"))

    def is_email_verified(self) -> bool:
        """Check if email_verified claim is true.

        Returns:
            bool: True if email is verified, False otherwise.
        """
        return self._claims.get("email_verified", False)

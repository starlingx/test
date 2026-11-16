"""Output for 'kcadm.sh get users'."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.security.keycloak.objects.kcadm_json_output import KcadmJsonOutput


class KeycloakUserListOutput(KcadmJsonOutput):
    """Parses the user list returned by kcadm.sh."""

    def __init__(self, output: str | list):
        """Constructor.

        Args:
            output (str | list): Raw output of 'kcadm.sh get users'.
        """
        super().__init__(output, "user list")

    def is_user(self, username: str) -> bool:
        """Check whether a user is in the list.

        Keycloak stores usernames in lower case, so the comparison ignores case.

        Args:
            username (str): Username.

        Returns:
            bool: True if the user exists.
        """
        return any(entry.get("username", "").lower() == username.lower() for entry in self.get_json_list())

    def get_user_id(self, username: str) -> str:
        """Get the internal UUID of a user.

        Args:
            username (str): Username, compared ignoring case.

        Returns:
            str: The user's internal UUID.

        Raises:
            KeywordException: If the user is not in the list or has no id.
        """
        for entry in self.get_json_list():
            if entry.get("username", "").lower() == username.lower():
                user_id = entry.get("id")
                if not user_id:
                    raise KeywordException(f"User '{username}' returned no id field")
                return user_id
        raise KeywordException(f"User '{username}' not found")

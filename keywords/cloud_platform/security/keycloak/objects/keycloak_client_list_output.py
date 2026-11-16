"""Output for 'kcadm.sh get clients'."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.security.keycloak.objects.kcadm_json_output import KcadmJsonOutput


class KeycloakClientListOutput(KcadmJsonOutput):
    """Parses the client list returned by kcadm.sh."""

    def __init__(self, output: str | list):
        """Constructor.

        Args:
            output (str | list): Raw output of 'kcadm.sh get clients'.
        """
        super().__init__(output, "client list")

    def is_client(self, client_id: str) -> bool:
        """Check whether a client with the given clientId is in the list.

        Args:
            client_id (str): The clientId.

        Returns:
            bool: True if the client exists.
        """
        return any(entry.get("clientId") == client_id for entry in self.get_json_list())

    def get_client_uuid(self, client_id: str) -> str:
        """Get the internal UUID of a client.

        Args:
            client_id (str): The clientId.

        Returns:
            str: The client's internal UUID.

        Raises:
            KeywordException: If the client is not in the list or has no id.
        """
        for entry in self.get_json_list():
            if entry.get("clientId") == client_id:
                client_uuid = entry.get("id")
                if not client_uuid:
                    raise KeywordException(f"Client '{client_id}' returned no id field")
                return client_uuid
        raise KeywordException(f"Client '{client_id}' not found")

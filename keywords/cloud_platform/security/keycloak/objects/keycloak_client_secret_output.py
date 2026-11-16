"""Output for 'kcadm.sh get clients/<uuid>/client-secret'."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.security.keycloak.objects.kcadm_json_output import KcadmJsonOutput


class KeycloakClientSecretOutput(KcadmJsonOutput):
    """Parses the client secret returned by kcadm.sh."""

    def __init__(self, output: str | list):
        """Constructor.

        Args:
            output (str | list): Raw output of 'kcadm.sh get clients/<uuid>/client-secret'.
        """
        super().__init__(output, "client secret")

    def get_secret(self) -> str:
        """Get the client secret.

        Returns:
            str: The client secret.

        Raises:
            KeywordException: If the response contains no secret value.
        """
        secret = self.get_json_dict().get("value")
        if not secret:
            raise KeywordException("Client secret response contains no value")
        return secret

"""Output for 'kcadm.sh get realms'."""

from keywords.cloud_platform.security.keycloak.objects.kcadm_json_output import KcadmJsonOutput


class KeycloakRealmListOutput(KcadmJsonOutput):
    """Parses the realm list returned by kcadm.sh."""

    def __init__(self, output: str | list):
        """Constructor.

        Args:
            output (str | list): Raw output of 'kcadm.sh get realms'.
        """
        super().__init__(output, "realm list")

    def is_realm(self, realm: str) -> bool:
        """Check whether a realm is in the list.

        Args:
            realm (str): Realm name.

        Returns:
            bool: True if the realm exists.
        """
        return any(entry.get("realm") == realm for entry in self.get_json_list())

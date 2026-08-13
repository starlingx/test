"""Output class for Barbican Secret List REST API response."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.barbican.objects.barbican_secret_object import BarbicanSecretObject


class BarbicanSecretListOutput:
    """Parses Barbican /v1/secrets REST API response into list of BarbicanSecretObject."""

    def __init__(self, response: RestResponse):
        """Initialize BarbicanSecretListOutput from REST response.

        Args:
            response (RestResponse): The REST response from Barbican API.
        """
        self.secret_objects = []
        secrets = response.get_json_content().get("secrets", [])
        for secret in secrets:
            secret_object = BarbicanSecretObject()
            if secret.get("secret_ref"):
                secret_object.set_secret_ref(secret["secret_ref"])
            if secret.get("name"):
                secret_object.set_name(secret["name"])
            if secret.get("status"):
                secret_object.set_status(secret["status"])
            if secret.get("created"):
                secret_object.set_created(secret["created"])
            self.secret_objects.append(secret_object)

    def get_secret_objects(self) -> list[BarbicanSecretObject]:
        """Get list of BarbicanSecretObject.

        Returns:
            list[BarbicanSecretObject]: List of BarbicanSecretObject instances.
        """
        return self.secret_objects

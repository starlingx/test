"""Output class for Barbican Secret REST API response."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.barbican.objects.barbican_secret_object import BarbicanSecretObject


class BarbicanSecretOutput:
    """Parses Barbican /v1/secrets/{id} REST API response into BarbicanSecretObject."""

    def __init__(self, response: RestResponse):
        """Initialize BarbicanSecretOutput from REST response.

        Args:
            response (RestResponse): The REST response from Barbican API.
        """
        secret = response.get_json_content()
        self.secret_object = BarbicanSecretObject()
        if secret.get("secret_ref"):
            self.secret_object.set_secret_ref(secret["secret_ref"])
        if secret.get("name"):
            self.secret_object.set_name(secret["name"])
        if secret.get("status"):
            self.secret_object.set_status(secret["status"])
        if secret.get("created"):
            self.secret_object.set_created(secret["created"])

    def get_secret_object(self) -> BarbicanSecretObject:
        """Get the BarbicanSecretObject.

        Returns:
            BarbicanSecretObject: The parsed secret object.
        """
        return self.secret_object

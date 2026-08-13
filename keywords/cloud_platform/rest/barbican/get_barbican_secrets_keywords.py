"""Keywords for Barbican secrets REST API operations."""

import json

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.barbican.objects.barbican_secret_list_output import BarbicanSecretListOutput
from keywords.cloud_platform.rest.barbican.objects.barbican_secret_output import BarbicanSecretOutput
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetBarbicanSecretsKeywords(BaseKeyword):
    """Keywords for Barbican secrets REST API operations."""

    def __init__(self):
        """Initialize GetBarbicanSecretsKeywords with Barbican base URL."""
        self.barbican_base_url = GetRestUrlKeywords().get_barbican_url()

    def list_secrets(self) -> BarbicanSecretListOutput:
        """List all secrets via Barbican REST API.

        Returns:
            BarbicanSecretListOutput: Parsed output with list of BarbicanSecretObject.
        """
        response = CloudRestClient().get(f"{self.barbican_base_url}/v1/secrets")
        self.validate_success_status_code(response)
        return BarbicanSecretListOutput(response)

    def create_secret(self, secret_name: str, payload: str | None = None) -> BarbicanSecretOutput:
        """Create a secret via Barbican REST API.

        Args:
            secret_name (str): The name of the secret.
            payload (str | None): Optional payload for the secret.

        Returns:
            BarbicanSecretOutput: Parsed output with created BarbicanSecretObject.
        """
        body = {"name": secret_name}
        if payload:
            body["payload"] = payload
            body["payload_content_type"] = "text/plain"
        response = CloudRestClient().post(f"{self.barbican_base_url}/v1/secrets", data=json.dumps(body))
        self.validate_success_status_code(response, expected_status_code=201)
        return BarbicanSecretOutput(response)

    def get_secret(self, secret_id: str) -> BarbicanSecretOutput:
        """Get a secret by ID via Barbican REST API.

        Args:
            secret_id (str): UUID of the secret.

        Returns:
            BarbicanSecretOutput: Parsed output with BarbicanSecretObject.
        """
        response = CloudRestClient().get(f"{self.barbican_base_url}/v1/secrets/{secret_id}")
        self.validate_success_status_code(response)
        return BarbicanSecretOutput(response)

    def update_secret(self, secret_id: str, payload: str):
        """Update a secret payload via Barbican REST API.

        Args:
            secret_id (str): UUID of the secret.
            payload (str): The payload to update.
        """
        response = CloudRestClient().put(f"{self.barbican_base_url}/v1/secrets/{secret_id}", data=payload, content_type="text/plain")
        self.validate_success_status_code(response, expected_status_code=204)

    def delete_secret(self, secret_id: str):
        """Delete a secret via Barbican REST API.

        Args:
            secret_id (str): UUID of the secret to delete.
        """
        response = CloudRestClient().delete(f"{self.barbican_base_url}/v1/secrets/{secret_id}")
        self.validate_success_status_code(response, expected_status_code=204)

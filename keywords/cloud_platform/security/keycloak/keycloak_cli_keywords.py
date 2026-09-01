"""Keywords for driving the Keycloak admin CLI (kcadm.sh) inside a container."""

import json
import shlex

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.docker.container.docker_container_keywords import DockerContainerKeywords


class KeycloakCliKeywords(BaseKeyword):
    """Keywords for Keycloak realm and client administration via kcadm.sh.

    Runs kcadm.sh inside a containerized Keycloak instance over the existing SSH
    connection, rather than calling the Keycloak admin REST API from the test
    runner. This works on labs where the runner has no HTTP route to the
    Keycloak port, since every command executes on the host running the
    container.

    For runner-side admin REST operations against an already-reachable Keycloak,
    use KeycloakAdminKeywords instead.
    """

    KCADM = "/opt/keycloak/bin/kcadm.sh"

    def __init__(self, ssh_connection: SSHConnection, container_name: str, keycloak_url: str):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host running the
                Keycloak container.
            container_name (str): Name of the Keycloak container.
            keycloak_url (str): Keycloak base URL as seen from inside the container
                (e.g. http://localhost:28080).
        """
        self.ssh_connection = ssh_connection
        self.container_name = container_name
        self.keycloak_url = keycloak_url
        self.container_keywords = DockerContainerKeywords(ssh_connection)

    def wait_for_keycloak_ready(self, realm: str = "master", timeout: int = 180, polling_sleep_time: int = 6) -> None:
        """Wait until the Keycloak realm endpoint answers.

        Args:
            realm (str): Realm to poll. Defaults to "master".
            timeout (int): Maximum time to wait in seconds. Defaults to 180.
            polling_sleep_time (int): Seconds between polls. Defaults to 6.
        """
        validate_equals_with_retry(
            lambda: self._get_realm_http_status(realm),
            "200",
            f"Keycloak realm '{realm}' endpoint is serving",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

    def login_as_admin(self, admin_username: str, admin_password: str, realm: str = "master") -> None:
        """Authenticate kcadm.sh against the Keycloak server.

        Must be called before any other kcadm operation; kcadm stores the
        resulting credentials inside the container for subsequent commands.

        Args:
            admin_username (str): Keycloak admin username.
            admin_password (str): Keycloak admin password.
            realm (str): Realm to authenticate against. Defaults to "master".
        """
        cmd = f"{self.KCADM} config credentials --server {shlex.quote(self.keycloak_url)} --realm {shlex.quote(realm)} --user {shlex.quote(admin_username)} --password {shlex.quote(admin_password)}"
        self.container_keywords.exec_in_container(self.container_name, cmd)
        get_logger().log_info(f"Authenticated kcadm against {self.keycloak_url} as '{admin_username}'")

    def update_realm(self, realm: str = "master", ssl_required: str = None, access_token_lifespan: int = None) -> None:
        """Update realm-level settings.

        Args:
            realm (str): Realm to update. Defaults to "master".
            ssl_required (str): Value for sslRequired (e.g. "NONE", "external", "all").
                Set to "NONE" to allow plain HTTP access. Defaults to None (unchanged).
            access_token_lifespan (int): Access token lifetime in seconds. Raise this
                when a test run is longer than the default lifetime. Defaults to None
                (unchanged).
        """
        settings = []
        if ssl_required is not None:
            settings.append(f"-s sslRequired={shlex.quote(ssl_required)}")
        if access_token_lifespan is not None:
            settings.append(f"-s accessTokenLifespan={access_token_lifespan}")
        if not settings:
            get_logger().log_info(f"No realm settings supplied for '{realm}', skipping update")
            return

        cmd = f"{self.KCADM} update realms/{shlex.quote(realm)} {' '.join(settings)}"
        self.container_keywords.exec_in_container(self.container_name, cmd)
        get_logger().log_info(f"Updated realm '{realm}': {' '.join(settings)}")

    def create_confidential_client(self, client_id: str, realm: str = "master", client_secret: str = None) -> str:
        """Create a confidential client that supports the client_credentials grant.

        Enables service accounts and direct access grants so the client can obtain
        tokens without a browser flow.

        Args:
            client_id (str): The clientId to create.
            realm (str): Realm to create the client in. Defaults to "master".
            client_secret (str): Secret to assign to the client. Supply a known
                value so that consumers can be configured ahead of time; Keycloak
                otherwise generates a different secret on every creation. Defaults
                to None, which leaves the generated secret in place.

        Returns:
            str: The internal UUID of the created client, needed to read its secret.
        """
        cmd = f"{self.KCADM} create clients -r {shlex.quote(realm)} -s clientId={shlex.quote(client_id)} -s enabled=true -s clientAuthenticatorType=client-secret -s publicClient=false -s standardFlowEnabled=true -s directAccessGrantsEnabled=true -s serviceAccountsEnabled=true"
        self.container_keywords.exec_in_container(self.container_name, cmd)
        get_logger().log_info(f"Created confidential client '{client_id}' in realm '{realm}'")
        client_uuid = self.get_client_uuid(client_id, realm)
        if client_secret:
            self.set_client_secret(client_uuid, client_secret, realm)
        return client_uuid

    def set_client_secret(self, client_uuid: str, client_secret: str, realm: str = "master") -> None:
        """Set a client's secret to a known value.

        Args:
            client_uuid (str): Internal UUID of the client (not the clientId).
            client_secret (str): The secret to assign.
            realm (str): Realm containing the client. Defaults to "master".
        """
        cmd = f"{self.KCADM} update clients/{shlex.quote(client_uuid)} -r {shlex.quote(realm)} -s secret={shlex.quote(client_secret)}"
        self.container_keywords.exec_in_container(self.container_name, cmd)
        get_logger().log_info(f"Set secret for client uuid '{client_uuid}'")

    def get_client_uuid(self, client_id: str, realm: str = "master") -> str:
        """Get the internal UUID of a client from its clientId.

        Args:
            client_id (str): The clientId to look up.
            realm (str): Realm containing the client. Defaults to "master".

        Returns:
            str: The client's internal UUID.

        Raises:
            KeywordException: If the client is not found or the response cannot be parsed.
        """
        cmd = f"{self.KCADM} get clients -r {shlex.quote(realm)} -q clientId={shlex.quote(client_id)}"
        output = self.container_keywords.exec_in_container(self.container_name, cmd)
        clients = self._parse_json(output, f"client list for '{client_id}'")
        if not clients:
            raise KeywordException(f"Client '{client_id}' not found in realm '{realm}'")
        client_uuid = clients[0].get("id")
        if not client_uuid:
            raise KeywordException(f"Client '{client_id}' returned no id field in realm '{realm}'")
        return client_uuid

    def get_client_secret(self, client_uuid: str, realm: str = "master") -> str:
        """Get the secret of a confidential client.

        Args:
            client_uuid (str): Internal UUID of the client (not the clientId).
            realm (str): Realm containing the client. Defaults to "master".

        Returns:
            str: The client secret.

        Raises:
            KeywordException: If the secret is absent from the response.
        """
        cmd = f"{self.KCADM} get clients/{shlex.quote(client_uuid)}/client-secret -r {shlex.quote(realm)}"
        output = self.container_keywords.exec_in_container(self.container_name, cmd)
        secret_data = self._parse_json(output, f"client secret for '{client_uuid}'")
        secret = secret_data.get("value")
        if not secret:
            raise KeywordException(f"Client '{client_uuid}' returned no secret value in realm '{realm}'")
        get_logger().log_info(f"Retrieved client secret for client uuid '{client_uuid}'")
        return secret

    def get_realm_public_key(self, realm: str = "master") -> str:
        """Get the realm's RSA public key used to sign access tokens.

        The key is returned as a bare base64 body with no PEM header or footer,
        which is how the realm endpoint reports it and the form consumers should
        pass on. Adding PEM delimiters is generally wrong: applications that need
        them add them themselves, and supplying them twice produces a malformed
        key that fails signature validation.

        Only available once the realm is serving, so call wait_for_keycloak_ready
        first.

        Args:
            realm (str): Realm to read. Defaults to "master".

        Returns:
            str: The base64-encoded public key body, without PEM delimiters.

        Raises:
            KeywordException: If the realm response contains no public_key.
        """
        output = self.ssh_connection.send(f"curl -s {shlex.quote(f'{self.keycloak_url}/realms/{realm}')}")
        realm_data = self._parse_json(output, f"realm metadata for '{realm}'")
        public_key = realm_data.get("public_key")
        if not public_key:
            raise KeywordException(f"Realm '{realm}' metadata contains no public_key field")
        get_logger().log_info(f"Retrieved realm '{realm}' public key ({len(public_key)} chars)")
        return public_key

    def get_token(self, client_id: str, client_secret: str, realm: str = "master") -> str:
        """Obtain an access token using the client_credentials grant.

        Runs curl on the remote host rather than from the test runner, so it works
        regardless of whether the runner has an HTTP route to Keycloak. Useful for
        validating the OAuth2 setup during bring-up.

        Args:
            client_id (str): The clientId to authenticate as.
            client_secret (str): The client secret.
            realm (str): Realm containing the client. Defaults to "master".

        Returns:
            str: The access token.

        Raises:
            KeywordException: If the response contains no access_token.
        """
        token_url = f"{self.keycloak_url}/realms/{realm}/protocol/openid-connect/token"
        data = f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}"
        cmd = f"curl -s -X POST {shlex.quote(token_url)} -H 'Content-Type: application/x-www-form-urlencoded' -d {shlex.quote(data)}"
        output = self.ssh_connection.send(cmd)
        token_data = self._parse_json(output, "token response")
        access_token = token_data.get("access_token")
        if not access_token:
            raise KeywordException(f"Token response for client '{client_id}' contains no access_token: {list(token_data.keys())}")
        get_logger().log_info(f"Obtained access token for client '{client_id}' ({len(access_token)} chars)")
        return access_token

    def _get_realm_http_status(self, realm: str) -> str:
        """Get the HTTP status code returned by the realm endpoint.

        Args:
            realm (str): Realm to query.

        Returns:
            str: The HTTP status code as a string, or "000" if no response.
        """
        cmd = f"curl -s -o /dev/null -w '%{{http_code}}' {shlex.quote(f'{self.keycloak_url}/realms/{realm}')}"
        output = self.ssh_connection.send(cmd)
        text = "\n".join(output) if isinstance(output, list) else output
        return text.strip().splitlines()[-1].strip() if text.strip() else "000"

    def _parse_json(self, output: str | list, description: str) -> dict | list:
        """Parse JSON from command output, tolerating leading non-JSON lines.

        kcadm returns clean JSON, but the surrounding shell can prepend warnings
        or echoed input, so parsing starts at the first '{' or '['.

        Args:
            output (str | list): Raw command output.
            description (str): What is being parsed, for the error message.

        Returns:
            dict | list: The parsed JSON.

        Raises:
            KeywordException: If no JSON body can be located or parsed.
        """
        text = "\n".join(output) if isinstance(output, list) else output
        start_positions = [pos for pos in (text.find("{"), text.find("[")) if pos != -1]
        if not start_positions:
            raise KeywordException(f"No JSON body found in {description}: {text[:300]}")
        try:
            return json.loads(text[min(start_positions) :])
        except json.JSONDecodeError as e:
            raise KeywordException(f"Failed to parse JSON from {description}: {e}. Raw output: {text[:300]}")

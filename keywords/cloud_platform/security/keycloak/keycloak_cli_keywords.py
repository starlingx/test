"""Keywords for driving the Keycloak admin CLI (kcadm.sh) inside a container or pod."""

import json
import os
import shlex
import tempfile
from typing import Dict, List, Optional

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.keycloak.objects.kcadm_json_output import KcadmJsonOutput
from keywords.cloud_platform.security.keycloak.objects.keycloak_client_list_output import KeycloakClientListOutput
from keywords.cloud_platform.security.keycloak.objects.keycloak_client_secret_output import KeycloakClientSecretOutput
from keywords.cloud_platform.security.keycloak.objects.keycloak_realm_list_output import KeycloakRealmListOutput
from keywords.cloud_platform.security.keycloak.objects.keycloak_user_list_output import KeycloakUserListOutput
from keywords.docker.container.docker_container_keywords import DockerContainerKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords


class KeycloakCliKeywords(BaseKeyword):
    """Keywords for Keycloak realm and client administration via kcadm.sh.

    Runs kcadm.sh inside a Keycloak instance over the existing SSH connection,
    rather than calling the Keycloak admin REST API from the test runner. This
    works on labs where the runner has no HTTP route to the Keycloak port, since
    every command executes on the host.

    The instance is reached either with docker exec (container_name) or with
    kubectl exec (pod_name and pod_namespace); exactly one must be given.
    wait_for_keycloak_ready, get_realm_public_key and get_token call
    keycloak_url with curl from the host, so they need container_name.

    For runner-side admin REST operations against an already-reachable Keycloak,
    use KeycloakAdminKeywords instead.
    """

    KCADM = "/opt/keycloak/bin/kcadm.sh"

    def __init__(self, ssh_connection: SSHConnection, container_name: Optional[str], keycloak_url: str, pod_name: Optional[str] = None, pod_namespace: Optional[str] = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host running Keycloak.
            container_name (Optional[str]): Name of the Keycloak container, for docker exec.
                Pass None when using pod_name.
            keycloak_url (str): Keycloak base URL as seen from inside the container or pod
                (e.g. http://localhost:28080).
            pod_name (Optional[str]): Name of the Keycloak pod, for kubectl exec. Defaults to None.
            pod_namespace (Optional[str]): Namespace of the Keycloak pod. Required with pod_name.
                Defaults to None.

        Raises:
            KeywordException: If neither or both of container_name and pod_name are given,
                or pod_name is given without pod_namespace.
        """
        if bool(container_name) == bool(pod_name):
            raise KeywordException("Exactly one of container_name and pod_name must be given")
        if pod_name and not pod_namespace:
            raise KeywordException("pod_namespace is required with pod_name")
        self.ssh_connection = ssh_connection
        self.container_name = container_name
        self.keycloak_url = keycloak_url
        self.pod_name = pod_name
        self.pod_namespace = pod_namespace
        self.container_keywords = DockerContainerKeywords(ssh_connection)
        self.pod_exec_keywords = KubectlExecInPodsKeywords(ssh_connection)

    def wait_for_keycloak_ready(self, realm: str = "master", timeout: int = 180, polling_sleep_time: int = 6) -> None:
        """Wait until the Keycloak realm endpoint answers.

        Args:
            realm (str): Realm to poll. Defaults to "master".
            timeout (int): Maximum time to wait in seconds. Defaults to 180.
            polling_sleep_time (int): Seconds between polls. Defaults to 6.

        Raises:
            KeywordException: If the instance is a pod (see _raise_if_pod_instance).
        """
        self._raise_if_pod_instance("wait_for_keycloak_ready")
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
        self.exec_in_container(cmd)
        get_logger().log_info(f"Authenticated kcadm against {self.keycloak_url} as '{admin_username}'")

    def update_realm(self, realm: str = "master", ssl_required: Optional[str] = None, access_token_lifespan: Optional[int] = None, access_token_lifespan_for_implicit_flow: Optional[int] = None) -> None:
        """Update realm-level settings.

        Args:
            realm (str): Realm to update. Defaults to "master".
            ssl_required (Optional[str]): Value for sslRequired (e.g. "NONE", "external", "all").
                Set to "NONE" to allow plain HTTP access. Defaults to None (unchanged).
            access_token_lifespan (Optional[int]): Access token lifetime in seconds. Raise this
                when a test run is longer than the default lifetime. Defaults to None
                (unchanged).
            access_token_lifespan_for_implicit_flow (Optional[int]): Access token lifetime in
                seconds for the implicit flow. Defaults to None (unchanged).
        """
        settings = []
        if ssl_required is not None:
            settings.append(f"-s sslRequired={shlex.quote(ssl_required)}")
        if access_token_lifespan is not None:
            settings.append(f"-s accessTokenLifespan={access_token_lifespan}")
        if access_token_lifespan_for_implicit_flow is not None:
            settings.append(f"-s accessTokenLifespanForImplicitFlow={access_token_lifespan_for_implicit_flow}")
        if not settings:
            get_logger().log_info(f"No realm settings supplied for '{realm}', skipping update")
            return

        cmd = f"{self.KCADM} update realms/{shlex.quote(realm)} {' '.join(settings)}"
        self.exec_in_container(cmd)
        get_logger().log_info(f"Updated realm '{realm}': {' '.join(settings)}")

    def create_confidential_client(self, client_id: str, realm: str = "master", client_secret: Optional[str] = None) -> str:
        """Create a confidential client that supports the client_credentials grant.

        Enables service accounts and direct access grants so the client can obtain
        tokens without a browser flow.

        Args:
            client_id (str): The clientId to create.
            realm (str): Realm to create the client in. Defaults to "master".
            client_secret (Optional[str]): Secret to assign to the client. Supply a known
                value so that consumers can be configured ahead of time; Keycloak
                otherwise generates a different secret on every creation. Defaults
                to None, which leaves the generated secret in place.

        Returns:
            str: The internal UUID of the created client, needed to read its secret.
        """
        cmd = f"{self.KCADM} create clients -r {shlex.quote(realm)} -s clientId={shlex.quote(client_id)} -s enabled=true -s clientAuthenticatorType=client-secret -s publicClient=false -s standardFlowEnabled=true -s directAccessGrantsEnabled=true -s serviceAccountsEnabled=true"
        self.exec_in_container(cmd)
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
        self.exec_in_container(cmd)
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
        client_list = self._get_client_list(client_id, realm)
        if not client_list.is_client(client_id):
            raise KeywordException(f"Client '{client_id}' not found in realm '{realm}'")
        return client_list.get_client_uuid(client_id)

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
        secret = KeycloakClientSecretOutput(self.exec_in_container(cmd)).get_secret()
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
            KeywordException: If the instance is a pod, or the realm response contains no public_key.
        """
        self._raise_if_pod_instance("get_realm_public_key")
        output = self.ssh_connection.send(f"curl -s {shlex.quote(f'{self.keycloak_url}/realms/{realm}')}")
        realm_data = KcadmJsonOutput(output, f"realm metadata for '{realm}'").get_json_dict()
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
            KeywordException: If the instance is a pod, or the response contains no access_token.
        """
        self._raise_if_pod_instance("get_token")
        token_url = f"{self.keycloak_url}/realms/{realm}/protocol/openid-connect/token"
        data = f"grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}"
        cmd = f"curl -s -X POST {shlex.quote(token_url)} -H 'Content-Type: application/x-www-form-urlencoded' -d {shlex.quote(data)}"
        output = self.ssh_connection.send(cmd)
        token_data = KcadmJsonOutput(output, "token response").get_json_dict()
        access_token = token_data.get("access_token")
        if not access_token:
            raise KeywordException(f"Token response for client '{client_id}' contains no access_token: {list(token_data.keys())}")
        get_logger().log_info(f"Obtained access token for client '{client_id}' ({len(access_token)} chars)")
        return access_token

    def is_realm_present(self, realm: str) -> bool:
        """Check whether a realm exists.

        Lists the realms rather than reading the realm directly, so a kcadm
        failure surfaces as an error instead of being mistaken for an absent realm.

        Args:
            realm (str): Realm name.

        Returns:
            bool: True if the realm exists.
        """
        return KeycloakRealmListOutput(self.exec_in_container(f"{self.KCADM} get realms --fields realm")).is_realm(realm)

    def ensure_realm(self, realm: str) -> None:
        """Create a realm if it does not exist.

        Args:
            realm (str): Realm name.
        """
        if self.is_realm_present(realm):
            get_logger().log_info(f"Realm '{realm}' already exists, skipping create")
            return
        self.exec_in_container(f"{self.KCADM} create realms -s realm={shlex.quote(realm)} -s enabled=true")
        get_logger().log_info(f"Created realm '{realm}'")

    def is_client_present(self, client_id: str, realm: str = "master") -> bool:
        """Check whether a client exists.

        Args:
            client_id (str): The clientId.
            realm (str): Realm containing the client. Defaults to "master".

        Returns:
            bool: True if the client exists.
        """
        return self._get_client_list(client_id, realm).is_client(client_id)

    def ensure_standard_flow_client(self, client_id: str, redirect_uris: List[str], realm: str = "master", extra_settings: Optional[Dict[str, str]] = None) -> str:
        """Create or update a confidential OIDC client using the standard (code) flow.

        The redirect URIs and settings are written on every call, so they always
        match the caller's current values.

        Args:
            client_id (str): The clientId.
            redirect_uris (List[str]): Valid redirect URIs for the client.
            realm (str): Realm containing the client. Defaults to "master".
            extra_settings (Optional[Dict[str, str]]): Additional client settings, each
                passed to kcadm as '-s key=value' (e.g. {"directAccessGrantsEnabled": "false"}).
                Defaults to None.

        Returns:
            str: The internal UUID of the client.
        """
        settings = [
            "-s enabled=true",
            "-s protocol=openid-connect",
            "-s publicClient=false",
            "-s clientAuthenticatorType=client-secret",
            "-s standardFlowEnabled=true",
            "-s " + shlex.quote("redirectUris=" + json.dumps(redirect_uris)),
        ] + ["-s " + shlex.quote(f"{key}={value}") for key, value in (extra_settings or {}).items()]
        realm_arg = shlex.quote(realm)
        client_list = self._get_client_list(client_id, realm)
        if client_list.is_client(client_id):
            client_uuid = client_list.get_client_uuid(client_id)
            self.exec_in_container(f"{self.KCADM} update clients/{shlex.quote(client_uuid)} -r {realm_arg} {' '.join(settings)}")
            get_logger().log_info(f"Updated client '{client_id}' in realm '{realm}'")
            return client_uuid
        self.exec_in_container(f"{self.KCADM} create clients -r {realm_arg} -s clientId={shlex.quote(client_id)} {' '.join(settings)}")
        get_logger().log_info(f"Created client '{client_id}' in realm '{realm}'")
        return self.get_client_uuid(client_id, realm)

    def get_user_list(self, username: str, realm: str = "master") -> KeycloakUserListOutput:
        """Get the users matching a username.

        Query the returned object (for example is_user or get_user_id) instead of
        running this command again.

        Args:
            username (str): The username to look up.
            realm (str): Realm containing the user. Defaults to "master".

        Returns:
            KeycloakUserListOutput: The matching users.
        """
        cmd = f"{self.KCADM} get users -r {shlex.quote(realm)} -q username={shlex.quote(username)} --fields id,username"
        return KeycloakUserListOutput(self.exec_in_container(cmd))

    def ensure_user(self, username: str, password: str, realm: str = "master", email: str = "", first_name: str = "", last_name: str = "") -> None:
        """Create a user if absent, then set its password.

        The password is set on every call so the given credentials always work.
        It is never put on a command line: it is passed to kcadm on stdin (see
        _set_password), so it does not appear in the process list or the SSH
        command log. Requires pod_name.

        Args:
            username (str): Username.
            password (str): Password to set.
            realm (str): Realm to create the user in. Defaults to "master".
            email (str): Email address, marked as verified. Defaults to "".
            first_name (str): First name. Defaults to "".
            last_name (str): Last name. Defaults to "".
        """
        realm_arg = shlex.quote(realm)
        user_list = self.get_user_list(username, realm)
        if user_list.is_user(username):
            get_logger().log_info(f"User '{username}' already exists in realm '{realm}', skipping create")
        else:
            settings = [f"-s username={shlex.quote(username)}", "-s enabled=true"]
            if email:
                settings += [f"-s email={shlex.quote(email)}", "-s emailVerified=true"]
            if first_name:
                settings.append(f"-s firstName={shlex.quote(first_name)}")
            if last_name:
                settings.append(f"-s lastName={shlex.quote(last_name)}")
            self.exec_in_container(f"{self.KCADM} create users -r {realm_arg} {' '.join(settings)}")
            get_logger().log_info(f"Created user '{username}' in realm '{realm}'")
        self._set_password(self.get_user_list(username, realm).get_user_id(username), password, realm)
        get_logger().log_info(f"Set the password of user '{username}' in realm '{realm}'")

    def _set_password(self, user_uuid: str, password: str, realm: str) -> None:
        """Set a user's password without putting it on a command line.

        The credential is uploaded over SFTP, which is not written to the command
        log, into a private temporary directory on the host. It is then passed to
        kcadm on stdin and the directory is removed.

        Args:
            user_uuid (str): Internal UUID of the user.
            password (str): The password to set.
            realm (str): Realm containing the user.
        """
        output = self.ssh_connection.send("mktemp -d")
        self.validate_success_return_code(self.ssh_connection)
        lines = output if isinstance(output, list) else output.splitlines()
        remote_dir = [line.strip() for line in lines if line.strip()][-1]
        remote_file = f"{remote_dir}/credential.json"
        file_keywords = FileKeywords(self.ssh_connection)
        try:
            with tempfile.TemporaryDirectory() as local_dir:
                local_file = os.path.join(local_dir, "credential.json")
                with open(local_file, "w") as credential:
                    json.dump({"type": "password", "value": password, "temporary": False}, credential)
                file_keywords.upload_file(local_file, remote_file)
            self._exec_with_stdin(f"{self.KCADM} update users/{shlex.quote(user_uuid)}/reset-password -r {shlex.quote(realm)} -n -f -", remote_file)
        finally:
            file_keywords.delete_directory(remote_dir)

    def _get_client_list(self, client_id: str, realm: str) -> KeycloakClientListOutput:
        """Get the clients matching a clientId.

        Args:
            client_id (str): The clientId to look up.
            realm (str): Realm containing the client.

        Returns:
            KeycloakClientListOutput: The matching clients.
        """
        cmd = f"{self.KCADM} get clients -r {shlex.quote(realm)} -q clientId={shlex.quote(client_id)} --fields id,clientId"
        return KeycloakClientListOutput(self.exec_in_container(cmd))

    def exec_in_container(self, cmd: str) -> str:
        """Run a command inside the Keycloak container or pod and assert success.

        Args:
            cmd (str): The command to run.

        Returns:
            str: The command output.
        """
        if self.pod_name:
            output = self.pod_exec_keywords.run_pod_exec_cmd(shlex.quote(self.pod_name), cmd, options=f"-n {shlex.quote(self.pod_namespace)}")
            return "\n".join(output) if isinstance(output, list) else output
        return self.container_keywords.exec_in_container(self.container_name, cmd)

    def _exec_with_stdin(self, cmd: str, stdin_file: str) -> str:
        """Run a command inside the Keycloak pod with a host file as its standard input.

        Args:
            cmd (str): The command to run.
            stdin_file (str): Path on the host of the file passed on stdin.

        Returns:
            str: The command output.

        Raises:
            KeywordException: If the instance is a container; docker exec is run without stdin.
        """
        if not self.pod_name:
            raise KeywordException("Passing a file on stdin is only supported with pod_name")
        output = self.pod_exec_keywords.run_pod_exec_cmd(shlex.quote(self.pod_name), f"{cmd} < {shlex.quote(stdin_file)}", options=f"-i -n {shlex.quote(self.pod_namespace)}")
        return "\n".join(output) if isinstance(output, list) else output

    def _raise_if_pod_instance(self, operation: str) -> None:
        """Fail when an operation that curls keycloak_url from the host runs against a pod.

        In pod mode keycloak_url is the URL seen from inside the pod, which the
        host cannot reach, so these operations would only time out.

        Args:
            operation (str): Name of the calling operation, for the error message.

        Raises:
            KeywordException: If the instance is a pod.
        """
        if self.pod_name:
            raise KeywordException(f"{operation} calls keycloak_url from the host and is only supported with container_name")

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

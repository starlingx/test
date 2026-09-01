import os
import uuid
from base64 import b64encode

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_greater_than
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.openstack.openstack_credentials_keywords import OpenStackCredentialsKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.openssl.openssl_keywords import OpenSSLKeywords

# One of the downloaded certificate files is a private key, so the directory and
# its contents are restricted to the owning user rather than left to the umask.
DIRECTORY_MODE_OWNER_ONLY = 0o700
FILE_MODE_OWNER_ONLY = 0o600


class OranO2Keywords(BaseKeyword):
    """Keywords for O-RAN O2 application operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection

    def create_smo_service_account(self, smo_service_account: str = "smo1") -> None:
        """Create the SMO service account, role and role binding.

        Args:
            smo_service_account (str): Name of the SMO service account. Defaults to 'smo1'.
        """
        get_logger().log_info("Creating SMO service account")
        template_path = get_stx_resource_path("resources/cloud_platform/applications/o_ran/smo-serviceaccount.yaml.j2")
        replacement_dict = {"smo_service_account": smo_service_account}
        yaml_keywords = YamlKeywords(self.ssh_connection)
        remote_file = yaml_keywords.generate_yaml_file_from_template(template_path, replacement_dict, "smo-serviceaccount.yaml", "/tmp")
        KubectlFileApplyKeywords(self.ssh_connection).apply_resource_from_yaml(remote_file)

    def create_smo_secret(self, smo_secret: str = "smo1-secret", smo_service_account: str = "smo1") -> str:
        """Create the SMO service account token secret and return its token.

        Args:
            smo_secret (str): Name of the SMO secret. Defaults to 'smo1-secret'.
            smo_service_account (str): Name of the SMO service account. Defaults to 'smo1'.

        Returns:
            str: The base64-encoded service account token, as required by the
                smo_token_data application configuration value.
        """
        get_logger().log_info("Creating SMO secret")
        template_path = get_stx_resource_path("resources/cloud_platform/applications/o_ran/smo-secret.yaml.j2")
        replacement_dict = {"smo_secret": smo_secret, "smo_service_account": smo_service_account}
        yaml_keywords = YamlKeywords(self.ssh_connection)
        remote_file = yaml_keywords.generate_yaml_file_from_template(template_path, replacement_dict, "smo-secret.yaml", "/tmp")
        KubectlFileApplyKeywords(self.ssh_connection).apply_resource_from_yaml(remote_file)
        return self.get_smo_token(smo_secret)

    def get_smo_token(self, smo_secret: str = "smo1-secret", namespace: str = "default") -> str:
        """Get the base64-encoded token from an SMO service account token secret.

        The token is returned still base64-encoded, which is the form the
        application configuration expects.

        Args:
            smo_secret (str): Name of the SMO secret. Defaults to 'smo1-secret'.
            namespace (str): Namespace containing the secret. Defaults to 'default'.

        Returns:
            str: The base64-encoded service account token.
        """
        # base64=False keeps the token base64-encoded, the form app.conf consumes.
        # The sibling call in regression/applications/test_o_ran_o2.py decodes it
        # because it uses the token directly.
        token = KubectlGetSecretsKeywords(self.ssh_connection).get_secret_with_custom_output(smo_secret, namespace, "jsonpath", "'{.data.token}'", base64=False).strip()
        validate_greater_than(len(token), 0, "SMO token retrieved")
        get_logger().log_info(f"Retrieved SMO token from secret '{smo_secret}' ({len(token)} chars)")
        return token

    def create_app_config_file(self, smo_register_url: str, ocloud_global_id: str = None, smo_token_data: str = "", oauth2_public_key: str = None, oauth2_verify_type: str = "jwt", oauth2_algorithm: str = "RS256") -> None:
        """Create the O2 application configuration file.

        The rendered file is mounted into the pod verbatim as /configs/o2app.conf.
        Nothing expands shell variables, so every value must be supplied in full:
        the chart declares OS_AUTH_URL, OS_USERNAME and OS_PASSWORD with no values,
        and leaving them unresolved makes the watcher serve no resource data.

        Args:
            smo_register_url (str): URL for SMO registration.
            ocloud_global_id (str): Global ID for the O-Cloud. Defaults to None, which generates a random UUID.
            smo_token_data (str): Base64-encoded SMO service account token. Defaults
                to an empty string.
            oauth2_public_key (str): Base64 body of the token issuer's RSA public key,
                with no PEM header or footer: the application adds the delimiters
                itself. Defaults to None, which omits the [OAUTH2] section and leaves
                the API unauthenticated.
            oauth2_verify_type (str): Token verification mode, either "jwt" for local
                signature validation or "introspection" to call the issuer. Defaults to "jwt".
            oauth2_algorithm (str): Signing algorithm of the issued tokens. Defaults to "RS256".
        """
        if ocloud_global_id is None:
            ocloud_global_id = str(uuid.uuid4())
        get_logger().log_info("Creating app.conf file")
        credentials_keywords = OpenStackCredentialsKeywords(self.ssh_connection)
        replacement_dict = {
            "smo_register_url": smo_register_url,
            "ocloud_global_id": ocloud_global_id,
            "smo_token_data": smo_token_data,
            "os_auth_url": credentials_keywords.get_openstack_auth_url(),
            "os_username": credentials_keywords.get_openstack_username(),
            "os_password": credentials_keywords.get_openstack_password(),
            "api_host_external_floating": ConfigurationManager.get_lab_config().get_floating_ip(),
            "oauth2_public_key": oauth2_public_key,
            "oauth2_verify_type": oauth2_verify_type,
            "oauth2_algorithm": oauth2_algorithm,
        }
        if oauth2_public_key:
            get_logger().log_info(f"Rendering [OAUTH2] section with verify_type={oauth2_verify_type}, algorithm={oauth2_algorithm}")
        else:
            get_logger().log_info("No OAuth2 public key supplied, omitting [OAUTH2] section")
        FileKeywords(self.ssh_connection).generate_file_from_template(
            get_stx_resource_path("resources/cloud_platform/applications/o_ran/app.conf.j2"),
            replacement_dict,
            "app.conf",
            "/tmp",
        )

    def create_certificates(self) -> None:
        """Create the CA, server and client certificates used by the O2 service.

        The O2 API server runs with mutual TLS required, so a client certificate
        signed by the same CA the server trusts is needed for any API call to
        succeed.

        The CA, server and client certificates must each carry a distinct subject.
        A leaf sharing its subject with the signing CA is treated as self-signed
        and rejected during the TLS handshake.

        Generates into /tmp/cert:
            my-root-ca-key.pem / my-root-ca-cert.pem  the signing CA (CN=imsRootCA)
            my-server-key.pem  / my-server-cert.pem   the server identity (CN=imsserver)
            my-client-key.pem  / my-client-cert.pem   the client identity (CN=imsclient)
        """
        get_logger().log_info("Creating O2 service certificates")
        FileKeywords(self.ssh_connection).create_directory("/tmp/cert")
        subject_prefix = "/C=CA/ST=ON/L=Ottawa/O=IMS/OU=IMS"
        ca_subject = f"{subject_prefix}/CN=imsRootCA"
        server_subject = f"{subject_prefix}/CN=imsserver"
        client_subject = f"{subject_prefix}/CN=imsclient"
        openssl = OpenSSLKeywords(self.ssh_connection)

        openssl.generate_rsa_key("/tmp/cert/my-root-ca-key.pem")
        openssl.create_self_signed_ca_certificate("/tmp/cert/my-root-ca-key.pem", "/tmp/cert/my-root-ca-cert.pem", ca_subject)

        openssl.generate_rsa_key("/tmp/cert/my-server-key.pem")
        openssl.create_certificate_signing_request("/tmp/cert/my-server-key.pem", "/tmp/cert/my-server.csr", server_subject)
        openssl.sign_certificate("/tmp/cert/my-server.csr", "/tmp/cert/my-root-ca-cert.pem", "/tmp/cert/my-root-ca-key.pem", "/tmp/cert/my-server-cert.pem")

        openssl.generate_rsa_key("/tmp/cert/my-client-key.pem")
        openssl.create_certificate_signing_request("/tmp/cert/my-client-key.pem", "/tmp/cert/my-client.csr", client_subject)
        openssl.sign_certificate("/tmp/cert/my-client.csr", "/tmp/cert/my-root-ca-cert.pem", "/tmp/cert/my-root-ca-key.pem", "/tmp/cert/my-client-cert.pem")

        openssl.verify_certificate_against_ca("/tmp/cert/my-root-ca-cert.pem", "/tmp/cert/my-server-cert.pem")
        openssl.verify_certificate_against_ca("/tmp/cert/my-root-ca-cert.pem", "/tmp/cert/my-client-cert.pem")
        get_logger().log_info("Server and client certificates verify against the CA")

    def download_client_certificates(self, local_directory: str) -> None:
        """Download the client certificate, client key and CA certificate locally.

        create_certificates generates these on the target host, but a REST client
        running on the test runner needs the client identity and the CA as local
        files. The client files are renamed to client-cert.pem and client-key.pem
        to match what REST client configuration expects. One of them is a private
        key, so permissions are set explicitly rather than left to the umask.

        Args:
            local_directory (str): Local directory to write the certificates into.
                Created if it does not already exist.
        """
        get_logger().log_info(f"Downloading client certificates to {local_directory}")
        target_directory = local_directory.rstrip("/")
        os.makedirs(target_directory, mode=DIRECTORY_MODE_OWNER_ONLY, exist_ok=True)
        # makedirs does not alter an existing directory, so apply the mode either way.
        os.chmod(target_directory, DIRECTORY_MODE_OWNER_ONLY)

        file_keywords = FileKeywords(self.ssh_connection)
        downloads = {
            "my-client-cert.pem": "client-cert.pem",
            "my-client-key.pem": "client-key.pem",
            "my-root-ca-cert.pem": "my-root-ca-cert.pem",
        }
        for remote_name, local_name in downloads.items():
            local_path = f"{target_directory}/{local_name}"
            file_keywords.download_file(f"/tmp/cert/{remote_name}", local_path)
            os.chmod(local_path, FILE_MODE_OWNER_ONLY)
            get_logger().log_info(f"Downloaded {remote_name} as {local_name}")
        get_logger().log_info(f"Certificate directory {target_directory} and its contents restricted to the owning user")

    def _get_remote_file_base64(self, remote_path: str) -> str:
        """Get base64-encoded content of a remote file.

        Args:
            remote_path (str): Path to the remote file.

        Returns:
            str: Base64-encoded content of the file.
        """
        content = "".join(FileKeywords(self.ssh_connection).read_file(remote_path))
        return b64encode(content.encode()).decode()

    def apply_helm_override(self, tls: bool = False) -> None:
        """Apply the helm override and deploy the application.

        With tls enabled the override supplies smocacrt, the CA the O2 API server
        uses to validate incoming client certificates. The server always requires
        mutual TLS, so leaving smocacrt unset makes it reject every client during
        the handshake. Changing the mounted secret does not restart the running
        pod; callers must restart the deployment for it to take effect.

        Args:
            tls (bool): Supply the client-validation CA so mutual TLS can succeed.
                Defaults to False, which deploys an API that rejects all client
                connections. Pass True for any deployment whose API will be called.
        """
        get_logger().log_info(f"Applying helm override (tls={tls})")
        template_file = "o2service-override-with-tls.yaml.j2" if tls else "o2service-override-no-tls.yaml.j2"
        replacement_dict = {
            "application_config": self._get_remote_file_base64("/tmp/app.conf"),
            "server_cert": self._get_remote_file_base64("/tmp/cert/my-server-cert.pem"),
            "server_key": self._get_remote_file_base64("/tmp/cert/my-server-key.pem"),
        }
        if tls:
            replacement_dict["smo_ca_cert"] = self._get_remote_file_base64("/tmp/cert/my-root-ca-cert.pem")
        override_file = YamlKeywords(self.ssh_connection).generate_yaml_file_from_template(
            get_stx_resource_path(f"resources/cloud_platform/applications/o_ran/{template_file}"),
            replacement_dict,
            "o2service-override.yaml",
            "/tmp",
        )
        SystemHelmOverrideKeywords(self.ssh_connection).update_helm_override(override_file, "oran-o2", "oran-o2", "oran-o2")
        SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply("oran-o2")

    def get_deployed_app_config(self, pod_name: str, namespace: str = "oran-o2") -> str:
        """Read the application configuration file as the running pod sees it.

        The chart mounts the applicationconfig override as o2app.conf, not
        app.conf. Reading it back confirms the configuration actually reached the
        pod, which is worth checking because updating the override alone does not
        restart the pod.

        Args:
            pod_name (str): Name of the O2 API pod.
            namespace (str): Namespace containing the pod. Defaults to 'oran-o2'.

        Returns:
            str: Contents of the deployed configuration file.
        """
        output = KubectlExecInPodsKeywords(self.ssh_connection).run_pod_exec_cmd(pod_name, "cat /configs/o2app.conf", options=f"-n {namespace} -c o2api")
        return "\n".join(output) if isinstance(output, list) else output

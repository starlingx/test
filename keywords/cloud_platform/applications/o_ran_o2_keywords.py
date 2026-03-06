import uuid

from config.configuration_manager import ConfigurationManager

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from base64 import b64encode

from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.openssl.openssl_keywords import OpenSSLKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords


class OranO2Keywords(BaseKeyword):
    """Keywords for O-RAN O2 application operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection

    def create_smo_service_account(self, smo_service_account: str = 'smo1') -> None:
        """Create SMO service account.

        Args:
            smo_service_account (str): Name of the SMO service account. Defaults to 'smo1'.
        """
        get_logger().log_info("Creating SMO service account")
        template_path = get_stx_resource_path(
            "resources/cloud_platform/applications/o_ran/smo-serviceaccount.yaml.j2"
        )
        replacement_dict = {"smo_service_account": smo_service_account}
        yaml_keywords = YamlKeywords(self.ssh_connection)
        remote_file = yaml_keywords.generate_yaml_file_from_template(
            template_path, replacement_dict, "smo-serviceaccount.yaml", "/tmp"
        )

    def create_smo_secret(self, smo_secret: str = 'smo1-secret', smo_service_account: str = 'smo1') -> None:
        """Create SMO secret.

        Args:
            smo_secret (str): Name of the SMO secret. Defaults to 'smo1-secret'.
            smo_service_account (str): Name of the SMO service account. Defaults to 'smo1'.
        """
        get_logger().log_info("Creating SMO secret")
        template_path = get_stx_resource_path(
            "resources/cloud_platform/applications/o_ran/smo-secret.yaml.j2"
        )
        replacement_dict = {"smo_secret": smo_secret, "smo_service_account": smo_service_account}
        yaml_keywords = YamlKeywords(self.ssh_connection)
        remote_file = yaml_keywords.generate_yaml_file_from_template(
            template_path, replacement_dict, "smo-secret.yaml", "/tmp"
        )
        KubectlFileApplyKeywords(self.ssh_connection).apply_resource_from_yaml(remote_file)

    def create_app_config_file(self, smo_register_url: str, ocloud_global_id: str = None) -> None:
        """Create O2 application configuration file.

        Args:
            smo_register_url (str): URL for SMO registration.
            ocloud_global_id (str): Global ID for the O-Cloud. Defaults to None, which generates a random UUID.
        """
        if ocloud_global_id is None:
            ocloud_global_id = str(uuid.uuid4())
        get_logger().log_info("Creating app.conf file")
        replacement_dict = {
            "smo_register_url": smo_register_url,
            "ocloud_global_id": ocloud_global_id,
            "api_host_external_floating": ConfigurationManager.get_lab_config().get_floating_ip(),
        }
        FileKeywords(self.ssh_connection).generate_file_from_template(
            get_stx_resource_path("resources/cloud_platform/applications/o_ran/app.conf.j2"),
            replacement_dict,
            "app.conf",
            "/tmp",
        )

    def create_certificates(self) -> None:
        """Create O2 service certificates."""
        get_logger().log_info("Creating O2 service certificates")
        FileKeywords(self.ssh_connection).create_directory("/tmp/cert")
        subj = "/C=CA/ST=ON/L=Ottawa/O=IMS/OU=IMS/CN=imsserver"
        openssl = OpenSSLKeywords(self.ssh_connection)
        openssl.generate_rsa_key("/tmp/cert/my-root-ca-key.pem")
        openssl.create_self_signed_ca_certificate("/tmp/cert/my-root-ca-key.pem", "/tmp/cert/my-root-ca-cert.pem", subj)
        openssl.generate_rsa_key("/tmp/cert/my-server-key.pem")
        openssl.create_certificate_signing_request("/tmp/cert/my-server-key.pem", "/tmp/cert/my-server.csr", subj)
        openssl.sign_certificate("/tmp/cert/my-server.csr", "/tmp/cert/my-root-ca-cert.pem", "/tmp/cert/my-root-ca-key.pem", "/tmp/cert/my-server-cert.pem")

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
        """Apply helm override and deploy application.

        Args:
            tls (bool): Whether to use TLS configuration. Defaults to False.
        """
        get_logger().log_info("Applying helm override")
        template_file = "o2service-override-with-tls.yaml.j2" if tls else "o2service-override-no-tls.yaml.j2"
        replacement_dict = {
            "application_config": self._get_remote_file_base64("/tmp/app.conf"),
            "server_cert": self._get_remote_file_base64("/tmp/cert/my-server-cert.pem"),
            "server_key": self._get_remote_file_base64("/tmp/cert/my-server-key.pem"),
        }
        if tls:
            replacement_dict["smo_ca_cert"] = self._get_remote_file_base64("/tmp/smo-ca.pem")
        override_file = YamlKeywords(self.ssh_connection).generate_yaml_file_from_template(
            get_stx_resource_path(f"resources/cloud_platform/applications/o_ran/{template_file}"),
            replacement_dict,
            "o2service-override.yaml",
            "/tmp",
        )
        SystemHelmOverrideKeywords(self.ssh_connection).update_helm_override(
            override_file, "oran-o2", "oran-o2", "oran-o2"
        )
        SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply("oran-o2")

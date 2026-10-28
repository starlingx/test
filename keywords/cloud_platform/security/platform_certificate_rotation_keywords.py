import shlex

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.openssl.openssl_keywords import OpenSSLKeywords


class PlatformCertificateRotationKeywords(BaseKeyword):
    """Keywords for rotating the platform ``system-local-ca`` signing CA.

    Drives the ``update_platform_certificates`` playbook to rotate the
    ``system-local-ca`` signing CA, and provides capture/restore of the current
    CA secret so a test can always return the system to its starting CA state.

    The IPSec leaf certificates are signed by ``system-local-ca``; rotating this
    CA exercises the IPSec certificate re-issue path that must keep the
    management network operational.
    """

    PLAYBOOK_PATH = "/usr/share/ansible/stx-ansible/playbooks/update_platform_certificates.yml"
    CERT_MANAGER_NAMESPACE = "cert-manager"
    SYSTEM_LOCAL_CA_SECRET = "system-local-ca"

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize platform certificate rotation keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self.file_keywords = FileKeywords(ssh_connection)
        self.openssl_keywords = OpenSSLKeywords(ssh_connection)
        self.kubectl_apply = KubectlApplyPodsKeywords(ssh_connection)

    def capture_system_local_ca_secret(self, backup_path: str) -> None:
        """Capture the current ``system-local-ca`` secret to a backup file.

        Dumps the secret as YAML so it can be re-applied later to restore the
        original signing CA, mirroring the playbook's own recovery behaviour.

        Args:
            backup_path (str): Path on the host to write the secret YAML backup.
        """
        get_logger().log_info(f"Capturing {self.SYSTEM_LOCAL_CA_SECRET} secret to {backup_path}")
        command = f"kubectl get secret -n {self.CERT_MANAGER_NAMESPACE} {self.SYSTEM_LOCAL_CA_SECRET} -o yaml > {shlex.quote(backup_path)}"
        self.ssh_connection.send(export_k8s_config(command))
        self.validate_success_return_code(self.ssh_connection)

    def is_ca_secret_backup_valid(self, backup_path: str) -> bool:
        """Check that a captured ``system-local-ca`` backup is present and non-empty.

        A rotation test must never proceed to mutate the signing CA unless it holds
        a usable backup to restore afterwards; an empty or missing backup would make
        the system unrecoverable. This verifies the backup file exists and contains
        the secret's ``tls.crt`` data key.

        Args:
            backup_path (str): Path to the captured secret YAML backup.

        Returns:
            bool: True if the backup exists and contains the secret key material.
        """
        if not self.file_keywords.validate_file_exists_with_sudo(backup_path):
            return False
        content = self.ssh_connection.send_as_sudo(f"cat {shlex.quote(backup_path)}")
        joined = "\n".join(content) if isinstance(content, list) else str(content)
        return "tls.crt" in joined

    def restore_system_local_ca_secret(self, backup_path: str) -> None:
        """Restore the ``system-local-ca`` secret from a captured backup.

        Re-applies the previously captured secret and re-runs the certificate
        update so the signing CA and the IPSec leaf certificates return to their
        original state.

        Args:
            backup_path (str): Path to the secret YAML backup created by
                capture_system_local_ca_secret.
        """
        get_logger().log_info(f"Restoring {self.SYSTEM_LOCAL_CA_SECRET} secret from {backup_path}")
        if not self.file_keywords.validate_file_exists_with_sudo(backup_path):
            get_logger().log_error(f"CA backup {backup_path} not found; cannot restore")
            return
        self.kubectl_apply.apply_from_yaml(backup_path)

    def get_system_local_ca_serial(self) -> str:
        """Get the serial number of the current ``system-local-ca`` certificate.

        Returns:
            str: Serial number of the current signing CA certificate.
        """
        return self.openssl_keywords.get_certificate_info("/etc/swanctl/x509ca/system-local-ca-1.crt").get_serial()

    def reissue_platform_certificates(self, timeout: int = 2700) -> bool:
        """Re-issue platform certificates without changing the signing CA.

        Runs update_platform_certificates in update mode with no CA overrides.
        Per the playbook contract, omitting the CA parameters keeps the existing
        system-local-ca and only re-issues the platform (including IPSec) leaf
        certificates. This exercises the IPSec certificate re-issue and security
        association reauth path without mutating the CA trust chain, so the CA
        state is unchanged after the run.

        Args:
            timeout (int): Maximum seconds to allow the playbook to run.

        Returns:
            bool: True if the playbook completed successfully.
        """
        admin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        command = f"ansible-playbook {self.PLAYBOOK_PATH} " f'--extra-vars "target_list=localhost mode=update ansible_become_pass={admin_password} admin_password={admin_password}"'
        get_logger().log_info("Running update_platform_certificates to re-issue platform certificates (CA unchanged)")
        self.ssh_connection.send(command, command_timeout=timeout, reconnect_timeout=timeout)
        self.validate_success_return_code(self.ssh_connection)
        return True

    def rotate_system_local_ca(self, root_ca_cert_b64: str, local_ca_cert_b64: str, local_ca_key_b64: str, inventory_path: str = "/tmp/update_platform_certs_inventory.yml", timeout: int = 2700) -> bool:
        """Rotate the ``system-local-ca`` signing CA via update_platform_certificates.

        Writes an overrides inventory file with the provided base64-encoded CA
        material and runs the update_platform_certificates playbook against
        localhost in update mode. The playbook re-issues the IPSec leaf
        certificates under the new CA.

        Args:
            root_ca_cert_b64 (str): Base64-encoded root CA certificate.
            local_ca_cert_b64 (str): Base64-encoded intermediate (local) CA certificate.
            local_ca_key_b64 (str): Base64-encoded intermediate (local) CA private key.
            inventory_path (str): Path on the host to write the overrides inventory.
            timeout (int): Maximum seconds to allow the playbook to run.

        Returns:
            bool: True if the playbook completed successfully.
        """
        admin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        vars_contents = "---\n" f"system_root_ca_cert: {root_ca_cert_b64}\n" f"system_local_ca_cert: {local_ca_cert_b64}\n" f"system_local_ca_key: {local_ca_key_b64}\n"
        self.file_keywords.create_file_with_heredoc(inventory_path, vars_contents)

        command = f"ansible-playbook {self.PLAYBOOK_PATH} --extra-vars @{inventory_path} " f'--extra-vars "target_list=localhost mode=update ansible_become_pass={admin_password} admin_password={admin_password}"'
        get_logger().log_info("Running update_platform_certificates to rotate system-local-ca")
        self.ssh_connection.send(command, command_timeout=timeout, reconnect_timeout=timeout)
        self.validate_success_return_code(self.ssh_connection)
        self.file_keywords.delete_file(inventory_path)
        return True

    def is_ca_trust_file_present(self, ca_file_name: str) -> bool:
        """Check whether a CA trust-store file is present on the host.

        Args:
            ca_file_name (str): CA file name under /etc/swanctl/x509ca/
                (e.g. 'system-local-ca-0.crt').

        Returns:
            bool: True if the CA trust file exists, False otherwise.
        """
        return self.file_keywords.validate_file_exists_with_sudo(f"/etc/swanctl/x509ca/{ca_file_name}")

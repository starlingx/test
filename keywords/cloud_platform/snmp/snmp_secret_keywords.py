"""Keywords for validating SNMP sensitive data is stored in a Secret.

Backs the SNMP secret-storage regression test. The fix moves the SNMP
configuration (snmpd.conf community strings and fm.conf FM-DB connection
string) out of plaintext kube-system ConfigMaps and into an Opaque Secret
(``snmpd-secret``), closing the credential-disclosure path.

Verified state on a fixed load:
    * no ``snmpd-*`` ConfigMap exists in kube-system;
    * an Opaque Secret ``snmpd-secret`` holds two data keys (snmpd.conf, fm.conf).
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.configmap.kubectl_get_configmap_keywords import KubectlGetConfigmapKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords

KUBE_SYSTEM_NAMESPACE = "kube-system"
SNMP_SECRET_NAME = "snmpd-secret"
SNMP_CONFIGMAP_MARKER = "snmp"


class SnmpSecretKeywords(BaseKeyword):
    """Validate that SNMP sensitive data lives in a Secret, not a ConfigMap."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self.secret_keywords = KubectlGetSecretsKeywords(ssh_connection)
        self.configmap_keywords = KubectlGetConfigmapKeywords(ssh_connection)

    def snmp_configmap_present(self) -> bool:
        """Return whether any SNMP ConfigMap exists in kube-system.

        Returns:
            bool: True if a ConfigMap whose name contains ``snmp`` exists.
        """
        present = self.configmap_keywords.has_configmap_matching(KUBE_SYSTEM_NAMESPACE, SNMP_CONFIGMAP_MARKER)
        get_logger().log_info(f"SNMP ConfigMap present in kube-system: {present}")
        return present

    def snmp_secret_present(self) -> bool:
        """Return whether the ``snmpd-secret`` Secret exists in kube-system.

        Returns:
            bool: True if the snmpd-secret Secret exists.
        """
        names = self.secret_keywords.get_secret_names(KUBE_SYSTEM_NAMESPACE)
        present = SNMP_SECRET_NAME in names
        get_logger().log_info(f"Secret '{SNMP_SECRET_NAME}' present: {present}")
        return present

    def get_snmp_secret_type(self) -> str:
        """Return the type of the ``snmpd-secret`` Secret.

        Returns:
            str: The Secret type (e.g. ``Opaque``).
        """
        secret = self.secret_keywords.get_secret_json_output(SNMP_SECRET_NAME, KUBE_SYSTEM_NAMESPACE)
        return secret.get_type()

    def get_snmp_secret_data_key_count(self) -> int:
        """Return the number of data keys in the ``snmpd-secret`` Secret.

        Returns:
            int: Count of data keys (expected 2: snmpd.conf and fm.conf).
        """
        secret = self.secret_keywords.get_secret_json_output(SNMP_SECRET_NAME, KUBE_SYSTEM_NAMESPACE)
        count = secret.get_data_key_count()
        get_logger().log_info(f"'{SNMP_SECRET_NAME}' data key count: {count}")
        return count

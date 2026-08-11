"""Shared OIDC test setup keywords for environment configuration, role-binding, and LDAP user management.

Provides reusable class-based keywords for OIDC test suites (FM, software, system, sw-manager)
using existing framework keywords instead of raw SSH commands.
"""


from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.oidc.dex_connector_keywords import DexConnectorKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.keyring.keyring_keywords import KeyringKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords

DEX_LOCAL_LDAP_OVERRIDE = """config:
  connectors:
  - config:
      bindDN: CN=ldapadmin,DC=cgcs,DC=local
      bindPW: '{ldap_admin_pw}'
      groupSearch:
        baseDN: ou=Group,dc=cgcs,dc=local
        filter: (objectClass=posixGroup)
        nameAttr: cn
        userMatchers:
        - groupAttr: memberUid
          userAttr: uid
      host: '{mgmt_ip}:636'
      insecureNoSSL: false
      insecureSkipVerify: false
      rootCA: /etc/ssl/certs/adcert/ca.crt
      userSearch:
        baseDN: ou=People,dc=cgcs,dc=local
        emailAttr: mail
        filter: (objectClass=posixAccount)
        idAttr: DN
        nameAttr: cn
        preferredUsernameAttr: uid
        username: uid
      usernamePrompt: Username
    id: ldap-1
    name: ldap-1
    type: ldap
  expiry:
    idTokens: 24h
volumeMounts:
- mountPath: /etc/ssl/certs/adcert
  name: certdir
- mountPath: /etc/dex/tls
  name: https-tls
volumes:
- name: certdir
  secret:
    secretName: oidc-auth-apps-certificate
- name: https-tls
  secret:
    defaultMode: 420
    secretName: oidc-auth-apps-certificate
"""

OIDC_CLIENT_OVERRIDE = """config:
  issuer_root_ca_secret: oidc-auth-apps-certificate
  issuer_root_ca: /home/ca.crt
tlsName: oidc-auth-apps-certificate
"""

OIDC_APP_NAME = "oidc-auth-apps"
OIDC_NAMESPACE = "kube-system"


class OidcSetupKeywords(BaseKeyword):
    """Keywords for shared OIDC test environment setup operations."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Active controller SSH connection.
        """
        self.ssh_connection = ssh_connection
        self.file_kw = FileKeywords(ssh_connection)
        self.helm_override_kw = SystemHelmOverrideKeywords(ssh_connection)
        self.app_apply_kw = SystemApplicationApplyKeywords(ssh_connection)
        self.app_list_kw = SystemApplicationListKeywords(ssh_connection)
        self.addrpool_kw = SystemAddrpoolListKeywords(ssh_connection)
        self.dex_kw = DexConnectorKeywords(ssh_connection)
        self.kubectl_pods_kw = KubectlGetPodsKeywords(ssh_connection)
        self.svc_param_kw = SystemServiceParameterKeywords(ssh_connection)
        self.ldap_kw = None

    def setup_oidc_environment(self) -> None:
        """Set up OIDC with local LDAP connector.

        Uses existing keywords for addrpool lookup, file creation, helm overrides,
        application apply, and pod readiness checks.

        Raises:
            KeywordException: If management IP cannot be determined or oidc-auth-apps is missing.
        """
        # Get LDAP admin bind password from system keyring
        ldap_admin_pw = KeyringKeywords(self.ssh_connection).get_keyring(service="ldap", identifier="ldapadmin")
        get_logger().log_info("Retrieved LDAP admin password from keyring")

        # Get management floating IP using SystemAddrpoolListKeywords
        addrpool_output = self.addrpool_kw.get_system_addrpool_list()
        mgmt_ip = addrpool_output.get_management_floating_address()
        if not mgmt_ip:
            raise KeywordException("Could not determine management floating IP from addrpool")
        if ":" in mgmt_ip:
            mgmt_ip = f"[{mgmt_ip}]"
        get_logger().log_info(f"Using management IP for LDAP: {mgmt_ip}")

        # Write dex override YAML using FileKeywords
        override_content = DEX_LOCAL_LDAP_OVERRIDE.format(ldap_admin_pw=ldap_admin_pw, mgmt_ip=mgmt_ip)
        self.file_kw.create_file_with_heredoc("/tmp/dex-oidc-override.yaml", override_content)

        # Write oidc-client override YAML using FileKeywords
        self.file_kw.create_file_with_heredoc("/tmp/oidc-client-override.yaml", OIDC_CLIENT_OVERRIDE)

        # Check current app state
        app_list = self.app_list_kw.get_system_application_list()
        if not app_list.application_exists(OIDC_APP_NAME):
            raise KeywordException(f"{OIDC_APP_NAME} not found on system")

        # Apply helm overrides using SystemHelmOverrideKeywords
        get_logger().log_info("Applying local LDAP dex + oidc-client helm overrides")
        self.helm_override_kw.update_helm_override("/tmp/dex-oidc-override.yaml", OIDC_APP_NAME, "dex", OIDC_NAMESPACE)
        self.helm_override_kw.update_helm_override("/tmp/oidc-client-override.yaml", OIDC_APP_NAME, "oidc-client", OIDC_NAMESPACE)

        # Apply the app using SystemApplicationApplyKeywords (waits for applied state)
        get_logger().log_info("Applying oidc-auth-apps")
        self.app_apply_kw.system_application_apply(OIDC_APP_NAME, timeout=300, wait_for_applied=True)

        # Wait for OIDC pods to be ready using KubectlGetPodsKeywords
        get_logger().log_info("Waiting for OIDC pods to be ready")
        self.kubectl_pods_kw.wait_for_pods_to_reach_status(
            expected_status="Running",
            pod_names=["oidc-dex", "stx-oidc-client"],
            namespace=OIDC_NAMESPACE,
            timeout=180,
        )
        get_logger().log_info("All OIDC pods are ready")

    def cleanup_oidc_environment(self) -> None:
        """Remove OIDC helm overrides, re-apply oidc-auth-apps, and delete temp files.

        Reverts the dex and oidc-client helm overrides applied by setup_oidc_environment(),
        re-applies the application to restore default state, and removes the temporary
        override YAML files from the controller.
        """
        get_logger().log_info("Cleaning up OIDC environment: removing helm overrides")
        self.helm_override_kw.delete_system_helm_override(OIDC_APP_NAME, "dex", OIDC_NAMESPACE)
        self.helm_override_kw.delete_system_helm_override(OIDC_APP_NAME, "oidc-client", OIDC_NAMESPACE)
        self.app_apply_kw.system_application_apply(OIDC_APP_NAME, timeout=300, wait_for_applied=True)
        self.file_kw.delete_file("/tmp/dex-oidc-override.yaml")
        self.file_kw.delete_file("/tmp/oidc-client-override.yaml")
        get_logger().log_info("OIDC environment restored to default state")

    def setup_role_bindings(self, group_name: str, role: str) -> callable:
        """Add identity stx role-bindings for the given group and role.

        Returns a teardown callable that the test should register via request.addfinalizer().

        Args:
            group_name (str): LDAP group name.
            role (str): STX role (admin, reader, operator, configurator).

        Returns:
            callable: Teardown function to remove the role-bindings.
        """
        service = "identity"
        section = "stx"
        param_name = "role-bindings"

        role_bindings_map = {
            "admin": f"%{group_name}:admin;%{group_name}:member;%{group_name}:reader",
            "configurator": f"%{group_name}:configurator;%{group_name}:reader",
            "operator": f"%{group_name}:operator;%{group_name}:reader",
            "reader": f"%{group_name}:reader",
        }
        param_value = role_bindings_map[role]

        existing = self.svc_param_kw.list_service_parameters(service=service, section=section)
        for param in existing.get_parameters():
            if param.get_name() == param_name:
                self.svc_param_kw.delete_service_parameter(param.get_uuid())
                self.svc_param_kw.apply_service_parameters(service, section=section)
                break

        self.svc_param_kw.add_service_parameter(service, section, param_name, param_value)
        self.svc_param_kw.apply_service_parameters(service, section=section)

        # Wait for puppet to create rolebindings.conf using validate_equals_with_retry
        validate_equals_with_retry(
            function_to_execute=lambda: self.file_kw.file_exists("/etc/platform/.rolebindings.conf"),
            expected_value=True,
            validation_description="Wait for /etc/platform/.rolebindings.conf to be created",
            timeout=60,
            polling_sleep_time=5,
        )

        def teardown() -> None:
            """Remove role-bindings service parameter."""
            current = self.svc_param_kw.list_service_parameters(service=service, section=section)
            for p in current.get_parameters():
                if p.get_name() == param_name:
                    self.svc_param_kw.delete_service_parameter(p.get_uuid())
                    self.svc_param_kw.apply_service_parameters(service, section=section)
                    break

        return teardown

    def setup_ldap_user(self, username: str, password: str, group_name: str) -> None:
        """Create LDAP user and group, add user to group.

        Args:
            username (str): LDAP username to create.
            password (str): Password for the LDAP user.
            group_name (str): LDAP group to create and add user to.
        """
        self.ldap_kw = LdapKeywords(self.ssh_connection, password)
        self.ldap_kw.create_user(username, password)
        self.ldap_kw.create_group(group_name)
        self.ldap_kw.add_user_to_group(username, group_name)

    def cleanup_ldap_user(self, username: str, password: str, group_name: str) -> None:
        """Delete LDAP user and group.

        Args:
            username (str): LDAP username to delete.
            password (str): Sysadmin password for ansible playbook.
            group_name (str): LDAP group to delete.
        """
        get_logger().log_info(f"Cleaning up LDAP user {username} and group {group_name}")
        ldap_kw = LdapKeywords(self.ssh_connection, password)
        ldap_kw.delete_user(username)
        ldap_kw.delete_group(group_name)

    def get_upload_app_tarball(self, base_path: str, app_name: str) -> str:
        """Find the application tarball on the lab for upload testing.

        Uses FileKeywords to list files in the base directory and match by prefix.

        Args:
            base_path (str): Base directory for application tarballs.
            app_name (str): Application name prefix to match (e.g. 'auditd').

        Returns:
            str: Full path to the application tarball.
        """
        files = self.file_kw.get_files_in_dir(base_path)
        for filename in files:
            if filename.startswith(app_name) and filename.endswith(".tgz"):
                return f"{base_path}{filename}"
        return f"{base_path}{app_name}.tgz"

    def verify_user_deleted(self, username: str, password: str) -> bool:
        """Verify an LDAP user no longer exists using LdapKeywords.

        Args:
            username (str): LDAP username to check.
            password (str): Sysadmin password for LdapKeywords.

        Returns:
            bool: True if user does not exist.
        """
        ldap_kw = LdapKeywords(self.ssh_connection, password)
        return not ldap_kw.user_exists_in_ldap(username)

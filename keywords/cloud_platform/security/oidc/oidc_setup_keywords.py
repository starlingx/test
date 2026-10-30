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
from keywords.cloud_platform.security.oidc.oidc_auth_keywords import OidcAuthKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.keyring.keyring_keywords import KeyringKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords

OIDC_DEX_POD_LABEL = "app.kubernetes.io/name=dex"
OIDC_CLIENT_POD_LABEL = "app=stx-oidc-client"
OIDC_POD_LABELS = (OIDC_DEX_POD_LABEL, OIDC_CLIENT_POD_LABEL)
OIDC_POD_NAME_PREFIXES = ("oidc-dex", "stx-oidc-client")

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
    idTokens: {id_token_expiry}
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
        self.delete_pods_kw = KubectlDeletePodsKeywords(ssh_connection)
        self.svc_param_kw = SystemServiceParameterKeywords(ssh_connection)
        self.ldap_kw = None

    def setup_oidc_environment(self, id_token_expiry: str = "24h") -> None:
        """Set up OIDC with local LDAP connector.

        Uses existing keywords for addrpool lookup, file creation, helm overrides,
        application apply, and pod readiness checks.

        Args:
            id_token_expiry (str): dex idTokens expiry (e.g. "24h" or "60s"). A short
                value is used to exercise token-expiry behaviour. Defaults to "24h".

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
        override_content = DEX_LOCAL_LDAP_OVERRIDE.format(ldap_admin_pw=ldap_admin_pw, mgmt_ip=mgmt_ip, id_token_expiry=id_token_expiry)
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

        # Apply the app, retrying if a prior apply/update is still in progress,
        # then wait for the applied state (serialised test runs can leave the
        # previous test's apply briefly in progress).
        get_logger().log_info("Applying oidc-auth-apps")
        self.app_apply_kw.system_application_apply_with_retry(OIDC_APP_NAME, timeout=1800, retry_interval=30)

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
        """Clean up temporary override files created by setup_oidc_environment.

        Removes the temporary YAML files from the controller. Does not delete the
        helm overrides or re-apply the app — removing the dex connector override
        leaves oidc-auth-apps with an incomplete OIDC configuration, which causes
        application-apply to be rejected. The setup is idempotent, so subsequent
        runs will re-apply the overrides as needed.
        """
        get_logger().log_info("Cleaning up OIDC environment: removing temporary override files")
        self.file_kw.delete_file("/tmp/dex-oidc-override.yaml")
        self.file_kw.delete_file("/tmp/oidc-client-override.yaml")
        get_logger().log_info("OIDC environment cleanup complete")

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

    def get_oidc_pod_names(self) -> list[str]:
        """Get the current dex and oidc-client pod names.

        Returns:
            list[str]: Names of the dex and stx-oidc-client pods in the OIDC namespace.
        """
        pod_names = []
        for pod_label in OIDC_POD_LABELS:
            pods = self.kubectl_pods_kw.get_pods(namespace=OIDC_NAMESPACE, label=pod_label).get_pods()
            pod_names.extend(pod.get_name() for pod in pods)
        return pod_names

    def delete_oidc_pods_and_wait_ready(self, pod_names: list, timeout: int = 300) -> None:
        """Delete the given OIDC pods and wait for replacements to reach Running.

        Args:
            pod_names (list): Pod names to delete (dex and/or oidc-client).
            timeout (int): Maximum wait for deletion and readiness in seconds.
        """
        for pod_name in pod_names:
            self.delete_pods_kw.delete_pod(pod_name, namespace=OIDC_NAMESPACE)
        self.wait_for_oidc_pods_recycled(pod_names, timeout=timeout)

    def wait_for_oidc_pods_recycled(self, old_pod_names: list, timeout: int = 300) -> None:
        """Wait for the OIDC pods to pick up a certificate change and be serving.

        After a certificate change the secret-observer may either recreate the
        dex/oidc-client pods or refresh the mounted secret in place, depending on
        the platform build. Pod deletion is therefore treated as best-effort; the
        enforced outcome is that the dex/oidc-client pods are Running and dex is
        serving OIDC requests (which means the new certificate is in effect).

        Args:
            old_pod_names (list): Pod names that may be replaced.
            timeout (int): Maximum wait in seconds.
        """
        try:
            self.kubectl_pods_kw.wait_for_pods_to_be_deleted(namespace=OIDC_NAMESPACE, pod_names=old_pod_names, timeout=timeout)
        except (TimeoutError, AssertionError):
            # Deletion is best-effort: the pods may refresh the cert in place
            # (no recreate), or a transient apiserver restart can make the
            # polling kubectl return non-zero. Either way the enforced outcome is
            # the readiness + dex-serving checks below.
            get_logger().log_info("OIDC pods were not observed deleted (in-place refresh or transient apiserver blip); continuing to readiness checks")
        self.kubectl_pods_kw.wait_for_pods_to_reach_status(expected_status="Running", pod_names=list(OIDC_POD_NAME_PREFIXES), namespace=OIDC_NAMESPACE, timeout=timeout)
        DexConnectorKeywords(self.ssh_connection).wait_for_dex_ready(namespace=OIDC_NAMESPACE, raise_on_timeout=True)

    def verify_user_access(self, oam_ip: str, username: str, password: str, timeout: int = 300, oidc_client_ip: str = "") -> None:
        """Verify an LDAP user authenticated via OIDC can act on the Kubernetes API.

        Waits for dex to be serving OIDC requests, then retries the authenticate +
        kubectl access until it succeeds within the timeout. A fresh login can be
        refused briefly after the dex pod is recreated (new signing keys, trust
        re-sync), so a single attempt is not reliable right after a pod recycle.

        Args:
            oam_ip (str): Lab OAM floating IP.
            username (str): LDAP username.
            password (str): LDAP user password.
            timeout (int): Maximum time in seconds to keep retrying access.
            oidc_client_ip (str): OIDC client host for centralized DC auth (the
                System Controller OAM). Defaults to "" (local dex).
        """
        DexConnectorKeywords(self.ssh_connection).wait_for_dex_ready(namespace=OIDC_NAMESPACE, raise_on_timeout=True)

        def attempt_access() -> bool:
            # A fresh oidc-auth login is refused for a short window after the dex
            # pod is recreated (new signing keys, trust re-sync). The failure
            # surfaces as an AssertionError (non-zero return code from oidc-auth)
            # or a connection error while establishing the user session; both mean
            # "not ready yet", so retry rather than fail.
            try:
                ldap_ssh = OidcAuthKeywords.create_ldap_user_ssh(oam_ip, username, password, oidc_client_ip=oidc_client_ip)
                KubectlGetPodsKeywords(ldap_ssh).get_pods()
                return True
            except (AssertionError, OSError, EOFError) as access_error:
                get_logger().log_info(f"OIDC user access not ready yet, retrying: {access_error}")
                return False

        validate_equals_with_retry(attempt_access, True, f"LDAP user {username} should gain OIDC access to the Kubernetes API", timeout=timeout, polling_sleep_time=15)

    def is_user_access_denied(self, ldap_ssh: SSHConnection) -> bool:
        """Check whether a user's cached OIDC token no longer grants API access.

        Used to detect id-token expiry: a kubectl call that is rejected means the
        cached token is no longer valid.

        Args:
            ldap_ssh (SSHConnection): SSH session of the authenticated LDAP user.

        Returns:
            bool: True if a kubectl call is rejected (expired/invalid token), False if it still succeeds.
        """
        try:
            KubectlGetPodsKeywords(ldap_ssh).get_pods()
            return False
        except (AssertionError, OSError, EOFError) as access_error:
            get_logger().log_info(f"User access is denied (token likely expired): {access_error}")
            return True

    def configure_subcloud_oidc_issuer(self, subcloud_ssh: SSHConnection, sc_oidc_issuer: str, username_claim: str = "preferred_username") -> None:
        """Point a subcloud kube-apiserver at the System Controller's dex for centralized OIDC.

        In a Distributed Cloud the subcloud does not run oidc-auth-apps; its
        kube-apiserver must be configured with the System Controller's dex as the
        OIDC issuer so subcloud users authenticate centrally.

        Args:
            subcloud_ssh (SSHConnection): SSH connection to the subcloud.
            sc_oidc_issuer (str): System Controller dex issuer URL.
            username_claim (str): OIDC username claim value. Defaults to "preferred_username".
        """
        svc_param_kw = SystemServiceParameterKeywords(subcloud_ssh)
        oidc_params = {
            "oidc-issuer-url": sc_oidc_issuer,
            "oidc-client-id": "stx-oidc-client-app",
            "oidc-username-claim": username_claim,
            "oidc-groups-claim": "groups",
        }
        for param_name, param_value in oidc_params.items():
            try:
                svc_param_kw.add_service_parameter("kubernetes", "kube_apiserver", param_name, param_value)
            except AssertionError:
                svc_param_kw.modify_service_parameter("kubernetes", "kube_apiserver", param_name, param_value)
        svc_param_kw.apply_service_parameters("kubernetes")
        get_logger().log_info("Applied subcloud OIDC service parameters; kube-apiserver will restart")

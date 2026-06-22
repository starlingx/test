"""Keywords for OIDC offline token validation testing."""

import time
from typing import List, Tuple

from config.lab.objects.lab_config import LabConfig
from config.security.objects.security_config import SecurityConfig
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.fm_oidc.fm_oidc_keywords import FmOidcKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
from keywords.k8s.deployments.kubectl_get_deployments_keywords import KubectlGetDeploymentsKeywords
from keywords.k8s.deployments.kubectl_scale_deployements_keywords import KubectlScaleDeploymentsKeywords
from keywords.k8s.pods.kubectl_wait_pod_keywords import KubectlWaitPodKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords


class OidcOfflineValidationKeywords(BaseKeyword):
    """Keywords for OIDC offline token validation test operations.

    Provides helpers for dex scaling, JWKS cache management, and OIDC
    command execution used by the offline validation test suite.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Active controller SSH connection.
        """
        self.ssh_connection = ssh_connection

    def setup_oidc_with_ldap_connector(
        self, security_config: SecurityConfig, lab_config: LabConfig
    ) -> bool:
        """Check if OIDC environment with LDAP connector is already configured.

        Returns True if already configured (no action needed), False if setup required.

        Args:
            security_config (SecurityConfig): Security configuration object.
            lab_config (LabConfig): Lab configuration object.

        Returns:
            bool: True if OIDC with LDAP is already applied, False if setup needed.
        """
        app_list = SystemApplicationListKeywords(self.ssh_connection).get_system_application_list()
        if app_list.application_exists("oidc-auth-apps"):
            app = app_list.get_application("oidc-auth-apps")
            if app.get_status() == "applied":
                output = self.ssh_connection.send(
                    source_openrc(
                        "system helm-override-show oidc-auth-apps dex kube-system"
                        " 2>/dev/null | grep -c 'ldapadmin'"
                    )
                )
                raw = "\n".join(output) if isinstance(output, list) else output
                if raw.strip() != "0":
                    get_logger().log_info(
                        "oidc-auth-apps already applied with LDAP connector — skipping re-apply"
                    )
                    return True
        return False

    def wait_for_group_membership(self, username: str, group_name: str, timeout: int = 60) -> None:
        """Wait for SSSD to propagate group membership for a user.

        Args:
            username (str): Username to check.
            group_name (str): Group that should appear in the user's groups.
            timeout (int): Maximum seconds to wait.
        """
        def check_group_visible() -> bool:
            """Check if id command shows the group.

            Returns:
                bool: True if group is in user's group list.
            """
            output = self.ssh_connection.send(source_openrc(f"id {username} 2>/dev/null"))
            raw = "\n".join(output) if isinstance(output, list) else output
            return group_name in raw

        validate_equals_with_retry(
            function_to_execute=check_group_visible,
            expected_value=True,
            validation_description=f"Wait for {username} to have {group_name} group via SSSD",
            timeout=timeout,
            polling_sleep_time=5,
        )

    def is_dc_system(self) -> bool:
        """Check if this is a Distributed Cloud systemcontroller.

        Returns:
            bool: True if system is a DC systemcontroller.
        """
        output = self.ssh_connection.send(source_openrc("system show | grep distributed_cloud_role"))
        raw = "\n".join(output) if isinstance(output, list) else (output or "")
        return "systemcontroller" in raw.lower()

    def get_oidc_test_commands(self) -> List[Tuple[str, str, bool]]:
        """Get the list of CLI commands to test based on lab type.

        Returns:
            list: List of (command, label, mandatory) tuples.
        """
        commands = [
            ("fm alarm-list", "FM", True),
            ("software list", "Software", True),
            ("sw-manager sw-deploy-strategy show", "SW-Manager", True),
            ("system host-list", "SysInv", True),
        ]
        if self.is_dc_system():
            commands.append(("dcmanager subcloud list", "DCManager", True))
        return commands

    def get_dex_replica_count(self) -> int:
        """Get the current replica count of the dex deployment.

        Returns:
            int: Current number of desired replicas.
        """
        dex_deployment = "oidc-dex"
        dex_namespace = "kube-system"
        deploy_kw = KubectlGetDeploymentsKeywords(self.ssh_connection)
        output = deploy_kw.get_deployment(dex_deployment, dex_namespace)
        deployments = output.get_deployments()
        for dep in deployments:
            if dex_deployment in dep.get_name():
                ready_str = dep.get_ready()
                return int(ready_str.split("/")[1]) if "/" in ready_str else 1
        return 1

    def scale_dex(self, replicas: int) -> None:
        """Scale the dex deployment to the specified replica count.

        Args:
            replicas (int): Desired number of replicas.
        """
        dex_deployment = "oidc-dex"
        dex_namespace = "kube-system"
        get_logger().log_info(f"Scaling {dex_deployment} to {replicas} replicas")
        scale_kw = KubectlScaleDeploymentsKeywords(self.ssh_connection)
        scale_kw.scale_deployment(dex_deployment, replicas, dex_namespace)

    def wait_for_dex_ready(self, timeout: int = 120) -> None:
        """Wait for dex pods to be ready.

        Args:
            timeout (int): Maximum seconds to wait.
        """
        dex_label = "app=dex"
        dex_namespace = "kube-system"
        admin_kubeconfig = "/etc/kubernetes/admin.conf"

        def check_dex_pod_exists() -> bool:
            """Check if at least one dex pod exists.

            Returns:
                bool: True if pod exists.
            """
            output = self.ssh_connection.send(
                f"kubectl --kubeconfig {admin_kubeconfig} get pods -l {dex_label}"
                f" -n {dex_namespace} --no-headers 2>/dev/null | wc -l"
            )
            raw = "\n".join(output) if isinstance(output, list) else output
            return raw.strip() != "0"

        validate_equals_with_retry(
            function_to_execute=check_dex_pod_exists,
            expected_value=True,
            validation_description="Wait for dex pod to be created",
            timeout=60,
            polling_sleep_time=5,
        )

        wait_kw = KubectlWaitPodKeywords(self.ssh_connection)
        wait_kw.wait_for_pods_ready(dex_label, dex_namespace, timeout)

    def wait_for_dex_terminated(self, timeout: int = 60) -> None:
        """Wait for all dex pods to terminate after scale-down.

        Args:
            timeout (int): Maximum seconds to wait.
        """
        dex_label = "app=dex"
        dex_namespace = "kube-system"
        admin_kubeconfig = "/etc/kubernetes/admin.conf"

        def check_no_dex_pods() -> bool:
            """Check if dex pods are gone.

            Returns:
                bool: True if no dex pods exist.
            """
            output = self.ssh_connection.send(
                f"kubectl --kubeconfig {admin_kubeconfig} get pods -l {dex_label}"
                f" -n {dex_namespace} --no-headers 2>/dev/null | wc -l"
            )
            raw = "\n".join(output) if isinstance(output, list) else output
            return raw.strip() == "0"

        validate_equals_with_retry(
            function_to_execute=check_no_dex_pods,
            expected_value=True,
            validation_description="Wait for dex pods to terminate",
            timeout=timeout,
            polling_sleep_time=5,
        )

    def wait_for_dex_connectable(self, lab_oam_ip: str, timeout: int = 120) -> None:
        """Wait for dex NodePort to accept connections.

        Args:
            lab_oam_ip (str): Lab OAM floating IP.
            timeout (int): Maximum seconds to wait.
        """
        oam_target = f"[{lab_oam_ip}]" if ":" in lab_oam_ip else lab_oam_ip

        def check_dex_reachable() -> bool:
            """Check if dex port is accepting connections.

            Returns:
                bool: True if dex responds.
            """
            output = self.ssh_connection.send(
                source_openrc(
                    f"curl -sk -o /dev/null -w '%{{http_code}}'"
                    f" https://{oam_target}:30556/keys 2>/dev/null"
                )
            )
            raw = "\n".join(output) if isinstance(output, list) else output
            http_code = raw.strip().strip("'")
            return http_code not in ("000", "")

        validate_equals_with_retry(
            function_to_execute=check_dex_reachable,
            expected_value=True,
            validation_description="Wait for dex NodePort to accept connections",
            timeout=timeout,
            polling_sleep_time=10,
        )

    def restore_dex(self, replicas: int) -> None:
        """Restore dex deployment to original replicas and wait for ready.

        Args:
            replicas (int): Number of replicas to restore.
        """
        try:
            self.scale_dex(replicas)
            self.wait_for_dex_ready()
        except Exception:
            get_logger().log_info("restore_dex: encountered an error (may already be running)")

    def run_oidc_command(
        self, fm_oidc_kw: FmOidcKeywords, username: str, password: str, lab_oam_ip: str, command: str
    ) -> bool:
        """Run a CLI command via OIDC and return success status.

        Args:
            fm_oidc_kw (FmOidcKeywords): FM OIDC keywords instance.
            username (str): LDAP username.
            password (str): User password.
            lab_oam_ip (str): Lab OAM IP.
            command (str): CLI command to execute.

        Returns:
            bool: True if command succeeded.
        """
        if command.startswith("fm "):
            result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, command)
            return result.is_successful()

        ldap_ssh = fm_oidc_kw.get_authenticated_session(username, password, lab_oam_ip)
        cli_name = command.split()[0]
        cmd_with_arg = command.replace(f"{cli_name} ", f"{cli_name} --stx-auth-type=oidc ", 1)
        full_cmd = (
            f"export KUBECONFIG=$HOME/.kube/config && "
            f"source /etc/platform/openrc --no_credentials && "
            f"export OS_USERNAME={username} && "
            f"export OS_PASSWORD={password} && "
            f"{cmd_with_arg}"
        )
        output = ldap_ssh.send(full_cmd, command_timeout=120)
        raw = "\n".join(output) if isinstance(output, list) else output
        if raw is None:
            raw = ""
        forbidden_indicators = ["Forbidden", "The requested action is not authorized", "Status: 403"]
        auth_errors = [
            "Invalid Identity credentials",
            "Unable to get OIDC token",
            "Failed OIDC validation",
            "You must provide a password",
            "User password not given",
        ]
        has_error = any(msg in raw for msg in forbidden_indicators + auth_errors)
        if has_error:
            return False
        content_markers = {
            "fm": "alarm_id",
            "software": "Release",
            "sw-manager": "strategy",
            "dcmanager": "management",
            "system": "hostname",
        }
        expected = content_markers.get(cli_name, "")
        if expected and expected not in raw:
            if raw.strip() == "":
                return True
            get_logger().log_info(
                f"Command '{command}' missing expected content '{expected}': {raw[:150]}"
            )
            return False
        return True

    def wait_for_fm_api_ready(self, timeout: int = 120) -> None:
        """Wait for fm-api to be running after restart.

        Args:
            timeout (int): Maximum seconds to wait.
        """
        def check_fm_api_running() -> bool:
            """Check if fm-api is active and listening.

            Returns:
                bool: True if fm-api is ready.
            """
            output = self.ssh_connection.send("systemctl is-active fm-api 2>/dev/null")
            raw = "\n".join(output) if isinstance(output, list) else output
            if not raw:
                return False
            if "inactive" in raw or "active" not in raw:
                return False
            output = self.ssh_connection.send("ss -tln 2>/dev/null | grep -c ':18002'")
            raw = "\n".join(output) if isinstance(output, list) else output
            if not raw:
                return False
            return raw.strip() != "0"

        validate_equals_with_retry(
            function_to_execute=check_fm_api_running,
            expected_value=True,
            validation_description="Wait for fm-api to restart",
            timeout=timeout,
            polling_sleep_time=10,
        )

    def setup_ldap_user(self, username: str, password: str, group_name: str) -> None:
        """Create LDAP user and group, add user to group.

        Args:
            username (str): LDAP username to create.
            password (str): Password for the LDAP user.
            group_name (str): LDAP group to create and add user to.
        """
        ldap_kw = LdapKeywords(self.ssh_connection, password)
        ldap_kw.create_user(username, password)
        ldap_kw.create_group(group_name)
        ldap_kw.add_user_to_group(username, group_name)

    def cleanup_ldap_user(self, username: str, password: str, group_name: str, fm_oidc_kw: FmOidcKeywords = None) -> None:
        """Delete LDAP user and group created by the test.

        Args:
            username (str): LDAP username to delete.
            password (str): Sysadmin password for ansible playbook.
            group_name (str): LDAP group to delete.
            fm_oidc_kw (FmOidcKeywords): Optional FmOidcKeywords instance to close session.
        """
        get_logger().log_info(f"Cleaning up LDAP user {username} and group {group_name}")
        if fm_oidc_kw:
            fm_oidc_kw.close_session()
        ldap_kw = LdapKeywords(self.ssh_connection, password)
        ldap_kw.delete_user(username)
        ldap_kw.delete_group(group_name)

    def wait_for_rolebindings_file(self, timeout_sec: int = 60) -> None:
        """Wait for /etc/platform/.rolebindings.conf to be created by puppet.

        Args:
            timeout_sec (int): Maximum seconds to wait.
        """
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            output = self.ssh_connection.send(source_openrc("cat /etc/platform/.rolebindings.conf 2>&1"))
            raw = "\n".join(output) if isinstance(output, list) else output
            if "No such file" not in raw and raw.strip():
                get_logger().log_info(f"rolebindings.conf found: {raw.strip()[:80]}")
                return
            time.sleep(5)
        get_logger().log_info("rolebindings.conf not created within timeout")

    def setup_role_bindings(self, group_name: str, role: str) -> None:
        """Add identity stx role-bindings service parameter for the given group and role.

        Args:
            group_name (str): LDAP group name.
            role (str): STX role (admin, reader, operator, configurator).
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

        svc_param_kw = SystemServiceParameterKeywords(self.ssh_connection)

        existing = svc_param_kw.list_service_parameters(service=service, section=section)
        for param in existing.get_parameters():
            if param.get_name() == param_name:
                svc_param_kw.delete_service_parameter(param.get_uuid())
                svc_param_kw.apply_service_parameters(service, section=section)
                break

        svc_param_kw.add_service_parameter(service, section, param_name, param_value)
        svc_param_kw.apply_service_parameters(service, section=section)
        self.wait_for_rolebindings_file()

    def remove_role_bindings(self) -> None:
        """Remove identity stx role-bindings service parameter."""
        service = "identity"
        section = "stx"
        param_name = "role-bindings"
        svc_param_kw = SystemServiceParameterKeywords(self.ssh_connection)
        current = svc_param_kw.list_service_parameters(service=service, section=section)
        for p in current.get_parameters():
            if p.get_name() == param_name:
                svc_param_kw.delete_service_parameter(p.get_uuid())
                svc_param_kw.apply_service_parameters(service, section=section)
                break

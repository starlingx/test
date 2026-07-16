"""Keywords for DEX connector attribute mapping and oidc-username-claim operations."""

import json
import re
import time

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.security.oidc.object.oidc_token_claims_object import OidcTokenClaimsObject
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class DexConnectorKeywords(BaseKeyword):
    """Keywords for DEX connector attribute mapping and oidc-username-claim operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize DEX connector keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection
        self.helm_override_keywords = SystemHelmOverrideKeywords(ssh_connection)
        self.system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
        self.service_param_keywords = SystemServiceParameterKeywords(ssh_connection)
        self.kubectl_pods = KubectlGetPodsKeywords(ssh_connection)

    def apply_dex_override_and_reapply(self, yaml_file: str, app_name: str, namespace: str) -> None:
        """Apply DEX helm override and re-apply oidc-auth-apps.

        Waits for Dex pod to be Running and ready to serve requests
        after the application-apply completes.

        Args:
            yaml_file (str): Path to override YAML on controller.
            app_name (str): Application name (e.g., 'oidc-auth-apps').
            namespace (str): Chart namespace.
        """
        get_logger().log_info(f"Applying DEX helm override: {yaml_file}")
        self.helm_override_keywords.update_helm_override(yaml_file, app_name, "dex", namespace, reuse_values=False)
        self.system_app_apply.system_application_apply(app_name)
        self.wait_for_dex_ready(namespace)

    def set_oidc_username_claim(self, claim_value: str) -> None:
        """Set oidc-username-claim and apply kubernetes service parameters.

        Checks the running kube-apiserver manifest to determine if an apply
        is actually needed. Only triggers a restart when the manifest doesn't
        match the desired value, avoiding unnecessary disruption to Dex.

        Args:
            claim_value (str): Claim value (e.g., 'preferred_username' or 'email').
        """
        current = self.get_oidc_username_claim()
        if current != claim_value:
            get_logger().log_info(f"Setting oidc-username-claim='{claim_value}'")
            self.service_param_keywords.modify_service_parameter("kubernetes", "kube_apiserver", "oidc-username-claim", claim_value)
        else:
            # Service parameter already matches. Check if manifest also matches
            # AND apiserver is actually serving — if so, safe to skip.
            output = self.ssh_connection.send_as_sudo("grep oidc-username-claim /etc/kubernetes/manifests/kube-apiserver.yaml")
            raw = "\n".join(output) if isinstance(output, list) else str(output)
            if f"--oidc-username-claim={claim_value}" in raw:
                api_output = self.ssh_connection.send(export_k8s_config("kubectl get nodes --request-timeout=5s 2>&1"))
                api_raw = "\n".join(api_output) if isinstance(api_output, list) else str(api_output)
                if "Ready" in api_raw and "refused" not in api_raw.lower():
                    get_logger().log_info(f"kube-apiserver already running with oidc-username-claim={claim_value}, skipping apply")
                    return

        get_logger().log_info(f"Applying service parameters to set oidc-username-claim={claim_value}")
        # Retry apply in case the platform isn't ready (e.g., apiserver still restarting
        # from a previous apply, "Failed to generate bootstrap token" error)
        apply_end_time = time.time() + 60
        while time.time() < apply_end_time:
            apply_output = self.ssh_connection.send(source_openrc("system service-parameter-apply kubernetes"))
            apply_raw = "\n".join(apply_output) if isinstance(apply_output, list) else str(apply_output)
            if "Applying" in apply_raw:
                get_logger().log_info("Service parameter apply accepted")
                break
            get_logger().log_info(f"Service parameter apply failed ({apply_raw.strip()[:80]}), retrying in 10s")
            time.sleep(10)

        # Wait for manifest to be updated (platform pushes new manifest)
        get_logger().log_info("Waiting for kube-apiserver manifest to update with new claim value")
        end_time = time.time() + 90
        while time.time() < end_time:
            verify_output = self.ssh_connection.send_as_sudo("grep oidc-username-claim /etc/kubernetes/manifests/kube-apiserver.yaml")
            verify_raw = "\n".join(verify_output) if isinstance(verify_output, list) else str(verify_output)
            if f"--oidc-username-claim={claim_value}" in verify_raw:
                get_logger().log_info(f"Confirmed kube-apiserver manifest has oidc-username-claim={claim_value}")
                break
            time.sleep(5)

        # Wait for apiserver pods to restart with new manifest and become Ready
        get_logger().log_info("Waiting for kube-apiserver pods to restart with new config")
        time.sleep(10)  # Give kubelet time to detect manifest change and initiate restart
        self._wait_for_all_apiservers_ready()

        # Verify the API is stable (both controllers serving via VIP).
        # After service-parameter-apply, controllers restart sequentially. The VIP
        # may briefly work (one controller) then go down (second controller restart).
        # Require 3 consecutive successes 5s apart to confirm stability.
        get_logger().log_info("Verifying kube-apiserver is stable (3 consecutive checks)")
        api_end_time = time.time() + 120
        consecutive_ok = 0
        while time.time() < api_end_time:
            api_output = self.ssh_connection.send(export_k8s_config("kubectl get nodes --request-timeout=5s 2>&1"))
            api_raw = "\n".join(api_output) if isinstance(api_output, list) else str(api_output)
            if "connection refused" not in api_raw.lower() and "refused" not in api_raw.lower() and "was refused" not in api_raw.lower():
                consecutive_ok += 1
                if consecutive_ok >= 3:
                    get_logger().log_info("kube-apiserver is stable (3 consecutive successful checks)")
                    break
            else:
                consecutive_ok = 0
                get_logger().log_info("kube-apiserver not ready yet, retrying in 5s")
            time.sleep(5)
        # Note: Do NOT restart Dex pods here. The oidc-username-claim is a
        # kube-apiserver parameter only. Restarting Dex generates new signing
        # keys, which invalidates all cached tokens and causes Unauthorized
        # errors until the apiserver refreshes its JWKS cache.

        # Wait for apiserver OIDC subsystem to initialize (fetch JWKS from Dex).
        # After restart, the apiserver needs to connect to the Dex issuer and
        # download signing keys before it can validate OIDC tokens.
        get_logger().log_info("Waiting for apiserver OIDC subsystem to fetch JWKS from Dex")
        oam_ip = ConfigurationManager.get_lab_config().get_floating_ip()
        if ":" in oam_ip:
            oam_ip = f"[{oam_ip}]"
        dex_jwks_url = f"https://{oam_ip}:30556/dex/keys"
        oidc_ready_time = time.time() + 60
        while time.time() < oidc_ready_time:
            jwks_output = self.ssh_connection.send(f"curl -sk {dex_jwks_url} 2>&1")
            jwks_raw = "\n".join(jwks_output) if isinstance(jwks_output, list) else str(jwks_output)
            if '"keys"' in jwks_raw:
                get_logger().log_info("Dex JWKS endpoint serving keys — apiserver OIDC should be ready")
                # Give apiserver a moment to fetch and cache the keys
                time.sleep(5)
                break
            time.sleep(5)

    def _wait_for_all_apiservers_ready(self, timeout: int = 300, require_fresh: bool = False) -> None:
        """Wait for all kube-apiserver pods to be 1/1 Ready.

        On DX/Standard systems there are multiple apiserver pods.
        After service-parameter-apply, all must restart and become ready.

        Args:
            timeout (int): Maximum wait time in seconds.
            require_fresh (bool): If True, also wait for pods to have age < 3m (recently restarted).
        """
        get_logger().log_info("Waiting for all kube-apiserver pods to be Ready")
        end_time = time.time() + timeout
        while time.time() < end_time:
            output = self.ssh_connection.send(export_k8s_config("kubectl get pods -n kube-system"))
            raw = "\n".join(output) if isinstance(output, list) else str(output)
            apiserver_lines = [line for line in raw.split("\n") if "kube-apiserver" in line]
            if apiserver_lines:
                all_ready = all("1/1" in line and "Running" in line for line in apiserver_lines)
                if all_ready:
                    if not require_fresh:
                        get_logger().log_info(f"All {len(apiserver_lines)} kube-apiserver pod(s) are Ready")
                        return
                    # Check pods are young: age column shows Xs or Xm where X < 3
                    all_fresh = all(re.search(r"\s(\d+s|[012]m\d+s|[012]m)\s", line) for line in apiserver_lines)
                    if all_fresh:
                        get_logger().log_info(f"All {len(apiserver_lines)} kube-apiserver pod(s) are Ready and freshly restarted")
                        return
            time.sleep(10)
        get_logger().log_info("Warning: Not all kube-apiserver pods became Ready within timeout")

    def wait_for_dex_ready(self, namespace: str = "kube-system", timeout: int = 120, raise_on_timeout: bool = False) -> None:
        """Wait for Dex pod to be Running and ready to serve OIDC requests.

        After application-apply, the Dex pod may take time to initialize
        connectors (especially remote OIDC connectors like Keycloak).
        This method waits until the Dex OIDC discovery AND auth endpoints
        respond successfully via the OAM NodePort.

        Args:
            namespace (str): Kubernetes namespace for Dex pods.
            timeout (int): Maximum wait time in seconds.
            raise_on_timeout (bool): If True, raise KeywordException on timeout instead of logging warning.
        """
        get_logger().log_info("Waiting for Dex pod to be ready and serving OIDC requests")
        self.kubectl_pods.wait_for_pod_status(
            pod_name="oidc-dex",
            expected_status="Running",
            namespace=namespace,
            timeout=timeout,
        )
        # Wait for Dex to respond to OIDC discovery and auth (connector initialized)
        oam_ip = ConfigurationManager.get_lab_config().get_floating_ip()
        if ":" in oam_ip:
            oam_ip = f"[{oam_ip}]"
        dex_url = f"https://{oam_ip}:30556/dex/.well-known/openid-configuration"
        dex_auth_url = f"https://{oam_ip}:30556/dex/auth?client_id=stx-oidc-client-app&response_type=code&scope=openid&redirect_uri=http://localhost:8000"
        get_logger().log_info(f"Checking Dex discovery endpoint: {dex_url}")
        end_time = time.time() + timeout
        while time.time() < end_time:
            output = self.ssh_connection.send(f"curl -sk {dex_url} 2>&1")
            raw = "\n".join(output) if isinstance(output, list) else str(output)
            if "issuer" in raw:
                # Also verify Dex auth endpoint works (connector initialized)
                auth_output = self.ssh_connection.send(f"curl -sk -o /dev/null -w '%{{http_code}}' '{dex_auth_url}' 2>&1")
                auth_raw = "\n".join(auth_output) if isinstance(auth_output, list) else str(auth_output)
                if "200" in auth_raw or "301" in auth_raw or "302" in auth_raw:
                    get_logger().log_info("Dex OIDC discovery and auth endpoints responding")
                    return
                # Auth endpoint not ready — remote OIDC connectors (Keycloak) need
                # time to initialize. Do NOT restart pods — that generates new signing
                # keys which invalidates all tokens and breaks apiserver OIDC validation.
                get_logger().log_info("Dex discovery OK but auth endpoint not ready yet, waiting 10s")
                time.sleep(10)
                continue
            time.sleep(5)
        if raise_on_timeout:
            raise KeywordException(f"Dex discovery endpoint did not respond within {timeout}s. Dex may not be functional.")
        get_logger().log_info("Warning: Dex discovery endpoint did not respond within timeout, proceeding anyway")

    def get_oidc_username_claim(self) -> str:
        """Get current oidc-username-claim value.

        Returns:
            str: Current value, or empty string if not set.
        """
        output = self.service_param_keywords.list_service_parameters(service="kubernetes", section="kube_apiserver")
        for param in output.get_parameters():
            if param.get_name() == "oidc-username-claim":
                return param.get_value()
        return ""

    def decode_cached_token(self) -> OidcTokenClaimsObject:
        """Decode the cached OIDC ID token and return structured claims object.

        Reads the ID token from the user's kubeconfig, decodes the JWT
        payload (base64), and returns an OidcTokenClaimsObject with typed
        getters for standard OIDC claims.

        Returns:
            OidcTokenClaimsObject: Parsed token claims with getter methods.

        Raises:
            KeywordException: If no token is found in kubeconfig or decoding fails.
        """
        get_logger().log_info("Decoding cached OIDC ID token")
        output = self.ssh_connection.send("grep 'token:' ~/.kube/config | head -1 | awk '{print $2}' | cut -d'.' -f2 | base64 -d 2>/dev/null")
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        raw = raw.strip()
        if not raw or raw == "None":
            raise KeywordException("No OIDC token found in ~/.kube/config. Ensure oidc-auth completed successfully before decoding.")
        try:
            claims_dict = json.loads(raw)
        except json.JSONDecodeError as e:
            raise KeywordException(f"Failed to decode OIDC token payload as JSON: {e}. Raw output: {raw[:200]}")
        return OidcTokenClaimsObject(claims_dict)

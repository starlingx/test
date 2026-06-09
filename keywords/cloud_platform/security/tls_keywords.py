"""Keywords for TLS endpoint connection testing and cipher validation."""

import time

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.security.objects.tls_endpoint_ips_object import TlsEndpointIpsObject
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.cloud_platform.system.oam.system_oam_show_keywords import SystemOamShowKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords

CONFIG_OUT_OF_DATE_ALARM_ID = "250.001"
KNOWN_OS_CODENAMES = ("bullseye", "bookworm", "trixie")
NGINX_INGRESS_CONFIGMAP = "ic-nginx-ingress-ingress-nginx-controller"
NGINX_INGRESS_NAMESPACE = "kube-system"
TLS_VERSIONS = {
    "-tls1_1": "TLS 1.1",
    "-tls1_2": "TLS 1.2",
    "-tls1_3": "TLS 1.3",
}


class TlsKeywords(BaseKeyword):
    """Keywords for TLS connection testing on platform endpoints."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize TLS keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self.oam_show_keywords = SystemOamShowKeywords(ssh_connection)
        self.addrpool_keywords = SystemAddrpoolListKeywords(ssh_connection)
        self.alarm_keywords = AlarmListKeywords(ssh_connection)
        self.service_param_keywords = SystemServiceParameterKeywords(ssh_connection)

    def get_endpoint_ips(self) -> TlsEndpointIpsObject:
        """Retrieve OAM and management floating IPs.

        Returns:
            TlsEndpointIpsObject: Object with oam_ip, mgmt_ip, and is_ipv6 getters.
        """
        lab_config = ConfigurationManager.get_lab_config()
        is_ipv6 = lab_config.is_ipv6()

        oam_info = self.oam_show_keywords.oam_show()
        oam_ip = oam_info.get_oam_floating_ip() or oam_info.get_oam_ip()
        get_logger().log_info(f"OAM IP: {oam_ip}")

        addrpool_output = self.addrpool_keywords.get_system_addrpool_list()
        mgmt_ip = addrpool_output.get_management_floating_address()
        get_logger().log_info(f"Management IP: {mgmt_ip}")

        return TlsEndpointIpsObject(oam_ip, mgmt_ip, is_ipv6)

    def get_os_version(self) -> str:
        """Get the OS version codename (bullseye, bookworm, trixie, etc.).

        Returns:
            str: OS version codename or 'unknown'.
        """
        output = self.ssh_connection.send("cat /etc/os-release | grep VERSION_CODENAME")  # no validation needed
        self.validate_success_return_code(self.ssh_connection)
        output_str = output if isinstance(output, str) else str(output)
        for codename in KNOWN_OS_CODENAMES:
            if codename in output_str.lower():
                return codename
        get_logger().log_warning(f"Unknown OS version from: {output}")
        return "unknown"

    def resolve_host(self, endpoint: dict, oam_ip: str, mgmt_ip: str) -> str:
        """Resolve the target host for an endpoint definition.

        Args:
            endpoint (dict): Endpoint dict with optional 'host', 'use_mgmt' keys.
            oam_ip (str): OAM floating IP.
            mgmt_ip (str): Management floating IP.

        Returns:
            str: Resolved host IP or hostname.
        """
        if endpoint.get("host"):
            return endpoint["host"]
        if endpoint.get("use_mgmt"):
            return mgmt_ip
        return oam_ip

    def build_connect_str(self, host: str, port: int, is_ipv6: bool = False) -> str:
        """Build the openssl -connect argument string.

        Args:
            host (str): Target host.
            port (int): Target port.
            is_ipv6 (bool): Whether to wrap host in brackets for IPv6.

        Returns:
            str: Connection string in host:port format.
        """
        if is_ipv6 and host not in ("registry.local",):
            return f"[{host}]:{port}"
        return f"{host}:{port}"

    def _normalize_output(self, output: object) -> str:
        """Normalize SSH command output to a lowercase string.

        Args:
            output (object): Raw output from ssh_connection.send().

        Returns:
            str: Lowercased string output.
        """
        if isinstance(output, list):
            return " ".join(str(item) for item in output).lower()
        return str(output).lower()

    def run_openssl_connection(self, host: str, port: int, tls_version: str, is_ipv6: bool = False) -> str:
        """Run openssl s_client with a specific TLS version flag.

        Args:
            host (str): Target host.
            port (int): Target port.
            tls_version (str): TLS version flag (e.g., '-tls1_2', '-tls1_3').
            is_ipv6 (bool): Whether the host is IPv6.

        Returns:
            str: Lowercased openssl output.
        """
        connect_str = self.build_connect_str(host, port, is_ipv6)
        cmd = f"echo | openssl s_client -connect {connect_str} {tls_version} 2>&1"
        output = self.ssh_connection.send(cmd)  # no validation needed
        # Note: validate_success_return_code intentionally skipped — openssl returns
        # non-zero on rejected handshakes, which is expected behavior under test.
        get_logger().log_info(f"openssl s_client {tls_version} to {connect_str} output: {output}")
        return self._normalize_output(output)

    def run_openssl_cipher_connection(self, host: str, port: int, cipher: str, is_ipv6: bool = False) -> str:
        """Run openssl s_client with a specific TLS 1.2 cipher suite.

        Args:
            host (str): Target host.
            port (int): Target port.
            cipher (str): OpenSSL cipher name.
            is_ipv6 (bool): Whether the host is IPv6.

        Returns:
            str: Lowercased openssl output.
        """
        connect_str = self.build_connect_str(host, port, is_ipv6)
        cmd = f"echo | openssl s_client -connect {connect_str} -tls1_2 -cipher '{cipher}' 2>&1"
        output = self.ssh_connection.send(cmd)  # no validation needed
        get_logger().log_info(f"openssl s_client -tls1_2 -cipher '{cipher}' to {connect_str} output: {output}")
        return self._normalize_output(output)

    def run_openssl_tls13_ciphersuite_connection(
        self,
        host: str,
        port: int,
        ciphersuite: str,
        is_ipv6: bool = False,
    ) -> str:
        """Run openssl s_client with a specific TLS 1.3 ciphersuite.

        Args:
            host (str): Target host.
            port (int): Target port.
            ciphersuite (str): TLS 1.3 ciphersuite name.
            is_ipv6 (bool): Whether the host is IPv6.

        Returns:
            str: Lowercased openssl output.
        """
        connect_str = self.build_connect_str(host, port, is_ipv6)
        cmd = f"echo | openssl s_client -connect {connect_str} -tls1_3 -ciphersuites '{ciphersuite}' 2>&1"
        output = self.ssh_connection.send(cmd)  # no validation needed
        get_logger().log_info(f"openssl s_client -tls1_3 -ciphersuites '{ciphersuite}' to {connect_str} output: {output}")
        return self._normalize_output(output)

    def run_openssl_default_connection(self, host: str, port: int, is_ipv6: bool = False) -> str:
        """Run openssl s_client with default settings.

        Args:
            host (str): Target host.
            port (int): Target port.
            is_ipv6 (bool): Whether the host is IPv6.

        Returns:
            str: Lowercased openssl output.
        """
        connect_str = self.build_connect_str(host, port, is_ipv6)
        cmd = f"echo | openssl s_client -connect {connect_str} 2>&1"
        output = self.ssh_connection.send(cmd)  # no validation needed
        get_logger().log_info(f"openssl s_client (default) to {connect_str} output: {output}")
        return self._normalize_output(output)

    def run_openssl_tls13_with_tls12_cipher(self, host: str, port: int, cipher: str, is_ipv6: bool = False) -> str:
        """Run openssl s_client forcing TLS 1.3 but with a TLS 1.2 -cipher flag.

        Tests that TLS 1.3 ignores the -cipher flag which is TLS 1.2 only.

        Args:
            host (str): Target host.
            port (int): Target port.
            cipher (str): TLS 1.2 cipher name to pass via -cipher flag.
            is_ipv6 (bool): Whether the host is IPv6.

        Returns:
            str: Lowercased openssl output.
        """
        connect_str = self.build_connect_str(host, port, is_ipv6)
        cmd = f"echo | openssl s_client -connect {connect_str} -tls1_3 -cipher '{cipher}' 2>&1"
        output = self.ssh_connection.send(cmd)  # no validation needed
        get_logger().log_info(f"openssl s_client -tls1_3 -cipher '{cipher}' to {connect_str} output: {output}")
        return self._normalize_output(output)

    def run_openssl_tls12_with_tls13_ciphersuite(self, host: str, port: int, ciphersuite: str, is_ipv6: bool = False) -> str:
        """Run openssl s_client forcing TLS 1.2 but with a TLS 1.3 -ciphersuites flag.

        Tests that TLS 1.2 ignores the -ciphersuites flag which is TLS 1.3 only.

        Args:
            host (str): Target host.
            port (int): Target port.
            ciphersuite (str): TLS 1.3 ciphersuite name to pass via -ciphersuites flag.
            is_ipv6 (bool): Whether the host is IPv6.

        Returns:
            str: Lowercased openssl output.
        """
        connect_str = self.build_connect_str(host, port, is_ipv6)
        cmd = f"echo | openssl s_client -connect {connect_str} -tls1_2 -ciphersuites '{ciphersuite}' 2>&1"
        output = self.ssh_connection.send(cmd)  # no validation needed
        get_logger().log_info(f"openssl s_client -tls1_2 -ciphersuites '{ciphersuite}' to {connect_str} output: {output}")
        return self._normalize_output(output)

    @staticmethod
    def is_tls_handshake_rejected(output: str) -> bool:
        """Check if TLS handshake was rejected.

        Null cipher means no TLS session established. Also handles OpenSSL
        client-side errors (invalid cipher names) as rejections.

        Args:
            output (str): Lowercased openssl s_client output.

        Returns:
            bool: True if handshake was rejected.
        """
        if "cipher is (none)" in output or "cipher    : 0000" in output:
            return True
        if "tlsv1 alert protocol version" in output:
            return True
        if "no cipher match" in output or "ssl_ctx_set_cipher_list" in output:
            return True
        return False

    def verify_cipher_rejected(self, host: str, port: int, cipher: str, endpoint_name: str, is_ipv6: bool = False) -> None:
        """Verify that a connection with the given cipher suite is rejected.

        Args:
            host (str): Target host.
            port (int): Target port.
            cipher (str): OpenSSL cipher name.
            endpoint_name (str): Human-readable endpoint name for logging.
            is_ipv6 (bool): Whether the host is IPv6.
        """
        get_logger().log_info(f"Verifying cipher '{cipher}' is rejected on {endpoint_name}")
        output = self.run_openssl_cipher_connection(host, port, cipher, is_ipv6)
        validate_equals(
            self.is_tls_handshake_rejected(output),
            True,
            f"Cipher '{cipher}' rejected on {endpoint_name} ({host}:{port})",
        )

    def verify_cipher_accepted(self, host: str, port: int, cipher: str, endpoint_name: str, is_ipv6: bool = False) -> None:
        """Verify that a TLS 1.2 connection with the given cipher suite succeeds.

        Args:
            host (str): Target host.
            port (int): Target port.
            cipher (str): OpenSSL cipher name.
            endpoint_name (str): Human-readable endpoint name for logging.
            is_ipv6 (bool): Whether the host is IPv6.
        """
        get_logger().log_info(f"Verifying cipher '{cipher}' is accepted on {endpoint_name}")
        output = self.run_openssl_cipher_connection(host, port, cipher, is_ipv6)
        validate_equals(
            self.is_tls_handshake_rejected(output),
            False,
            f"Cipher '{cipher}' accepted on {endpoint_name} ({host}:{port})",
        )

    def verify_ecdsa_cipher_rejected_cert_mismatch(
        self,
        host: str,
        port: int,
        cipher: str,
        endpoint_name: str,
        is_ipv6: bool = False,
    ) -> None:
        """Verify ECDSA cipher is rejected due to RSA certificate mismatch.

        Args:
            host (str): Target host.
            port (int): Target port.
            cipher (str): ECDSA cipher name.
            endpoint_name (str): Human-readable endpoint name for logging.
            is_ipv6 (bool): Whether the host is IPv6.
        """
        get_logger().log_info(f"Verifying ECDSA cipher '{cipher}' rejected (cert mismatch) on {endpoint_name}")
        output = self.run_openssl_cipher_connection(host, port, cipher, is_ipv6)
        validate_equals(
            self.is_tls_handshake_rejected(output),
            True,
            f"ECDSA cipher '{cipher}' rejected on {endpoint_name} ({host}:{port})",
        )

    def verify_tls13_ciphersuite_accepted(
        self,
        host: str,
        port: int,
        ciphersuite: str,
        endpoint_name: str,
        is_ipv6: bool = False,
    ) -> None:
        """Verify that a TLS 1.3 connection with the given ciphersuite succeeds.

        Args:
            host (str): Target host.
            port (int): Target port.
            ciphersuite (str): TLS 1.3 ciphersuite name.
            endpoint_name (str): Human-readable endpoint name for logging.
            is_ipv6 (bool): Whether the host is IPv6.
        """
        get_logger().log_info(f"Verifying TLS 1.3 ciphersuite '{ciphersuite}' accepted on {endpoint_name}")
        output = self.run_openssl_tls13_ciphersuite_connection(host, port, ciphersuite, is_ipv6)
        validate_equals(
            self.is_tls_handshake_rejected(output),
            False,
            f"TLS 1.3 '{ciphersuite}' accepted on {endpoint_name} ({host}:{port})",
        )

    def verify_tls13_ciphersuite_rejected(
        self,
        host: str,
        port: int,
        ciphersuite: str,
        endpoint_name: str,
        is_ipv6: bool = False,
    ) -> None:
        """Verify that a TLS 1.3 connection with the given ciphersuite is rejected.

        Args:
            host (str): Target host.
            port (int): Target port.
            ciphersuite (str): TLS 1.3 ciphersuite name.
            endpoint_name (str): Human-readable endpoint name for logging.
            is_ipv6 (bool): Whether the host is IPv6.
        """
        get_logger().log_info(f"Verifying TLS 1.3 ciphersuite '{ciphersuite}' rejected on {endpoint_name}")
        output = self.run_openssl_tls13_ciphersuite_connection(host, port, ciphersuite, is_ipv6)
        validate_equals(
            self.is_tls_handshake_rejected(output),
            True,
            f"TLS 1.3 '{ciphersuite}' rejected on {endpoint_name} ({host}:{port})",
        )

    def verify_default_cipher_in_use(self, host: str, port: int, endpoint_name: str, is_ipv6: bool = False) -> None:
        """Verify that a default connection negotiates a non-null cipher.

        Args:
            host (str): Target host.
            port (int): Target port.
            endpoint_name (str): Human-readable endpoint name for logging.
            is_ipv6 (bool): Whether the host is IPv6.
        """
        get_logger().log_info(f"Verifying default cipher in use on {endpoint_name}")
        output = self.run_openssl_default_connection(host, port, is_ipv6)
        validate_equals(
            self.is_tls_handshake_rejected(output),
            False,
            f"Allowed cipher negotiated on {endpoint_name} ({host}:{port})",
        )

    def wait_for_tls_version_propagation(self, host: str, port: int, tls_flag: str, expect_rejected: bool, is_ipv6: bool = False, timeout: int = 180, interval: int = 15) -> None:
        """Poll until TLS version enforcement has propagated to the endpoint.

        Args:
            host (str): Target host.
            port (int): Target port.
            tls_flag (str): OpenSSL TLS version flag (e.g. '-tls1_2').
            expect_rejected (bool): True if we expect the version to be rejected.
            is_ipv6 (bool): Whether the host is IPv6.
            timeout (int): Maximum seconds to wait.
            interval (int): Seconds between polls.
        """
        deadline = time.time() + timeout
        while True:
            output = self.run_openssl_connection(host, port, tls_flag, is_ipv6)
            rejected = self.is_tls_handshake_rejected(output)
            if rejected == expect_rejected:
                status = "rejected" if rejected else "accepted"
                get_logger().log_info(f"TLS {tls_flag} on {host}:{port} is {status} as expected")
                return
            if time.time() >= deadline:
                status = "rejected" if expect_rejected else "accepted"
                get_logger().log_warning(f"Timeout waiting for TLS {tls_flag} to be {status} on {host}:{port}")
                return
            status = "rejected" if expect_rejected else "accepted"
            get_logger().log_info(f"TLS {tls_flag} not yet {status} on {host}:{port}, retrying in {interval}s")
            time.sleep(interval)

    def wait_for_cipher_propagation(
        self,
        host: str,
        port: int,
        cipher: str,
        expect_rejected: bool,
        is_ipv6: bool = False,
        timeout: int = 180,
        interval: int = 15,
    ) -> None:
        """Poll until the cipher enforcement change has propagated to the endpoint.

        Args:
            host (str): Target host.
            port (int): Target port.
            cipher (str): OpenSSL cipher name to test.
            expect_rejected (bool): True if we expect the cipher to be rejected.
            is_ipv6 (bool): Whether the host is IPv6.
            timeout (int): Maximum seconds to wait.
            interval (int): Seconds between polls.
        """
        deadline = time.time() + timeout
        while True:
            output = self.run_openssl_cipher_connection(host, port, cipher, is_ipv6)
            rejected = self.is_tls_handshake_rejected(output)
            if rejected == expect_rejected:
                status = "rejected" if rejected else "accepted"
                get_logger().log_info(f"Cipher '{cipher}' on {host}:{port} is {status} as expected")
                return
            if time.time() >= deadline:
                get_logger().log_info(f"Timeout waiting for cipher propagation on {host}:{port}")
                return
            status = "rejected" if expect_rejected else "accepted"
            get_logger().log_info(f"Cipher '{cipher}' not yet {status}, retrying in {interval}s")
            time.sleep(interval)

    def run_nmap_cipher_scan(self, host: str, port: int, is_ipv6: bool = False) -> str:
        """Run nmap ssl-enum-ciphers script against the given host:port.

        Args:
            host (str): Target host.
            port (int): Target port.
            is_ipv6 (bool): Whether the host is IPv6.

        Returns:
            str: Lowercased nmap output.
        """
        ipv6_flag = "-6" if is_ipv6 else ""
        cmd = f"nmap {ipv6_flag} --script ssl-enum-ciphers -p {port} {host} 2>&1"
        output = self.ssh_connection.send(cmd)  # no validation needed
        get_logger().log_info(f"nmap ssl-enum-ciphers on {host}:{port} output: {output}")
        return self._normalize_output(output)

    def apply_cipher_list(self, cipher_list: str) -> None:
        """Apply a cipher list to platform and kubernetes service parameters.

        Args:
            cipher_list (str): IANA cipher list string to apply.
        """
        self.service_param_keywords.modify_service_parameter("platform", "config", "tls-cipher-suite", cipher_list)
        self.service_param_keywords.modify_service_parameter("kubernetes", "kube_apiserver", "tls-cipher-suites", cipher_list)
        self.service_param_keywords.apply_service_parameters("kubernetes")
        self.wait_for_config_out_of_date_alarm_clear()

    def restore_cipher_with_retry(self, service: str, section: str, parameter: str, value: str) -> None:
        """Restore a cipher parameter with retry and add-fallback.

        Args:
            service (str): Service name (platform/kubernetes).
            section (str): Section name (config/kube_apiserver).
            parameter (str): Parameter name.
            value (str): Value to restore.
        """
        self.service_param_keywords.modify_service_parameter(service, section, parameter, value)

    def restore_original_cipher_config(self, original_cipher_list: str) -> None:
        """Restore original cipher suite parameters for both platform and kubernetes.

        Args:
            original_cipher_list (str): The original IANA cipher list to restore.
        """
        get_logger().log_info("Restoring original cipher configurations")
        self.restore_cipher_with_retry("platform", "config", "tls-cipher-suite", original_cipher_list)
        self.service_param_keywords.apply_service_parameters("platform")
        self.restore_cipher_with_retry("kubernetes", "kube_apiserver", "tls-cipher-suites", original_cipher_list)
        self.service_param_keywords.apply_service_parameters("kubernetes")

    def wait_for_config_out_of_date_alarm_clear(self, timeout: int = 300, interval: int = 15) -> bool:
        """Wait for alarm 250.001 (config out-of-date) to be raised and cleared.

        After applying service parameters, this indicates all services have
        picked up the new config.

        Args:
            timeout (int): Maximum seconds to wait for alarm to clear.
            interval (int): Seconds between polls.

        Returns:
            bool: True if alarm cleared successfully, False on timeout.
        """
        get_logger().log_info("Waiting 10s for config out-of-date alarm (250.001) to be raised")
        time.sleep(10)

        if not self.alarm_keywords.is_alarm_present(CONFIG_OUT_OF_DATE_ALARM_ID):
            get_logger().log_info(f"Alarm {CONFIG_OUT_OF_DATE_ALARM_ID} not present, config may already be applied")
            return True

        get_logger().log_info(f"Alarm {CONFIG_OUT_OF_DATE_ALARM_ID} detected, waiting to clear (up to {timeout}s)")

        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.alarm_keywords.is_alarm_present(CONFIG_OUT_OF_DATE_ALARM_ID):
                get_logger().log_info(f"Alarm {CONFIG_OUT_OF_DATE_ALARM_ID} cleared — config applied to all services")
                self.wait_for_app_reapply_alarm_clear()
                return True
            get_logger().log_info(f"Alarm {CONFIG_OUT_OF_DATE_ALARM_ID} still active, retrying in {interval}s")
            time.sleep(interval)

        get_logger().log_warning(f"Alarm {CONFIG_OUT_OF_DATE_ALARM_ID} did not clear within {timeout}s")
        return False

    def wait_for_app_reapply_alarm_clear(self, timeout: int = 300, interval: int = 15) -> bool:
        """Wait for alarm 750.006 (app reapply needed) and 750.004 (apply in progress) to clear.

        After TLS/cipher changes, nginx-ingress and oidc-auth-apps are auto-reapplied.
        This waits for the reapply to complete so pods are ready with new config.

        Args:
            timeout (int): Maximum seconds to wait.
            interval (int): Seconds between polls.

        Returns:
            bool: True if alarms cleared, False on timeout.
        """
        APP_REAPPLY_ALARM_ID = "750.006"
        APP_APPLY_IN_PROGRESS_ALARM_ID = "750.004"
        if not self.alarm_keywords.is_alarm_present(APP_REAPPLY_ALARM_ID) and not self.alarm_keywords.is_alarm_present(APP_APPLY_IN_PROGRESS_ALARM_ID):
            return True
        get_logger().log_info(f"Alarm 750.006/750.004 present — waiting for auto-reapply to complete (up to {timeout}s)")
        deadline = time.time() + timeout
        while time.time() < deadline:
            has_reapply = self.alarm_keywords.is_alarm_present(APP_REAPPLY_ALARM_ID)
            has_in_progress = self.alarm_keywords.is_alarm_present(APP_APPLY_IN_PROGRESS_ALARM_ID)
            if not has_reapply and not has_in_progress:
                get_logger().log_info("Alarms 750.006 and 750.004 cleared — apps reapplied successfully")
                ep_ips = self.get_endpoint_ips()
                self.wait_for_port_ready(ep_ips.get_oam_ip(), 443, ep_ips.is_ipv6_lab())
                return True
            time.sleep(interval)
        get_logger().log_warning(f"App reapply alarms did not clear within {timeout}s")
        return False

    def get_haproxy_bind_ciphers(self) -> str:
        """Get ssl-default-bind-ciphers from haproxy.cfg.

        Returns:
            str: The haproxy ssl-default-bind-ciphers line content.
        """
        output = self.ssh_connection.send("sudo grep ssl-default-bind-ciphers /etc/haproxy/haproxy.cfg")  # no validation needed
        return str(output)

    def get_nginx_configmap_value(self, key: str) -> str:
        """Get a value from nginx-ingress-controller ConfigMap.

        Args:
            key (str): The key to grep for (e.g. ssl-protocols, ssl-ciphers).

        Returns:
            str: The matching ConfigMap content.
        """
        output = self.ssh_connection.send(f"kubectl get cm -n {NGINX_INGRESS_NAMESPACE} {NGINX_INGRESS_CONFIGMAP} -o yaml | grep {key}")  # no validation needed
        return str(output)

    def wait_for_port_ready(self, host: str, port: int, is_ipv6: bool = False, retries: int = 5, delay: int = 2) -> bool:
        """Wait until a TCP port is accepting connections.

        Args:
            host (str): Target host.
            port (int): Target port.
            is_ipv6 (bool): Whether the host is IPv6.
            retries (int): Number of retries.
            delay (int): Seconds between retries.

        Returns:
            bool: True if port is ready.
        """
        for attempt in range(retries):
            cmd = f"bash -c 'echo > /dev/tcp/{host}/{port}' 2>&1"
            output = self.ssh_connection.send(cmd)  # no validation needed
            output_str = output if isinstance(output, str) else str(output)
            if "connection refused" not in output_str.lower() and "no route" not in output_str.lower():
                return True
            get_logger().log_info(f"Port {host}:{port} not ready, retry {attempt + 1}/{retries} in {delay}s")
            time.sleep(delay)
        get_logger().log_warning(f"Port {host}:{port} not ready after {retries} retries")
        return False

    def verify_cipher_removal_on_endpoints(self, endpoints: list, cipher_config: dict, endpoint_context: dict) -> None:
        """Verify cipher removal enforcement across all endpoints.

        Args:
            endpoints (list): List of endpoint dicts to test.
            cipher_config (dict): Dict with removed_tls12, removed_tls13, remaining_tls12, remaining_tls13.
            endpoint_context (dict): Dict with oam_ip, mgmt_ip, is_ipv6, tls13_not_enforced, skip_cipher_removal.
        """
        oam_ip = endpoint_context["oam_ip"]
        mgmt_ip = endpoint_context["mgmt_ip"]
        is_ipv6 = endpoint_context["is_ipv6"]
        tls13_not_enforced = endpoint_context["tls13_not_enforced"]
        skip_cipher_removal = endpoint_context["skip_cipher_removal"]

        for ep in endpoints:
            host = self.resolve_host(ep, oam_ip, mgmt_ip)
            ep_is_ipv6 = is_ipv6 and not ep.get("host")
            name = ep["name"]

            if name in skip_cipher_removal:
                get_logger().log_info(f"Skipping {name} - not governed by platform tls-cipher-suite")
                continue

            get_logger().log_test_case_step(f"Verifying cipher removal on {name}")
            self.verify_cipher_rejected(host, ep["port"], cipher_config["removed_tls12"], name, ep_is_ipv6)

            if name in tls13_not_enforced:
                self.verify_tls13_ciphersuite_accepted(host, ep["port"], cipher_config["removed_tls13"], name, ep_is_ipv6)
            else:
                self.verify_tls13_ciphersuite_rejected(host, ep["port"], cipher_config["removed_tls13"], name, ep_is_ipv6)

            self.verify_cipher_accepted(host, ep["port"], cipher_config["remaining_tls12"], name, ep_is_ipv6)
            self.verify_tls13_ciphersuite_accepted(host, ep["port"], cipher_config["remaining_tls13"], name, ep_is_ipv6)

    def verify_single_cipher_on_endpoints(self, endpoints: list, accepted_cipher: str, rejected_ciphers: list, endpoint_context: dict) -> None:
        """Verify only one cipher is accepted and others are rejected on endpoints.

        Args:
            endpoints (list): List of endpoint dicts to test.
            accepted_cipher (str): The single cipher that should be accepted.
            rejected_ciphers (list): List of ciphers that should be rejected.
            endpoint_context (dict): Dict with keys oam_ip, mgmt_ip, is_ipv6.
        """
        oam_ip = endpoint_context["oam_ip"]
        mgmt_ip = endpoint_context["mgmt_ip"]
        is_ipv6 = endpoint_context["is_ipv6"]

        for ep in endpoints:
            host = self.resolve_host(ep, oam_ip, mgmt_ip)
            ep_is_ipv6 = is_ipv6 and not ep.get("host")
            name = ep["name"]

            get_logger().log_test_case_step(f"Verifying single cipher enforcement on {name}")
            self.verify_cipher_accepted(host, ep["port"], accepted_cipher, name, ep_is_ipv6)
            for cipher in rejected_ciphers:
                self.verify_cipher_rejected(host, ep["port"], cipher, name, ep_is_ipv6)

    def verify_tls_rejected(self, host: str, port: int, tls_flag: str, endpoint_name: str, is_ipv6: bool = False) -> None:
        """Verify that a TLS connection with the given version flag is rejected.

        Args:
            host (str): Target host.
            port (int): Target port.
            tls_flag (str): TLS version flag (e.g., '-tls1_1').
            endpoint_name (str): Endpoint display name for logging.
            is_ipv6 (bool): Whether the host is IPv6.
        """
        tls_label = TLS_VERSIONS.get(tls_flag, tls_flag)
        get_logger().log_info(f"Verifying {tls_label} is rejected on {endpoint_name} ({host}:{port})")
        output = self.run_openssl_connection(host, port, tls_flag, is_ipv6)
        validate_equals(
            self.is_tls_handshake_rejected(output),
            True,
            f"{tls_label} rejected on {endpoint_name} ({host}:{port})",
        )

    def verify_tls_accepted(self, host: str, port: int, tls_flag: str, endpoint_name: str, is_ipv6: bool = False) -> None:
        """Verify that a TLS connection with the given version flag is accepted.

        Args:
            host (str): Target host.
            port (int): Target port.
            tls_flag (str): TLS version flag (e.g., '-tls1_2').
            endpoint_name (str): Endpoint display name for logging.
            is_ipv6 (bool): Whether the host is IPv6.
        """
        tls_label = TLS_VERSIONS.get(tls_flag, tls_flag)
        get_logger().log_info(f"Verifying {tls_label} is accepted on {endpoint_name} ({host}:{port})")
        output = self.run_openssl_connection(host, port, tls_flag, is_ipv6)
        validate_equals(
            self.is_tls_handshake_rejected(output),
            False,
            f"{tls_label} accepted on {endpoint_name} ({host}:{port})",
        )

    def get_haproxy_bind_options(self) -> str:
        """Retrieve ssl-default-bind-options from haproxy.cfg.

        Returns:
            str: Lowercased ssl-default-bind-options line content.
        """
        output = self.ssh_connection.send_as_sudo("grep 'ssl-default-bind-options' /etc/haproxy/haproxy.cfg 2>&1")
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"HAProxy ssl-default-bind-options: {output}")
        return output.lower() if isinstance(output, str) else str(output).lower()

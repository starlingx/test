import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.objects.ipsec_certificate_output import IPSecCertificateOutput
from keywords.cloud_platform.security.objects.ipsec_dnsmasq_output import IPSecDnsmasqOutput
from keywords.cloud_platform.security.objects.ipsec_security_association_output import IPSecSecurityAssociationOutput
from keywords.cloud_platform.system.host.system_host_addr_keywords import SystemHostAddrKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManager
from keywords.files.file_keywords import FileKeywords
from keywords.linux.systemctl.systemctl_keywords import SystemCTLKeywords


class IPSecKeywords(BaseKeyword):
    """Keywords for IPSec operations and validations.

    This class provides methods for managing IPSec certificates,
    security associations, and service status validation.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize IPSec keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        # Initialize reusable keyword classes
        self.file_keywords = FileKeywords(ssh_connection)
        self.system_show = SystemShowKeywords(ssh_connection)
        self.system_host_list = SystemHostListKeywords(ssh_connection)
        self.system_host_addr = SystemHostAddrKeywords(ssh_connection)
        self.systemctl_keywords = SystemCTLKeywords(ssh_connection)

    def get_management_ips(self, mgmt_if_name: str = "mgmt0") -> set:
        """Get the set of per-host management-network IP addresses.

        Collects the address of the management interface for every host. Note that
        this returns the per-host unit addresses only; the management floating
        address is not enumerated per host, so local SA endpoints are validated by
        subnet membership (see get_management_subnet) rather than against this set.

        Args:
            mgmt_if_name (str): Management interface name to collect addresses for.

        Returns:
            set: Set of per-host management IP addresses.
        """
        mgmt_ips = set()
        for host in self.system_host_list.get_system_host_list().get_hosts():
            addr_output = self.system_host_addr.get_system_host_addr_list(host.get_host_name())
            for addr in addr_output.get_system_host_addr():
                if addr.get_if_name() == mgmt_if_name and addr.get_address():
                    mgmt_ips.add(addr.get_address())
        return mgmt_ips

    def get_management_subnet(self, mgmt_if_name: str = "mgmt0") -> str:
        """Get the management network subnet in CIDR notation.

        Derives the subnet from the management interface address and prefix of the
        active controller, so SA endpoint IPs (including the floating address) can
        be validated by subnet membership.

        Args:
            mgmt_if_name (str): Management interface name to derive the subnet from.

        Returns:
            str: Management subnet in CIDR notation (for example, a '/64' IPv6 or
                '/24' IPv4 network), or an empty string if no management address is found.
        """
        active_controller = self.system_host_list.get_active_controller()
        addr_output = self.system_host_addr.get_system_host_addr_list(active_controller.get_host_name())
        for addr in addr_output.get_system_host_addr():
            if addr.get_if_name() == mgmt_if_name and addr.get_address():
                return f"{addr.get_address()}/{addr.get_prefix()}"
        return ""

    def get_dnsmasq_hosts(self) -> IPSecDnsmasqOutput:
        """Get dnsmasq.hosts file content.

        Returns:
            IPSecDnsmasqOutput: Parsed dnsmasq.hosts content.
        """
        system_show_object = self.system_show.system_show().get_system_show_object()
        software_version = system_show_object.get_software_version()
        dnsmasq_path = f"/opt/platform/config/{software_version}/dnsmasq.hosts"
        output = self.ssh_connection.send(f"cat {dnsmasq_path}")
        self.validate_success_return_code(self.ssh_connection)
        return IPSecDnsmasqOutput(output)

    def get_security_associations(self, stable_count: int = 3, interval: int = 2, timeout: int = 60) -> IPSecSecurityAssociationOutput:
        """Get IPSec security associations, waiting until the count stabilizes.

        Polls until the association count is identical across consecutive polls
        to ensure the full output buffer has been captured.

        Args:
            stable_count (int): Number of consecutive identical counts required before returning.
            interval (int): Seconds to wait between polls.
            timeout (int): Maximum seconds to wait before raising an exception.

        Returns:
            IPSecSecurityAssociationOutput: Parsed security associations.

        Raises:
            KeywordException: If the count does not stabilize within the timeout.
        """
        consecutive = 0
        last_count = -1
        last_output = None
        timeout_time = time.time() + timeout

        while time.time() < timeout_time:
            output = self.ssh_connection.send_as_sudo("swanctl --list-sa")
            self.validate_success_return_code(self.ssh_connection)
            parsed = IPSecSecurityAssociationOutput(output)
            current_count = len(parsed.get_associations())

            if current_count == last_count:
                consecutive += 1
            else:
                consecutive = 1
                last_count = current_count
                last_output = output

            if consecutive >= stable_count:
                return IPSecSecurityAssociationOutput(last_output)

            time.sleep(interval)

        raise KeywordException(f"Security associations did not stabilize within {timeout} seconds")

    def get_expected_security_association_count(self) -> int:
        """Compute the expected number of IPsec security associations for the lab.

        Each host forms two security associations per remote host (one per
        direction), so the expected total is (number_of_hosts - 1) * 2.

        Returns:
            int: Expected security-association count for the current topology.
        """
        hosts = self.system_host_list.get_system_host_list().get_hosts()
        return (len(hosts) - 1) * 2

    def are_all_security_associations_established(self, expected_count: int) -> bool:
        """Check whether all expected IPsec security associations are established.

        Intended for use with retry-based validation after lifecycle operations
        (swact, reboot, lock/unlock) that temporarily disrupt the SAs.

        Args:
            expected_count (int): Expected number of security associations.

        Returns:
            bool: True if the association count matches expected_count and every
                association is established, False otherwise.
        """
        associations = self.get_security_associations().get_associations()
        if len(associations) != expected_count:
            return False
        return all(association.is_established() for association in associations)

    def get_certificate_serial(self, cert_path: str) -> str:
        """Get the serial number of a certificate.

        Args:
            cert_path (str): Path to the certificate file.

        Returns:
            str: Certificate serial number (the value after 'serial=').
        """
        cmd = f"openssl x509 -in {cert_path} -noout -serial"
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        lines = output if isinstance(output, list) else [output]
        for line in lines:
            if "serial=" in line:
                return line.split("serial=", 1)[1].strip()
        return ""

    def renew_ipsec_certificate(self, pxe_controller: str = "pxecontroller") -> str:
        """Renew the IPsec certificate on the host using the IPsec client.

        Runs the IPsec client certificate-renewal operation (op code 2), which
        requests a new leaf certificate from the IPsec server and reloads the
        StrongSwan credentials and connections so the new certificate is used on
        the next re-authentication.

        Args:
            pxe_controller (str): PXE controller hostname the IPsec client contacts.

        Returns:
            str: Raw command output from the IPsec client renewal operation.
        """
        get_logger().log_info("Running IPsec certificate renewal (op code 2)")
        output = self.ssh_connection.send_as_sudo(f"ipsec-client {pxe_controller} -o 2")
        self.validate_success_return_code(self.ssh_connection)
        return output

    def get_certificate_info_by_type(self, cert_type: str) -> IPSecCertificateOutput:
        """Get certificate information by certificate type with automatic path resolution.

        Args:
            cert_type (str): Certificate type (root_ca, ica_l1, ica).

        Returns:
            IPSecCertificateOutput: Certificate output with requested information.
        """
        valid_types = ["root_ca", "ica_l1", "ica"]
        if cert_type not in valid_types:
            raise KeywordException(f"Invalid cert_type '{cert_type}'. Valid types: {valid_types}")

        cert_path = None
        if cert_type == "ica_l1":
            cert_path = "x509ca/system-local-ca-1_l1.crt"
        elif cert_type == "ica":
            cert_path = "x509ca/system-local-ca-1.crt"
        elif cert_type == "root_ca":
            cert_path = "x509ca/system-root-ca-1.crt"

        full_primary_path = f"/etc/swanctl/{cert_path}"

        # Use FileKeywords to check if file exists
        if not self.file_keywords.validate_file_exists_with_sudo(full_primary_path):
            cert_path = "x509ca/system-root-ca-1.crt"  # Fallback to root_ca
            full_primary_path = f"/etc/swanctl/{cert_path}"

        return self.get_certificate_info_subject_issuer(full_primary_path)

    def get_certificate_info_subject_issuer(self, cert_path: str) -> IPSecCertificateOutput:
        """Get certificate subject and issuer information.

        Args:
            cert_path (str): Path to the certificate file.

        Returns:
            IPSecCertificateOutput: Certificate output with subject/issuer information.
        """
        cmd = f"openssl x509 -in {cert_path} -noout -subject -issuer"
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return IPSecCertificateOutput(output, "subject_issuer", "active_controller", cert_path)

    def is_ipsec_leaf_issued_by_local_ca(self, hostname: str) -> bool:
        """Check that a host's IPSec leaf is issued by the local signing CA.

        Compares the IPSec leaf certificate issuer to the subject of the local
        CA (system-local-ca-1). This is chain-agnostic and avoids building an
        openssl verify chain, which varies between the self-signed and full CA
        hierarchy scenarios.

        Args:
            hostname (str): Host whose IPSec leaf certificate is checked.

        Returns:
            bool: True if the leaf issuer matches the local CA subject.
        """
        leaf_cert = self.get_certificate_info_subject_issuer(self.get_ipsec_certificate_path(hostname)).get_certificate()
        local_ca_cert = self.get_certificate_info_subject_issuer("/etc/swanctl/x509ca/system-local-ca-1.crt").get_certificate()
        return leaf_cert.matches_issuer(local_ca_cert.get_subject())

    def get_certificate_info_cert_md5(self, cert_path: str) -> IPSecCertificateOutput:
        """Get the MD5 of the certificate's public key.

        Hashes the DER-encoded public key extracted from the certificate so the
        comparison is key-type agnostic (works for RSA and ECDSA certificates).

        Args:
            cert_path (str): Path to the certificate file.

        Returns:
            IPSecCertificateOutput: Certificate output with the public-key MD5 hash.
        """
        cmd = f"openssl x509 -in {cert_path} -pubkey -noout | openssl pkey -pubin -outform DER | openssl md5"
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return IPSecCertificateOutput(output, "cert_md5", "active_controller", cert_path)

    def get_certificate_info_key_md5(self, cert_path: str) -> IPSecCertificateOutput:
        """Get the MD5 of the private key's public component.

        Derives the public key from the private key and hashes its DER encoding so
        the comparison is key-type agnostic (works for RSA and ECDSA keys). This
        matches the public-key MD5 produced by get_certificate_info_cert_md5 when
        the key and certificate correspond.

        Args:
            cert_path (str): Path to the certificate key file.

        Returns:
            IPSecCertificateOutput: Certificate output with the public-key MD5 hash.
        """
        cmd = f"openssl pkey -in {cert_path} -pubout -outform DER | openssl md5"
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return IPSecCertificateOutput(output, "key_md5", "active_controller", cert_path)

    def get_ipsec_service_name(self) -> str:
        """Get the correct IPSec service name based on OS version.

        In Trixie (strongSwan 6.0), ipsec.service was replaced by strongswan.service.
        In Bullseye (strongSwan 5.9), the service is named ipsec.

        Returns:
            str: Service name ('strongswan' for Trixie, 'ipsec' for Bullseye).
        """
        return "strongswan" if CloudPlatformVersionManager.is_trixie(self.ssh_connection) else "ipsec"

    def validate_service_name_is_valid(self, service_name: str) -> bool:
        """Check if the IPSec service name is valid.

        Args:
            service_name (str): Service name to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        return service_name in ["ipsec-server", "ipsec", "strongswan"]

    def restart_ipsec_service(self) -> None:
        """Restart the IPSec (StrongSwan/charon) service on the host.

        Restarts the OS-appropriate IPSec service so the charon daemon is
        bounced; security associations renegotiate automatically afterwards.
        """
        service_name = self.get_ipsec_service_name()
        get_logger().log_info(f"Restarting IPSec service '{service_name}'")
        self.systemctl_keywords.systemctl_restart(service_name)
        self.validate_success_return_code(self.ssh_connection)

    def is_luks_ipsec_keys_dir_present(self) -> bool:
        """Check whether the LUKS-backed IPSec keys directory is present.

        The IPSec private keys are stored on the LUKS-encrypted vault and
        symlinked into /etc/swanctl/private. If the LUKS vault is not mounted,
        this directory is absent and the IPSec service cannot read its keys.

        Returns:
            bool: True if the LUKS IPSec keys directory exists, False otherwise.
        """
        return self.file_keywords.validate_file_exists_with_sudo("/var/luks/stx/luks_fs/ipsec/keys")

    def get_ipsec_certificate_path(self, hostname: str) -> str:
        """Get full IPSec certificate path for hostname.

        Args:
            hostname (str): Hostname for certificate.

        Returns:
            str: Full certificate path.
        """
        return f"/etc/swanctl/x509/system-ipsec-certificate-{hostname}.crt"

    def get_ipsec_key_path(self, hostname: str) -> str:
        """Get full IPSec key path for hostname.

        Args:
            hostname (str): Hostname for key.

        Returns:
            str: Full key path.
        """
        return f"/etc/swanctl/private/system-ipsec-certificate-{hostname}.key"

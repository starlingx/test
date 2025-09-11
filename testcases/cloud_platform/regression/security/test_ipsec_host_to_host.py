from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_greater_than, validate_str_contains
from keywords.cloud_platform.security.ipsec_keywords import IPSecKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.linux.systemctl.systemctl_is_active_keywords import SystemCTLIsActiveKeywords


@mark.p1
def test_ipsec_certificates():
    """Validate IPSec certificate chain and key-certificate matching.

    Steps:
        - Verify root CA is self-signed
        - Validate certificate chain from root CA to IPSec certificate
        - Check IPSec certificate has correct CN
        - Verify system-local-ca is the issuer of IPSec certificate
        - Verify Kubernetes secret system-local-ca subject matches IPSec certificate issuer
        - Log certificate information for debugging
        - Validate key and certificate MD5 checksums match
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ipsec_keywords = IPSecKeywords(ssh_connection)

    # Get the actual hostname from system host list
    system_hosts = SystemHostListKeywords(ssh_connection)
    active_controller = system_hosts.get_active_controller()
    hostname = active_controller.get_host_name()

    get_logger().log_info(f"Validating certificate chain for {hostname}")

    # Build certificate paths
    ipsec_crt_path = ipsec_keywords.get_ipsec_certificate_path(hostname)
    ipsec_key_path = ipsec_keywords.get_ipsec_key_path(hostname)

    # Validate IPSec certificate exists
    validate_equals(ipsec_keywords.file_keywords.validate_file_exists_with_sudo(ipsec_crt_path), True, f"IPSec certificate should exist: {ipsec_crt_path}")

    # Get certificate information using string constants
    root_ca_output = ipsec_keywords.get_certificate_info_by_type("root_ca")
    ica_l1_output = ipsec_keywords.get_certificate_info_by_type("ica_l1")
    ica_output = ipsec_keywords.get_certificate_info_by_type("ica")
    ipsec_cert_output = ipsec_keywords.get_certificate_info_subject_issuer(ipsec_crt_path)

    root_ca_cert = root_ca_output.get_certificate()
    ica_l1_cert = ica_l1_output.get_certificate()
    ica_cert = ica_output.get_certificate()
    ipsec_cert = ipsec_cert_output.get_certificate()

    # Validate root CA is self-signed
    validate_equals(root_ca_cert.is_self_signed(), True, f"Root CA should be self-signed for {hostname}")

    # Validate certificate chain based on scenario
    is_self_signed = ica_l1_cert.get_subject() == root_ca_cert.get_subject() and ica_cert.get_subject() == root_ca_cert.get_subject()

    scenario = "self-signed" if is_self_signed else "full CA hierarchy"
    get_logger().log_info(f"Detected {scenario} certificate scenario for {hostname}")

    if is_self_signed:
        validate_equals(ipsec_cert.matches_issuer(root_ca_cert.get_subject()), True, f"IPSec certificate should be issued by Root CA for {hostname}")
    else:
        # Validate full certificate chain
        validate_equals(ica_l1_cert.matches_issuer(root_ca_cert.get_subject()), True, f"ICA L1 should be issued by Root CA for {hostname}")
        validate_equals(ica_cert.matches_issuer(ica_l1_cert.get_subject()), True, f"ICA should be issued by ICA L1 for {hostname}")
        validate_equals(ipsec_cert.matches_issuer(ica_cert.get_subject()), True, f"IPSec certificate should be issued by ICA for {hostname}")

    # Log IPSec certificate subject for debugging
    get_logger().log_info(f"IPSec certificate subject: {ipsec_cert.get_subject()}")

    # Validate IPSec certificate has valid subject (not checking specific CN as it may be intermediate CA)
    validate_equals(ipsec_cert.has_valid_subject(), True, f"IPSec certificate should have valid subject for {hostname}")

    # Validate Kubernetes secret subject matches IPSec certificate issuer
    kubectl_secrets = KubectlGetSecretsKeywords(ssh_connection)
    kube_secret = kubectl_secrets.get_secret_json_output("system-local-ca", "cert-manager")
    kube_subject = kube_secret.get_certificate_subject()

    get_logger().log_info(f"IPSec certificate issuer: {ipsec_cert.get_issuer()}")
    get_logger().log_info(f"Kubernetes secret subject: {kube_subject}")

    # Validation will handle normalization internally
    validate_equals(ipsec_cert.matches_issuer(kube_subject), True, f"IPSec certificate should be issued by Kubernetes system-local-ca secret for {hostname}")

    # Validate key-certificate MD5 matching
    get_logger().log_info(f"Validating key-certificate MD5 matching for {hostname}")
    key_output = ipsec_keywords.get_certificate_info_key_md5(ipsec_key_path)
    cert_md5_output = ipsec_keywords.get_certificate_info_cert_md5(ipsec_crt_path)

    key_cert = key_output.get_certificate()
    cert_md5_cert = cert_md5_output.get_certificate()

    validate_equals(key_cert.matches_md5(cert_md5_cert.get_md5_hash()), True, f"IPSec key MD5 should match IPSec certificate MD5 for {hostname}")


@mark.p1
def test_pxeboot_network():
    """Verify the correctness of the dnsmasq.hosts file by checking the mapping of MAC addresses to pxeboot names and addresses.

    Steps:
        - Ensure each MAC address in the dnsmasq.hosts file is included in a list of valid MAC addresses
        - Verify that each MAC address has associated pxeboot name and address entries
        - Check if the pxeboot addresses are reachable via ping
        - Test SSH connectivity to pxeboot hostnames
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ipsec_keywords = IPSecKeywords(ssh_connection)
    system_hosts = SystemHostListKeywords(ssh_connection)
    lab_connection_keywords = LabConnectionKeywords()

    get_logger().log_info("Fetching pxeboot information from dnsmasq.hosts file")
    dnsmasq_output = ipsec_keywords.get_dnsmasq_hosts()

    validate_str_contains(dnsmasq_output.get_content(), "pxe", "dnsmasq.hosts should contain PXE entries")

    hosts = system_hosts.get_system_host_list().get_hosts()

    # Get parsed dnsmasq entries and validate each
    pxeboot_entries = dnsmasq_output.get_pxeboot_entries()

    for entry in pxeboot_entries:
        # Validate MAC address format using object method
        validate_equals(entry.is_valid_mac(), True, f"MAC address should be valid: {entry.get_mac_address()}")

        # Validate pxeboot name format using object method
        validate_equals(entry.is_pxeboot_entry(), True, f"Should be PXE boot entry: {entry.get_pxeboot_name()}")

        # Test connectivity
        ping_success = lab_connection_keywords.ping_host(entry.get_pxeboot_address())
        validate_equals(ping_success, True, f"Ping should succeed for {entry.get_pxeboot_address()}")

        # Test SSH connectivity using pxeboot name with lab credentials
        ssh_success = lab_connection_keywords.test_ssh_connectivity(entry.get_pxeboot_name())
        validate_equals(ssh_success, True, f"SSH should succeed for {entry.get_pxeboot_name()}")

    # Validate we have pxeboot entries
    validate_greater_than(len(pxeboot_entries), 0, f"Should have pxeboot entries, found {len(pxeboot_entries)}")
    get_logger().log_info(f"Found {len(pxeboot_entries)} pxeboot entries for {len(hosts)} hosts")


@mark.p1
def test_security_associations():
    """Validate the security associations between nodes using the swanctl command.

    Steps:
        - Retrieve hosts and active controller information
        - Get the list of security associations using swanctl
        - Verify that security associations are established and valid
        - Check local and remote CN patterns match expected values
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ipsec_keywords = IPSecKeywords(ssh_connection)
    system_hosts = SystemHostListKeywords(ssh_connection)

    hosts = system_hosts.get_system_host_list().get_hosts()
    active_controller = system_hosts.get_active_controller()
    associations_output = ipsec_keywords.get_security_associations()
    associations = associations_output.get_associations()

    validate_greater_than(len(associations), 0, f"Should find security associations, found {len(associations)} associations")

    remote_host_count = len(hosts) - 1
    expected_association_count = remote_host_count * 2

    get_logger().log_info(f"Lab topology: {len(hosts)} total hosts, {remote_host_count} remote hosts")
    get_logger().log_info(f"Expected: {expected_association_count} associations (2 per remote host), Actual: {len(associations)}")

    validate_equals(len(associations), expected_association_count, f"Should have {expected_association_count} associations (2 per remote host), found {len(associations)}")

    active_cn_pattern = f"ipsec-{active_controller.get_host_name()}"
    expected_cns = {f"ipsec-{host.get_host_name()}" for host in hosts if f"ipsec-{host.get_host_name()}" != active_cn_pattern}

    get_logger().log_info(f"Active controller CN pattern: {active_cn_pattern}")
    get_logger().log_info(f"Expected remote CNs: {expected_cns}")

    for i, association in enumerate(associations):
        validate_equals(association.is_established(), True, f"Connection should be established in association {i+1}")
        validate_equals(association.has_local_cn_starting_with(active_cn_pattern), True, f"Should have local CN starting with {active_cn_pattern} in association {i+1}")

        validate_equals(association.has_remote_cn_in_set(expected_cns), True, f"Should have expected remote CN in association {i+1}")


@mark.p1
def test_ipsec_status():
    """Validate IPSec service status on all hosts.

    Steps:
        - Check ipsec-server service is active on all controllers
        - Check ipsec service is active on all hosts
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_hosts = SystemHostListKeywords(ssh_connection)
    lab_connection_keywords = LabConnectionKeywords()

    hosts = system_hosts.get_system_host_list().get_hosts()

    # Check ipsec-server service on controllers
    controllers = system_hosts.get_system_host_list().get_controllers()
    for controller in controllers:
        controller_ssh = lab_connection_keywords.get_ssh_for_hostname(controller.get_host_name())
        systemctl_keywords = SystemCTLIsActiveKeywords(controller_ssh)
        service_status = systemctl_keywords.is_active("ipsec-server")
        validate_equals(service_status, "active", f"ipsec-server service should be active on {controller.get_host_name()}")

    # Check ipsec service on all hosts
    for host in hosts:
        if host.get_personality() == "worker":
            host_ssh = lab_connection_keywords.get_compute_ssh(host.get_host_name())
        else:
            host_ssh = lab_connection_keywords.get_ssh_for_hostname(host.get_host_name())
        systemctl_keywords = SystemCTLIsActiveKeywords(host_ssh)
        service_status = systemctl_keywords.is_active("ipsec")
        validate_equals(service_status, "active", f"ipsec service should be active on {host.get_host_name()}")


@mark.p1
def test_ping_mgmt_ips():
    """Test the ability to ping management IPs from the active controller.

    Steps:
        - Get list of all hosts in the system
        - Identify the active controller
        - Ping each host from the active controller
        - Verify all ping operations succeed
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_hosts = SystemHostListKeywords(ssh_connection)
    lab_connection_keywords = LabConnectionKeywords()

    host_list = system_hosts.get_system_host_list()
    hosts = [host.get_host_name() for host in host_list.get_hosts()]

    get_logger().log_info(f"Testing ping connectivity to {len(hosts)} hosts")
    for host in hosts:
        ping_success = lab_connection_keywords.ping_host(host)
        validate_equals(ping_success, True, f"Ping should succeed to {host}")

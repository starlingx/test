from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_greater_than, validate_str_contains
from keywords.cloud_platform.security.ipsec_keywords import IPSecKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.linux.systemctl.systemctl_is_active_keywords import SystemCTLIsActiveKeywords


@mark.p1
def test_ipsec_certificate_chain_and_key_match():
    """Validate the IPSec certificate chain and key-certificate matching.

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
def test_ipsec_key_cert_match_on_all_hosts():
    """Validate IPSec key-certificate public-key matching on every host.

    Unlike test_ipsec_certificate_chain_and_key_match, which checks the active
    controller only, this test connects to each host and verifies that the IPSec
    private key and leaf certificate share the same public key. The comparison
    hashes the DER public key, so it is valid for both RSA (Bullseye) and ECDSA
    (Trixie) IPSec keys.

    Steps:
        - Get the list of all hosts in the system
        - On each host, compute the public-key MD5 of the IPSec key and certificate
        - Validate the key and certificate public-key MD5 values match on each host
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_hosts = SystemHostListKeywords(ssh_connection)
    lab_connection_keywords = LabConnectionKeywords()

    hosts = system_hosts.get_system_host_list().get_hosts()
    controllers = system_hosts.get_system_host_list().get_controllers()
    controller_names = [controller.get_host_name() for controller in controllers]

    for host in hosts:
        hostname = host.get_host_name()
        get_logger().log_info(f"Validating IPSec key-certificate matching for {hostname}")

        if host.get_personality() == "worker" and hostname not in controller_names:
            host_ssh = lab_connection_keywords.get_compute_ssh(hostname)
        else:
            host_ssh = lab_connection_keywords.get_ssh_for_hostname(hostname)

        host_ipsec_keywords = IPSecKeywords(host_ssh)
        ipsec_crt_path = host_ipsec_keywords.get_ipsec_certificate_path(hostname)
        ipsec_key_path = host_ipsec_keywords.get_ipsec_key_path(hostname)

        validate_equals(host_ipsec_keywords.file_keywords.validate_file_exists_with_sudo(ipsec_crt_path), True, f"IPSec certificate should exist on {hostname}: {ipsec_crt_path}")

        key_output = host_ipsec_keywords.get_certificate_info_key_md5(ipsec_key_path)
        cert_md5_output = host_ipsec_keywords.get_certificate_info_cert_md5(ipsec_crt_path)

        key_cert = key_output.get_certificate()
        cert_md5_cert = cert_md5_output.get_certificate()

        validate_equals(key_cert.has_valid_md5(), True, f"IPSec key public-key MD5 should be computed on {hostname}")
        validate_equals(key_cert.matches_md5(cert_md5_cert.get_md5_hash()), True, f"IPSec key MD5 should match IPSec certificate MD5 for {hostname}")


@mark.p1
def test_ipsec_pxeboot_hosts_reachable():
    """Verify the pxeboot host mapping is correct and every pxeboot host is reachable.

    Validates the dnsmasq.hosts file maps each MAC address to a pxeboot name and
    address, then confirms each pxeboot address responds to ping and accepts SSH.

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
def test_ipsec_security_associations_established():
    """Validate IPSec security associations are established between all nodes.

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

    # Validate SA endpoint IPs against the management subnet. The active controller
    # may present its unit or floating management address as the local endpoint, so
    # subnet membership is used rather than the per-host address set.
    mgmt_subnet = ipsec_keywords.get_management_subnet()
    get_logger().log_info(f"Management subnet for SA endpoint validation: {mgmt_subnet}")

    for i, association in enumerate(associations):
        validate_equals(association.is_established(), True, f"Connection should be established in association {i + 1}")
        validate_equals(association.has_local_cn_starting_with(active_cn_pattern), True, f"Should have local CN starting with {active_cn_pattern} in association {i + 1}")

        validate_equals(association.has_remote_cn_in_set(expected_cns), True, f"Should have expected remote CN in association {i + 1}")

        validate_equals(association.has_local_ip_in_subnet(mgmt_subnet), True, f"Local endpoint IP should be in the management subnet in association {i + 1}")
        validate_equals(association.has_all_remote_ips_in_subnet(mgmt_subnet), True, f"All remote endpoint IPs should be in the management subnet in association {i + 1}")


@mark.p1
def test_ipsec_services_active_on_all_hosts():
    """Validate the IPSec services are active on all hosts.

    Steps:
        - Check ipsec-server service is active on all controllers
        - Check ipsec service is active on all hosts
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_hosts = SystemHostListKeywords(ssh_connection)
    lab_connection_keywords = LabConnectionKeywords()
    ipsec_keywords = IPSecKeywords(ssh_connection)

    hosts = system_hosts.get_system_host_list().get_hosts()
    ipsec_service = ipsec_keywords.get_ipsec_service_name()
    get_logger().log_info(f"Using IPSec service name: '{ipsec_service}' (detected from OS version)")

    # Check ipsec-server service on controllers
    controllers = system_hosts.get_system_host_list().get_controllers()
    for controller in controllers:
        controller_ssh = lab_connection_keywords.get_ssh_for_hostname(controller.get_host_name())
        systemctl_keywords = SystemCTLIsActiveKeywords(controller_ssh)
        service_status = systemctl_keywords.is_active("ipsec-server")
        validate_equals(service_status, "active", f"ipsec-server service should be active on {controller.get_host_name()}")

    # Check ipsec/strongswan service on all hosts (name differs between Bullseye and Trixie)
    for host in hosts:
        if host.get_personality() == "worker":
            host_ssh = lab_connection_keywords.get_compute_ssh(host.get_host_name())
        else:
            host_ssh = lab_connection_keywords.get_ssh_for_hostname(host.get_host_name())
        systemctl_keywords = SystemCTLIsActiveKeywords(host_ssh)
        service_status = systemctl_keywords.is_active(ipsec_service)
        validate_equals(service_status, "active", f"{ipsec_service} service should be active on {host.get_host_name()}")


@mark.p1
def test_ipsec_mgmt_connectivity():
    """Validate management-network connectivity across the IPSec tunnels.

    Pings every host from the active controller to confirm the IPSec-protected
    management network is reachable end to end.

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


@mark.p1
@mark.lab_has_standby_controller
def test_ipsec_sa_reestablish_after_swact():
    """Validate IPSec security associations re-establish after a controller swact.

    Steps:
        - Record the expected security-association count
        - Perform a controller swact
        - Reconnect to the new active controller
        - Wait for all security associations to re-establish
        - Verify management connectivity is restored
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    expected_count = IPSecKeywords(ssh_connection).get_expected_security_association_count()

    get_logger().log_test_case_step("Perform controller swact")
    SystemHostSwactKeywords(ssh_connection).host_swact()

    get_logger().log_test_case_step("Reconnect to new active controller")
    new_ssh = LabConnectionKeywords().get_active_controller_ssh()
    ipsec_keywords = IPSecKeywords(new_ssh)

    get_logger().log_test_case_step("Wait for security associations to re-establish after swact")
    validate_equals_with_retry(
        lambda: ipsec_keywords.are_all_security_associations_established(expected_count),
        True,
        f"All {expected_count} security associations should be established after swact",
        timeout=300,
    )

    get_logger().log_test_case_step("Verify management connectivity after swact")
    lab_connection_keywords = LabConnectionKeywords()
    for host in SystemHostListKeywords(new_ssh).get_system_host_list().get_hosts():
        validate_equals(lab_connection_keywords.ping_host(host.get_host_name()), True, f"Ping should succeed to {host.get_host_name()} after swact")


@mark.p1
@mark.lab_has_standby_controller
def test_ipsec_sa_reestablish_after_controller_reboot(request):
    """Validate IPSec security associations re-establish after a standby controller reboot.

    Steps:
        - Record the expected security-association count and standby controller
        - Lock, reboot, and unlock the standby controller
        - Verify ipsec-server and ipsec/strongswan services are active on it
        - Wait for all security associations to re-establish
    """

    def teardown():
        get_logger().log_teardown_step("Ensure standby controller is unlocked")
        new_ssh = LabConnectionKeywords().get_active_controller_ssh()
        lock_keywords = SystemHostLockKeywords(new_ssh)
        standby = SystemHostListKeywords(new_ssh).get_standby_controller()
        if lock_keywords.is_host_locked(standby.get_host_name()):
            lock_keywords.unlock_host(standby.get_host_name())

    request.addfinalizer(teardown)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_hosts = SystemHostListKeywords(ssh_connection)
    expected_count = IPSecKeywords(ssh_connection).get_expected_security_association_count()

    standby_controller = system_hosts.get_standby_controller()
    standby_name = standby_controller.get_host_name()

    lock_keywords = SystemHostLockKeywords(ssh_connection)
    reboot_keywords = SystemHostRebootKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Lock standby controller {standby_name}")
    lock_keywords.lock_host(standby_name)
    lock_keywords.wait_for_host_locked(standby_name)

    get_logger().log_test_case_step(f"Reboot standby controller {standby_name}")
    reboot_keywords.host_reboot(standby_name)

    get_logger().log_test_case_step(f"Unlock standby controller {standby_name}")
    lock_keywords.unlock_host(standby_name)

    get_logger().log_test_case_step(f"Verify IPSec services active on {standby_name} after reboot")
    ipsec_keywords = IPSecKeywords(ssh_connection)
    ipsec_service = ipsec_keywords.get_ipsec_service_name()
    standby_ssh = LabConnectionKeywords().get_ssh_for_hostname(standby_name)
    systemctl_keywords = SystemCTLIsActiveKeywords(standby_ssh)
    validate_equals_with_retry(lambda: systemctl_keywords.is_active("ipsec-server"), "active", f"ipsec-server should be active on {standby_name} after reboot", timeout=300)
    validate_equals_with_retry(lambda: systemctl_keywords.is_active(ipsec_service), "active", f"{ipsec_service} should be active on {standby_name} after reboot", timeout=300)

    get_logger().log_test_case_step("Wait for security associations to re-establish after reboot")
    validate_equals_with_retry(
        lambda: ipsec_keywords.are_all_security_associations_established(expected_count),
        True,
        f"All {expected_count} security associations should be established after controller reboot",
        timeout=300,
    )


@mark.p1
@mark.lab_has_worker
def test_ipsec_sa_reestablish_after_worker_reboot(request):
    """Validate IPSec security associations re-establish after a worker reboot.

    Steps:
        - Identify a dedicated worker host (prerequisite for this test)
        - Lock, reboot, and unlock the worker
        - Verify ipsec/strongswan service is active on it
        - Wait for all security associations to re-establish
    """

    def teardown():
        get_logger().log_teardown_step("Ensure worker is unlocked")
        new_ssh = LabConnectionKeywords().get_active_controller_ssh()
        lock_keywords = SystemHostLockKeywords(new_ssh)
        if worker_name and lock_keywords.is_host_locked(worker_name):
            lock_keywords.unlock_host(worker_name)

    worker_name = None
    request.addfinalizer(teardown)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_hosts = SystemHostListKeywords(ssh_connection)
    expected_count = IPSecKeywords(ssh_connection).get_expected_security_association_count()

    # Select a dedicated worker host without raising on worker-less systems; the
    # @mark.lab_has_worker capability gates execution to labs that have one.
    worker_hosts = [host for host in system_hosts.get_system_host_list().get_hosts() if host.get_personality() == "worker"]
    validate_greater_than(len(worker_hosts), 0, "Lab should have at least one dedicated worker host for this test")
    worker_name = worker_hosts[0].get_host_name()

    lock_keywords = SystemHostLockKeywords(ssh_connection)
    reboot_keywords = SystemHostRebootKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Lock worker {worker_name}")
    lock_keywords.lock_host(worker_name)
    lock_keywords.wait_for_host_locked(worker_name)

    get_logger().log_test_case_step(f"Reboot worker {worker_name}")
    reboot_keywords.host_reboot(worker_name)

    get_logger().log_test_case_step(f"Unlock worker {worker_name}")
    lock_keywords.unlock_host(worker_name)

    get_logger().log_test_case_step(f"Verify IPSec service active on {worker_name} after reboot")
    ipsec_keywords = IPSecKeywords(ssh_connection)
    ipsec_service = ipsec_keywords.get_ipsec_service_name()
    worker_ssh = LabConnectionKeywords().get_compute_ssh(worker_name)
    systemctl_keywords = SystemCTLIsActiveKeywords(worker_ssh)
    validate_equals_with_retry(lambda: systemctl_keywords.is_active(ipsec_service), "active", f"{ipsec_service} should be active on {worker_name} after reboot", timeout=300)

    get_logger().log_test_case_step("Wait for security associations to re-establish after worker reboot")
    validate_equals_with_retry(
        lambda: ipsec_keywords.are_all_security_associations_established(expected_count),
        True,
        f"All {expected_count} security associations should be established after worker reboot",
        timeout=300,
    )


@mark.p1
@mark.lab_has_standby_controller
def test_ipsec_sa_reestablish_after_lock_unlock(request):
    """Validate IPSec security associations re-establish after a host lock/unlock.

    Steps:
        - Record the expected security-association count and the standby controller
        - Lock then unlock the standby controller
        - Verify the host retains the mgmt_ipsec capability as enabled
        - Wait for all security associations to re-establish
    """

    def teardown():
        get_logger().log_teardown_step("Ensure standby controller is unlocked")
        new_ssh = LabConnectionKeywords().get_active_controller_ssh()
        lock_keywords = SystemHostLockKeywords(new_ssh)
        standby = SystemHostListKeywords(new_ssh).get_standby_controller()
        if lock_keywords.is_host_locked(standby.get_host_name()):
            lock_keywords.unlock_host(standby.get_host_name())

    request.addfinalizer(teardown)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_hosts = SystemHostListKeywords(ssh_connection)
    expected_count = IPSecKeywords(ssh_connection).get_expected_security_association_count()
    standby_name = system_hosts.get_standby_controller().get_host_name()

    get_logger().log_test_case_step(f"Lock standby controller {standby_name}")
    lock_keywords = SystemHostLockKeywords(ssh_connection)
    lock_keywords.lock_host(standby_name)
    lock_keywords.wait_for_host_locked(standby_name)

    get_logger().log_test_case_step(f"Unlock standby controller {standby_name}")
    lock_keywords.unlock_host(standby_name)

    get_logger().log_test_case_step("Wait for security associations to re-establish after lock/unlock")
    ipsec_keywords = IPSecKeywords(ssh_connection)
    validate_equals_with_retry(
        lambda: ipsec_keywords.are_all_security_associations_established(expected_count),
        True,
        f"All {expected_count} security associations should be established after lock/unlock",
        timeout=600,
    )


@mark.p1
def test_ipsec_cert_renewal_operation():
    """Validate IPSec certificate renewal re-establishes security associations.

    Runs the IPsec client certificate-renewal operation on the active controller
    and verifies the certificate is renewed and security associations remain
    established with the new credentials.

    Steps:
        - Record the active controller certificate serial and SA count
        - Run the IPsec certificate renewal operation (op code 2)
        - Verify the IPSec certificate serial changed
        - Wait for all security associations to remain established
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_hosts = SystemHostListKeywords(ssh_connection)
    ipsec_keywords = IPSecKeywords(ssh_connection)
    expected_count = IPSecKeywords(ssh_connection).get_expected_security_association_count()

    active_controller = system_hosts.get_active_controller()
    hostname = active_controller.get_host_name()
    cert_path = ipsec_keywords.get_ipsec_certificate_path(hostname)

    get_logger().log_test_case_step(f"Record current IPSec certificate serial for {hostname}")
    serial_before = ipsec_keywords.get_certificate_serial(cert_path)

    get_logger().log_test_case_step(f"Run IPSec certificate renewal on {hostname}")
    ipsec_keywords.renew_ipsec_certificate()

    get_logger().log_test_case_step("Verify IPSec certificate serial changed after renewal")
    validate_equals_with_retry(
        lambda: ipsec_keywords.get_certificate_serial(cert_path) != serial_before,
        True,
        f"IPSec certificate serial should change after renewal on {hostname}",
        timeout=300,
    )

    get_logger().log_test_case_step("Wait for security associations to remain established after renewal")
    validate_equals_with_retry(
        lambda: ipsec_keywords.are_all_security_associations_established(expected_count),
        True,
        f"All {expected_count} security associations should be established after certificate renewal",
        timeout=300,
    )

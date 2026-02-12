from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.kube_rootca.system_kube_rootca_update_keywords import SystemKubeRootcaUpdateKeywords


@mark.p1
def test_k8s_root_ca_update(request):
    """Test Kubernetes Root CA certificate update procedure.

    Steps:
        - Start update and generate certificate
        - Update all hosts through trust-both-cas phase
        - Update pods trust-both-cas
        - Update all hosts through update-certs phase
        - Update all hosts through trust-new-ca phase
        - Update pods trust-new-ca
        - Complete update
    """

    def cleanup_kube_rootca_update():
        get_logger().log_test_case_step("Kube rootca update test completed")

    request.addfinalizer(cleanup_kube_rootca_update)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kube_rootca = SystemKubeRootcaUpdateKeywords(ssh_connection)
    system_hosts = SystemHostListKeywords(ssh_connection)

    get_logger().log_test_case_step("Starting kube rootca update")
    update_output = kube_rootca.kube_rootca_update_start(force=True)
    validate_equals(update_output.get_kube_rootca_update().is_update_started(), True, "Update should start")

    get_logger().log_test_case_step("Generating new certificate")
    kube_rootca.kube_rootca_update_generate_cert("2031-08-25", "C=CA ST=ON L=Ottawa O=company OU=sale CN=kubernetes")
    validate_equals(kube_rootca.wait_for_update_state("update-new-rootca-cert-generated", 60), True, "Certificate should generate")

    hosts_output = system_hosts.get_system_host_list()
    all_hosts = hosts_output.get_controllers()
    try:
        all_hosts += hosts_output.get_workers()
    except Exception:
        pass

    for host in all_hosts:
        hostname = host.get_host_name()
        get_logger().log_test_case_step(f"Updating {hostname} trust-both-cas")
        kube_rootca.kube_rootca_host_update(hostname, "trust-both-cas")
        validate_equals(kube_rootca.wait_for_host_update_state(hostname, "updated-host-trust-both-cas", 600), True, f"{hostname} should update")

    kube_rootca.kube_rootca_pods_update("trust-both-cas")
    validate_equals(kube_rootca.wait_for_update_state("updated-pods-trust-both-cas", 3600), True, "Pods should update trust-both-cas")

    for host in all_hosts:
        hostname = host.get_host_name()
        get_logger().log_test_case_step(f"Updating {hostname} update-certs")
        kube_rootca.kube_rootca_host_update(hostname, "update-certs")
        validate_equals(kube_rootca.wait_for_host_update_state(hostname, "updated-host-update-certs", 600), True, f"{hostname} should update certs")

    for host in all_hosts:
        hostname = host.get_host_name()
        get_logger().log_test_case_step(f"Updating {hostname} trust-new-ca")
        kube_rootca.kube_rootca_host_update(hostname, "trust-new-ca")
        validate_equals(kube_rootca.wait_for_host_update_state(hostname, "updated-host-trust-new-ca", 600), True, f"{hostname} should trust new ca")

    kube_rootca.kube_rootca_pods_update("trust-new-ca")
    validate_equals(kube_rootca.wait_for_update_state("updated-pods-trust-new-ca", 3600), True, "Pods should trust new ca")

    get_logger().log_test_case_step("Completing kube rootca update")
    complete_output = kube_rootca.kube_rootca_update_complete()
    validate_equals(complete_output.get_kube_rootca_update().is_update_completed(), True, "Update should complete")
    get_logger().log_test_case_step("Kubernetes Root CA update completed successfully")

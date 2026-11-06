from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.snmp.snmp_keywords import SNMPKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


@mark.p2
def test_snmp_configuration_active_controller(request):
    """Verify SNMP application installs and is configured on the active controller.

    Installs and configures the SNMP application, then verifies the SNMP and
    nginx ingress controller applications reach the applied state, their pods
    are running, and the generated SNMP configuration inside the SNMP pod
    contains the expected community and user directives. Does not cover read
    operations, traps, the standby controller, or the nginx ingress mapping,
    Service ports, network policy and helm overrides.
    On a Distributed Cloud lab it checks the system controller only; the
    subclouds are not covered.

    Preconditions:
        - Active controller is accessible
        - SNMP application package is staged on the controller

    Setup:
        - Establish SSH connection to the active controller
        - Install and configure the SNMP application

    Test Steps:
        1. Verify the SNMP and nginx ingress controller applications are applied
        2. Verify the SNMP and nginx ingress controller pods are running
        3. Verify the SNMP configuration contains the expected directives

    Teardown:
        - Remove and delete the SNMP application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    snmp_keywords = SNMPKeywords(ssh_connection)
    config = ConfigurationManager.get_snmp_config()
    app_name = config.get_snmp_app_name()
    nginx_app_name = ConfigurationManager.get_app_config().get_nginx_ingress_controller_name()
    nginx_controller_pod_prefix = "ic-nginx-ingress-ingress-nginx-controller"

    def cleanup_snmp():
        """Remove and delete the SNMP application."""
        get_logger().log_teardown_step(f"Remove and delete application '{app_name}'")
        SNMPKeywords(LabConnectionKeywords().get_active_controller_ssh()).remove_and_cleanup_snmp()

    request.addfinalizer(cleanup_snmp)

    get_logger().log_setup_step("Install and configure SNMP application")
    snmp_keywords.install_and_configure_snmp()

    get_logger().log_test_case_step("Verify SNMP and nginx ingress controller applications are applied")
    applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    snmp_application = applications.get_application(app_name)
    validate_equals(snmp_application.get_status(), "applied", f"Application '{app_name}' status")
    nginx_application = applications.get_application(nginx_app_name)
    validate_equals(nginx_application.get_status(), "applied", f"Application '{nginx_app_name}' status")

    get_logger().log_test_case_step("Verify SNMP and nginx ingress controller pods are running")
    pod_name = snmp_keywords.get_running_snmp_pod_name()
    get_logger().log_info(f"Running SNMP pod: {pod_name}")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status("Running", pod_names=[nginx_controller_pod_prefix], namespace="kube-system", timeout=300)

    get_logger().log_test_case_step("Verify SNMP configuration contains the expected directives")
    config_content = snmp_keywords.get_snmp_config_object(pod_name).get_snmp_object().get_content()
    community_directive = "rocommunity6" if ConfigurationManager.get_lab_config().is_ipv6() else "rocommunity"
    validate_str_contains(config_content, f"{community_directive} {config.get_snmp_v2c_community()} ", f"'{community_directive}' directive for the SNMP community in snmpd.conf")
    validate_str_contains(config_content, f"createUser {config.get_snmp_v3_username()} ", "'createUser' directive for the SNMP v3 user in snmpd.conf")
    validate_str_contains(config_content, f"rwuser {config.get_snmp_v3_username()} ", "'rwuser' directive for the SNMP v3 user in snmpd.conf")

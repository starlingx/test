from pytest import mark, fail
import time

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_if_keywords import SystemHostInterfaceKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.deployment_assets.host_profile_yaml_keywords import HostProfileYamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.patch.kubectl_apply_patch_keywords import KubectlApplyPatchKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_wait_pod_keywords import KubectlWaitPodKeywords
from keywords.files.file_keywords import FileKeywords


@mark.p2
@mark.lab_has_subcloud
def test_dm_force_failure_mtu_change(request):
    """
    Force a deployment manager failure by setting an invalid MTU value.

    Test Steps:
        - Change mtu value in deployment manager file.
        - Apply the deployment-manager.yaml using kubectl.
        - Patch the host to trigger reconciliation.
        - List pods in platform-deployment-manager namespace.
        - Delete the platform-deployment-manager pod.
        - Wait for new pod to be ready.
        - Verify alarm 260.001 is raised via fm alarm-list.
    """
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    
    hostname = SystemHostListKeywords(subcloud_ssh).get_active_controller().get_host_name()
    kubectl_apply_keywords = KubectlFileApplyKeywords(subcloud_ssh)
    kubectl_patch_keywords = KubectlApplyPatchKeywords(subcloud_ssh)
    kubectl_pods_keywords = KubectlGetPodsKeywords(subcloud_ssh)
    kubectl_delete_keywords = KubectlDeletePodsKeywords(subcloud_ssh)
    kubectl_wait_keywords = KubectlWaitPodKeywords(subcloud_ssh)
    alarm_keywords = AlarmListKeywords(subcloud_ssh)
    host_profile_yaml_keywords = HostProfileYamlKeywords(subcloud_ssh)
    file_keywords = FileKeywords(subcloud_ssh)
    
    # Get current MTU value
    old_mtu_str = SystemHostInterfaceKeywords(subcloud_ssh).system_host_interface_show(hostname, "lo").get_imtu()
    old_mtu = int(old_mtu_str) if isinstance(old_mtu_str, str) else old_mtu_str
    
    get_logger().log_info(f"Current MTU for 'lo' interface on {hostname}: {old_mtu}")

    # Get deployment-manager.yaml from subcloud assets
    deployment_config_file = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_deployment_config_file()
    get_logger().log_info(f"Using deployment config file: {deployment_config_file}")

    get_logger().log_test_case_step("Create backup of deployment-manager.yaml")
    deployment_config_backup = f"{deployment_config_file}.backup"
    file_keywords.copy_file(deployment_config_file, deployment_config_backup)
    
    get_logger().log_test_case_step("Modify deployment-manager.yaml to set MTU to 2000")
    host_profile_yaml_keywords.edit_yaml_host_interface_mtu("lo", 2000, deployment_config_file)

    get_logger().log_test_case_step("Apply deployment-manager.yaml with MTU 2000 configuration")
    kubectl_apply_keywords.apply_resource_from_yaml(deployment_config_file)
    
    get_logger().log_test_case_step("Patch host to trigger reconciliation")
    kubectl_patch_keywords.patch_host(
        host_name=hostname,
        namespace="deployment",
        patch_data='{"status": {"reconciled": false}}',
        patch_type="merge",
        subresource="status"
    )
    
    get_logger().log_test_case_step("List pods in platform-deployment-manager namespace")
    pods_output = kubectl_pods_keywords.get_pods(namespace="platform-deployment-manager")
    dm_pods = [pod for pod in pods_output.get_pods() if "platform-deployment-manager" in pod.get_name()]
    
    if not dm_pods:
        get_logger().log_error("No platform-deployment-manager pod found")
        fail("platform-deployment-manager pod not found in namespace")
    
    dm_pod_name = dm_pods[0].get_name()
    get_logger().log_info(f"Found deployment manager pod: {dm_pod_name}")
    
    get_logger().log_test_case_step("Delete platform-deployment-manager pod")
    kubectl_delete_keywords.delete_pod(dm_pod_name, namespace="platform-deployment-manager")
    
    get_logger().log_test_case_step("Wait for new deployment manager pod to be ready")
    kubectl_wait_keywords.wait_for_pods_ready(
        label="app=platform-deployment-manager",
        namespace="platform-deployment-manager",
        timeout=300
    )
    
    get_logger().log_info("Deployment manager pod is running again")
    
    get_logger().log_test_case_step("Verify alarm 260.001 is raised via fm alarm-list")
    validate_equals_with_retry(
        function_to_execute=lambda: alarm_keywords.is_alarm_present("260.001"),
        expected_value=True,
        validation_description="Alarm 260.001 should be present in fm alarm-list",
        timeout=300,
        polling_sleep_time=10
    )
    
    get_logger().log_info("Alarm 260.001 raised.")
    
    get_logger().log_test_case_step("Restore original deployment-manager.yaml from backup")
    file_keywords.move_file(deployment_config_backup, deployment_config_file)
    
    get_logger().log_test_case_step("Apply original deployment-manager.yaml")
    kubectl_apply_keywords.apply_resource_from_yaml(deployment_config_file)
    
    get_logger().log_test_case_step("Patch host to trigger reconciliation with correct MTU")
    kubectl_patch_keywords.patch_host(
        host_name=hostname,
        namespace="deployment",
        patch_data='{"status": {"reconciled": true}}',
        patch_type="merge",
        subresource="status"
    )
    
    get_logger().log_test_case_step("Verify alarm 260.001 is cleared")
    validate_equals_with_retry(
        function_to_execute=lambda: alarm_keywords.is_alarm_present("260.001"),
        expected_value=False,
        validation_description="Alarm 260.001 should be cleared from fm alarm-list",
        timeout=300,
        polling_sleep_time=10
    )
    
    get_logger().log_info("Alarm 260.001 cleared.")

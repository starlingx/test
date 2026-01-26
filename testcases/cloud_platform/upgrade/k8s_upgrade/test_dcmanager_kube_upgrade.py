from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains, validate_not_none
from keywords.cloud_platform.dcmanager.dcmanager_kube_deploy_strategy_keywords import DcmanagerKubeStrategyKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords


@mark.p2
@mark.lab_has_subcloud
def test_dcmanager_kube_upgrade_subcloud():
    """Test Kubernetes upgrade orchestration on subcloud using dcmanager.

    This test performs Kubernetes upgrade orchestration for a subcloud or group of subclouds
    from the system controller using dcmanager kube-upgrade-strategy.

    Test Steps:
        - Get system controller SSH connection
        - Validate Kubernetes versions on system controller
        - Get subcloud configuration
        - Create and apply dcmanager kube-upgrade-strategy
        - Verify upgrade completion on subcloud

    Raises:
        AssertionError: If any validation step fails.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    k8s_config = ConfigurationManager.get_k8s_config()

    dcm_kube_keywords = DcmanagerKubeStrategyKeywords(central_ssh)
    system_kube_keywords = SystemKubernetesListKeywords(central_ssh)

    subcloud_group = k8s_config.get_subcloud_group()
    subcloud_name = k8s_config.get_subcloud_name()

    get_logger().log_test_case_step("Get Active Kubernetes version from system controller")
    kube_version_list = system_kube_keywords.get_system_kube_version_list()
    active_kube_version = kube_version_list.get_active_kubernetes_version()
    validate_not_none(active_kube_version, f"Active Kubernetes version found {active_kube_version}")

    target_version = k8s_config.get_k8_target_version()
    if target_version and target_version != "":
        get_logger().log_info(f"Target kubernetes version from config: {target_version}")
    else:
        target_version = None
        get_logger().log_info("No target version specified, dcmanager will use active version from system controller")

    # Use subcloud from config if specified
    if subcloud_name != "None":
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    get_logger().log_test_case_step("Create dcmanager kube-upgrade-strategy")
    if subcloud_name != "None":
        get_logger().log_info(f"Using subcloud: {subcloud_name}")
        dcm_kube_keywords.dcmanager_kube_upgrade_strategy_create(kube_version=target_version, subcloud=subcloud_name)
    elif subcloud_group != "None":
        get_logger().log_info(f"Using subcloud group: {subcloud_group}")
        dcm_kube_keywords.dcmanager_kube_upgrade_strategy_create(kube_version=target_version, subcloud_group=subcloud_group)
    else:
        get_logger().log_info("No subcloud or group specified, applying to all subclouds")
        dcm_kube_keywords.dcmanager_kube_upgrade_strategy_create(kube_version=target_version, subcloud_group="Default")

    get_logger().log_test_case_step("Apply dcmanager kube-upgrade-strategy")
    dcm_kube_keywords.dcmanager_kube_upgrade_strategy_apply()

    if target_version and subcloud_group == "None" and subcloud_name != "None":
        get_logger().log_test_case_step(f"Verify target version {target_version} is active on subcloud {subcloud_name}")
        subcloud_kube_keywords = SystemKubernetesListKeywords(subcloud_ssh)
        active_kube_versions = subcloud_kube_keywords.get_system_kube_version_list().get_active_kubernetes_version()
        validate_equals(active_kube_versions, target_version, "Target version is active on subcloud")

    get_logger().log_test_case_step("Delete dcmanager kube-upgrade-strategy")
    dcm_kube_keywords.dcmanager_kube_strategy_delete()

from pytest import fail, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_kube_deploy_strategy_keywords import DcmanagerKubeStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords


@mark.p2
@mark.lab_has_subcloud
def test_kube_upgrade_to_active_version(request):
    """
    Verify subcloud kubernetes upgrade to central
    cloud kubernetes version one by one.

    Test Steps:
        - Create the kubernetes strategy upgrade
          for N+1 subcloud version available in
          the central cloud.
        - Apply strategy.
        - Loop over the versions until reaching
          central cloud active kubernetes version.

    """

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = subcloud_list_keywords.get_dcmanager_subcloud_list().get_lower_id_async_subcloud()
    subcloud_name = lowest_subcloud.get_name()

    # get subcloud ssh
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    central_k8s_active_version = SystemKubernetesListKeywords(central_ssh).get_kubernetes_versions_by_state("active")[0]
    remote_k8s_active_version = SystemKubernetesListKeywords(subcloud_ssh).get_kubernetes_versions_by_state("active")[0]

    get_logger().log_info(f"Central cloud active kubernetes version: {central_k8s_active_version}, subcloud kubernetes active version: {remote_k8s_active_version}")
    if remote_k8s_active_version >= central_k8s_active_version:
        fail("Subcloud k8s version is equal or higher than central cloud version.")

    get_logger().log_info(f"Upgrading subcloud kubernetes to {central_k8s_active_version}...")
    DcmanagerKubeStrategyKeywords(central_ssh).dcmanager_kube_upgrade_strategy_create(subcloud=subcloud_name, kube_version=central_k8s_active_version)
    DcmanagerKubeStrategyKeywords(central_ssh).dcmanager_kube_upgrade_strategy_apply()
    DcmanagerKubeStrategyKeywords(central_ssh).dcmanager_kube_strategy_delete()

    current_subcloud_k8s_version = SystemKubernetesListKeywords(subcloud_ssh).get_kubernetes_versions_by_state("active")[0]
    validate_equals(central_k8s_active_version, current_subcloud_k8s_version, "Validate that subcloud and centra cloud has the same kubernetes version.")

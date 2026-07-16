"""Batch rehoming tests for subclouds between system controllers."""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.dcmanager.rehoming_utils import determine_rehome_direction, perform_batch_rehome_operation, verify_subcloud_healthy
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


def count_pods_on_subcloud(subcloud_ssh: SSHConnection) -> int:
    """Count the total number of pods running on a subcloud.

    Args:
        subcloud_ssh (SSHConnection): SSH connection to the subcloud.

    Returns:
        int: Total number of pods on the subcloud.
    """
    kubectl_keywords = KubectlGetPodsKeywords(subcloud_ssh)
    pods_output = kubectl_keywords.get_pods_all_namespaces()
    pod_count = len(pods_output.get_pods())
    get_logger().log_info(f"Total pods on subcloud: {pod_count}")
    return pod_count


@mark.p2
@mark.lab_has_secondary_system_controller
@mark.lab_has_subcloud
def test_rehome_subclouds_in_batch_n_release():
    """Verify batch rehoming of all online N-release subclouds between two system controllers.

    Rehomes all available online subclouds running the current (N) release from
    the system controller that owns them to the peer system controller. All
    migrate operations are triggered in parallel, then polled to completion.

    Preconditions:
        - Lab has two system controllers (geo-redundant DC)
        - At least one online subcloud on the current release is present in config

    Setup:
        - Establish SSH connections to both system controllers
        - Determine rehome direction (origin = controller with online subclouds)
        - Ensure controller-0 is active on duplex subclouds
        - Count pods on each subcloud before rehoming

    Test Steps:
        1. Rehome all selected subclouds in batch (parallel migrate + poll)
        2. Verify each subcloud is healthy after rehoming
        3. Verify pod count is consistent on each subcloud after rehoming

    Teardown:
        - None
    """
    cloud_a_ssh = LabConnectionKeywords().get_active_controller_ssh()
    cloud_b_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()

    origin_ssh, destination_ssh, selected_subcloud_names = determine_rehome_direction(cloud_a_ssh, cloud_b_ssh, load="N")

    validate_not_equals(len(selected_subcloud_names), 0, "At least one online N-release subcloud must be available for rehoming")
    get_logger().log_info(f"Subclouds selected for rehoming: {selected_subcloud_names}")

    # Pre-rehome: ensure duplex subclouds have controller-0 active and count pods
    pods_before = {}
    lab_config = ConfigurationManager.get_lab_config()
    for subcloud_name in selected_subcloud_names:
        sc_config = lab_config.get_subcloud(subcloud_name)
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

        if sc_config.get_lab_type() == LabTypeEnum.DUPLEX.value:
            get_logger().log_info(f"Ensuring controller-0 is active on duplex subcloud {subcloud_name}")
            SystemHostSwactKeywords(subcloud_ssh).ensure_duplex_subcloud_c0_is_active(subcloud_name)

        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        get_logger().log_info(f"Counting pods on subcloud {subcloud_name} before rehoming")
        pods_before[subcloud_name] = count_pods_on_subcloud(subcloud_ssh)

    # Build batch descriptor and perform rehome
    get_logger().log_test_case_step("Rehome all selected subclouds in batch")
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subclouds_for_batch = []
    for subcloud_name in selected_subcloud_names:
        bootstrap = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
        install = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()
        subclouds_for_batch.append({
            "name": subcloud_name,
            "bootstrap_values": bootstrap,
            "install_values": install,
        })

    perform_batch_rehome_operation(origin_ssh, destination_ssh, subclouds_for_batch)

    # Post-rehome validations
    get_logger().log_test_case_step("Verify subclouds are healthy after batch rehoming")
    for subcloud_name in selected_subcloud_names:
        get_logger().log_info(f"Validating subcloud {subcloud_name} is healthy after rehome")
        verify_subcloud_healthy(destination_ssh, subcloud_name, check_sync=False)

    get_logger().log_test_case_step("Verify pod counts are consistent after batch rehoming")
    for subcloud_name in selected_subcloud_names:
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        pods_after = count_pods_on_subcloud(subcloud_ssh)
        validate_equals(pods_before[subcloud_name], pods_after, f"Pod count on {subcloud_name} should be consistent before and after rehoming")


@mark.p2
@mark.lab_has_secondary_system_controller
@mark.lab_has_subcloud
def test_rehome_subclouds_in_batch_n_minus_1_release():
    """Verify batch rehoming of all online N-1 release subclouds between two system controllers.

    Rehomes all available online subclouds running the previous (N-1) release from
    the system controller that owns them to the peer system controller. All
    migrate operations are triggered in parallel with the --release flag.

    Preconditions:
        - Lab has two system controllers (geo-redundant DC)
        - At least one online subcloud on the N-1 release is present in config

    Setup:
        - Establish SSH connections to both system controllers
        - Determine rehome direction (origin = controller with online N-1 subclouds)
        - Ensure controller-0 is active on duplex subclouds
        - Count pods on each subcloud before rehoming

    Test Steps:
        1. Rehome all selected N-1 subclouds in batch (parallel migrate + poll)
        2. Verify each subcloud is healthy after rehoming
        3. Verify pod count is consistent on each subcloud after rehoming

    Teardown:
        - None
    """
    cloud_a_ssh = LabConnectionKeywords().get_active_controller_ssh()
    cloud_b_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()

    # Resolve N-1 release version
    n_minus_1_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    origin_ssh, destination_ssh, selected_subcloud_names = determine_rehome_direction(cloud_a_ssh, cloud_b_ssh, load="N-1")

    validate_not_equals(len(selected_subcloud_names), 0, "At least one online N-1 subcloud must be available for rehoming")
    get_logger().log_info(f"N-1 subclouds selected for rehoming: {selected_subcloud_names}")

    # Pre-rehome: ensure duplex subclouds have controller-0 active and count pods
    pods_before = {}
    lab_config = ConfigurationManager.get_lab_config()
    for subcloud_name in selected_subcloud_names:
        sc_config = lab_config.get_subcloud(subcloud_name)
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

        if sc_config.get_lab_type() == LabTypeEnum.DUPLEX.value:
            get_logger().log_info(f"Ensuring controller-0 is active on duplex subcloud {subcloud_name}")
            SystemHostSwactKeywords(subcloud_ssh).ensure_duplex_subcloud_c0_is_active(subcloud_name)

        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        get_logger().log_info(f"Counting pods on subcloud {subcloud_name} before rehoming")
        pods_before[subcloud_name] = count_pods_on_subcloud(subcloud_ssh)

    # Build batch descriptor and perform rehome with release flag
    get_logger().log_test_case_step("Rehome all selected N-1 subclouds in batch")
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subclouds_for_batch = []
    for subcloud_name in selected_subcloud_names:
        bootstrap = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
        install = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()
        subclouds_for_batch.append({
            "name": subcloud_name,
            "bootstrap_values": bootstrap,
            "install_values": install,
        })

    perform_batch_rehome_operation(origin_ssh, destination_ssh, subclouds_for_batch, release=n_minus_1_release)

    # Post-rehome validations
    get_logger().log_test_case_step("Verify N-1 subclouds are healthy after batch rehoming")
    for subcloud_name in selected_subcloud_names:
        get_logger().log_info(f"Validating subcloud {subcloud_name} is healthy after rehome")
        verify_subcloud_healthy(destination_ssh, subcloud_name, check_sync=False)

    get_logger().log_test_case_step("Verify pod counts are consistent after batch rehoming")
    for subcloud_name in selected_subcloud_names:
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        pods_after = count_pods_on_subcloud(subcloud_ssh)
        validate_equals(pods_before[subcloud_name], pods_after, f"Pod count on {subcloud_name} should be consistent before and after rehoming")

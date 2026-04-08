import json5
import os
import pytest
from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.objects.swmanager_sw_deploy_strategy_create_config import SwManagerSwDeployStrategyCreateConfig
from keywords.cloud_platform.swmanager.swmanager_sw_deploy_strategy_keywords import SwManagerSwDeployStrategyKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.system_test.patching_keywords import PatchingKeywords
from keywords.system_test.setup_stress_pods import SetupStressPods
from keywords.system_test.timing_logger import PatchingTimingLogger
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords

@mark.p0
def test_patching_apply_and_remove(request: pytest.FixtureRequest):
    """
    Test software patching apply and remove procedures under system load.

    This test performs a complete patching cycle with stress pods running to simulate
    real-world conditions and measure performance impact during patching operations.

    Test Steps:
    - Setup mixed workload stress pods to simulate system load
    - Get build information from /etc/build.info
    - Download available patches from build server
    - Upload patch using 'software upload'
    - Verify patch is uploaded with 'software list'
    - Create sw-deploy strategy for patch apply
    - Monitor strategy status until ready-to-apply
    - Apply the patch using sw-deploy strategy
    - Monitor strategy until completion and extract timings
    - Verify system health after patch apply
    - Create sw-deploy strategy for patch removal
    - Monitor removal strategy until ready-to-apply
    - Apply patch removal strategy
    - Monitor removal strategy until completion and extract timings
    - Verify system health after patch removal
    - Delete the removed release

    Cleanup:
      - Delete any remaining strategies
      - Remove patch files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    patching_keywords = PatchingKeywords(ssh_connection)
    usm_keywords = USMKeywords(ssh_connection)
    software_list_keywords = SoftwareListKeywords(ssh_connection)
    sw_deploy_keywords = SwManagerSwDeployStrategyKeywords(ssh_connection)
    timing_logger = PatchingTimingLogger()

    get_logger().log_test_case_step("Setup stress pods to simulate system load")
    stress_pods = SetupStressPods(ssh_connection)
    stress_pods.setup_stress_pods(benchmark="mixed")

    get_logger().log_test_case_step("Get build information from /etc/build.info")
    build_info = patching_keywords.get_and_validate_build_info()
    build_id = build_info["BUILD_ID"]
    job = build_info["JOB"]

    get_logger().log_test_case_step("Download available patches from build server")
    patch_files = patching_keywords.download_patch_files(job, build_id)
    validate_equals(len(patch_files) > 0, True, "At least one patch file should be downloaded")

    def cleanup_resources():
        """Finalizer to cleanup resources"""
        get_logger().log_info("Cleaning up patching test resources...")

        if sw_deploy_keywords.check_sw_deploy_strategy_exists():
            sw_deploy_keywords.get_sw_deploy_strategy_delete()

        file_keywords = FileKeywords(ssh_connection)
        for patch_file in patch_files:
            file_keywords.delete_file(patch_file)

        namespace_deleter = KubectlDeleteNamespaceKeywords(ssh_connection)
        namespace_deleter.delete_namespace("mixed-benchmark")

    request.addfinalizer(cleanup_resources)

    get_logger().log_test_case_step("Upload patch file using 'software upload'")
    patch_file = patch_files[0]
    usm_keywords.upload_patch_file(patch_file, sudo=False)

    get_logger().log_test_case_step("Verify patch is uploaded with 'software list'")
    software_list_output = software_list_keywords.get_software_list(sudo=False)
    available_release = patching_keywords.get_available_release_for_apply(software_list_output)
    validate_equals(available_release is not None, True, "An available release should be found after patch upload")

    get_logger().log_test_case_step(f"Create sw-deploy strategy for {available_release} apply")
    strategy_config = SwManagerSwDeployStrategyCreateConfig(
        release=available_release,
        alarm_restrictions="relaxed",
        delete=True,
        max_parallel_worker_hosts=10,
        worker_apply_type="parallel"
    )

    create_success = sw_deploy_keywords.get_sw_deploy_strategy_create(strategy_config)
    validate_equals(create_success, True, "Strategy creation should succeed")

    get_logger().log_test_case_step("Monitor strategy status until ready-to-apply")
    strategy_ready = sw_deploy_keywords.wait_for_state(["ready-to-apply"], timeout=300)
    validate_equals(strategy_ready, True, "Strategy should reach ready-to-apply state")

    get_logger().log_test_case_step("Apply the patch using sw-deploy strategy")
    apply_success = sw_deploy_keywords.get_sw_deploy_strategy_apply()
    validate_equals(apply_success, True, "Strategy apply should succeed")

    get_logger().log_test_case_step("Monitor strategy until completion")
    strategy_completed = sw_deploy_keywords.wait_for_state(["applied"], timeout=1800)
    validate_equals(strategy_completed, True, "Strategy should complete successfully")

    get_logger().log_test_case_step("Extract detailed timing information for patch apply")
    details_output = sw_deploy_keywords.get_sw_deploy_strategy_show_details()
    patching_keywords.extract_and_log_timings(details_output, "apply", timing_logger)

    get_logger().log_test_case_step("Delete strategy after successful apply")
    sw_deploy_keywords.get_sw_deploy_strategy_delete()

    get_logger().log_test_case_step("Verify system health after patch apply")
    patching_keywords.verify_system_health(timeout=300)

    get_logger().log_test_case_step("Prepare for patch removal")
    software_list_output = software_list_keywords.get_software_list(sudo=False)
    remove_release = patching_keywords.get_deployed_release_for_remove(software_list_output)
    validate_equals(remove_release is not None, True, "A deployed release should be found for removal")

    get_logger().log_test_case_step(f"Create sw-deploy strategy removal for {remove_release}")
    remove_strategy_config = SwManagerSwDeployStrategyCreateConfig(
        release=remove_release,
        alarm_restrictions="relaxed",
        delete=True,
        max_parallel_worker_hosts=10,
        worker_apply_type="parallel"
    )

    create_success = sw_deploy_keywords.get_sw_deploy_strategy_create(remove_strategy_config)
    validate_equals(create_success, True, "Removal strategy creation should succeed")

    get_logger().log_test_case_step("Monitor removal strategy until ready-to-apply")
    strategy_ready = sw_deploy_keywords.wait_for_state(["ready-to-apply"], timeout=300)
    validate_equals(strategy_ready, True, "Removal strategy should reach ready-to-apply state")

    get_logger().log_test_case_step("Apply patch removal strategy")
    apply_success = sw_deploy_keywords.get_sw_deploy_strategy_apply()
    validate_equals(apply_success, True, "Removal strategy apply should succeed")

    get_logger().log_test_case_step("Monitor removal strategy until completion")
    strategy_completed = sw_deploy_keywords.wait_for_state(["applied"], timeout=1800)  # 30 minutes
    validate_equals(strategy_completed, True, "Removal strategy should complete successfully")

    get_logger().log_test_case_step("Extract detailed timing information for patch removal")
    details_output = sw_deploy_keywords.get_sw_deploy_strategy_show_details()
    patching_keywords.extract_and_log_timings(details_output, "remove", timing_logger)

    get_logger().log_test_case_step("Delete strategy after successful removal")
    sw_deploy_keywords.get_sw_deploy_strategy_delete()

    get_logger().log_test_case_step("Verify system health after patch removal")
    patching_keywords.verify_system_health(timeout=300)

    get_logger().log_test_case_step("Delete the removed release")
    software_list_output = software_list_keywords.get_software_list(sudo=False)
    release_to_delete = patching_keywords.get_available_release_for_apply(software_list_output)
    usm_keywords.software_delete(release_to_delete, sudo=False)

    get_logger().log_test_case_step("Collect and upload results")
    patching_keywords.collect_and_upload_results(timing_logger)

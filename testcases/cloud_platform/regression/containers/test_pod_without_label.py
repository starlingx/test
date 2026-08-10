from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_str_contains_with_retry
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.date.date_keywords import DateKeywords
from keywords.linux.log.log_grep_keywords import LogGrepKeywords

COLLECTD_LOG_PATH = "/var/log/collectd.log"
POD_NAME = "testpod"
POD_YAML_RESOURCE = "resources/cloud_platform/containers/pod_without_label.yaml"
REMOTE_POD_YAML_PATH = "/home/sysadmin/pod_without_label.yaml"
COLLECTD_CPU_DISPATCH_PATTERN = "platform cpu dispatch"


@mark.p2
def test_collectd_no_error_with_unlabeled_pod(request: FixtureRequest):
    """Verify collectd logs for errors when a pod without labels is running.

    Test Steps:
        - Verify collectd is healthy by confirming 'platform cpu dispatch' logs appear
        - Upload and deploy pod_no_label.yaml (pod with no labels)
        - Wait for the pod to reach Running status
        - Verify no traceback or AttributeError appears in collectd.log
        - Verify 'platform cpu dispatch' logs continue appearing after pod deployment

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    date_keywords = DateKeywords(ssh_connection)
    log_grep_keywords = LogGrepKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)

    # Step 1: Verify collectd is healthy before pod deployment
    get_logger().log_test_case_step("Verify collectd is dispatching cpu metrics before pod deployment")
    validate_str_contains_with_retry(
        lambda: log_grep_keywords.grep_log_for_errors(COLLECTD_LOG_PATH, COLLECTD_CPU_DISPATCH_PATTERN, tail=5),
        COLLECTD_CPU_DISPATCH_PATTERN,
        "Collectd is healthy: 'platform cpu dispatch' logs are present before pod deployment",
        timeout=60,
        polling_sleep_time=10,
    )

    # Step 2: Upload pod yaml to active controller
    get_logger().log_test_case_step("Upload pod_no_label.yaml to active controller")
    local_yaml_path = get_stx_resource_path(POD_YAML_RESOURCE)
    file_keywords.upload_file(local_yaml_path, REMOTE_POD_YAML_PATH)

    # Teardown: ensure pod is cleaned up
    def cleanup():
        get_logger().log_teardown_step(f"Delete pod {POD_NAME} if it exists")
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod(POD_NAME)

    request.addfinalizer(cleanup)

    # Step 3: Deploy pod without labels and record start time for log filtering
    get_logger().log_test_case_step("Deploy pod without labels")
    post_deploy_time = date_keywords.get_current_datetime()
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(REMOTE_POD_YAML_PATH)

    # Step 4: Wait for pod to reach Running status
    get_logger().log_test_case_step(f"Wait for pod {POD_NAME} to reach Running status")
    validate_equals(
        KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(POD_NAME, "Running", namespace="default", timeout=120),
        True,
        f"Pod {POD_NAME} reached Running status",
    )

    # Step 5: Verify 'platform cpu dispatch' logs continue after pod deployment
    get_logger().log_test_case_step("Verify collectd continues dispatching cpu metrics after pod deployment")
    validate_str_contains_with_retry(
        lambda: log_grep_keywords.grep_log_for_errors(COLLECTD_LOG_PATH, COLLECTD_CPU_DISPATCH_PATTERN, tail=3),
        COLLECTD_CPU_DISPATCH_PATTERN,
        "Collectd continues dispatching cpu metrics after unlabeled pod is running",
        timeout=90,
        polling_sleep_time=15,
    )

    # Step 6: Verify no traceback or AttributeError in collectd.log after pod deployment
    get_logger().log_test_case_step("Verify no traceback or AttributeError in collectd.log after pod deployment")
    end_time = date_keywords.get_current_datetime()

    error_output = file_keywords.read_file_with_pattern_range(
        COLLECTD_LOG_PATH,
        post_deploy_time,
        end_time,
        "'AttributeError'",
    )
    has_attribute_error = bool(error_output and any("NoneType" in line for line in error_output))
    validate_equals(
        has_attribute_error,
        False,
        "No AttributeError 'NoneType object has no attribute get' in collectd.log",
    )

    traceback_output = file_keywords.read_file_with_pattern_range(
        COLLECTD_LOG_PATH,
        post_deploy_time,
        end_time,
        "'Traceback'",
    )
    has_traceback = bool(traceback_output and any("Traceback" in line for line in traceback_output))
    validate_equals(
        has_traceback,
        False,
        "No Traceback in collectd.log after deploying unlabeled pod",
    )

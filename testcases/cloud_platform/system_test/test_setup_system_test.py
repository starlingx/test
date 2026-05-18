"""System Test Setup — PVC Pod and SRIOV FEC Accelerator Configuration.

Sets up prerequisites for system testing:
- Deploys a PVC-backed busybox pod to verify storage
- Identifies and configures SRIOV FEC accelerator cards

Prerequisites:
- Lab is accessible and active controller is available
- SRIOV FEC operator tarball is present on the system

Run with:
    python framework/runner/scripts/test_executor.py \
        --tests_location=testcases/cloud_platform/system_test/test_setup_system_test.py \
        --lab_config_file=config/lab/files/<lab>.json5
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.system_test.setup_system_test_keywords import SetupSystemTestKeywords


REMOTE_PATH = "/home/sysadmin"


@mark.p0
def test_setup_system_test() -> None:
    """Set up PVC pod and SRIOV FEC accelerator for system testing.

    Test Steps:
        1. Deploy PVC-backed busybox pod and verify it's running
        2. Identify network accelerator card (acc100, acc200, vrb2, n3000)
        3. Upload and apply SRIOV FEC operator
        4. Apply SRIOV FEC cluster configuration
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    setup_keywords = SetupSystemTestKeywords(ssh_connection)

    # Step 1: Deploy and verify PVC pod
    get_logger().log_test_case_step("Step 1: Deploy PVC pod")
    setup_keywords.setup_pvc_pod(REMOTE_PATH)

    # Step 2: Identify and configure network accelerator
    get_logger().log_test_case_step("Step 2: Setup SRIOV FEC accelerator")
    setup_keywords.setup_accelerator_card(REMOTE_PATH)

    get_logger().log_info("System test setup completed successfully")

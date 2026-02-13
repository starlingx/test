from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.swmanager.swmanager_kube_rootca_update_strategy_keywords import SwManagerKubeRootcaUpdateStrategyKeywords


@mark.p1
def test_apply_kube_rootca_update_strategy(request):
    """Test sw-manager orchestrated kube-rootca-update strategy.

    This test creates, applies, and validates a kube-rootca-update strategy
    using sw-manager orchestration.

    Steps:
        - Create kube-rootca-update strategy with certificate parameters
        - Verify strategy reaches ready-to-apply state
        - Apply strategy and wait for completion
        - Verify strategy reaches applied state
        - Delete strategy in cleanup
    """

    def cleanup_strategy():
        """Clean up kube-rootca-update strategy after test."""
        get_logger().log_info("Cleaning up kube-rootca-update strategy")
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        strategy_keywords = SwManagerKubeRootcaUpdateStrategyKeywords(ssh_connection)
        strategy_keywords.delete_kube_rootca_update_strategy()

    request.addfinalizer(cleanup_strategy)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    strategy_keywords = SwManagerKubeRootcaUpdateStrategyKeywords(ssh_connection)

    get_logger().log_test_case_step("Creating kube-rootca-update strategy")
    strategy = strategy_keywords.create_kube_rootca_update_strategy(expiry_date="2031-08-25", subject="C=CA ST=ON L=Ottawa O=company OU=sale CN=kubernetes")
    validate_equals(strategy.is_ready_to_apply(), True, "Strategy should reach ready-to-apply state")

    get_logger().log_test_case_step("Applying kube-rootca-update strategy")
    applied_strategy = strategy_keywords.apply_kube_rootca_update_strategy(timeout=7200)
    validate_equals(applied_strategy.is_applied(), True, "Strategy should reach applied state")

    get_logger().log_test_case_step("Kube-rootca-update strategy completed successfully")

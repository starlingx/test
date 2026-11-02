from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords

FACTORY_INSTALL_COMPLETE_MARKER = "/var/lib/factory-install/complete"


@mark.p2
@mark.lab_has_subcloud
def test_verify_subcloud_factory_ready():
    """Verify the target subcloud is factory-installed and reachable.

    A shared DC precondition: sequence it before an enroll or factory-restore test
    in the test plan so an unready subcloud fails here (fast, with a clear reason)
    instead of deep in the downstream playbook. Kept separate from the enroll tests
    so those stay focused on the operation + KPI capture.

    Checks the first configured subcloud:
        - an SSH session establishes at its factory IP with the factory
          credentials (an unreachable or down box fails here);
        - /var/lib/factory-install/complete exists (factory-install finished);
        - the cluster is healthy (alarms clear, pods/apps healthy).
    """
    lab_config = ConfigurationManager.get_lab_config()
    subcloud_name = lab_config.get_subcloud_names()[0]
    factory_ip = lab_config.get_subcloud(subcloud_name).get_factory_ip()

    get_logger().log_test_case_step(f"Connect to {subcloud_name} at factory IP {factory_ip} and verify factory-install")
    try:
        subcloud_ssh = LabConnectionKeywords().get_subcloud_factory_ssh(subcloud_name)
    except Exception as connect_error:
        fail(f"{subcloud_name} is not reachable at factory IP {factory_ip} ({connect_error}). Is it factory-installed and powered on?")

    if not FileKeywords(subcloud_ssh).file_exists(FACTORY_INSTALL_COMPLETE_MARKER):
        fail(f"{subcloud_name} is reachable but {FACTORY_INSTALL_COMPLETE_MARKER} is missing; it is not factory-installed.")

    get_logger().log_test_case_step(f"Verify {subcloud_name} cluster is healthy")
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

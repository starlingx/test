from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.subcloud_factory_ready_keywords import SubcloudFactoryReadyKeywords


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

    get_logger().log_test_case_step(f"Verify {subcloud_name} (factory IP {factory_ip}) is factory-ready")
    SubcloudFactoryReadyKeywords().validate_subcloud_factory_ready(subcloud_name)

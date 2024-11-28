from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords


def test_hello_world():
    """
    Simples test that connects to the active controller. Should be removed when we have real tests
    Returns:

    """
    get_logger().log_info('Hello World')
    # raise Exception("Hello")
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    system_applications_list_keywords = SystemApplicationListKeywords(ssh_connection)
    hosts = system_applications_list_keywords.get_system_application_list()
    assert hosts is not None

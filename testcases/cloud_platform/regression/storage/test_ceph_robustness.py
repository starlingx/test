from pytest import mark

from framework.logging.automation_logger import get_logger
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.server.power_keywords import PowerKeywords


@mark.p2
def test_ceph_soft_reboot_all_nodes():
    """
    Soft reboot all nodes and verify ceph health before and after.

    Test Steps:
        - Check ceph health before reboot
        - Reboot all nodes
        - Wait until all nodes finishes rebooting
        - Check ceph health after reboot

    Args: None
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Checking ceph health before reboot nodes.")
    ceph_status_keywords = CephStatusKeywords(active_ssh_connection)
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)

    system_host_list_keyword = SystemHostListKeywords(active_ssh_connection)
    system_host_output = system_host_list_keyword.get_system_host_with_extra_column(["capabilities", "uptime"])
    active_controller_name = system_host_output.get_active_controller().get_host_name()
    full_hosts_list = system_host_output.get_host_names()
    hosts_except_active_controller = system_host_output.get_host_names_except_active_controller()

    for host in hosts_except_active_controller:
        get_logger().log_test_case_step(f"Soft reboot {host}.")
        host_ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(host)
        host_ssh_connection.send_as_sudo("sudo reboot -f")

    get_logger().log_test_case_step(f"Soft reboot active controller {active_controller_name}.")
    active_ssh_connection.send_as_sudo("sudo reboot -f")

    for host in full_hosts_list:
        get_logger().log_test_case_step(f"Check whether {host} reboot success.")
        pre_uptime = system_host_output.get_host(host).get_uptime()
        reboot_success = SystemHostRebootKeywords(active_ssh_connection).wait_for_force_reboot(host, pre_uptime)
        assert reboot_success, f"{host} was not rebooted successfully"

    get_logger().log_test_case_step("Checking ceph health after reboot.")
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)


@mark.p2
def test_ceph_hard_reboot_all_nodes():
    """
    Hard reboot all nodes and verify ceph health before and after.

    Test Steps:
        - Check ceph health before reboot
        - Power off/on all nodes
        - Wait until all nodes finishes rebooting
        - Check ceph health after reboot

    Args: None
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Checking ceph health before power off/on nodes.")
    ceph_status_keywords = CephStatusKeywords(active_ssh_connection)
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)

    system_host_list_keyword = SystemHostListKeywords(active_ssh_connection)
    system_host_output = system_host_list_keyword.get_system_host_with_extra_column(["capabilities", "uptime"])
    active_controller_name = system_host_output.get_active_controller().get_host_name()
    full_hosts_list = system_host_output.get_host_names()
    hosts_except_active_controller = system_host_output.get_host_names_except_active_controller()

    power_keywords = PowerKeywords(active_ssh_connection)
    for host in hosts_except_active_controller:
        get_logger().log_test_case_step(f"Powers cycle {host}.")
        power_keywords.power_cycle(host)

    get_logger().log_test_case_step(f"Power cycle active controller: {active_controller_name}.")
    power_keywords.power_cycle(active_controller_name)

    for host in full_hosts_list:
        get_logger().log_test_case_step(f"Check whether {host} reboot success.")
        pre_uptime = system_host_output.get_host(host).get_uptime()
        reboot_success = SystemHostRebootKeywords(active_ssh_connection).wait_for_force_reboot(host, pre_uptime)
        assert reboot_success, f"{host} was not rebooted successfully"

    get_logger().log_test_case_step("Checking ceph health after reboot.")
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)

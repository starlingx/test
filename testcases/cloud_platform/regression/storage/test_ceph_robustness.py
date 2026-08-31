from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_output import AlarmListOutput
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_if_keywords import SystemHostInterfaceKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_reinstall_keywords import SystemHostReinstallKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.linux.ip.ip_keywords import IPKeywords
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


@mark.lab_has_standby_controller
def test_reinstall_standby_host():
    """
    Test to validate standby controller reinstallation and ceph health.

    Test Steps:
        - Check the hosts healthy
        - Check if controller-0 is the active controller
        - Get the active alarms
        - Lock standby controller
        - Reinstall standby controller
        - Unlock standby controller
        - Checking if there are any new active alarms
        - Checking storage backend health after reinstall.

    Args: None
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    standby_controller = system_host_list_keywords.get_standby_controller().get_host_name()
    system_host_reinstall_keywords = SystemHostReinstallKeywords(ssh_connection)
    ceph_status_keywords = CephStatusKeywords(ssh_connection)
    alarm_list_keywords = AlarmListKeywords(ssh_connection)
    health_keywords = HealthKeywords(ssh_connection)
    system_host_swact_keywords = SystemHostSwactKeywords(ssh_connection)

    get_logger().log_test_case_step("Check the hosts healthy")
    health_keywords.validate_hosts_health()

    get_logger().log_test_case_step("Check if controller-0 is the active controller")
    if standby_controller == "controller-0":
        system_host_swact_keywords.host_swact()
        standby_controller = system_host_list_keywords.get_standby_controller().get_host_name()

    get_logger().log_test_case_step("Get the active alarms")
    initial_alarm_list_ids = alarm_list_keywords.get_alarm_list().alarms_id()

    get_logger().log_test_case_step(f"Lock {standby_controller}")
    system_host_lock_keywords.lock_host(standby_controller)

    get_logger().log_test_case_step(f"Reinstall {standby_controller}")
    system_host_reinstall_keywords.reinstall_host(standby_controller)

    get_logger().log_test_case_step(f"Unlock {standby_controller}")
    system_host_lock_keywords.unlock_host(standby_controller)

    get_logger().log_test_case_step("Checking if there are any new active alarms")
    final_alarm_list_ids = alarm_list_keywords.get_alarm_list().alarms_id()
    validate_equals(AlarmListOutput.is_new_alarm_id_since(initial_alarm_list_ids, final_alarm_list_ids), False, "No new alarms should be present")

    get_logger().log_test_case_step("Checking storage backend health after reinstall.")
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)


@mark.p2
@mark.lab_has_standby_controller
def test_verify_ceph_recovery_after_one_mgmt_interface_is_down():
    """
    Verify ceph recovery after one mgmt interface is brought down on the standby controller.

    Test Steps:
        - Check the hosts are healthy
        - Get the initial active alarms
        - Get the mgmt interface of the standby controller
        - Bring down the mgmt interface on the standby controller
        - Verify ceph health is not okay while interface is down
        - Bring up the mgmt interface on the standby controller
        - Wait for ceph health to recover
        - Verify no new alarms are present after recovery

    Args: None
    """

    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(active_ssh_connection)
    standby_controller = system_host_list_keywords.get_standby_controller().get_host_name()
    standby_ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(standby_controller)
    health_keywords = HealthKeywords(active_ssh_connection)
    system_host_if_keywords = SystemHostInterfaceKeywords(active_ssh_connection)
    ceph_status_keywords = CephStatusKeywords(active_ssh_connection)
    ip_keywords = IPKeywords(standby_ssh_connection)

    get_logger().log_test_case_step("Check the hosts healthy")
    health_keywords.validate_hosts_health()

    get_logger().log_test_case_step("Get the initial active alarms")
    alarm_list_keywords = AlarmListKeywords(active_ssh_connection)
    initial_alarms = alarm_list_keywords.get_alarm_list().get_alarms()

    get_logger().log_test_case_step(f"Get the mgmt interface of standby controller {standby_controller}")
    interface_output = system_host_if_keywords.get_system_host_interface_list(standby_controller)
    mgmt_device_name = interface_output.get_interface_by_name("mgmt0").get_kernel_device_name()

    get_logger().log_test_case_step(f"Bring down mgmt interface {mgmt_device_name} on {standby_controller}")
    ip_keywords.set_ip_port_state(mgmt_device_name, "down")
    interface_state = ip_keywords.ip_link_show_interface(mgmt_device_name).get_interface().get_state()
    validate_equals(interface_state, "DOWN", f"mgmt interface {mgmt_device_name} should be DOWN")

    get_logger().log_test_case_step("Checking ceph health is not okay after mgmt interface is down")
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=False, timeout=300)

    get_logger().log_test_case_step(f"Bring up mgmt interface {mgmt_device_name} on {standby_controller}")
    ip_keywords.set_ip_port_state(mgmt_device_name, "up")
    interface_state = ip_keywords.ip_link_show_interface(mgmt_device_name).get_interface().get_state()
    validate_equals(interface_state, "UP", f"mgmt interface {mgmt_device_name} should be UP")

    get_logger().log_test_case_step("Waiting for ceph health to recover after mgmt interface is back up")
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True, timeout=1800)

    get_logger().log_test_case_step("Verifying no new alarms remain after recovery")
    alarm_list_keywords.set_timeout_in_seconds(1200)
    alarm_list_keywords.wait_for_all_alarms_cleared_excluding(excluded_alarms=initial_alarms, stable_checks=3, tolerate_query_failure=True)

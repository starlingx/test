from pytest import mark

from framework.validation.validation import validate_equals_with_retry
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.linux.kernel.kernel_keywords import KernelKeywords


@mark.p0
def test_auto_recover_after_service_affecting_failure(request):
    """
    Testcase to verify there are no alarms on the system
    Test Steps:
        - connect to active controller
        - run command fm alarm-list
        - verify that no alarms exist
        - Enter root on standby controller
        - run command echo c > /proc/sysrq-trigger
        - run command fm alarm-list
        - verify 200.004 alarm is triggered
        - wait for alarms to clear

    """
    ssh_connection_active_controller = LabConnectionKeywords().get_active_controller_ssh()
    ssh_connection_standby_controller = LabConnectionKeywords().get_standby_controller_ssh()

    standby_controller = SystemHostListKeywords(ssh_connection_active_controller).get_standby_controller()

    # Get the host name of the standby controller
    standby_controller_host_name = standby_controller.get_host_name()

    # Check if the system already has any alarm on it
    alarms_to_clear = AlarmListKeywords(ssh_connection_active_controller).alarm_list()
    assert not alarms_to_clear, "There are no alarms on the system"

    # Use trigger_kernal_crash keyword to crash standby controller
    KernelKeywords(ssh_connection_standby_controller).trigger_kernel_crash()

    def alarm_exists():
        alarms = AlarmListKeywords(ssh_connection_active_controller).alarm_list()
        alarms_list = [alarm_object for alarm_object in alarms if alarm_object.get_alarm_id() == "200.004"]
        return len(alarms_list) > 0

    validate_equals_with_retry(alarm_exists, True, "Validating that alarm 200.004 exists", timeout=120)

    # Check if the alarm 200.004 was triggered
    alarms = AlarmListKeywords(ssh_connection_active_controller).alarm_list()
    alarms_list = [alarm_object for alarm_object in alarms if alarm_object.get_alarm_id() == "200.004"]
    assert alarms_list, "Alarm 200.004 was found on the system"

    # Wait for standby controller reboot
    def wait_standby_controller_reboot():
        host_value = SystemHostListKeywords(ssh_connection_active_controller).get_system_host_list().get_host(standby_controller_host_name)

        return host_value.get_availability() == "available" and host_value.get_administrative() == "unlocked" and host_value.get_operational() == "enabled"

    validate_equals_with_retry(wait_standby_controller_reboot, True, "Waiting for standby controller reboot", timeout=800)

    # Check if the alarms clears after a period of times
    validate_equals_with_retry(alarm_exists, False, "Validating that alarm 200.004 exists", timeout=120)
    alarms_to_clear = AlarmListKeywords(ssh_connection_active_controller).alarm_list()
    alarms_list = [alarm_object for alarm_object in alarms_to_clear if alarm_object.get_alarm_id() == "200.004"]
    assert not alarms_list, "There are no more alarms on the system"

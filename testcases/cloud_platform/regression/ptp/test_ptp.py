import os
import time

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.ptp.ptp_readiness_keywords import PTPReadinessKeywords
from keywords.cloud_platform.system.ptp.ptp_setup_executor_keywords import PTPSetupExecutorKeywords
from keywords.cloud_platform.system.ptp.ptp_teardown_executor_keywords import PTPTeardownExecutorKeywords
from keywords.cloud_platform.system.ptp.ptp_verify_config_keywords import PTPVerifyConfigKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.ip.ip_keywords import IPKeywords
from keywords.linux.systemctl.systemctl_keywords import SystemCTLKeywords
from keywords.ptp.gnss_keywords import GnssKeywords
from keywords.ptp.phc_ctl_keywords import PhcCtlKeywords
from keywords.ptp.ptp4l.ptp_service_status_validator import PTPServiceStatusValidator
from keywords.ptp.setup.ptp_setup_reader import PTPSetupKeywords
from keywords.ptp.sma_keywords import SmaKeywords


@mark.p0
@mark.lab_has_standby_controller
def test_delete_and_add_all_ptp_configuration():
    """
    Delete and Add all PTP configurations
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    get_logger().log_info("Delete all PTP configuration")
    ptp_teardown_keywords = PTPTeardownExecutorKeywords(ssh_connection)
    ptp_teardown_keywords.delete_all_ptp_configurations()

    get_logger().log_info("Add all PTP configuration")
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_setup_template.json5")
    ptp_setup_keywords = PTPSetupExecutorKeywords(ssh_connection, ptp_setup_template_path)
    ptp_setup_keywords.add_all_ptp_configurations()


@mark.p0
@mark.lab_has_compute
@mark.lab_has_ptp_configuration_compute
def test_delete_and_add_all_ptp_configuration_for_compute():
    """
    Delete and Add all PTP configurations
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    get_logger().log_info("Delete all PTP configuration")
    ptp_teardown_keywords = PTPTeardownExecutorKeywords(ssh_connection)
    ptp_teardown_keywords.delete_all_ptp_configurations()

    get_logger().log_info("Add all PTP configuration")
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")
    ptp_setup_executor_keywords = PTPSetupExecutorKeywords(ssh_connection, ptp_setup_template_path)
    ptp_setup_executor_keywords.add_all_ptp_configurations()

    get_logger().log_info("Verify all PTP configuration")
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ptp_setup)
    ptp_verify_config_keywords.verify_all_ptp_configurations()


@mark.p1
@mark.lab_has_compute
@mark.lab_has_ptp_configuration_compute
def test_ptp_operation_interface_down_and_up():
    """
    Verify PTP operation and status change when an interface goes down and comes back up.

    Test Steps:
        - Bring down controller-0 NIC1.
        - Verify that alarm "100.119" appears on controller-1.
        - Wait for the PMC port states on controller-1.
        - Verify the PMC data on controller-1.
        - Bring up controller-0 NIC1.
        - Verify that alarm "100.119" clears on controller-1.
        - Wait for PMC port states on controller-1.
        - Verify the PMC data on controller-1.
        - Bring down controller-0 NIC2.
        - Verify that alarm "100.119" appears on controller-1.
        - Wait for PMC port states on controller-1.
        - Verify the PMC data on controller-1.
        - Bring up controller-0 NIC2.
        - Verify that alarm "100.119" clears on controller-1.
        - Wait for PMC port states on controller-1.
        - Verify the PMC data on controller-1.
        - Download the "/var/log/user.log" file from the active controller.

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_configuration_expectation_compute.json5.

    Notes:
        - In this scenario, controller-0 NIC1 (configured with ptp1) is powered off.
          Initially, ctrl0 NIC1 is in MASTER state, and ctrl1 NIC1 is in SLAVE state.
          After powering off ctrl0 NIC1, ctrl1 NIC1 transitions to MASTER independently,
          rather than remaining dependent on the peer controller.

        - In this scenario, controller-0 NIC2 (configured with ptp3) is powered off.
          Initially, ctrl0 NIC2 is in MASTER state, and ctrl1 NIC2 is in SLAVE state.
          After powering off ctrl0 NIC2, ctrl1 NIC2 transitions to MASTER independently,
          rather than remaining dependent on the peer controller.

        GM Clock Class Examples:
        - 6–7    → Primary reference (e.g., GNSS locked)
        - 13–14  → Grandmaster in holdover
        - 52–53  → Slave-only clocks
        - 165    → Not synchronized / GNSS invalid
        - 248    → Not used for synchronization

        Accuracy Examples:
        - 0x20 → ±25 ns (GNSS locked)
        - 0x21 → ±100 ns
        - 0x22 → ±250 ns
        - 0xFE → Unknown (not traceable)
        - 0xFF → Reserved / Invalid

        Offset Scaled Log Variance Examples:
        - 0xFFFF → Unknown or unspecified
        - e.g., 0x0100 → Valid stability/variance info
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    ip_keywords = IPKeywords(ssh_connection)

    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")

    get_logger().log_info("Verify PTP operation and the corresponding status change when an interface goes down")

    ctrl0_nic1_iface_down_ptp_selection = [("ptp1", "controller-1", ["ptp1if1"])]

    ctrl0_nic1_iface_down_exp_dict = """{
        "ptp4l": [
            {
                "name": "ptp1",
                "controller-1": {
                    "parent_data_set": {
                        "gm_clock_class": 165, // The GM clock loses its connection to the Primary Reference Time Clock
                        "gm_clock_accuracy": "0xfe", // Unknown
                        "gm_offset_scaled_log_variance": "0xffff" // Unknown stability
                    },
                    "time_properties_data_set": {
                        "current_utc_offset": 37,
                        "current_utc_offset_valid": 0, // The offset is not currently valid
                        "time_traceable": 0, // Time is not traceable to UTC
                        "frequency_traceable": 0 //  Frequency is not traceable to a known source.
                    },
                    "grandmaster_settings": {
                        "clock_class": 165, // The GM clock loses its connection to the Primary Reference Time Clock
                        "clock_accuracy": "0xfe", // Unknown
                        "offset_scaled_log_variance": "0xffff", // Unknown or unspecified stability
                        "time_traceable": 0, // Time is not traceable — the clock may be in holdover, unsynchronized, or degraded.
                        "frequency_traceable": 0, // Frequency is not traceable — may be in holdover or unsynchronized
                        "time_source": "0xa0",
                        "current_utc_offset_valid": 0 // UTC offset is not valid
                    },
                    "port_data_set": [
                        {
                            "interface": "{{ controller_1.nic1.nic_connection.interface }}",
                            "port_state": "MASTER", // A master port will send PTP sync messages to other device
                            // its own master instead of using the remote
                            "parent_port_identity": {
                                "name": "ptp1",
                                "hostname": "controller-1",
                                "interface": "{{ controller_1.nic1.nic_connection.interface }}"
                            }
                        },
                        {
                            "interface": "{{ controller_1.nic1.conn_to_proxmox }}",
                            "port_state": "MASTER" // A master port will send PTP sync messages to other device
                        }
                    ]
                }
            }
        ]
    }"""

    ctrl0_nic1_iface_down_ptp_setup = ptp_setup_keywords.filter_and_render_ptp_config(ptp_setup_template_path, ctrl0_nic1_iface_down_ptp_selection, ctrl0_nic1_iface_down_exp_dict)

    get_logger().log_info("Interface down Controller-0 NIC1.")
    interfaces = ctrl0_nic1_iface_down_ptp_setup.get_ptp4l_setup("ptp1").get_ptp_interface("ptp1if1").get_interfaces_for_hostname("controller-0")
    if not interfaces:
        raise Exception("No interfaces found for controller-0 NIC1")
    ctrl0_nic1_interface = interfaces[0]
    ip_keywords.set_ip_port_state(ctrl0_nic1_interface, "down")

    get_logger().log_info(f"Waiting for 100.119 alarm to appear after interface {ctrl0_nic1_interface} goes down.")
    not_locked_alarm_obj = AlarmListObject()
    not_locked_alarm_obj.set_alarm_id("100.119")
    not_locked_alarm_obj.set_reason_text("controller-1 is not locked to remote PTP Grand Master")
    not_locked_alarm_obj.set_entity_id("host=controller-1.instance=ptp1.ptp=no-lock")
    AlarmListKeywords(ssh_connection).wait_for_alarms_to_appear([not_locked_alarm_obj])

    get_logger().log_info(f"Waiting for PMC port states after interface {ctrl0_nic1_interface} goes down.")
    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-1"))
    ptp_readiness_keywords.wait_for_port_state_appear_in_port_data_set("ptp1", ["MASTER", "MASTER"])

    get_logger().log_info(f"Verifying PMC data after interface {ctrl0_nic1_interface} goes down.")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic1_iface_down_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()

    ctrl0_nic1_iface_up_ptp_selection = [("ptp1", "controller-0", []), ("ptp1", "controller-1", [])]
    ctrl0_nic1_iface_up_ptp_setup = ptp_setup_keywords.filter_and_render_ptp_config(ptp_setup_template_path, ctrl0_nic1_iface_up_ptp_selection)

    get_logger().log_info("Interface up Controller-0 NIC1.")
    ip_keywords.set_ip_port_state(ctrl0_nic1_interface, "up")

    get_logger().log_info(f"Waiting for alarm 100.119 to clear after interface {ctrl0_nic1_interface} comes up.")
    AlarmListKeywords(ssh_connection).wait_for_alarms_cleared([not_locked_alarm_obj])

    get_logger().log_info(f"Waiting for PMC port states after interface {ctrl0_nic1_interface} comes up.")
    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-1"))
    ptp_readiness_keywords.wait_for_port_state_appear_in_port_data_set("ptp1", ["SLAVE", "MASTER"])

    get_logger().log_info(f"Verifying PMC data after interface {ctrl0_nic1_interface} comes up.")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic1_iface_up_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()

    ctrl0_nic2_iface_down_ptp_selection = [("ptp4", "controller-1", [])]
    ctrl0_nic2_iface_down_exp_dict = """{
        "ptp4l": [
            {
                "name": "ptp4",
                "controller-1" : {
                    "parent_data_set" : {
                        "gm_clock_class" : 165, // The GM clock loses its connection to the Primary Reference Time Clock
                        "gm_clock_accuracy" : "0xfe", // Unknown
                        "gm_offset_scaled_log_variance" : "0xffff" // Unknown stability
                    },
                    "time_properties_data_set": {
                        "current_utc_offset": 37,
                        "current_utc_offset_valid": 0, // The offset is not currently valid
                        "time_traceable": 0, // Time is not traceable — the clock may be in holdover, unsynchronized, or degraded.
                        "frequency_traceable": 0 // Frequency is not traceable
                    },
                    "grandmaster_settings": {
                        "clock_class": 165, // The GM clock loses its connection to the Primary Reference Time Clock
                        "clock_accuracy": "0xfe", // Unknown
                        "offset_scaled_log_variance": "0xffff", // Unknown or unspecified stability
                        "time_traceable": 0, // Time is not traceable — the clock may be in holdover, unsynchronized, or degraded.
                        "frequency_traceable": 0, // Frequency is not traceable — may be in holdover or unsynchronized
                        "time_source": "0xa0",
                        "current_utc_offset_valid": 0 // The offset is not currently valid
                    },
                    "port_data_set": [
                        {
                            "interface": "{{ controller_1.nic2.nic_connection.interface  }}",
                            "port_state": "MASTER", // A master port will send PTP sync messages to other device
                            // becomes its own master instead of using the remote.
                            "parent_port_identity" : {
                                "name": "ptp4",
                                "hostname":"controller-1",
                                "interface": "{{ controller_1.nic2.nic_connection.interface }}"
                            },
                        },
                        {
                            "interface": "{{ controller_1.nic2.conn_to_proxmox }}",
                            "port_state": "MASTER" // A master port will send PTP sync messages to other device
                        }
                    ]
                }
            }
        ]
    }
    """
    ctrl0_nic2_iface_down_ptp_setup = ptp_setup_keywords.filter_and_render_ptp_config(ptp_setup_template_path, ctrl0_nic2_iface_down_ptp_selection, ctrl0_nic2_iface_down_exp_dict)

    ctrl0_nic2_iface_up_ptp_selection = [("ptp3", "controller-0", ["ptp3if1"]), ("ptp4", "controller-1", [])]
    ctrl0_nic2_iface_up_exp_dict_overrides = {"ptp4l": [{"name": "ptp4", "controller-1": {"grandmaster_settings": {"clock_class": 165}}}]}
    ctrl0_nic2_iface_up_ptp_setup = ptp_setup_keywords.filter_and_render_ptp_config(ptp_setup_template_path, ctrl0_nic2_iface_up_ptp_selection, expected_dict_overrides=ctrl0_nic2_iface_up_exp_dict_overrides)

    get_logger().log_info("Interface down Controller-0 NIC2.")
    interfaces = ctrl0_nic2_iface_up_ptp_setup.get_ptp4l_setup("ptp3").get_ptp_interface("ptp3if1").get_interfaces_for_hostname("controller-0")
    if not interfaces:
        raise Exception("No interfaces found for controller-0 NIC2")
    ctrl0_nic2_interface = interfaces[0]
    ip_keywords.set_ip_port_state(ctrl0_nic2_interface, "down")

    get_logger().log_info(f"Waiting for 100.119 alarm to appear after interface {ctrl0_nic2_interface} goes down.")
    not_locked_alarm_obj = AlarmListObject()
    not_locked_alarm_obj.set_alarm_id("100.119")
    not_locked_alarm_obj.set_reason_text("controller-1 is not locked to remote PTP Grand Master")
    not_locked_alarm_obj.set_entity_id("host=controller-1.instance=ptp4.ptp=no-lock")
    AlarmListKeywords(ssh_connection).wait_for_alarms_to_appear([not_locked_alarm_obj])

    get_logger().log_info(f"Waiting for PMC port states after interface {ctrl0_nic2_interface} goes down.")
    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-1"))
    ptp_readiness_keywords.wait_for_port_state_appear_in_port_data_set("ptp4", ["MASTER", "MASTER"])

    get_logger().log_info(f"Verifying PMC data after interface {ctrl0_nic2_interface} goes down.")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic2_iface_down_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()

    get_logger().log_info("Interface up Controller-0 NIC2.")
    ip_keywords.set_ip_port_state(ctrl0_nic2_interface, "up")

    get_logger().log_info(f"Waiting for alarm 100.119 to clear after interface {ctrl0_nic2_interface} comes up.")
    AlarmListKeywords(ssh_connection).wait_for_alarms_cleared([not_locked_alarm_obj])

    get_logger().log_info(f"Waiting for PMC port states after interface {ctrl0_nic2_interface} comes up.")
    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-1"))
    ptp_readiness_keywords.wait_for_port_state_appear_in_port_data_set("ptp4", ["SLAVE", "MASTER"])

    get_logger().log_info(f"Verifying PMC data after interface {ctrl0_nic2_interface} comes up.")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic2_iface_up_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()

    get_logger().log_info("Downloading /var/log/user.log for reference.")
    local_file_path = os.path.join(get_logger().get_test_case_log_dir(), "user.log")
    FileKeywords(ssh_connection).download_file("/var/log/user.log", local_file_path)


@mark.p1
@mark.lab_has_compute
@mark.lab_has_ptp_configuration_compute
def test_ptp_operation_sma_disabled_and_enable():
    """
    Verify PTP operation and status changes when the SMA is disabled and then re-enabled.

    Test Steps:
        - Disable SMA1 on Controller-0 NIC2.
        - Wait for 100.119 to alarms to appear.
        - Wait for clock class to appear in grandmaster settings.
        - Verify PTP PMC values.
        - Enable SMA1 on Controller-0 NIC2.
        - Wait for 100.119 to alarm to clear.
        - Wait for clock class to appear in grandmaster settings.
        - Verify PTP PMC values.

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_configuration_expectation_compute.json5.
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")

    get_logger().log_info("Verifying PTP operation and corresponding status changes when SMA is disabled.")

    ctrl0_nic2_sma1_disable_ptp_selection = [("ptp3", "controller-0", []), ("ptp4", "controller-1", [])]
    ctrl0_nic2_sma1_disable_exp_dict = """{
        "ptp4l": [
            {
                "name": "ptp3",
                "controller-0": {
                        "parent_data_set" : {
                        "gm_clock_class" : 7, // clock is a valid time reference, but not the highest possible quality
                        "gm_clock_accuracy" : "0xfe", // Unknown
                        "gm_offset_scaled_log_variance" : "0xffff" // Unknown stability
                    },
                    "time_properties_data_set": {
                        "current_utc_offset": 37,
                        "current_utc_offset_valid": 0, // The offset is not currently valid
                        "time_traceable": 1, // clock’s time can be traced back to a valid time reference
                        "frequency_traceable": 1 // Frequency of the clock is traceable to a stable
                    },
                    "grandmaster_settings": {
                        "clock_class": 7,
                        "clock_accuracy": "0xfe", // Unknown
                        "offset_scaled_log_variance": "0xffff", // Unknown or unspecified stability
                        "time_traceable": 1, // clock’s time can be traced back to a valid time reference
                        "frequency_traceable": 1, // Frequency of the clock is traceable to a stable
                        "time_source": "0xa0",
                        "current_utc_offset_valid": 0 // The offset is not currently valid
                    },
                    "port_data_set": [
                        {
                            "interface": "{{ controller_0.nic2.nic_connection.interface }}", // ctrl0 NIC2 is MASTER and ctr1 NIC2 is SLAVE
                            "port_state": "MASTER" // A master port will send PTP sync messages to other device
                        },
                        {
                            "interface": "{{ controller_0.nic2.conn_to_proxmox }}",
                            "port_state": "MASTER" // A master port will send PTP sync messages to other device
                        }
                    ]
                }
            },
            {
                "name": "ptp4",
                "controller-1": {
                        "parent_data_set" : {
                        "gm_clock_class" : 7, // clock is a valid time reference, but not the highest possible quality
                        "gm_clock_accuracy" : "0xfe", // Unknown
                        "gm_offset_scaled_log_variance" : "0xffff" // Unknown stability
                    },
                    "time_properties_data_set": {
                        "current_utc_offset": 37,
                        "current_utc_offset_valid": 0, // The offset is not currently valid
                        "time_traceable": 1, // clock’s time can be traced back to a valid time reference
                        "frequency_traceable": 1 // Frequency of the clock is traceable to a stable
                    },
                    "grandmaster_settings": {
                        "clock_class": [165, 248], // The GM clock loses its connection to the Primary Reference Time Clock
                        "clock_accuracy": "0xfe", // Unknown
                        "offset_scaled_log_variance": "0xffff", // Unknown or unspecified stability
                        "time_traceable": 0, // Time is not traceable — the clock may be in holdover, unsynchronized, or degraded.
                        "frequency_traceable": 0, // Frequency is not traceable — may be in holdover or unsynchronized
                        "time_source": "0xa0",
                        "current_utc_offset_valid": 0 // The offset is not currently valid
                    },
                    "port_data_set": [
                        {
                            "interface": "{{ controller_1.nic2.nic_connection.interface }}",
                            "port_state": "SLAVE", // The slave port is synchronizing to the master port's time
                            "parent_port_identity": {
                                "name": "ptp3",
                                "hostname": "controller-0",
                                "interface": "{{ controller_0.nic2.nic_connection.interface }}" // ctrl-0 NIC2 is Master and ctrl-1 NIC2 is slave
                            }
                        },
                        {
                            "interface": "{{ controller_1.nic2.conn_to_proxmox }}",
                            "port_state": "MASTER" // A master port will send PTP sync messages to other device
                        }
                    ]
                }
            }
        ]
    }
    """
    ctrl0_nic2_sma1_disable_exp_ptp_setup = ptp_setup_keywords.filter_and_render_ptp_config(ptp_setup_template_path, ctrl0_nic2_sma1_disable_ptp_selection, ctrl0_nic2_sma1_disable_exp_dict)

    get_logger().log_info("Disabled SMA1 for Controller-0 NIC2.")
    sma_keywords = SmaKeywords(ssh_connection)
    sma_keywords.disable_sma("controller-0", "nic2")

    get_logger().log_info("Waiting for alarm 100.119 to appear after SMA is disabled.")
    ptp_config = ConfigurationManager.get_ptp_config()
    interface = ptp_config.get_host("controller_0").get_nic("nic2").get_base_port()

    not_locked_alarm_obj = AlarmListObject()
    not_locked_alarm_obj.set_alarm_id("100.119")
    not_locked_alarm_obj.set_reason_text("controller-0 is not locked to remote PTP Grand Master")
    not_locked_alarm_obj.set_entity_id("host=controller-0.instance=ptp3.ptp=no-lock")

    signal_loss_alarm_obj = AlarmListObject()
    signal_loss_alarm_obj.set_alarm_id("100.119")
    signal_loss_alarm_obj.set_reason_text("controller-0 1PPS signal loss state: holdover")
    signal_loss_alarm_obj.set_entity_id(f"host=controller-0.interface={interface}.ptp=1PPS-signal-loss")

    AlarmListKeywords(ssh_connection).wait_for_alarms_to_appear([not_locked_alarm_obj, signal_loss_alarm_obj])

    get_logger().log_info("Waiting for clock class after SMA1 is disabled")
    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-0"))
    ptp_readiness_keywords.wait_for_clock_class_appear_in_grandmaster_settings_np("ptp3", 7)

    get_logger().log_info("Verifying PMC data after SMA1 is disabled")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic2_sma1_disable_exp_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()

    get_logger().log_info("Verifying PTP operation and corresponding status changes when SMA is enabled.")

    ctrl0_nic2_sma1_enable_ptp_selection = [("ptp3", "controller-0", []), ("ptp4", "controller-1", [])]
    ctrl0_nic2_sma1_enable_exp_ptp_setup = ptp_setup_keywords.filter_and_render_ptp_config(ptp_setup_template_path, ctrl0_nic2_sma1_enable_ptp_selection)

    sma_keywords.enable_sma("controller-0", "nic2")
    get_logger().log_info("Waiting for 100.119 alarm to clear after SMA1 is enabled")
    alarm_list_object = AlarmListObject()
    alarm_list_object.set_alarm_id("100.119")
    AlarmListKeywords(ssh_connection).wait_for_alarms_cleared([alarm_list_object])

    get_logger().log_info("Waiting for clock class after SMA1 is enabled")
    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-0"))
    ptp_readiness_keywords.wait_for_clock_class_appear_in_grandmaster_settings_np("ptp3", 6)

    get_logger().log_info("Verifying PMC data after SMA1 is enabled")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic2_sma1_enable_exp_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()


@mark.p1
@mark.lab_has_compute
@mark.lab_has_ptp_configuration_compute
def test_ptp_operation_gnss_off_and_on():
    """
    Verify PTP behavior when GNSS is powered off and then back on.

    Test Steps:
        - Powers off the GNSS input for Controller-0 NIC1.
        - Verifies the expected PTP alarms and clock class degradation.
        - Verifies expected PTP PMC configuration when GNSS is off.
        - Powers the GNSS back on.
        - Confirms the alarms are cleared and clock class is restored.
        - Verifies expected PTP PMC configuration when GNSS is back on.

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_configuration_expectation_compute.json5.

    Notes:
        When analyzing test results, pay attention to:
        1. **Clock Class Transitions**:
        - 6 → 7: Brief GNSS signal loss, entering holdover
        - 6 → 248: Complete GNSS signal loss, uncalibrated
        - 248 → 6: GNSS signal recovery

        2. **Port State Changes**:
        - MASTER → SLAVE: Loss of reference or better clock available
        - SLAVE → MASTER: Becoming best available clock
        - Any state → FAULTY: Hardware or connectivity issue

        3. **Flag Value Changes**:
        - time_traceable 1 → 0: Loss of traceable time reference
        - frequency_traceable 1 → 0: Loss of traceable frequency reference
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")

    get_logger().log_info("Verifying PTP operation and status when GNSS is turned off...")

    selected_instances = [("ptp1", "controller-0", []), ("ptp1", "controller-1", []), ("ptp3", "controller-0", []), ("ptp4", "controller-1", [])]

    # Flag Values:
    #   time_traceable=1: Time is traceable to primary reference (GNSS/UTC)
    #   time_traceable=0: Time is not traceable to primary reference
    #   frequency_traceable=1: Frequency is traceable to primary reference
    #   frequency_traceable=0: Frequency is not traceable to primary reference
    #   current_utc_offset_valid=0: UTC offset cannot be trusted without GNSS
    #
    # When GNSS signal is lost:
    #   - Controller-0 changes from clock class 6 to 7 (brief loss) or 248 (complete loss)
    #   - Port roles may reverse with the best available clock becoming MASTER
    #   - External clients continue receiving time from both controllers
    #
    # Role Changes During GNSS Signal Loss
    # When GNSS signal is lost, the following changes occur in the PTP network:

    # 1. Controller-0 with GNSS:
    # - Clock class changes from 6 (GNSS-synchronized) to 248 (uncalibrated)
    # - Port state changes from MASTER to SLAVE
    # - time_traceable and frequency_traceable flags change from 1 to 0

    # 2. Controller-1 without direct GNSS:
    # - Takes over as best available time source with clock class 165
    # - Port state changes from SLAVE to MASTER
    # - Becomes the new reference for Controller-0

    # 3. External Clients:
    # - Continue receiving time from both controllers
    # - Service availability is maintained despite degraded accuracy

    # This role reversal ensures that the best available clock is always used as the reference,
    # maintaining time synchronization even when the primary reference is lost.
    ctrl0_nic1_gnss_disable_exp_dict = """{
        "ptp4l": [
            {
                "name": "ptp1",
                "controller-0": {
                    "parent_data_set": {
                        "gm_clock_class": 7, // GM is in holdover or degraded mode due to GNSS loss
                        "gm_clock_accuracy": "0xfe", // Accuracy unknown due to GNSS signal loss
                        "gm_offset_scaled_log_variance": "0xffff" // Clock stability unknown
                    },
                    "time_properties_data_set": {
                        "current_utc_offset": 37, // Standard UTC offset (can be static)
                        "current_utc_offset_valid": 0, // UTC offset is not currently valid
                        "time_traceable": 1, // Time is not traceable to a valid source
                        "frequency_traceable": 1 // Frequency is not traceable to a valid reference
                    },
                    "grandmaster_settings": {
                        "clock_class": 7, // Indicates GNSS signal is lost (free-running or degraded)
                        "clock_accuracy": "0xfe", // Accuracy is unknown
                        "offset_scaled_log_variance": "0xffff", // Clock variance is unknown
                        "time_traceable": 1, // Time not traceable
                        "frequency_traceable": 1, // Frequency not traceable
                        "time_source": "0xa0", // Time source originally GNSS (0xA0)
                        "current_utc_offset_valid": 0 // UTC offset invalid due to signal loss
                    },
                    "port_data_set": [
                        {
                            "interface": "{{ controller_0.nic1.nic_connection.interface }}",
                            "port_state": "MASTER",
                        },
                        {
                            "interface": "{{ controller_0.nic1.conn_to_proxmox }}",
                            "port_state": "MASTER"  // Continues to send time sync to Proxmox as master
                        }
                    ]
                },
                "controller-1": {
                    "parent_data_set": {
                        "gm_clock_class": 7,
                        "gm_clock_accuracy": "0xfe",  // Unknown accuracy
                        "gm_offset_scaled_log_variance": "0xffff"  // Unknown clock variance
                    },
                    "time_properties_data_set": {
                        "current_utc_offset": 37,
                        "current_utc_offset_valid": 0,
                        "time_traceable": 1,
                        "frequency_traceable": 1
                    },
                    "grandmaster_settings": {
                        "clock_class": [165,248],
                        "clock_accuracy": "0xfe",
                        "offset_scaled_log_variance": "0xffff",
                        "time_traceable": 0,
                        "frequency_traceable": 0,
                        "time_source": "0xa0",
                        "current_utc_offset_valid": 0
                    },
                    "port_data_set": [
                        {
                            "interface": "{{ controller_1.nic1.nic_connection.interface }}",
                            "port_state": "SLAVE",
                            "parent_port_identity" : {
                                "name": "ptp1",
                                "hostname":"controller-0",
                                "interface": "{{ controller_0.nic1.nic_connection.interface }}" // ctrl-0 NIC1 is Master and ctrl-1 NIC1 is slave
                            },
                        },
                        {
                            "interface": "{{ controller_1.nic1.conn_to_proxmox }}",
                            "port_state": "MASTER"  // Continues acting as master toward external clients
                        }
                    ]
                }
            },
            {
                "name": "ptp3",
                "controller-0": {
                    "parent_data_set": {
                        "gm_clock_class": 7, // Lost GNSS, degraded state
                        "gm_clock_accuracy": "0xfe",
                        "gm_offset_scaled_log_variance": "0xffff"
                    },
                    "time_properties_data_set": {
                        "current_utc_offset": 37,
                        "current_utc_offset_valid": 0,
                        "time_traceable": 1,
                        "frequency_traceable": 1
                    },
                    "grandmaster_settings": {
                        "clock_class": 7, // Lost GNSS, degraded state
                        "clock_accuracy": "0xfe",
                        "offset_scaled_log_variance": "0xffff",
                        "time_traceable": 1,
                        "frequency_traceable": 1,
                        "time_source": "0xa0",
                        "current_utc_offset_valid": 0
                    },
                    "port_data_set": [
                        {
                            "interface": "{{ controller_0.nic2.nic_connection.interface }}",
                            "port_state": "MASTER",
                        },
                        {
                            "interface": "{{ controller_0.nic2.conn_to_proxmox }}",
                            "port_state": "MASTER" // Still acting as master to Proxmox
                        }
                    ]
                }
            },
            {
                "name": "ptp4",
                "controller-1": {
                    "parent_data_set": {
                        "gm_clock_class": 7,
                        "gm_clock_accuracy": "0xfe",
                        "gm_offset_scaled_log_variance": "0xffff"
                    },
                    "time_properties_data_set": {
                        "current_utc_offset": 37,
                        "current_utc_offset_valid": 0,
                        "time_traceable": 1,
                        "frequency_traceable": 1
                    },
                    "grandmaster_settings": {
                        "clock_class": [165,248],
                        "clock_accuracy": "0xfe",
                        "offset_scaled_log_variance": "0xffff",
                        "time_traceable": 0,
                        "frequency_traceable": 0,
                        "time_source": "0xa0",
                        "current_utc_offset_valid": 0
                    },
                    "port_data_set": [
                        {
                            "interface": "{{ controller_1.nic2.nic_connection.interface }}",
                            "port_state": "SLAVE", // Acting as GM for NIC2
                            "parent_port_identity" : {
                                "name": "ptp3",
                                "hostname":"controller-0",
                                "interface": "{{ controller_0.nic2.nic_connection.interface }}" // ctrl-0 NIC2 is Master and ctrl-1 NIC2 is slave
                            },
                        },
                        {
                            "interface": "{{ controller_1.nic2.conn_to_proxmox }}",
                            "port_state": "MASTER"  // Acts as GM for external Proxmox
                        }
                    ]
                }
            }
        ]
    }"""

    ctrl0_nic1_gnss_disable_exp_ptp_setup = ptp_setup_keywords.filter_and_render_ptp_config(ptp_setup_template_path, selected_instances, ctrl0_nic1_gnss_disable_exp_dict)

    get_logger().log_info("Turning off GNSS for Controller-0 NIC1.")
    gnss_keywords = GnssKeywords()
    gnss_keywords.gnss_power_off("controller-0", "nic1")

    get_logger().log_info("Waiting for alarm 100.119 to appear due to GNSS off.")
    ptp_config = ConfigurationManager.get_ptp_config()
    interface = ptp_config.get_host("controller_0").get_nic("nic1").get_base_port()

    ptp1_not_locked_alarm_obj = AlarmListObject()
    ptp1_not_locked_alarm_obj.set_alarm_id("100.119")
    ptp1_not_locked_alarm_obj.set_reason_text("controller-0 is not locked to remote PTP Grand Master")
    ptp1_not_locked_alarm_obj.set_entity_id("host=controller-0.instance=ptp1.ptp=no-lock")

    pps_signal_loss_alarm_obj = AlarmListObject()
    pps_signal_loss_alarm_obj.set_alarm_id("100.119")
    pps_signal_loss_alarm_obj.set_reason_text("controller-0 1PPS signal loss state: LockStatus.HOLDOVER")
    pps_signal_loss_alarm_obj.set_entity_id(f"host=controller-0.interface={interface}.ptp=1PPS-signal-loss")

    gnss_signal_loss_alarm_obj = AlarmListObject()
    gnss_signal_loss_alarm_obj.set_alarm_id("100.119")
    gnss_signal_loss_alarm_obj.set_reason_text("controller-0 GNSS signal loss state: LockStatus.HOLDOVER")
    gnss_signal_loss_alarm_obj.set_entity_id(f"host=controller-0.interface={interface}.ptp=GNSS-signal-loss")

    AlarmListKeywords(ssh_connection).wait_for_alarms_to_appear([ptp1_not_locked_alarm_obj, pps_signal_loss_alarm_obj, gnss_signal_loss_alarm_obj])

    get_logger().log_info("Verifying clock class degradation after GNSS is off.")
    # The clock is in "Holdover" or "Degraded" mode
    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-0"))
    ptp_readiness_keywords.wait_for_clock_class_appear_in_grandmaster_settings_np("ptp1", 7)
    ptp_readiness_keywords.wait_for_clock_class_appear_in_grandmaster_settings_np("ptp3", 7)
    # GNSS loss
    ptp_readiness_keywords.wait_for_gm_clock_class_appear_in_parent_data_set("ptp1", 7)

    get_logger().log_info("Verifying PMC configuration after GNSS is off.")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic1_gnss_disable_exp_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()

    get_logger().log_info("Turning GNSS back on for Controller-0 NIC1...")
    gnss_keywords.gnss_power_on("controller-0", "nic1")

    get_logger().log_info("Waiting for alarm 100.119 to clear after GNSS is back on.")
    AlarmListKeywords(ssh_connection).wait_for_alarms_cleared([ptp1_not_locked_alarm_obj, pps_signal_loss_alarm_obj, gnss_signal_loss_alarm_obj])

    get_logger().log_info("Verifying clock class restoration after GNSS is on.")
    ptp_readiness_keywords.wait_for_clock_class_appear_in_grandmaster_settings_np("ptp1", 6)
    ptp_readiness_keywords.wait_for_clock_class_appear_in_grandmaster_settings_np("ptp3", 6)
    ptp_readiness_keywords.wait_for_gm_clock_class_appear_in_parent_data_set("ptp1", 6)

    get_logger().log_info("Verifying PMC configuration after GNSS is restored.")
    ctrl0_nic1_gnss_enable_exp_ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic1_gnss_enable_exp_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()


@mark.p1
@mark.lab_has_compute
@mark.lab_has_ptp_configuration_compute
def test_ptp_operation_phc_ctl_time_change():
    """
    Verify PTP behavior when the PHC (Precision Hardware Clock) is adjusted manually using `phc_ctl`
    and then returned to normal.

    Test Steps:
        - Identify controller-0 NIC1 interface.
        - Start phc_ctl loop on controller-0 NIC1 and verify that out-of-tolerance alarms (ID 100.119) are triggered.
        - Stop the adjustment and wait for alarms to clear.
        - Identify controller-1 NIC2 interface.
        - Start phc_ctl loop on controller-1 NIC2 and verify that out-of-tolerance alarms (ID 100.119) are triggered.
        - Stop the adjustment and wait for alarms to clear.

    Preconditions:
        - The system must have a valid PTP configuration as defined in `ptp_configuration_expectation_compute.json5`.
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)

    get_logger().log_info("Verifying PTP operation with phc_ctl time change on controller-0 NIC1...")
    interfaces = ptp_setup.get_ptp4l_setup("ptp1").get_ptp_interface("ptp1if1").get_interfaces_for_hostname("controller-0")
    if not interfaces:
        raise Exception("No interfaces found for controller-0 NIC1")
    ctrl0_nic1_interface = interfaces[0]

    ctrl0_ptp3_oot_alarm_obj = AlarmListObject()
    ctrl0_ptp3_oot_alarm_obj.set_alarm_id("100.119")
    ctrl0_ptp3_oot_alarm_obj.set_reason_text(r"controller-0 Precision Time Protocol \(PTP\) clocking is out of tolerance by (\d+\.\d+) (milli|micro)secs")
    ctrl0_ptp3_oot_alarm_obj.set_entity_id("host=controller-0.instance=ptp3.ptp=out-of-tolerance")

    ctrl0_ptp1_oot_alarm_obj = AlarmListObject()
    ctrl0_ptp1_oot_alarm_obj.set_alarm_id("100.119")
    ctrl0_ptp1_oot_alarm_obj.set_reason_text(r"controller-0 Precision Time Protocol \(PTP\) clocking is out of tolerance by ((\d+\.\d+) (milli|micro)secs|more than \d+ seconds)")
    ctrl0_ptp1_oot_alarm_obj.set_entity_id("host=controller-0.instance=ptp1.ptp=out-of-tolerance")

    ctrl1_ptp1_oot_alarm_obj = AlarmListObject()
    ctrl1_ptp1_oot_alarm_obj.set_alarm_id("100.119")
    ctrl1_ptp1_oot_alarm_obj.set_reason_text(r"controller-1 Precision Time Protocol \(PTP\) clocking is out of tolerance by ((\d+\.\d+) (milli|micro)secs|more than \d+ seconds)")
    ctrl1_ptp1_oot_alarm_obj.set_entity_id("host=controller-1.instance=ptp1.ptp=out-of-tolerance")

    phc_ctl_keywords = PhcCtlKeywords(lab_connect_keywords.get_ssh_for_hostname("controller-0"))
    phc_ctl_keywords.wait_for_phc_ctl_adjustment_alarm(ctrl0_nic1_interface, [ctrl0_ptp3_oot_alarm_obj, ctrl0_ptp1_oot_alarm_obj, ctrl1_ptp1_oot_alarm_obj])

    get_logger().log_info("Waiting for alarm 100.119 to clear after stopping phc_ctl on controller-0...")
    AlarmListKeywords(ssh_connection).wait_for_alarms_cleared([ctrl0_ptp3_oot_alarm_obj, ctrl0_ptp1_oot_alarm_obj, ctrl1_ptp1_oot_alarm_obj])

    get_logger().log_info("Verifying PTP operation with phc_ctl time change on controller-1 NIC2...")
    interfaces = ptp_setup.get_ptp4l_setup("ptp4").get_ptp_interface("ptp4if1").get_interfaces_for_hostname("controller-1")
    if not interfaces:
        raise Exception("No interfaces found for controller-1 NIC2")
    ctrl1_nic2_interface = interfaces[0]

    ctrl1_ptp4_oot_alarm_obj = AlarmListObject()
    ctrl1_ptp4_oot_alarm_obj.set_alarm_id("100.119")
    ctrl1_ptp4_oot_alarm_obj.set_reason_text(r"controller-1 Precision Time Protocol \(PTP\) clocking is out of tolerance by ((\d+\.\d+) (milli|micro)secs|more than \d+ seconds)")
    ctrl1_ptp4_oot_alarm_obj.set_entity_id("host=controller-1.instance=ptp4.ptp=out-of-tolerance")

    phc_ctl_keywords = PhcCtlKeywords(lab_connect_keywords.get_ssh_for_hostname("controller-1"))
    phc_ctl_keywords.wait_for_phc_ctl_adjustment_alarm(ctrl1_nic2_interface, [ctrl1_ptp1_oot_alarm_obj, ctrl1_ptp4_oot_alarm_obj])

    get_logger().log_info("Waiting for alarm 100.119 to clear after stopping phc_ctl on controller-1...")
    AlarmListKeywords(ssh_connection).wait_for_alarms_cleared([ctrl1_ptp1_oot_alarm_obj, ctrl1_ptp4_oot_alarm_obj])


@mark.p1
@mark.lab_has_compute
@mark.lab_has_ptp_configuration_compute
def test_ptp_operation_service_stop_start_restart():
    """
    Verify Precision Time Protocol (PTP) behavior when the PTP service is stopped, started, and restarted.

    Test Steps:
        - Stop the PTP service (ptp4l@ptp1.service) on controller-0.
        - Verify service status becomes inactive and appropriate alarms are raised.
        - Verify degradation in PTP configuration (clock class, grandmaster settings).
        - Start the PTP service on controller-0.
        - Verify service status becomes active and alarms clear.
        - Verify full restoration of PTP configuration.
        - Restart the PTP service.
        - Verify service reactivation, alarm clearance, and final configuration validation.

    Preconditions:
        - System is configured with a valid PTP setup (as per ptp_configuration_expectation_compute.json5).
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")
    systemctl_keywords = SystemCTLKeywords(ssh_connection)
    ptp_service_status_validator = PTPServiceStatusValidator(ssh_connection)

    get_logger().log_info("Stopping ptp4l@ptp1.service on controller-0...")

    selected_instances = [("ptp1", "controller-0", []), ("ptp1", "controller-1", [])]

    # Expected degraded configuration after service stop on controller-0
    ctrl0_ptp1_service_stop_exp_dict = """{
        "ptp4l": [
            {
                "name": "ptp1",
                "controller-0": {
                    "parent_data_set": {
                        "gm_clock_class": -1,
                        "gm_clock_accuracy": "",
                        "gm_offset_scaled_log_variance": ""
                    },
                    "time_properties_data_set": {
                        "current_utc_offset": -1,
                        "current_utc_offset_valid": -1,
                        "time_traceable": -1,
                        "frequency_traceable": -1
                    },
                    "grandmaster_settings": {
                        "clock_class": -1,
                        "clock_accuracy": "",
                        "offset_scaled_log_variance": "",
                        "time_traceable": -1,
                        "frequency_traceable": -1,
                        "time_source": "",
                        "current_utc_offset_valid": -1
                    },
                    "port_data_set": [
                        {
                            "interface": "{{ controller_1.nic1.nic_connection.interface }}",
                            "port_state": ""
                        },
                        {
                            "interface": "{{ controller_1.nic1.conn_to_proxmox }}",
                            "port_state": ""
                        }
                    ]
                },
                "controller-1": {
                    "parent_data_set": {
                        "gm_clock_class": 165, // Controller-1 is now acting as the Grandmaster (GM) in degraded mode
                        "gm_clock_accuracy": "0xfe", // Clock accuracy unknown
                        "gm_offset_scaled_log_variance": "0xffff" // Clock stability/variance is unknown
                    },
                    "time_properties_data_set": {
                        "current_utc_offset": 37, // Standard UTC offset
                        "current_utc_offset_valid": 0, // UTC offset is not currently valid (as time source is degraded)
                        "time_traceable": 0, // The time is not traceable to a known accurate source
                        "frequency_traceable": 0 // The frequency is not traceable either
                    },
                    "grandmaster_settings": {
                        "clock_class": 165, // Degraded or holdover mode (not traceable to GNSS or accurate time)
                        "clock_accuracy": "0xfe", // Accuracy unknown
                        "offset_scaled_log_variance": "0xffff", // Stability unknown
                        "time_traceable": 0, // Time not traceable
                        "frequency_traceable": 0, // Frequency not traceable
                        "time_source": "0xa0", // GNSS is the original source (0xA0), but signal is currently not valid
                        "current_utc_offset_valid": 0 // UTC offset validity flag is unset
                    },
                    "port_data_set": [
                        {
                            "interface": "{{ controller_1.nic1.nic_connection.interface }}",
                            "port_state": "MASTER" // controller-1's NIC1 is now the active master (providing time)
                        },
                        {
                            "interface": "{{ controller_1.nic1.conn_to_proxmox }}",
                            "port_state": "MASTER" // controller-1 continues to serve time externally (to Proxmox or others)
                        }
                    ]
                }
            }
        ]
    }"""

    ctrl0_ptp1_service_stop_exp_ptp_setup = ptp_setup_keywords.filter_and_render_ptp_config(ptp_setup_template_path, selected_instances, ctrl0_ptp1_service_stop_exp_dict)

    systemctl_keywords.systemctl_stop("ptp4l", "ptp1")
    time.sleep(10)

    get_logger().log_info("Verifying ptp service status and recent stop event...")
    ptp_service_status_validator.verify_service_status_and_recent_event("ptp4l", "ptp1", 30, "inactive (dead)")

    get_logger().log_info("Waiting for alarms 100.119 due to service stop...")
    ctrl0_alarm = AlarmListObject()
    ctrl0_alarm.set_alarm_id("100.119")
    
    ctrl0_alarm.set_reason_text("controller-0 PTP service ptp4l@ptp1.service enabled but not running")
    ctrl0_alarm.set_entity_id("host=controller-0.instance=ptp1.ptp")

    ctrl1_alarm = AlarmListObject()
    ctrl1_alarm.set_alarm_id("100.119")
    ctrl1_alarm.set_reason_text("controller-1 is not locked to remote PTP Grand Master")
    ctrl1_alarm.set_entity_id("host=controller-1.instance=ptp1.ptp=no-lock")

    AlarmListKeywords(ssh_connection).wait_for_alarms_to_appear([ctrl0_alarm, ctrl1_alarm])

    get_logger().log_info("Verifying degraded PMC values after service stop...")
    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-1"))
    ptp_readiness_keywords.wait_for_gm_clock_class_appear_in_parent_data_set("ptp1", 165)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_ptp1_service_stop_exp_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values(check_domain=False)

    get_logger().log_info("Starting ptp4l@ptp1.service on controller-0...")
    systemctl_keywords.systemctl_start("ptp4l", "ptp1")
    time.sleep(10)
    ptp_service_status_validator.verify_service_status_and_recent_event("ptp4l", "ptp1", 30)

    get_logger().log_info("Waiting for alarms to clear after start...")
    AlarmListKeywords(ssh_connection).wait_for_alarms_cleared([ctrl0_alarm, ctrl1_alarm])

    get_logger().log_info("Verifying full PMC configuration after service start...")
    ptp_readiness_keywords.wait_for_gm_clock_class_appear_in_parent_data_set("ptp1", 6)
    start_exp_ptp_setup = ptp_setup_keywords.filter_and_render_ptp_config(ptp_setup_template_path, selected_instances)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, start_exp_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values(check_domain=False)

    get_logger().log_info("Restarting ptp4l@ptp1.service on controller-0...")
    systemctl_keywords.systemctl_restart("ptp4l", "ptp1")
    time.sleep(10)
    ptp_service_status_validator.verify_service_status_and_recent_event("ptp4l", "ptp1", 30)

    get_logger().log_info("Waiting for alarms to clear after restart...")
    AlarmListKeywords(ssh_connection).wait_for_alarms_cleared([ctrl0_alarm, ctrl1_alarm])

    get_logger().log_info("Verifying PMC configuration and clock class after service restart...")
    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-0"))
    ptp_readiness_keywords.wait_for_clock_class_appear_in_grandmaster_settings_np("ptp1", 6)
    ptp_readiness_keywords.wait_for_gm_clock_class_appear_in_parent_data_set("ptp1", 6)
    ptp_verify_config_keywords.verify_ptp_pmc_values(check_domain=False)


@mark.p1
@mark.lab_has_compute
@mark.lab_has_ptp_configuration_compute
def test_ptp_host_operation_swact(request):
    """
    Verify PTP configuration persistence and functionality after controller swact.

    Test Steps:
        - Perform swact operation on the active controller
        - Verify all PTP configurations remain intact after swact

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_configuration_expectation_compute.json5.
        - Both controllers are operational with one active and one standby.

    Notes:
        - This test validates that PTP services continue to function properly after a controller switchover
        - The test will automatically swact back to the original controller at the end of the test
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    active_controller = system_host_list_keywords.get_active_controller()
    standby_controller = system_host_list_keywords.get_standby_controller()

    get_logger().log_info("Performing controller swact operation")
    system_host_swact_keywords = SystemHostSwactKeywords(ssh_connection)
    system_host_swact_keywords.host_swact()
    swact_success = system_host_swact_keywords.wait_for_swact(active_controller, standby_controller)
    validate_equals(swact_success, True, "Host swact")

    get_logger().log_info("Verifying all PTP configurations after swact")
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ptp_setup)
    ptp_verify_config_keywords.verify_all_ptp_configurations()

    # if swact was successful, swact again at the end
    def swact_controller():
        get_logger().log_info("Starting teardown_swact(). Re-establishing the previous active/standby configuration of the controllers.")
        system_host_list_keyword = SystemHostListKeywords(ssh_connection)
        active_controller_teardown_before_swact = system_host_list_keyword.get_active_controller()
        standby_controller_teardown_before_swact = system_host_list_keyword.get_standby_controller()
        system_host_swact_keywords_teardown = SystemHostSwactKeywords(ssh_connection)
        system_host_swact_keywords_teardown.host_swact()
        system_host_swact_keywords_teardown.wait_for_swact(active_controller_teardown_before_swact, standby_controller_teardown_before_swact)

    request.addfinalizer(swact_controller)


@mark.p1
@mark.lab_has_compute
@mark.lab_has_ptp_configuration_compute
def test_ptp_host_operation_lock_and_unlock():
    """
    Verify PTP configuration persistence and functionality after controller lock and unlock operations.

    Test Steps:
        - Lock the standby controller
        - Unlock the standby controller
        - Verify all PTP configurations remain intact after lock and unlock operations

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_configuration_expectation_compute.json5
        - Both controllers are operational with one active and one standby

    Expected Results:
        - Lock and unlock operations complete successfully
        - PTP configuration remains intact and functional after operations
        - No unexpected PTP alarms are present after operations

    Notes:
        - This test validates that PTP services continue to function properly after controller maintenance operations
        - The test performs operations on the standby controller to minimize service disruption
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    standby_controller = system_host_list_keywords.get_standby_controller()

    get_logger().log_info("Performing lock operation on the standby controller")
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(standby_controller.get_host_name())
    validate_equals(lock_success, True, "Controller locked")

    get_logger().log_info("Performing unlock operation on the standby controller")
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(standby_controller.get_host_name())
    validate_equals(unlock_success, True, "Controller unlocked")

    get_logger().log_info("Waiting for PMC port states after lock and unlock host")
    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-0"))
    ptp_readiness_keywords.wait_for_port_state_appear_in_port_data_set("ptp1", ["MASTER", "MASTER"])
    ptp_readiness_keywords = PTPReadinessKeywords(LabConnectionKeywords().get_ssh_for_hostname("controller-1"))
    ptp_readiness_keywords.wait_for_port_state_appear_in_port_data_set("ptp1", ["SLAVE", "MASTER"])

    get_logger().log_info("Verifying PTP configurations after lock and unlock operations")
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ptp_setup)
    ptp_verify_config_keywords.verify_all_ptp_configurations()


@mark.p1
@mark.lab_has_compute
@mark.lab_has_ptp_configuration_compute
def test_ptp_host_operation_reboot():
    """
    Verify PTP configuration persistence and functionality after controller reboot.

    Test Steps:
        - Lock, reboot, and unlock the standby controller
        - Verify all PTP configurations remain intact after reboot

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_configuration_expectation_compute.json5.
        - Both controllers are operational with one active and one standby.

    Notes:
        - This test validates that PTP services continue to function properly after a controller reboot
        - The test performs operations on the standby controller to avoid service disruption
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    standby_controller = system_host_list_keywords.get_standby_controller()

    get_logger().log_info("Performing controller reboot operation")
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(standby_controller.get_host_name())
    validate_equals(lock_success, True, "Controller locked")
    reboot_success = SystemHostRebootKeywords(ssh_connection).host_reboot(standby_controller.get_host_name())
    validate_equals(reboot_success, True, "Host reboot")
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(standby_controller.get_host_name())
    validate_equals(unlock_success, True, "Controller unlocked")

    get_logger().log_info("Verifying all PTP configurations after reboot")
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ptp_setup)
    ptp_verify_config_keywords.verify_all_ptp_configurations()


@mark.p1
@mark.lab_has_compute
@mark.lab_has_ptp_configuration_compute
def test_ptp_host_operation_force_switchover(request):
    """
    Verify PTP configuration persistence and functionality after controller force switchover.

    Test Steps:
        - Performing controller force switchover operation
        - Verify all PTP configurations remain intact after force switchover

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_configuration_expectation_compute.json5
        - Both controllers are operational with one active and one standby
        - PTP services are running correctly before the test

    Notes:
        - This test validates that PTP services continue to function properly after a forced controller switchover
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    active_controller = system_host_list_keywords.get_active_controller()
    standby_controller = system_host_list_keywords.get_standby_controller()

    get_logger().log_info("Performing controller force switchover operation")
    system_host_swact_keywords = SystemHostSwactKeywords(ssh_connection)
    system_host_swact_keywords.host_swact_force()
    swact_success = system_host_swact_keywords.wait_for_swact(active_controller, standby_controller)
    validate_equals(swact_success, True, "Host swact")

    get_logger().log_info("Verifying all PTP configurations after force switchover")
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ptp_setup)
    ptp_verify_config_keywords.verify_all_ptp_configurations()

    # if swact was successful, swact again at the end
    def swact_controller():
        get_logger().log_info("Starting teardown_swact(). Re-establishing the previous active/standby configuration of the controllers.")
        system_host_list_keyword = SystemHostListKeywords(ssh_connection)
        active_controller_teardown_before_swact = system_host_list_keyword.get_active_controller()
        standby_controller_teardown_before_swact = system_host_list_keyword.get_standby_controller()
        system_host_swact_keywords_teardown = SystemHostSwactKeywords(ssh_connection)
        system_host_swact_keywords_teardown.host_swact()
        system_host_swact_keywords_teardown.wait_for_swact(active_controller_teardown_before_swact, standby_controller_teardown_before_swact)

    request.addfinalizer(swact_controller)

import os

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals_with_retry
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.ptp.ptp_setup_executor_keywords import PTPSetupExecutorKeywords
from keywords.cloud_platform.system.ptp.ptp_teardown_executor_keywords import PTPTeardownExecutorKeywords
from keywords.cloud_platform.system.ptp.ptp_verify_config_keywords import PTPVerifyConfigKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.ip.ip_keywords import IPKeywords
from keywords.ptp.pmc.pmc_keywords import PMCKeywords
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

    # This template is derived from the reference file ptp_configuration_expectation_compute.json5 and
    # should maintain consistency in structure. Only the expected_dict section is intended to change in
    # response to different PTP operation scenarios.

    # In ptp4l (e.g., ptp1 with controller-0), only the required instances that need to be verified are included.
    # Unnecessary entries in instance_hostnames and ptp_interface_names—those not relevant to the verification—are
    # removed when compared to the original ptp_configuration_expectation_compute.json5 file.

    # The ptp1if1 interface is used to retrieve the interface name for the down operation.
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
    wait_for_port_state_appear_in_port_data_set("ptp1", "controller-1", ["MASTER", "MASTER"])

    get_logger().log_info(f"Verifying PMC data after interface {ctrl0_nic1_interface} goes down.")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic1_iface_down_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()

    # This template is derived from the reference file ptp_configuration_expectation_compute.json5 and
    # should maintain consistency in structure. Only the expected_dict section is intended to change in
    # response to different PTP operation scenarios.

    # In ptp4l (e.g., ptp1 with controller-0 and controller-1), only the required instances that need to be verified
    # are included. Unnecessary entries in instance_hostnames and ptp_interface_names—those not relevant to the verification—are
    # removed when compared to the original ptp_configuration_expectation_compute.json5 file.
    ctrl0_nic1_iface_up_ptp_selection = [("ptp1", "controller-0", []), ("ptp1", "controller-1", [])]
    ctrl0_nic1_iface_up_ptp_setup = ptp_setup_keywords.filter_and_render_ptp_config(ptp_setup_template_path, ctrl0_nic1_iface_up_ptp_selection)

    get_logger().log_info("Interface up Controller-0 NIC1.")
    ip_keywords.set_ip_port_state(ctrl0_nic1_interface, "up")

    get_logger().log_info(f"Waiting for alarm 100.119 to clear after interface {ctrl0_nic1_interface} comes up.")
    AlarmListKeywords(ssh_connection).wait_for_alarms_cleared([not_locked_alarm_obj])

    get_logger().log_info(f"Waiting for PMC port states after interface {ctrl0_nic1_interface} comes up.")
    wait_for_port_state_appear_in_port_data_set("ptp1", "controller-1", ["SLAVE", "MASTER"])

    get_logger().log_info(f"Verifying PMC data after interface {ctrl0_nic1_interface} comes up.")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic1_iface_up_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()

    # This template is derived from the reference file ptp_configuration_expectation_compute.json5 and
    # should maintain consistency in structure. Only the expected_dict section is intended to change in
    # response to different PTP operation scenarios.

    # In ptp4l (e.g., ptp4 with controller-1), only the required instances that need to be verified are included.
    # Unnecessary entries in instance_hostnames and ptp_interface_names—those not relevant to the verification—are
    # removed when compared to the original ptp_configuration_expectation_compute.json5 file.
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

    # This template is derived from the reference file ptp_configuration_expectation_compute.json5 and
    # should maintain consistency in structure. Only the expected_dict section is intended to change in
    # response to different PTP operation scenarios.

    # In ptp4l (e.g., ptp3 with controller-0 and ptp4 with controller-1), only the required instances that need
    # to be verified are included. Unnecessary entries in instance_hostnames and ptp_interface_names—those not
    # relevant to the verification—are removed when compared to the original ptp_configuration_expectation_compute.json5 file.

    # The ptp3if1 interface is used to retrieve the interface name for the down operation.
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
    wait_for_port_state_appear_in_port_data_set("ptp4", "controller-1", ["MASTER", "MASTER"])

    get_logger().log_info(f"Verifying PMC data after interface {ctrl0_nic2_interface} goes down.")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic2_iface_down_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()

    get_logger().log_info("Interface up Controller-0 NIC2.")
    ip_keywords.set_ip_port_state(ctrl0_nic2_interface, "up")

    get_logger().log_info(f"Waiting for alarm 100.119 to clear after interface {ctrl0_nic2_interface} comes up.")
    AlarmListKeywords(ssh_connection).wait_for_alarms_cleared([not_locked_alarm_obj])

    get_logger().log_info(f"Waiting for PMC port states after interface {ctrl0_nic2_interface} comes up.")
    wait_for_port_state_appear_in_port_data_set("ptp4", "controller-1", ["SLAVE", "MASTER"])

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
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup_template_path = get_stx_resource_path("resources/ptp/setup/ptp_configuration_expectation_compute.json5")

    get_logger().log_info("Verifying PTP operation and corresponding status changes when SMA is disabled.")

    # This template is derived from the reference file ptp_configuration_expectation_compute.json5 and
    # should maintain consistency in structure. Only the expected_dict section is intended to change in
    # response to different PTP operation scenarios.

    # In ptp4l (e.g., ptp3 with controller-0 and ptp4 with controller-1), only the required instances that need
    # to be verified are included. Unnecessary entries in instance_hostnames and ptp_interface_names—those not
    # relevant to the verification—are removed when compared to the original ptp_configuration_expectation_compute.json5 file.

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

    not_locked_alarm_obj = AlarmListObject()
    not_locked_alarm_obj.set_alarm_id("100.119")
    not_locked_alarm_obj.set_reason_text("controller-0 is not locked to remote PTP Grand Master")
    not_locked_alarm_obj.set_entity_id("host=controller-0.instance=ptp3.ptp=no-lock")

    signal_loss_alarm_obj = AlarmListObject()
    signal_loss_alarm_obj.set_alarm_id("100.119")
    signal_loss_alarm_obj.set_reason_text("controller-0 1PPS signal loss state: holdover")
    signal_loss_alarm_obj.set_entity_id("host=controller-0.interface=enp138s0f0.ptp=1PPS-signal-loss")

    AlarmListKeywords(ssh_connection).wait_for_alarms_to_appear([not_locked_alarm_obj, signal_loss_alarm_obj])

    get_logger().log_info("Waiting for clock class after SMA1 is disabled")
    wait_for_clock_class_appear_in_grandmaster_settings_np("ptp3", "controller-0", 7)

    get_logger().log_info("Verifying PMC data after SMA1 is disabled")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic2_sma1_disable_exp_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()

    get_logger().log_info("Verifying PTP operation and corresponding status changes when SMA is enabled.")

    ctrl0_nic2_sma1_enable_ptp_selection = [("ptp3", "controller-0", []), ("ptp4", "controller-1", [])]
    ctrl0_nic2_sma1_enable_exp_dict_overrides = {"ptp4l": [{"name": "ptp4", "controller-1": {"grandmaster_settings": {"clock_class": 165}}}]}
    ctrl0_nic2_sma1_enable_exp_ptp_setup = ptp_setup_keywords.filter_and_render_ptp_config(ptp_setup_template_path, ctrl0_nic2_sma1_enable_ptp_selection, expected_dict_overrides=ctrl0_nic2_sma1_enable_exp_dict_overrides)

    sma_keywords.enable_sma("controller-0", "nic2")
    get_logger().log_info("Waiting for 100.119 alarm to clear after SMA1 is enabled")
    alarm_list_object = AlarmListObject()
    alarm_list_object.set_alarm_id("100.119")
    AlarmListKeywords(ssh_connection).wait_for_alarms_cleared([alarm_list_object])

    get_logger().log_info("Waiting for clock class after SMA1 is enabled")
    wait_for_clock_class_appear_in_grandmaster_settings_np("ptp3", "controller-0", 6)

    get_logger().log_info("Verifying PMC data after SMA1 is enabled")
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ctrl0_nic2_sma1_enable_exp_ptp_setup)
    ptp_verify_config_keywords.verify_ptp_pmc_values()


def wait_for_port_state_appear_in_port_data_set(name: str, hostname: str, expected_port_states: list[str]) -> None:
    """
    Waits until the port states observed in the port data set match the expected states, or times out.

    Args:
        name (str): Name of the PTP instance.
        hostname (str): Hostname of the target system.
        expected_port_states (list[str]): List of expected port states to wait for.

    Raises:
        Exception: If expected port states do not appear within the timeout.
    """

    def check_port_state_in_port_data_set(name: str, hostname: str) -> list[str]:
        """
        Checks whether the observed port states from the port data set match the expected port states.

        Args:
            name (str): Name of the PTP instance.
            hostname (str): Hostname of the target system.

        Returns:
            list[str]: List of expected port states.
        """
        config_file = f"/etc/linuxptp/ptpinstance/ptp4l-{name}.conf"
        socket_file = f"/var/run/ptp4l-{name}"

        ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(hostname)
        pmc_keywords = PMCKeywords(ssh_connection)

        observed_states = [obj.get_port_state() for obj in pmc_keywords.pmc_get_port_data_set(config_file, socket_file).get_pmc_get_port_data_set_objects()]

        return observed_states

    validate_equals_with_retry(lambda: check_port_state_in_port_data_set(name, hostname), expected_port_states, "port state in port data set", 120, 30)


def wait_for_clock_class_appear_in_grandmaster_settings_np(name: str, hostname: str, expected_clock_class: int) -> None:
    """
    Waits until the clock class observed in the grandmaster settings np match the expected clock class, or times out.

    Args:
        name (str): Name of the PTP instance.
        hostname (str): Hostname of the target system.
        expected_clock_class (int): expected clock class to wait for.

    Raises:
        Exception: If expected clock class do not appear within the timeout.
    """

    def get_clock_class_in_grandmaster_settings_np(name: str, hostname: str) -> int:
        """
        Get the observed clock class from the grandmaster settings np.

        Args:
            name (str): Name of the PTP instance.
            hostname (str): Hostname of the target system.

        Returns:
            int: observed clock class.
        """
        config_file = f"/etc/linuxptp/ptpinstance/ptp4l-{name}.conf"
        socket_file = f"/var/run/ptp4l-{name}"

        ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(hostname)
        pmc_keywords = PMCKeywords(ssh_connection)

        get_grandmaster_settings_np_object = pmc_keywords.pmc_get_grandmaster_settings_np(config_file, socket_file).get_pmc_get_grandmaster_settings_np_object()
        observed_clock_class = get_grandmaster_settings_np_object.get_clock_class()

        return observed_clock_class

    validate_equals_with_retry(lambda: get_clock_class_in_grandmaster_settings_np(name, hostname), expected_clock_class, "clock class in grandmaster settings np", 120, 30)

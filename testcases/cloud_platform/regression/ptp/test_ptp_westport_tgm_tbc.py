from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.ptp.objects.operation_type_object import OperationType
from keywords.cloud_platform.system.ptp.objects.status_constants_object import StatusConstants
from keywords.cloud_platform.system.ptp.objects.verification_type_object import VerificationType
from keywords.cloud_platform.system.ptp.ptp_scenario_executor_keywords import PTPScenarioExecutorKeywords
from keywords.cloud_platform.system.ptp.ptp_setup_executor_keywords import PTPSetupExecutorKeywords
from keywords.cloud_platform.system.ptp.ptp_teardown_executor_keywords import PTPTeardownExecutorKeywords
from keywords.cloud_platform.system.ptp.ptp_verify_config_keywords import PTPVerifyConfigKeywords
from keywords.ptp.setup.ptp_setup_reader import PTPSetupKeywords

relative_path = "resources/ptp/ptp_data_westport_dx_plus_tgm_tbc.json5"


@mark.p0
@mark.lab_has_dx_plus_westport
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
    ptp_setup_template_path = get_stx_resource_path(relative_path)
    ptp_setup_executor_keywords = PTPSetupExecutorKeywords(ssh_connection, ptp_setup_template_path)
    ptp_setup_executor_keywords.add_all_ptp_configurations()

    get_logger().log_info("Verify all PTP configuration")
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ptp_setup)
    ptp_verify_config_keywords.verify_all_ptp_configurations()


@mark.p1
@mark.lab_has_dx_plus_westport
def test_ptp_operation_interface_down_and_up(request):
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
        - System is set up with valid PTP configuration as defined in ptp_data_westport_dx_plus_tgm_tbc.json5.

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
    test_scenario = [
        {
            "description": "Bring interface down",
            "operations": [
                {
                    "name": "ctrl0_nic1_interface_down",
                    "description": "Controller-0 NIC1 interface down scenario",
                    "type": OperationType.interface,
                    "status": StatusConstants.interface_down,
                    "interface_mapping": {"hostname": "controller-0", "nic": "nic1"},
                },
            ],
            "verification": [
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-1 is not locked to remote PTP Grand Master",
                            "entity_id": "host=controller-1.instance=ptp1.ptp=no-lock"
                        },
                    ],
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values": [
                        {
                            "name": "ptp1",
                            "controller-1": {
                                "parent_data_set": {
                                    "gm_clock_class": 165,
                                    "gm_clock_accuracy": "0xfe",
                                    "gm_offset_scaled_log_variance": "0xffff"
                                },
                                "time_properties_data_set": {
                                    "current_utc_offset": 37,
                                    "current_utc_offset_valid": 0,
                                    "time_traceable": 0,
                                    "frequency_traceable": 0
                                },
                                "grandmaster_settings": {
                                    "clock_class": 165,
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
                                        "port_state": ["MASTER"],
                                        "parent_port_identity": {
                                            "name": "ptp1",
                                            "hostname": "controller-1"
                                        }
                                    },
                                    {
                                        "interface": "{{ controller_1.nic1.conn_to_proxmox }}",
                                        "port_state": "MASTER"
                                    },
                                ],
                            },
                        },
                    ],
                },
            ],
        },
        {
            "description": "Bring interface up",
            "operations": [
                {
                    "name": "ctrl0_nic1_interface_up",
                    "description": "Controller-0 NIC1 interface up scenario",
                    "type": OperationType.interface,
                    "status": StatusConstants.interface_up,
                    "interface_mapping": {"hostname": "controller-0", "nic": "nic1"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "severity": "major",
                            "reason_text": "controller-1 is not locked to remote PTP Grand Master",
                            "entity_id": "host=controller-1.instance=ptp1.ptp=no-lock"
                        },
                    ],
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values_overrides": [
                        {
                            "name": "ptp1",
                            "controller-1": {
                                "grandmaster_settings": {
                                    "clock_class": 165
                                }
                            }
                        }
                    ]
                },
            ],
        },
        {
            "description": "Bring interface down",
            "operations": [
                {
                    "name": "ctrl0_nic2_interface_down",
                    "description": "Controller-0 NIC2 interface down scenario",
                    "type": OperationType.interface,
                    "status": StatusConstants.interface_down,
                    "interface_mapping": {"hostname": "controller-0", "nic": "nic2"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-1 is not locked to remote PTP Grand Master",
                            "entity_id": "host=controller-1.instance=ptp4.ptp=no-lock"
                        },
                    ],
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values": [
                        {
                            "name": "ptp4",
                            "controller-1": {
                                "parent_data_set": {
                                    "gm_clock_class": 165,
                                    "gm_clock_accuracy": "0xfe",
                                    "gm_offset_scaled_log_variance": "0xffff"
                                },
                                "time_properties_data_set": {
                                    "current_utc_offset": 37,
                                    "current_utc_offset_valid": 0,
                                    "time_traceable": 0,
                                    "frequency_traceable": 0
                                },
                                "grandmaster_settings": {
                                    "clock_class": 165,
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
                                        "port_state": "MASTER",
                                        "parent_port_identity": {
                                            "name": "ptp4",
                                            "hostname": "controller-1"
                                        }
                                    },
                                    {
                                        "interface": "{{ controller_1.nic2.conn_to_proxmox }}",
                                        "port_state": "MASTER"
                                    },
                                ],
                            },
                        },
                    ],
                },
            ],
        },
        {
            "description": "Bring interface up",
            "operations": [
                {
                    "name": "ctrl0_nic2_interface_up",
                    "description": "Controller-0 NIC2 interface up scenario",
                    "type": OperationType.interface,
                    "status": StatusConstants.interface_up,
                    "interface_mapping": {"hostname": "controller-0", "nic": "nic2"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "severity": "major",
                            "reason_text": "controller-1 is not locked to remote PTP Grand Master",
                            "entity_id": "host=controller-1.instance=ptp1.ptp=no-lock"
                        },
                    ],
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values_overrides": [
                        {
                            "name": "ptp4",
                            "controller-1": {
                                "grandmaster_settings": {
                                    "clock_class": 165
                                }
                            }
                        }
                    ]
                },
            ],
        },
    ]

    resource_path = get_stx_resource_path(relative_path)
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    ptp_scenario_executor = PTPScenarioExecutorKeywords(ssh_connection, resource_path)
    ptp_scenario_executor.execute_test_scenario(test_scenario, request)


@mark.p1
@mark.lab_has_dx_plus_westport
def test_ptp_operation_sma_disabled_and_enable(request):
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
        - System is set up with valid PTP configuration as defined in ptp_data_westport_dx_plus_tgm_tbc.json5.
    """
    test_scenario = [
        {
            "description": "Disable sma port",
            "operations": [
                {
                    "name": "ctrl0_nic2_sma1_disable",
                    "description": "Controller-0 NIC2 SMA1 disable scenario",
                    "type": OperationType.sma,
                    "status": StatusConstants.gnss_sma_disable,
                    "sma_config": {"hostname": "controller-0", "nic": "nic2", "ptp_instance": "ptp3"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-0 is not locked to remote PTP Grand Master",
                            "entity_id": "host=controller-0.instance=ptp3.ptp=no-lock"
                        },
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-0 1PPS signal loss state: LockStatus.HOLDOVER",
                            "entity_id": "host=controller-0.interface={{ controller_0.nic2.base_port }}.ptp=1PPS-signal-loss"
                        },
                    ],
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values_overrides": [
                        {
                            "name": "ptp3",
                            "controller-0": {
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
                                    "clock_class": 7,
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
                                        "port_state": "MASTER"
                                    },
                                    {
                                        "interface": "{{ controller_0.nic2.conn_to_proxmox }}",
                                        "port_state": "MASTER"
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
                                    "clock_class": [165, 248],
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
                                        "port_state": "SLAVE",
                                        "parent_port_identity": {
                                            "name": "ptp3",
                                            "hostname": "controller-0",
                                            "interface": "{{ controller_0.nic2.nic_connection.interface }}"
                                        }
                                    },
                                    {
                                        "interface": "{{ controller_1.nic2.conn_to_proxmox }}",
                                        "port_state": "MASTER"
                                    }
                                ]
                            }
                        },
                    ],
                },
            ],
        },
        {
            "description": "Enable sma port",
            "operations": [
                {
                    "name": "ctrl0_nic2_sma1_enable",
                    "description": "Controller-0 NIC2 SMA1 enable scenario",
                    "type": OperationType.sma,
                    "status": StatusConstants.gnss_sma_enable,
                    "sma_config": {"hostname": "controller-0", "nic": "nic2", "ptp_instance": "ptp3"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "severity": "major",
                            "reason_text": "controller-0 is not locked to remote PTP Grand Master",
                            "entity_id": "host=controller-0.instance=ptp3.ptp=no-lock"
                        },
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-0 1PPS signal loss state: LockStatus.HOLDOVER",
                            "entity_id": "host=controller-0.interface={{ controller_0.nic2.base_port }}.ptp=1PPS-signal-loss"
                        },
                    ],
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values_overrides": []
                },
            ],
        },
    ]

    resource_path = get_stx_resource_path(relative_path)
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ptp_scenario_executor = PTPScenarioExecutorKeywords(ssh_connection, resource_path)
    ptp_scenario_executor.execute_test_scenario(test_scenario, request)


@mark.p1
@mark.lab_has_dx_plus_westport
def test_ptp_operation_gnss_off_and_on(request):
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
        - System is set up with valid PTP configuration as defined in ptp_data_westport_dx_plus_tgm_tbc.json5.

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
    test_scenario = [
        {
            "description": "Turn off gnss signal",
            "operations": [
                {
                    "name": "ctrl0_nic1_gnss_disable",
                    "description": "Controller-0 NIC1 GNSS disable scenario",
                    "type": OperationType.gnss,
                    "status": StatusConstants.gnss_sma_disable,
                    "gnss_config": {"hostname": "controller-0", "nic": "nic1"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-0 is not locked to remote PTP Grand Master",
                            "entity_id": "host=controller-0.instance=ptp1.ptp=no-lock"
                        },
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-0 1PPS signal loss state: LockStatus.HOLDOVER",
                            "entity_id": "host=controller-0.interface={{ controller_0.nic1.base_port }}.ptp=1PPS-signal-loss"
                        },
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-0 GNSS signal loss state: LockStatus.HOLDOVER",
                            "entity_id": "host=controller-0.interface={{ controller_0.nic1.base_port }}.ptp=GNSS-signal-loss"
                        },
                    ],
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values_overrides": [
                        {
                            "name": "ptp1",
                            "controller-0": {
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
                                    "clock_class": 7,
                                    "clock_accuracy": "0xfe",
                                    "offset_scaled_log_variance": "0xffff",
                                    "time_traceable": 1,
                                    "frequency_traceable": 1,
                                    "time_source": "0xa0",
                                    "current_utc_offset_valid": 0
                                },
                                "port_data_set": [
                                    {
                                        "interface": "{{ controller_0.nic1.nic_connection.interface }}",
                                        "port_state": "MASTER"
                                    },
                                    {
                                        "interface": "{{ controller_0.nic1.conn_to_proxmox }}",
                                        "port_state": "MASTER"
                                    },
                                ]
                            }
                        },
                        {
                            "name": "ptp3",
                            "controller-0": {
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
                                    "clock_class": 7,
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
                                        "port_state": "MASTER"
                                    },
                                    {
                                        "interface": "{{ controller_0.nic2.conn_to_proxmox }}",
                                        "port_state": "MASTER"
                                    },
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
                                    "clock_class": [165, 248],
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
                                        "port_state": "SLAVE",
                                        "parent_port_identity": {
                                            "name": "ptp3",
                                            "hostname": "controller-0",
                                            "interface": "{{ controller_0.nic2.nic_connection.interface }}"
                                        }
                                    },
                                    {
                                        "interface": "{{ controller_1.nic2.conn_to_proxmox }}",
                                        "port_state": "MASTER"
                                    },
                                ]
                            }
                        },
                    ],
                },
            ],
        },
        {
            "description": "Turn on gnss signal",
            "operations": [
                {
                    "name": "ctrl0_nic1_gnss_enable",
                    "description": "Controller-0 NIC1 GNSS enable scenario",
                    "type": OperationType.gnss,
                    "status": StatusConstants.gnss_sma_enable,
                    "gnss_config": {"hostname": "controller-0", "nic": "nic1"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "severity": "major",
                            "reason_text": "controller-0 is not locked to remote PTP Grand Master",
                            "entity_id": "host=controller-0.instance=ptp1.ptp=no-lock"
                        },
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "severity": "major",
                            "reason_text": "controller-0 1PPS signal loss state: LockStatus.HOLDOVER",
                            "entity_id": "host=controller-0.interface={{ controller_0.nic1.base_port }}.ptp=1PPS-signal-loss"
                        },
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "severity": "major",
                            "reason_text": "controller-0 GNSS signal loss state: LockStatus.HOLDOVER",
                            "entity_id": "host=controller-0.interface={{ controller_0.nic1.base_port }}.ptp=GNSS-signal-loss"
                        },
                    ],
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values_overrides": []
                },
            ],
        },
    ]

    resource_path = get_stx_resource_path(relative_path)
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ptp_scenario_executor = PTPScenarioExecutorKeywords(ssh_connection, resource_path)
    ptp_scenario_executor.execute_test_scenario(test_scenario, request)


@mark.p1
@mark.lab_has_dx_plus_westport
def test_ptp_operation_phc_ctl_time_change(request):
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
        - The system must have a valid PTP configuration as defined in `ptp_data_westport_dx_plus_tgm_tbc.json5`.
    """
    test_scenario = [
        {
            "description": "phc_ctl time change",
            "operations": [
                {
                    "name": "ctrl0_nic1_phc_ctl_time",
                    "description": "Controller-0 NIC1 PHC control time change scenario",
                    "type": OperationType.phc_ctl_loop,
                    "status": "loop",
                    "interface_mapping": {"hostname": "controller-0", "nic": "nic1"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "reason_text": "controller-0 Precision Time Protocol \\(PTP\\) clocking is out of tolerance by (\\d+\\.\\d+) (milli|micro)secs",
                            "entity_id": "host=controller-0.instance=ptp3.ptp=out-of-tolerance"
                        },
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "reason_text": "controller-0 Precision Time Protocol \\(PTP\\) clocking is out of tolerance by (\\d+\\.\\d+) (milli|micro)secs",
                            "entity_id": "host=controller-0.instance=ptp1.ptp=out-of-tolerance"
                        },
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "reason_text": "controller-1 Precision Time Protocol \\(PTP\\) clocking is out of tolerance by (\\d+\\.\\d+) (milli|micro)secs",
                            "entity_id": "host=controller-1.instance=ptp1.ptp=out-of-tolerance"
                        },
                    ],
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values_overrides": []
                },
            ],
        },
        {
            "description": "phc_ctl time change",
            "operations": [
                {
                    "name": "ctrl1_nic2_phc_ctl_time",
                    "description": "Controller-1 NIC2 PHC control time change scenario",
                    "type": OperationType.phc_ctl_loop,
                    "status": "loop",
                    "interface_mapping": {"hostname": "controller-1", "nic": "nic2"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "reason_text": "controller-1 Precision Time Protocol \\(PTP\\) clocking is out of tolerance by (\\d+\\.\\d+) (milli|micro)secs",
                            "entity_id": "host=controller-1.instance=ptp1.ptp=out-of-tolerance"
                        },
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "reason_text": "controller-1 Precision Time Protocol \\(PTP\\) clocking is out of tolerance by (\\d+\\.\\d+) (milli|micro)secs",
                            "entity_id": "host=controller-1.instance=ptp4.ptp=out-of-tolerance"
                        },
                    ],
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values_overrides": []
                },
            ],
        },
    ]

    resource_path = get_stx_resource_path(relative_path)
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ptp_scenario_executor = PTPScenarioExecutorKeywords(ssh_connection, resource_path)
    ptp_scenario_executor.execute_test_scenario(test_scenario, request)


@mark.p1
@mark.lab_has_dx_plus_westport
def test_ptp_operation_service_stop_start_restart(request):
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
        - System is configured with a valid PTP setup (as per ptp_data_westport_dx_plus_tgm_tbc.json5).
    """
    test_scenario = [
        {
            "description": "service stop",
            "operations": [
                {
                    "name": "ctrl0_ptp1_service_stop",
                    "description": "Controller-0 PTP1 service stop scenario",
                    "type": OperationType.service,
                    "status": StatusConstants.service_stop,
                    "service_config": {"service_name": "ptp4l", "instance_name": "ptp1"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.service_status,
                    "timeout": 30,
                    "service_status": [{"service_name": "ptp4l", "instance_name": "ptp1", "expected_status": "inactive (dead)"}],
                },
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-0 PTP service ptp4l@ptp1.service enabled but not running",
                            "entity_id": "host=controller-0.instance=ptp1.ptp"
                        },
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-1 is not locked to remote PTP Grand Master",
                            "entity_id": "host=controller-1.instance=ptp1.ptp=no-lock"
                        },
                    ],
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values": [
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
                                    },
                                ]
                            }
                        },
                    ],
                },
            ],
        },
        {
            "description": "service start",
            "operations": [
                {
                    "name": "ctrl0_ptp1_service_start",
                    "description": "Controller-0 PTP1 service start scenario",
                    "type": OperationType.service,
                    "status": StatusConstants.service_start,
                    "service_config": {"service_name": "ptp4l", "instance_name": "ptp1"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.service_status,
                    "timeout": 30,
                    "service_status": [{"service_name": "ptp4l", "instance_name": "ptp1", "expected_status": "active (running)"}],
                },
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "severity": "major",
                            "reason_text": "controller-0 PTP service ptp4l@ptp1.service enabled but not running",
                            "entity_id": "host=controller-0.instance=ptp1.ptp"
                        },
                        {

                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-1 is not locked to remote PTP Grand Master",
                            "entity_id": "host=controller-1.instance=ptp1.ptp=no-lock"
                        },
                    ],
                },
                {

                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values_overrides": []
                },
            ],
        },
        {
            "description": "service restart",
            "operations": [
                {
                    "name": "ctrl0_ptp1_service_restart",
                    "description": "Controller-0 PTP1 service restart scenario",
                    "type": OperationType.service,
                    "status": StatusConstants.service_restart,
                    "service_config": {"service_name": "ptp4l", "instance_name": "ptp1"},
                }
            ],
            "verification": [
                {
                    "type": VerificationType.service_status,
                    "timeout": 30,
                    "service_status": [{"service_name": "ptp4l", "instance_name": "ptp1", "expected_status": "active (running)"}],
                },
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": [
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_clear,
                            "severity": "major",
                            "reason_text": "controller-0 PTP service ptp4l@ptp1.service enabled but not running",
                            "entity_id": "host=controller-0.instance=ptp1.ptp"
                        },
                        {
                            "alarm_id": "100.119",
                            "state": StatusConstants.alarm_set,
                            "severity": "major",
                            "reason_text": "controller-1 is not locked to remote PTP Grand Master",
                            "entity_id": "host=controller-1.instance=ptp1.ptp=no-lock"
                        },
                    ],
                },
                {

                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values_overrides": []

                },
            ],
        },
    ]

    resource_path = get_stx_resource_path(relative_path)
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ptp_scenario_executor = PTPScenarioExecutorKeywords(ssh_connection, resource_path)
    ptp_scenario_executor.execute_test_scenario(test_scenario, request)


@mark.p1
@mark.lab_has_dx_plus_westport
def test_ptp_host_operation_swact(request):
    """
    Verify PTP configuration persistence and functionality after controller swact.

    Test Steps:
        - Perform swact operation on the active controller
        - Verify all PTP configurations remain intact after swact

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_data_westport_dx_plus_tgm_tbc.json5.
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
    ptp_setup_template_path = get_stx_resource_path(relative_path)
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
@mark.lab_has_dx_plus_westport
def test_ptp_host_operation_lock_and_unlock():
    """
    Verify PTP configuration persistence and functionality after controller lock and unlock operations.

    Test Steps:
        - Lock the standby controller
        - Unlock the standby controller
        - Verify all PTP configurations remain intact after lock and unlock operations

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_data_westport_dx_plus_tgm_tbc.json5
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

    ptp_setup_template_path = get_stx_resource_path(relative_path)
    get_logger().log_info("Verifying PTP configurations after lock and unlock operations")
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ptp_setup)
    ptp_verify_config_keywords.verify_all_ptp_configurations()


@mark.p1
@mark.lab_has_dx_plus_westport
def test_ptp_host_operation_reboot():
    """
    Verify PTP configuration persistence and functionality after controller reboot.

    Test Steps:
        - Lock, reboot, and unlock the standby controller
        - Verify all PTP configurations remain intact after reboot

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_data_westport_dx_plus_tgm_tbc.json5.
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
    ptp_setup_template_path = get_stx_resource_path(relative_path)
    ptp_setup_keywords = PTPSetupKeywords()
    ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)
    ptp_verify_config_keywords = PTPVerifyConfigKeywords(ssh_connection, ptp_setup)
    ptp_verify_config_keywords.verify_all_ptp_configurations()


@mark.p1
@mark.lab_has_dx_plus_westport
def test_ptp_host_operation_force_switchover(request):
    """
    Verify PTP configuration persistence and functionality after controller force switchover.

    Test Steps:
        - Performing controller force switchover operation
        - Verify all PTP configurations remain intact after force switchover

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_data_westport_dx_plus_tgm_tbc.json5
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
    ptp_setup_template_path = get_stx_resource_path(relative_path)
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


@mark.p2
@mark.lab_has_dx_plus_westport
def test_proxmox_ptp_vm_verification(request):
    """
    Test PTP VM verification with automatic service recovery.

    This test verifies PTP (Precision Time Protocol) functionality in a Proxmox VM environment
    by checking service status, retrieving PTP data sets, and validating against expected values.

    Test Steps:
        - Connect to PTP VM and setup test environment
        - Verify PTP service is running (auto-start if needed)
        - Validate PORT_DATA_SET - Check port state is SLAVE
        - Validate PARENT_DATA_SET - Verify GM clock properties
        - Validate TIME_PROPERTIES_DATA_SET - Check UTC offset and traceability
        - Cross-validate parent port identity with master configuration

    Expected Results:
        - PTP service runs successfully with auto-recovery capability
        - Port operates in SLAVE state as expected
        - Parent data set matches expected GM clock configuration
        - Time properties align with system UTC settings
        - Parent port identity correctly maps to master port

    Preconditions:
        - System is set up with valid PTP configuration as defined in ptp_data_westport_dx_plus_tgm_tbc.json5.
    """
    test_scenario = [
        {
            "description": "Proxmox PTP VM verification scenario",
            "operations": [
                {
                    "name": "proxmox_ptp_vm",
                    "description": "Proxmox PTP VM verification scenario",
                    "type": OperationType.proxmox,
                    "status": "pass",
                    "proxmox_config": {
                        "hostname": "controller-0",
                        "nic": "nic1",
                        "ptp_config_file": "/etc/ptp4l.conf",
                        "ptp_instance": "ptp1",
                        "validation_hostname": "controller-0",
                        "expected_port_state": "SLAVE",
                        "master_ptp_config_path": "/etc/linuxptp/ptpinstance/ptp4l-ptp1.conf",
                        "master_ptp_uds_path": "/var/run/ptp4l-ptp1"
                    }
                }
            ],
            "verification": [
                {
                    "type": VerificationType.alarm,
                    "timeout": 120,
                    "alarms": []
                },
                {
                    "type": VerificationType.pmc_value,
                    "timeout": 30,
                    "pmc_values": [
                        {
                            "name": "ptp1",
                            "controller-0": {
                                "parent_data_set": {
                                    "gm_clock_class": 6,
                                    "gm_clock_accuracy": "0x20",
                                    "gm_offset_scaled_log_variance": "0x4e5d"
                                },
                                "time_properties_data_set": {
                                    "current_utc_offset": 37,
                                    "current_utc_offset_valid": 0,
                                    "time_traceable": 1,
                                    "frequency_traceable": 1
                                },
                                "grandmaster_settings": {
                                    "clock_class": 6,
                                    "clock_accuracy": "0x20",
                                    "offset_scaled_log_variance": "0x4e5d",
                                    "time_traceable": 1,
                                    "frequency_traceable": 1,
                                    "time_source": "0x20",
                                    "current_utc_offset_valid": 0
                                },
                            },
                        }
                    ],
                },
            ],
        }
    ]

    resource_path = get_stx_resource_path(relative_path)
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ptp_scenario_executor = PTPScenarioExecutorKeywords(ssh_connection, resource_path)
    ptp_scenario_executor.execute_test_scenario(test_scenario, request)

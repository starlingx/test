"""Tests for SNMP sensitive-data storage and fault-management trap delivery.

A single end-to-end validation that exercises two SNMP behaviours against one
SNMP application install:

    * SNMP sensitive data (community strings, FM-DB connection) is stored in an
      Opaque Secret rather than a plaintext ConfigMap.
    * A fault-management alarm raised with fmClientCli produces an SNMP trap that
      is delivered to a receiver running on the test runner.
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_none
from keywords.cloud_platform.snmp.snmp_keywords import SNMPKeywords
from keywords.cloud_platform.snmp.snmp_secret_keywords import SnmpSecretKeywords
from keywords.cloud_platform.snmp.snmp_trap_receiver_keywords import SnmpTrapReceiverKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

EXPECTED_SECRET_TYPE = "Opaque"
EXPECTED_SECRET_DATA_KEYS = 2


@mark.p2
def test_snmp_secret_storage_and_trap_delivery(request):
    """SNMP stores sensitive data in a Secret and delivers an FM-alarm trap.

    Test Steps:
        - Start a trap receiver on the test runner
        - Install SNMP with trap2sink pointing at the receiver
        - Verify no SNMP ConfigMap exists in kube-system
        - Verify the snmpd-secret Opaque Secret exists with two data keys
        - Raise a fault-management alarm with fmClientCli
        - Verify the resulting trap is captured by the receiver

    Teardown:
        - Delete the test alarm
        - Remove and clean up the SNMP application
        - Stop the trap receiver
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    snmp_keywords = SNMPKeywords(ssh_connection)
    secret_keywords = SnmpSecretKeywords(ssh_connection)
    receiver = SnmpTrapReceiverKeywords()

    request.addfinalizer(receiver.stop_receiver)
    request.addfinalizer(snmp_keywords.remove_and_cleanup_snmp)
    request.addfinalizer(snmp_keywords.remove_test_alarm)

    controller_oam_ip = ConfigurationManager.get_lab_config().get_floating_ip()

    get_logger().log_test_case_step("Deriving the receiver IP and starting the trap receiver")
    receiver_ip = receiver.get_receiver_ip(controller_oam_ip)
    validate_not_none(receiver_ip, "Must derive a routable receiver IP toward the controller")
    receiver.start_receiver()
    validate_equals(receiver.is_receiver_running(), True, "The snmptrapd receiver must be running")

    get_logger().log_test_case_step("Installing SNMP with trap2sink targeting the receiver")
    snmp_keywords.install_and_configure_snmp_with_trap_target(receiver_ip, receiver.get_port())

    get_logger().log_test_case_step("Verifying no SNMP ConfigMap exists in kube-system")
    validate_equals(secret_keywords.snmp_configmap_present(), False, "No SNMP ConfigMap should exist in kube-system")

    get_logger().log_test_case_step("Verifying the snmpd-secret Opaque Secret exists")
    validate_equals(secret_keywords.snmp_secret_present(), True, "snmpd-secret Secret should exist")
    validate_equals(secret_keywords.get_snmp_secret_type(), EXPECTED_SECRET_TYPE, "snmpd-secret should be of type Opaque")
    validate_equals(secret_keywords.get_snmp_secret_data_key_count(), EXPECTED_SECRET_DATA_KEYS, "snmpd-secret should hold two data keys")

    get_logger().log_test_case_step("Raising a fault-management alarm with fmClientCli")
    receiver.clear_captured_traps()
    snmp_keywords.generate_test_alarm()

    get_logger().log_test_case_step("Verifying the trap is delivered to the receiver")
    validate_equals(receiver.wait_for_trap(), True, "The fault-management alarm should produce a trap delivered to the receiver")

from typing import Any, List, Tuple

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.ptp.system_host_if_ptp_keywords import SystemHostIfPTPKeywords
from keywords.cloud_platform.system.ptp.system_host_ptp_instance_keywords import SystemHostPTPInstanceKeywords
from keywords.cloud_platform.system.ptp.system_ptp_instance_keywords import SystemPTPInstanceKeywords
from keywords.cloud_platform.system.ptp.system_ptp_instance_parameter_keywords import SystemPTPInstanceParameterKeywords
from keywords.cloud_platform.system.ptp.system_ptp_interface_keywords import SystemPTPInterfaceKeywords
from keywords.linux.systemctl.systemctl_status_keywords import SystemCTLStatusKeywords
from keywords.ptp.gnss_keywords import GnssKeywords
from keywords.ptp.setup.object.ptp_setup import PTPSetup
from keywords.ptp.setup.ptp_setup_reader import PTPSetupKeywords


class PTPSetupExecutorKeywords(BaseKeyword):
    """
    Create all PTP setup configurations using given SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection, ptp_setup_template_path):
        """
        Initializes the PTPSetupExecutorKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
            ptp_setup_template_path : ptp setup template path
        """
        self.ssh_connection = ssh_connection
        ptp_setup_keywords = PTPSetupKeywords()
        ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)

        self.ptp4l_setup_list = ptp_setup.get_ptp4l_setup_list()
        self.phc2sys_setup_list = ptp_setup.get_phc2sys_setup_list()
        self.ts2phc_setup_list = ptp_setup.get_ts2phc_setup_list()
        self.clock_setup_list = ptp_setup.get_clock_setup_list()

    def add_all_ptp_configurations(self):
        """
        Configure all ptp configurations
        """
        system_ptp_instance_keywords = SystemPTPInstanceKeywords(self.ssh_connection)

        self.add_all_ptp_configurations_for_ptp4l_service()

        self.add_all_ptp_configurations_for_phc2sync_service()

        self.add_all_ptp_configurations_for_ts2phc_service()

        self.add_all_ptp_configurations_for_clock_service()

        system_ptp_instance_apply_output = system_ptp_instance_keywords.system_ptp_instance_apply()
        validate_equals(system_ptp_instance_apply_output, "Applying the PTP Instance configuration", "apply PTP instance configuration")

        self.wait_for_ptp_configuration_to_update_after_applying()

    def add_all_ptp_configurations_for_ptp4l_service(self):
        """
        Configure all ptp configurations for ptp4l service
        """
        for ptp4l_instance_obj in self.ptp4l_setup_list:

            self.ptp_instance_add_and_assign_hosts(ptp4l_instance_obj, "ptp4l")

            self.ptp_instance_parameter_add(ptp4l_instance_obj)

            self.ptp_interfaces_add_and_assign_hosts(ptp4l_instance_obj)

    def add_all_ptp_configurations_for_phc2sync_service(self):
        """
        Configure all ptp configurations for phc2sync service
        """
        for phc2sys_instance_obj in self.phc2sys_setup_list:

            self.ptp_instance_add_and_assign_hosts(phc2sys_instance_obj, "phc2sys")

            self.ptp_instance_parameter_add(phc2sys_instance_obj)

            self.ptp_interfaces_add_and_assign_hosts(phc2sys_instance_obj)

    def add_all_ptp_configurations_for_ts2phc_service(self):
        """
        Configure all ptp configurations for ts2phc service
        """
        for ts2phc_instance_obj in self.ts2phc_setup_list:

            self.ptp_instance_add_and_assign_hosts(ts2phc_instance_obj, "ts2phc")

            self.ptp_instance_parameter_add(ts2phc_instance_obj)

            self.ptp_interfaces_add_and_assign_hosts(ts2phc_instance_obj)

    def add_all_ptp_configurations_for_clock_service(self):
        """
        Configure all ptp configurations for clock service
        """
        for clock_instance_obj in self.clock_setup_list:

            self.ptp_instance_add_and_assign_hosts(clock_instance_obj, "clock")

            self.ptp_instance_parameter_add(clock_instance_obj)

            self.ptp_interfaces_add_and_assign_hosts(clock_instance_obj)

    def ptp_instance_add_and_assign_hosts(self, ptp_instance_obj: Any, service: str):
        """
        Add ptp instance, assign hosts and validate

        Args:
            ptp_instance_obj : PTP instance setup object
            service : type of instance
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_active_controller_ssh()
        system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)
        system_host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)

        name = ptp_instance_obj.get_name()

        system_ptp_instance_output = system_ptp_instance_keywords.system_ptp_instance_add(name, service)
        validate_equals(system_ptp_instance_output.get_ptp_instance().get_name(), name, "add PTP instance")

        hostnames = ptp_instance_obj.get_instance_hostnames()
        for hostname in hostnames:
            system_host_ptp_instance_output = system_host_ptp_instance_keywords.system_host_ptp_instance_assign(hostname, name)
            validate_equals(system_host_ptp_instance_output.get_host_ptp_instance_for_name(name).get_service(), service, "assign PTP host instance")

    def ptp_instance_parameter_add(self, ptp_instance_obj: PTPSetup):
        """
        Add ptp instance parameter and validate

        Args:
            ptp_instance_obj : PTP instance setup object
            name : name of instance
        """
        name = ptp_instance_obj.get_name()
        instance_parameters = ptp_instance_obj.get_instance_parameters()
        if not instance_parameters:
            get_logger().log_debug(f"PTP instance parameters were not found for {name}")
            return

        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_active_controller_ssh()
        system_ptp_instance_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)

        system_ptp_instance_parameter_output = system_ptp_instance_parameter_keywords.system_ptp_instance_parameter_add(name, instance_parameters)
        self.validate_parameters(system_ptp_instance_parameter_output.get_ptp_instance_parameters(), instance_parameters, "add PTP instance parameters")

    def ptp_interfaces_add_and_assign_hosts(self, ptp_instance_obj: PTPSetup):
        """
        Add ptp interfaces, assign hosts and validate

        Args:
            ptp_instance_obj : PTP instance setup object
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_active_controller_ssh()
        system_ptp_interface_keywords = SystemPTPInterfaceKeywords(ssh_connection)
        system_host_if_ptp_keywords = SystemHostIfPTPKeywords(ssh_connection)

        name = ptp_instance_obj.get_name()
        ptp_host_ifs = ptp_instance_obj.get_ptp_interfaces()

        hosts = SystemHostListKeywords(ssh_connection).get_system_host_list().get_controllers_and_computes()

        for ptp_host_if in ptp_host_ifs:
            interface_name = ptp_host_if.get_name()
            system_ptp_interface_output = system_ptp_interface_keywords.system_ptp_interface_add(interface_name, name)
            validate_equals(system_ptp_interface_output.get_ptp_interface().get_ptp_instance_name(), name, "PTP instance name of the PTP interface")
            validate_str_contains(system_ptp_interface_output.get_ptp_interface().get_name(), interface_name, "add PTP interface")

            for host in hosts:
                hostname = host.get_host_name()
                interfaces = ptp_host_if.get_interfaces_for_hostname(hostname)
                for interface in filter(None, interfaces):
                    system_host_if_ptp_keywords.system_host_if_ptp_assign(hostname, interface, interface_name)
                    system_ptp_interface_show_output = system_ptp_interface_keywords.get_system_ptp_interface_show(interface_name)
                    validate_str_contains(system_ptp_interface_show_output.get_ptp_interface().get_interface_names(), f"{hostname}/{interface}", f"assign ptp interface for {hostname}")

            ptp_interface_parameters = ptp_host_if.get_ptp_interface_parameter()
            if ptp_interface_parameters:
                system_ptp_interface_parameter_add_output = system_ptp_interface_keywords.system_ptp_interface_parameter_add(interface_name, ptp_interface_parameters)
                self.validate_parameters(system_ptp_interface_parameter_add_output.get_ptp_interface_parameters(), ptp_interface_parameters, "add PTP interface parameters")

    def validate_parameters(self, observed_value: str, expected_value: str, validation_description: str) -> None:
        """
        This function will validate if the observed value matches the expected value with associated logging.

        Args:
            observed_value (str): Value that we see on the system.
            expected_value (str): Value that is expected and against which we are asserting.
            validation_description (str): Description of this validation for logging purposes.

        Returns: None

        Raises:
            Exception: raised when validate fails
        """
        validate_equals(set(observed_value.split()), set(expected_value.split()), validation_description)

    def wait_for_ptp_configuration_to_update_after_applying(self) -> None:
        """
        Wait for the PTP configuration to update after applying

        Returns: None

        Raises:
            TimeoutError: raised when validate does not equal in the required time
        """
        gnss_keywords = GnssKeywords()

        # wait for systemctl status
        def check_ptp4l_status() -> bool:
            """
            Checks if the PTP4L service is active and running.

            Returns:
                bool: True if the service is active and running, False otherwise.
            """
            ptp4l_status_output = SystemCTLStatusKeywords(self.ssh_connection).get_status("ptp4l@*")
            return any("Active: active (running)" in line for line in ptp4l_status_output or [])

        validate_equals_with_retry(check_ptp4l_status, True, "systemctl status for ptp4l", 120, 30)

        # wait for SMA status
        check_sma_status = False
        for clock_instance_obj in self.clock_setup_list:

            ifaces_to_check = [(host, iface) for host in clock_instance_obj.get_instance_hostnames() for ptp_host_if in clock_instance_obj.get_ptp_interfaces() if "input" in ptp_host_if.get_ptp_interface_parameter() for iface in filter(None, ptp_host_if.get_interfaces_for_hostname(host))]

            for host, interface in ifaces_to_check:
                pci_address = gnss_keywords.get_pci_slot_name(host, interface)
                cgu_location = f"/sys/kernel/debug/ice/{pci_address}/cgu"
                gnss_keywords.validate_gnss_1pps_state_and_pps_dpll_status(host, cgu_location, "SMA1", "valid", ["locked_ho_acq"], 120, 30)
                check_sma_status = True
                break

            if check_sma_status:
                break

        # wait for GNSS status
        check_gnss_status = False
        for ts2phc_instance_obj in self.ts2phc_setup_list:
            expected_gnss_port = gnss_keywords.extract_gnss_port(ts2phc_instance_obj.get_instance_parameters())
            if not expected_gnss_port:
                continue
            ifaces_to_check = [(host, iface) for host in ts2phc_instance_obj.get_instance_hostnames() for ptp_host_if in ts2phc_instance_obj.get_ptp_interfaces() for iface in filter(None, ptp_host_if.get_interfaces_for_hostname(host)) if gnss_keywords.get_gnss_serial_port_from_gnss_directory(host, iface) == expected_gnss_port]
            for host, interface in ifaces_to_check:
                pci_address = gnss_keywords.get_pci_slot_name(host, interface)
                cgu_location = f"/sys/kernel/debug/ice/{pci_address}/cgu"
                gnss_keywords.validate_gnss_1pps_state_and_pps_dpll_status(host, cgu_location, "GNSS-1PPS", "valid", ["locked_ho_acq"], 120, 30)
                check_gnss_status = True
                break

            if check_gnss_status:
                break

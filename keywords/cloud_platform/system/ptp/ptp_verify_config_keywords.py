import re
from typing import Any, Dict

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_list_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.linux.systemctl.systemctl_status_keywords import SystemCTLStatusKeywords
from keywords.ptp.cat.cat_clock_conf_keywords import CatClockConfKeywords
from keywords.ptp.cat.cat_ptp_cgu_keywords import CatPtpCguKeywords
from keywords.ptp.cat.cat_ptp_config_keywords import CatPtpConfigKeywords
from keywords.ptp.gnss_keywords import GnssKeywords
from keywords.ptp.pmc.pmc_keywords import PMCKeywords
from keywords.ptp.setup.ptp_setup_reader import PTPSetupKeywords


class PTPVerifyConfigKeywords(BaseKeyword):
    """
    Verify all PTP configurations using given SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection, ptp_setup_template_path):
        """
        Initializes the PTPVerifyConfigKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
            ptp_setup_template_path : ptp setup template path
        """
        self.ssh_connection = ssh_connection
        ptp_setup_keywords = PTPSetupKeywords()
        ptp_setup = ptp_setup_keywords.generate_ptp_setup_from_template(ptp_setup_template_path)
        self.ptp_setup = ptp_setup

        self.ptp4l_setup_list = ptp_setup.get_ptp4l_setup_list()
        self.phc2sys_setup_list = ptp_setup.get_phc2sys_setup_list()
        self.ts2phc_setup_list = ptp_setup.get_ts2phc_setup_list()
        self.clock_setup_list = ptp_setup.get_clock_setup_list()

        self.ptp4l_expected_list_objects = ptp_setup.get_expected_ptp4l_list()
        self.expected_parent_data_set_object = ptp_setup.get_parent_data_set()
        self.expected_time_properties_data_set_object = ptp_setup.get_time_properties_data_set()
        self.expected_grandmaster_settings_tbc_object = ptp_setup.get_grandmaster_settings_tbc()
        self.expected_grandmaster_settings_tgm_object = ptp_setup.get_grandmaster_settings_tgm()

    def verify_all_ptp_configurations(self) -> None:
        """
        verify all ptp configurations

        Returns: None
        """
        hosts = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_controllers_and_computes()

        self.verify_gnss_status(hosts)

        self.verify_sma_status(hosts)

        self.verify_systemctl_status()

        self.verify_ptp_pmc_values()

        self.verify_ptp_config_file_content()

        validate_equals_with_retry(self.no_alarms, True, "Validate that no alarms on the system", 300)

    def verify_gnss_status(self, hosts: list) -> None:
        """
        verify GNSS status

        Args:
            hosts (list): list of controllers and computes

        Returns: None
        """
        gnss_keywords = GnssKeywords()

        for ts2phc_instance_obj in self.ts2phc_setup_list:
            expected_gnss_port = gnss_keywords.extract_gnss_port(ts2phc_instance_obj.get_instance_parameters())

            if not expected_gnss_port:  # No need to verify GNSS status if ts2phc.nmea_serialport not configured
                get_logger().log_info("Validation skipped as expected; GNSS port is None")
                continue

            for ptp_host_if in ts2phc_instance_obj.get_ptp_interfaces():
                for host in hosts:
                    interfaces = ptp_host_if.get_interfaces_for_hostname(host.get_host_name())
                    for interface in filter(None, interfaces):  # Skip None or empty values
                        self.validate_gnss_status_on_hostname(host.get_host_name(), interface, expected_gnss_port)

    def verify_sma_status(self, hosts: list) -> None:
        """
        verify SMA status

        Args:
            hosts (list): list of controllers and computes

        Returns: None
        """
        for clock_instance_obj in self.clock_setup_list:
            for ptp_host_if in clock_instance_obj.get_ptp_interfaces():
                if "input" not in ptp_host_if.get_ptp_interface_parameter():
                    continue

                for host in hosts:
                    interfaces = ptp_host_if.get_interfaces_for_hostname(host.get_host_name())
                    for interface in filter(None, interfaces):
                        self.validate_sma_status_on_hostname(host.get_host_name(), interface)

    def verify_systemctl_status(self) -> None:
        """
        verify ptp systemctl ptp services status

        Returns: None
        """
        systemctl_status_Keywords = SystemCTLStatusKeywords(self.ssh_connection)

        for service_type, setup_list in [
            ("ptp4l", self.ptp4l_setup_list),
            ("phc2sys", self.phc2sys_setup_list),
            ("ts2phc", self.ts2phc_setup_list),
        ]:
            for instance_obj in setup_list:
                name = instance_obj.get_name()
                service_name = f"{service_type}@{name}.service"
                hostnames = instance_obj.get_instance_hostnames()
                instance_parameters = instance_obj.get_instance_parameters()

                for hostname in hostnames:
                    if service_type == "phc2sys":
                        systemctl_status_Keywords.verify_ptp_status_and_instance_parameters_on_hostname(hostname, name, service_name, instance_parameters)
                    else:
                        systemctl_status_Keywords.verify_status_on_hostname(hostname, name, service_name)

    def verify_ptp_config_file_content(self) -> None:
        """
        Verify ptp config file content

        Returns: None
        """
        for service_type, setup_list in [
            ("ptp4l", self.ptp4l_setup_list),
            ("ts2phc", self.ts2phc_setup_list),
            ("clock", self.clock_setup_list),
        ]:
            for instance_obj in setup_list:
                config_file = f"/etc/linuxptp/ptpinstance/{service_type}-{instance_obj.get_name()}.conf" if service_type != "clock" else "/etc/linuxptp/ptpinstance/clock-conf.conf"
                hostnames = instance_obj.get_instance_hostnames()
                for hostname in hostnames:
                    if service_type == "clock":
                        self.validate_ptp_config_file_content_for_clock(instance_obj, hostname, config_file)
                    else:
                        self.validate_ptp_config_file_content(instance_obj, hostname, config_file)

    def verify_ptp_pmc_values(self) -> None:
        """
        verify ptp pmc values

        Returns: None
        """
        port_data_set = self.get_port_data_set_using_interface_and_port_identity_mapping()

        validate_parent = bool(self.expected_parent_data_set_object)
        validate_time_props = bool(self.expected_time_properties_data_set_object)

        if not validate_parent:
            get_logger().log_info("Validation skipped as expected; expected_parent_data_set_object is None")
        if not validate_time_props:
            get_logger().log_info("Validation skipped as expected; expected_time_properties_data_set_object is None")

        for ptp4l_instance_obj in self.ptp4l_setup_list:
            name = ptp4l_instance_obj.get_name()
            config_file = f"/etc/linuxptp/ptpinstance/ptp4l-{name}.conf"
            socket_file = f"/var/run/ptp4l-{name}"

            instance_parameters = ptp4l_instance_obj.get_instance_parameters()
            ptp_role = self.ptp_setup.get_ptp4l_expected_by_name(name).get_ptp_role()

            for hostname in ptp4l_instance_obj.get_instance_hostnames():

                self.validate_port_data_set(hostname, name, config_file, socket_file)

                self.validate_get_domain(hostname, instance_parameters, config_file, socket_file)

                if validate_parent:
                    self.validate_parent_data_set(hostname, name, port_data_set, config_file, socket_file)

                if validate_time_props:
                    self.validate_time_properties_data_set(hostname, config_file, socket_file)

                self.validate_grandmaster_settings_np(hostname, ptp_role, config_file, socket_file)

    def validate_gnss_status_on_hostname(self, hostname: str, interface: str, expected_gnss_port: str) -> None:
        """
        Validate GNSS status on the hostname

        Args:
            hostname (str): The name of the host.
            interface (str): The name of the ptp interface (e.g., "enp138s0f0").
            expected_gnss_port (str): Expected GNSS serial port value

        Returns: None
        """
        gnss_keywords = GnssKeywords()

        input_name = "GNSS-1PPS"
        expected_gnss_1pps_state = "valid"
        expected_dpll_status = "locked_ho_acq"

        observed_gnss_port = gnss_keywords.get_gnss_serial_port_from_gnss_directory(hostname, interface)
        if expected_gnss_port == observed_gnss_port:
            pci_address = gnss_keywords.get_pci_slot_name(hostname, interface)
            cgu_location = f"/sys/kernel/debug/ice/{pci_address}/cgu"
            self.validate_cgu_input_and_dpll_status(hostname, cgu_location, input_name, expected_gnss_1pps_state, expected_dpll_status)
        else:
            get_logger().log_info(f"Validation skipped; GNSS port does not match for hostname {hostname} and interface {interface}")
            get_logger().log_info(f"Expected GNSS port: {expected_gnss_port}")
            get_logger().log_info(f"Observed GNSS port: {observed_gnss_port}")

    def validate_sma_status_on_hostname(self, hostname: str, interface: str) -> None:
        """
        Validate SMA status on the hostname

        Args:
            hostname (str): The name of the host.
            interface (str): The name of the ptp interface (e.g., "enp138s0f0").

        Returns: None
        """
        gnss_keywords = GnssKeywords()

        input_name = "SMA1"
        expected_sma1_state = "valid"
        expected_dpll_status = "locked_ho_acq"

        pci_address = gnss_keywords.get_pci_slot_name(hostname, interface)
        cgu_location = f"/sys/kernel/debug/ice/{pci_address}/cgu"
        self.validate_cgu_input_and_dpll_status(hostname, cgu_location, input_name, expected_sma1_state, expected_dpll_status)

    def validate_cgu_input_and_dpll_status(
        self,
        hostname: str,
        cgu_location: str,
        input_name: str,
        expected_input_state: str,
        expected_status: str,
    ) -> None:
        """
        Validates the cgu and dpll status.

        Args:
            hostname (str): The name of the host.
            cgu_location (str): the cgu location.
            input_name (str): the cgu input name.
            expected_input_state (str): The expected cgu input state.
            expected_status (str): expected of DPLL status.

        Returns: None

        Raises:
            Exception: raised when validate fails
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)
        cat_ptp_cgu_keywords = CatPtpCguKeywords(ssh_connection)

        ptp_cgu_output = cat_ptp_cgu_keywords.cat_ptp_cgu(cgu_location)
        ptp_cgu_component = ptp_cgu_output.get_cgu_component()

        input_object = ptp_cgu_component.get_cgu_input(input_name)
        state = input_object.get_state()

        eec_dpll_object = ptp_cgu_component.get_eec_dpll()
        eec_dpll_current_reference = eec_dpll_object.get_current_reference()
        eec_dpll_status = eec_dpll_object.get_status()

        pps_dpll_object = ptp_cgu_component.get_pps_dpll()
        pps_dpll_current_reference = pps_dpll_object.get_current_reference()
        pps_dpll_status = pps_dpll_object.get_status()

        if state == expected_input_state and eec_dpll_current_reference == input_name and eec_dpll_status == expected_status and pps_dpll_current_reference == input_name and pps_dpll_status == expected_status:
            get_logger().log_info(f"Validation Successful - {input_name} state and DPLL status")
        else:
            get_logger().log_info(f"Validation Failed - {input_name} state and DPLL status")
            get_logger().log_info(f"Expected {input_name}: {expected_input_state}")
            get_logger().log_info(f"Observed {input_name}: {state}")

            get_logger().log_info(f"Expected EEC DPLL current refrence: {input_name}")
            get_logger().log_info(f"Observed EEC DPLL current refrence: {eec_dpll_current_reference}")
            get_logger().log_info(f"Expected EEC DPLL status: {expected_status}")
            get_logger().log_info(f"Observed EEC DPLL status: {eec_dpll_status}")

            get_logger().log_info(f"Expected PPS DPLL current refrence: {input_name}")
            get_logger().log_info(f"Observed PPS DPLL current refrence: {pps_dpll_current_reference}")
            get_logger().log_info(f"Expected PPS DPLL status: {expected_status}")
            get_logger().log_info(f"Observed PPS DPLL status: {pps_dpll_status}")

            raise Exception("Validation Failed")

    def validate_ptp_config_file_content(
        self,
        ptp_instance_obj: Any,
        hostname: str,
        config_file: str,
    ) -> None:
        """
        Validates the ptp config file content.

        Args:
            ptp_instance_obj (Any) : PTP instance setup object
            hostname (str): The name of the host.
            config_file (str): the config file.

        Returns: None

        Raises:
            Exception: raised when validate fails
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)

        cat_ptp_config_keywords = CatPtpConfigKeywords(ssh_connection)
        cat_ptp_config_output = cat_ptp_config_keywords.cat_ptp_config(config_file)
        get_pmc_get_default_data_set_object = cat_ptp_config_output.data_set_output.get_pmc_get_default_data_set_object()

        instance_parameters = ptp_instance_obj.get_instance_parameters()
        parameters = self.parse_instance_parameters_string(instance_parameters)

        expected_ts2phc_nmea_serialport = parameters.get("ts2phc.nmea_serialport")
        if expected_ts2phc_nmea_serialport:
            observed_expected_ts2phc_nmea_serialport = get_pmc_get_default_data_set_object.get_ts2phc_nmea_serialport()
            validate_equals(observed_expected_ts2phc_nmea_serialport, expected_ts2phc_nmea_serialport, "ts2phc.nmea_serialport value within PTP config file content")

        expected_boundary_clock_jbod = parameters.get("boundary_clock_jbod")
        if expected_boundary_clock_jbod:
            observed_boundary_clock_jbod = get_pmc_get_default_data_set_object.get_boundary_clock_jbod()
            validate_equals(observed_boundary_clock_jbod, expected_boundary_clock_jbod, "boundary_clock_jbod value within PTP config file content")

        expected_dataset_comparison = parameters.get("dataset_comparison")
        if expected_dataset_comparison:
            observed_dataset_comparison = get_pmc_get_default_data_set_object.get_dataset_comparison()
            validate_equals(observed_dataset_comparison, expected_dataset_comparison, "dataset_comparison value within PTP config file content")

        expected_domain_number = parameters.get("domainNumber")
        if expected_domain_number:
            observed_domain_number = get_pmc_get_default_data_set_object.get_domain_number()
            validate_equals(observed_domain_number, expected_domain_number, "domainNumber value within PTP config file content")

        expected_priority1 = parameters.get("priority1")
        if expected_priority1:
            observed_priority1 = get_pmc_get_default_data_set_object.get_priority1()
            validate_equals(observed_priority1, expected_priority1, "priority1 value within PTP config file content")

        expected_priority2 = parameters.get("priority2")
        if expected_priority2:
            observed_priority2 = get_pmc_get_default_data_set_object.get_priority2()
            validate_equals(observed_priority2, expected_priority2, "priority2 value within PTP config file content")

        expected_tx_timestamp_timeout = parameters.get("tx_timestamp_timeout")
        if expected_tx_timestamp_timeout:
            observed_tx_timestamp_timeout = get_pmc_get_default_data_set_object.get_tx_timestamp_timeout()
            validate_equals(observed_tx_timestamp_timeout, expected_tx_timestamp_timeout, "tx_timestamp_timeout value within PTP config file content")

        expected_associated_interfaces = [interface for ptp_host_if in ptp_instance_obj.get_ptp_interfaces() for interface in ptp_host_if.get_interfaces_for_hostname(hostname) if interface]

        observed_associated_interfaces = cat_ptp_config_output.get_associated_interfaces()
        validate_equals(observed_associated_interfaces, expected_associated_interfaces, "Associated interfaces within PTP config file content")

    def validate_ptp_config_file_content_for_clock(
        self,
        ptp_instance_obj: Any,
        hostname: str,
        config_file: str,
    ) -> None:
        """
        Validates the ptp config file content for clock.

        Args:
            ptp_instance_obj (Any): PTP instance setup object
            hostname (str): The name of the host.
            config_file (str): The config file.

        Raises:
            Exception: raised when validation fails
        """
        ssh_connection = LabConnectionKeywords().get_ssh_for_hostname(hostname)
        cat_ptp_config_output = CatClockConfKeywords(ssh_connection).cat_clock_conf(config_file)
        observed_clock_conf_objects = cat_ptp_config_output.get_clock_conf_objects()

        expected_config_by_ifname = {", ".join(sorted(interfaces)): ptp_if.get_ptp_interface_parameter() for ptp_if in ptp_instance_obj.get_ptp_interfaces() if (interfaces := ptp_if.get_interfaces_for_hostname(hostname))}

        # Validate each observed config against expected
        for observed_clock_conf_obj in observed_clock_conf_objects:
            observed_ifname = ", ".join(sorted(observed_clock_conf_obj.get_ifname().split(", ")))
            observed_sma_name = observed_clock_conf_obj.get_sma_name()
            observed_sma_mode = observed_clock_conf_obj.get_sma_mode()

            expected_params = expected_config_by_ifname.get(observed_ifname)
            if expected_params is None:
                raise Exception(f"No expected PTP config found for observed ifname: {observed_ifname}")

            if "=" not in expected_params:
                raise Exception(f"Expected parameter '{expected_params}' is not in 'name=mode' format")

            expected_sma_name, expected_sma_mode = expected_params.split("=", 1)

            validate_list_contains(observed_sma_name, expected_sma_name, "sma name value within PTP config file content for clock-conf.conf")
            validate_list_contains(observed_sma_mode, expected_sma_mode, "sma mode value within PTP config file content for clock-conf.conf")

    def validate_port_data_set(
        self,
        hostname: str,
        name: str,
        config_file: str,
        socket_file: str,
    ) -> None:
        """
        Validates the get port data set.

        Args:
            hostname (str): The name of the host.
            name (str): The ptp instance name
            config_file (str): the config file.
            socket_file (str): the socket file.

        Returns: None

        Raises:
            Exception: raised when validate fails
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)
        pmc_keywords = PMCKeywords(ssh_connection)

        ptp4l_expected_obj = self.ptp_setup.get_ptp4l_expected_by_name(name)
        expected_port_data_set_objects = ptp4l_expected_obj.get_port_data_set_for_hostname(hostname)
        observed_port_data_set_objects = pmc_keywords.pmc_get_port_data_set(config_file, socket_file).get_pmc_get_port_data_set_objects()

        if len(observed_port_data_set_objects) > len(expected_port_data_set_objects):
            raise Exception("Observed port data set objects contains more entries than expected port data set objects")

        for expected_port_data_set_obj, observed_port_data_set_obj in zip(expected_port_data_set_objects, observed_port_data_set_objects):
            validate_equals(observed_port_data_set_obj.get_port_state(), expected_port_data_set_obj.get_port_state(), "portState value within GET PORT_DATA_SET")

    def validate_get_domain(
        self,
        hostname: str,
        instance_parameters: str,
        config_file: str,
        socket_file: str,
    ) -> None:
        """
        Validates the get domain number.

        Args:
            hostname (str): The name of the host.
            instance_parameters (str): instance parameters
            config_file (str): the config file.
            socket_file (str): the socket file.

        Returns: None

        Raises:
            Exception: raised when validate fails
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)
        pmc_keywords = PMCKeywords(ssh_connection)

        parameters = self.parse_instance_parameters_string(instance_parameters)
        expected_domain_number = parameters.get("domainNumber")

        get_domain_output = pmc_keywords.pmc_get_domain(config_file, socket_file)
        observed_domain_number = get_domain_output.get_pmc_get_domain_object().get_domain_number()

        validate_equals(observed_domain_number, expected_domain_number, "domainNumber value within GET DOMAIN")

    def validate_parent_data_set(
        self,
        hostname: str,
        name: str,
        port_data_set: Dict,
        config_file: str,
        socket_file: str,
    ) -> None:
        """
        Validates the get parent data set.

        Args:
            hostname (str): The name of the host.
            name (str): The ptp instance name
            port_data_set (Dict): port data set using interface and port indentity mapping
            config_file (str): the config file.
            socket_file (str): the socket file.

        Returns: None

        Raises:
            Exception: raised when validate fails
        """

        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)
        pmc_keywords = PMCKeywords(ssh_connection)

        parent_data_set_obj = pmc_keywords.pmc_get_parent_data_set(config_file, socket_file).get_pmc_get_parent_data_set_object()

        validate_equals(parent_data_set_obj.get_gm_clock_class(), self.expected_parent_data_set_object.get_gm_clock_class(), "gm.ClockClass value within GET PARENT_DATA_SET")
        validate_equals(parent_data_set_obj.get_gm_clock_accuracy(), self.expected_parent_data_set_object.get_gm_clock_accuracy(), "gm.ClockAccuracy value within GET PARENT_DATA_SET")
        validate_equals(parent_data_set_obj.get_gm_offset_scaled_log_variance(), self.expected_parent_data_set_object.get_gm_offset_scaled_log_variance(), "gm.OffsetScaledLogVariance value within GET PARENT_DATA_SET")

        # Validates the parentPortIdentity of the SLAVE's PARENT_DATA_SET against the portIdentity of the MASTER's PORT_DATA_SET.
        if not port_data_set:
            return

        ptp4l_expected_obj = self.ptp_setup.get_ptp4l_expected_by_name(name)
        expected_port_data_set_objects = ptp4l_expected_obj.get_port_data_set_for_hostname(hostname)
        observed_parent_port_identity = parent_data_set_obj.get_parent_port_identity()

        for expected_port_data_set_obj in expected_port_data_set_objects:

            parent_port_identity_info = expected_port_data_set_obj.get_parent_port_identity()
            if not parent_port_identity_info:
                continue

            parent_instance_name = parent_port_identity_info.get("name")
            parent_hostname = parent_port_identity_info.get("hostname")
            parent_interface = parent_port_identity_info.get("interface")

            if not all([parent_instance_name, parent_hostname, parent_interface]):
                continue  # Skip incomplete entries

            for observed_port_data_set in port_data_set:
                if observed_port_data_set.get("name") == parent_instance_name and observed_port_data_set.get("hostname") == parent_hostname and parent_interface in observed_port_data_set:
                    expected_port_identity = observed_port_data_set.get(parent_interface)
                    validate_equals(observed_parent_port_identity, expected_port_identity, "Parent port identity matches the master port identity")

    def validate_time_properties_data_set(
        self,
        hostname: str,
        config_file: str,
        socket_file: str,
    ) -> None:
        """
        Validates the get time properties data set.

        Args:
            hostname (str): The name of the host.
            config_file (str): the config file.
            socket_file (str): the socket file.

        Returns: None

        Raises:
            Exception: raised when validate fails
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)
        pmc_keywords = PMCKeywords(ssh_connection)

        expected_current_utc_offset = self.expected_time_properties_data_set_object.get_current_utc_offset()
        expected_current_utc_offset_valid = self.expected_time_properties_data_set_object.get_current_utc_offset_valid()
        expected_time_traceable = self.expected_time_properties_data_set_object.get_time_traceable()
        expected_frequency_traceable = self.expected_time_properties_data_set_object.get_frequency_traceable()

        get_time_properties_data_set_output = pmc_keywords.pmc_get_time_properties_data_set(config_file, socket_file)
        get_time_properties_data_set_object = get_time_properties_data_set_output.get_pmc_get_time_properties_data_set_object()
        observed_current_utc_offset = get_time_properties_data_set_object.get_current_utc_offset()
        observed_current_utc_off_set_valid = get_time_properties_data_set_object.get_current_utc_off_set_valid()
        observed_time_traceable = get_time_properties_data_set_object.get_time_traceable()
        observed_frequency_traceable = get_time_properties_data_set_object.get_frequency_traceable()

        validate_equals(observed_current_utc_offset, expected_current_utc_offset, "currentUtcOffset value within GET TIME_PROPERTIES_DATA_SET")
        validate_equals(observed_current_utc_off_set_valid, expected_current_utc_offset_valid, "currentUtcOffsetValid value within GET TIME_PROPERTIES_DATA_SET")
        validate_equals(observed_time_traceable, expected_time_traceable, "timeTraceable value within GET TIME_PROPERTIES_DATA_SET")
        validate_equals(observed_frequency_traceable, expected_frequency_traceable, "frequencyTraceable value within GET TIME_PROPERTIES_DATA_SET")

    def validate_grandmaster_settings_np(
        self,
        hostname: str,
        ptp_role: str,
        config_file: str,
        socket_file: str,
    ) -> None:
        """
        Validates the get grandmaster settings np.

        Args:
            hostname (str): The name of the host.
            ptp_role (str): state of the port (e.g., MASTER and SLAVE)
            config_file (str): the config file.
            socket_file (str): the socket file.

        Returns: None

        Raises:
            Exception: raised when validate fails
        """
        expected_grandmaster_settings_object_map = {"tgm": self.expected_grandmaster_settings_tgm_object, "tbc": self.expected_grandmaster_settings_tbc_object}

        expected_grandmaster_settings_object = expected_grandmaster_settings_object_map.get(ptp_role)

        if not expected_grandmaster_settings_object:
            get_logger().log_info(f"Validation skipped as expected; expected_grandmaster_settings_{ptp_role}_object is None")
            return

        expected_clock_class = expected_grandmaster_settings_object.get_clock_class()
        expected_clock_accuracy = expected_grandmaster_settings_object.get_clock_accuracy()
        expected_offset_scaled_log_variance = expected_grandmaster_settings_object.get_offset_scaled_log_variance()
        expected_time_traceable = expected_grandmaster_settings_object.get_time_traceable()
        expected_frequency_traceable = expected_grandmaster_settings_object.get_frequency_traceable()
        expected_time_source = expected_grandmaster_settings_object.get_time_source()
        expected_current_utc_offset_valid = expected_grandmaster_settings_object.get_current_utc_offset_valid()

        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)
        pmc_keywords = PMCKeywords(ssh_connection)
        get_grandmaster_settings_np_output = pmc_keywords.pmc_get_grandmaster_settings_np(config_file, socket_file)
        get_grandmaster_settings_np_object = get_grandmaster_settings_np_output.get_pmc_get_grandmaster_settings_np_object()
        observed_clock_class = get_grandmaster_settings_np_object.get_clock_class()
        observed_clock_accuracy = get_grandmaster_settings_np_object.get_clock_accuracy()
        observed_offset_scaled_log_variance = get_grandmaster_settings_np_object.get_offset_scaled_log_variance()
        observed_current_utc_offset_valid = get_grandmaster_settings_np_object.get_current_utc_off_set_valid()
        observed_time_traceable = get_grandmaster_settings_np_object.get_time_traceable()
        observed_frequency_traceable = get_grandmaster_settings_np_object.get_frequency_traceable()
        observed_time_source = get_grandmaster_settings_np_object.get_time_source()

        validate_equals(observed_clock_class, expected_clock_class, "clockClass value within GET GRANDMASTER_SETTINGS_NP")
        validate_equals(observed_clock_accuracy, expected_clock_accuracy, "clockAccuracy value within GET GRANDMASTER_SETTINGS_NP")
        validate_equals(observed_offset_scaled_log_variance, expected_offset_scaled_log_variance, "offsetScaledLogVariance value within GET GRANDMASTER_SETTINGS_NP")
        validate_equals(observed_current_utc_offset_valid, expected_current_utc_offset_valid, "currentUtcOffsetValid value within GET GRANDMASTER_SETTINGS_NP")
        validate_equals(observed_time_traceable, expected_time_traceable, "timeTraceable value within GET GRANDMASTER_SETTINGS_NP")
        validate_equals(observed_frequency_traceable, expected_frequency_traceable, "frequencyTraceable value within GET GRANDMASTER_SETTINGS_NP")
        validate_equals(observed_time_source, expected_time_source, "timeSource value within GET GRANDMASTER_SETTINGS_NP")

    def get_port_data_set_using_interface_and_port_identity_mapping(self) -> Dict:
        """
        Get port data set using interface and port identity mapping to validate the parentPortIdentity of the SLAVE's
        PARENT_DATA_SET against the portIdentity of the MASTER's PORT_DATA_SET.

        Returns:
            Dict: port data set using interface and port identity mapping
        """
        port_data_set_list = []
        lab_connect_keywords = LabConnectionKeywords()

        for ptp4l_instance_obj in self.ptp4l_setup_list:
            name = ptp4l_instance_obj.get_name()
            config_file = f"/etc/linuxptp/ptpinstance/ptp4l-{name}.conf"
            socket_file = f"/var/run/ptp4l-{name}"
            hostnames = ptp4l_instance_obj.get_instance_hostnames()

            ptp4l_expected_obj = self.ptp_setup.get_ptp4l_expected_by_name(name)

            for hostname in hostnames:
                ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)
                pmc_keywords = PMCKeywords(ssh_connection)

                expected_port_data_set_objects = ptp4l_expected_obj.get_port_data_set_for_hostname(hostname)

                get_port_data_set_output = pmc_keywords.pmc_get_port_data_set(config_file, socket_file)
                observed_port_data_set_objects = get_port_data_set_output.get_pmc_get_port_data_set_objects()

                if len(observed_port_data_set_objects) > len(expected_port_data_set_objects):
                    raise Exception("Observed port data set index exceeds expected port data set")

                port_data_set_dict = {"name": name, "hostname": hostname}

                for observed_port_data_set_obj, expected_port_data_set_obj in zip(observed_port_data_set_objects, expected_port_data_set_objects):
                    interface = expected_port_data_set_obj.get_interface()
                    port_data_set_dict[interface] = observed_port_data_set_obj.get_port_identity()

                port_data_set_list.append(port_data_set_dict)

        return port_data_set_list

    def parse_instance_parameters_string(self, instance_parameters: str) -> dict:
        """
        Parses a string containing instance parameters and returns a dictionary.

        Args:
            instance_parameters (str): A string containing instance parameters (e.g., "key1=value1 key2=value2").

        Returns:
            dict: A dictionary where keys are the instance parameter names and values are the
            corresponding values.  Returns an empty dictionary if the input string
            is empty or doesn't contain any valid parameters.
            Values are returned as integers if they consist only of digits,
            otherwise as strings.
        """
        parameters = {}
        # Split the string by spaces to get individual key-value pairs
        for item in instance_parameters.split():
            # boundary_clock_jbod=1
            match = re.search(r"([^=]+)=([^ ]+)", item)
            if match:
                key, value = match.groups()
                # Try converting the value to an integer; if it fails, keep it as a string
                try:
                    value = int(value)
                except ValueError:
                    pass
                parameters[key] = value
        return parameters

    def no_alarms(self) -> bool:
        """
        Checks if there are no alarms on the system

        Returns:
            bool: True if no alarms
        """
        alarms = AlarmListKeywords(self.ssh_connection).alarm_list()
        return not alarms

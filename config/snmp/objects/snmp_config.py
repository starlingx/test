import json5


class SNMPConfig:
    """Class to hold configuration for SNMP operations."""

    def __init__(self, config_file: str):
        """Constructor.

        Args:
            config_file (str): Path to configuration file.
        """
        with open(config_file) as json_data:
            config_dict = json5.load(json_data)

        # Application configuration
        self.snmp_app_name = config_dict["snmp_app_name"]
        self.snmp_namespace = config_dict["snmp_namespace"]
        self.snmp_package_path = config_dict["snmp_package_path"]

        # Configuration files
        self.config_file_ipv4 = config_dict["config_file_ipv4"]
        self.config_file_ipv6 = config_dict["config_file_ipv6"]
        self.port_config_file = config_dict["port_config_file"]
        self.policy_file_ipv4 = config_dict["policy_file_ipv4"]
        self.policy_file_ipv6 = config_dict["policy_file_ipv6"]
        self.port_restore_file = config_dict["port_restore_file"]

        # Authentication
        self.snmp_v3_username = config_dict["snmp_v3_username"]
        self.snmp_v3_auth_password = config_dict["snmp_v3_auth_password"]
        self.snmp_v3_priv_password = config_dict["snmp_v3_priv_password"]
        self.snmp_v2c_community = config_dict["snmp_v2c_community"]

        # Test alarm configuration
        self.test_alarm_id = config_dict["test_alarm_id"]
        self.test_entity_type_id = config_dict["test_entity_type_id"]
        self.test_entity_id = config_dict["test_entity_id"]
        self.test_severity = config_dict["test_severity"]
        self.test_reason_text = config_dict["test_reason_text"]
        self.test_alarm_type = config_dict["test_alarm_type"]

        # Network configuration
        self.active_alarm_oid = config_dict["active_alarm_oid"]
        self.default_udp_port = config_dict["default_udp_port"]
        self.get_timeout = config_dict["get_timeout"]
        self.snmp_server_ip = config_dict["snmp_server_ip"]
        self.snmp_server_port = config_dict["snmp_server_port"]
        self.trap_server_ip = config_dict["trap_server_ip"]
        self.trap_server_ipv6 = config_dict["trap_server_ipv6"]
        self.trap_server_port = config_dict["trap_server_port"]

        # Validation patterns
        self.required_config_patterns = config_dict["required_config_patterns"]
        self.alarm_patterns = config_dict["alarm_patterns"]

    def get_snmp_app_name(self) -> str:
        """Getter for SNMP app name.

        Returns:
            str: SNMP application name.
        """
        return self.snmp_app_name

    def get_trap_alarm_id(self) -> str:
        """Getter for trap alarm ID.

        Returns:
            str: Test alarm ID used for trap testing.
        """
        return self.test_alarm_id

    def get_snmp_server_address(self) -> str:
        """Getter for SNMP server address.

        Returns:
            str: SNMP server in ip:port format.
        """
        return f"{self.snmp_server_ip}:{self.snmp_server_port}"

    def get_trap_server_address(self) -> str:
        """Getter for trap server address.

        Returns:
            str: Trap server in ip:port format.
        """
        return f"{self.trap_server_ip}:{self.trap_server_port}"

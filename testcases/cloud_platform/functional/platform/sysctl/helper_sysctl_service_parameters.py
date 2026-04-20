from collections import namedtuple

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.bmc.redfish.chassis.power.redfish_chassis_power_keywords import RedFishChassisPowerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.ssh.ssh_keywords import SSHKeywords
from keywords.cloud_platform.sysctl.sysctl_keywords import SysctlKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.service.objects.system_service_parameter_object import SystemServiceParameterObject
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords

Constants = namedtuple("Constants", ["SERVICE", "SECTION"])
CONST = Constants(SERVICE="platform", SECTION="sysctl")

TESTDATA = [
    # (parameter, value, supported, modified_value)
    # -----------------------------
    # Can be modified by user via service parameter api
    # -----------------------------
    ("net.ipv4.tcp_rmem", "4096 87380 16777216", True, "8192 131072 33554432"),
    ("net.ipv4.tcp_wmem", "4096 65536 16777216", True, "8192 131072 33554432"),
    ("net.ipv4.tcp_mtu_probing", "1", True, "2"),
    ("net.ipv4.tcp_slow_start_after_idle", "0", True, "1"),
    ("net.netfilter.nf_conntrack_max", "2000000", True, "4000000"),
    ("net.netfilter.nf_conntrack_tcp_timeout_established", "86400", True, "172800"),
    ("vm.dirty_ratio", "15", True, "20"),
    ("vm.dirty_background_ratio", "5", True, "10"),
    ("vm.vfs_cache_pressure", "50", True, "100"),
    ("vm.min_free_kbytes", "65536", True, "131072"),
    ("kernel.msgmax", "65536", True, "131072"),
    ("kernel.msgmnb", "65536", True, "131072"),
    ("net.ipv4.neigh.default.gc_thresh1", "1024", True, "2048"),
    ("net.ipv4.neigh.default.gc_thresh2", "2048", True, "4096"),
    ("net.ipv4.neigh.default.gc_thresh3", "4096", True, "8192"),
    ("fs.inotify.max_user_watches", "524288", True, "1048576"),
    ("fs.inotify.max_user_instances", "512", True, "1024"),
    ("net.core.netdev_max_backlog", "5", True, "10"),
    ("fs.aio-max-nr", "1048576", True, "2097152"),
    ("vm.overcommit_ratio", "50", True, "75"),
    ("net.ipv4.ip_local_port_range", "10240 65535", True, "20480 65535"),
    ("net.ipv4.tcp_keepalive_time", "600", True, "1200"),
    ("net.ipv4.tcp_keepalive_intvl", "30", True, "60"),
    ("net.ipv4.tcp_keepalive_probes", "10", True, "15"),
    ("fs.protected_hardlinks", "1", True, "0"),
    ("fs.protected_symlinks", "1", True, "0"),
    ("net.ipv4.conf.all.accept_redirects", "0", True, "1"),
    ("net.ipv6.conf.all.accept_redirects", "0", True, "1"),
    # -----------------------------
    # Cannot be modified by user via service parameter api
    # -----------------------------
    # Kubelet will override
    ("vm.panic_on_oom", "0", False, "0"),
    ("vm.overcommit_memory", "0", False, "0"),
    ("kernel.panic", "0", False, "0"),
    ("kernel.panic_on_oops", "1", False, "1"),
    ("kernel.keys.root_maxkeys", "1000000", False, "1000000"),
    ("kernel.keys.root_maxbytes", "25000000", False, "25000000"),
    # Dangerous/ Considered unsafe to modify
    ("kernel.modules_disabled", "0", False, "0"),
    ("kernel.sysrq", "16", False, "16"),
    # Write-only / triggers an action
    ("vm.compact_memory", "1", False, "1"),
    ("vm.drop_caches", "0", False, "0"),
    # Read-only values
    ("kernel.arch", "x86_64", False, "x86_64"),
    ("kernel.bootloader_type", "114", False, "114"),
    ("kernel.bootloader_version", "2", False, "2"),
    ("kernel.cap_last_cap", "40", False, "40"),
    ("kernel.ngroups_max", "65536", False, "65536"),
    ("kernel.osrelease", "5.10.0", False, "5.10.0"),
    ("kernel.ostype", "Linux", False, "Linux"),
    ("kernel.random.boot_id", "b1a048d3-6dc2-4974-b46c-90b3c040c0e4", False, "b1a048d3-6dc2-4974-b46c-90b3c040c0e4"),
    ("kernel.random.entropy_avail", "256", False, "256"),
    ("kernel.random.poolsize", "4096", False, "4096"),
    ("kernel.random.uuid", "12345678-1234-1234-1234-123456789012", False, "12345678-1234-1234-1234-123456789012"),
    ("kernel.version", "#1 SMP", False, "#1 SMP"),
]


class HelperSysctlServiceParameters:
    """Helper class for testing sysctl service parameters via the platform service parameter API.

    Provides setup/teardown lifecycle methods that back up and restore existing sysctl
    service parameters, and a suite of reusable test operations for adding, modifying,
    and validating sysctl parameters across active controllers, standby controllers,
    compute nodes, and storage nodes. Also supports validation through host swact,
    lock/unlock, and Redfish power-cycle scenarios.
    """

    def __init__(self) -> None:
        self.lab_name: str = ConfigurationManager.get_lab_config().get_lab_name()
        self.ssh_oam_connection: SSHConnection
        self.current_parameters: list[SystemServiceParameterObject] = []
        self.service_parameter_keywords: SystemServiceParameterKeywords

    def setup_method(self):
        """Connect to the lab, back up existing sysctl service parameters, and delete them."""
        get_logger().log_setup_step(f"Connecting to lab: {self.lab_name}")
        self.ssh_oam_connection = LabConnectionKeywords().get_active_controller_ssh()
        self.service_parameter_keywords = SystemServiceParameterKeywords(self.ssh_oam_connection)
        self.current_parameters = self.service_parameter_keywords.list_service_parameters(
            service=CONST.SERVICE,
            section=CONST.SECTION,
        ).get_parameters()
        names = [parameter.get_name() for parameter in self.current_parameters]
        get_logger().log_setup_step(f"Backing up current sysctl service parameters: {names}")
        for parameter in self.current_parameters:
            self.service_parameter_keywords.delete_service_parameter(
                uuid=parameter.get_uuid(),
            )

    def teardown_method(self):
        """Delete any sysctl parameters created during the test and restore the original ones."""
        listed_parameters = self.service_parameter_keywords.list_service_parameters(
            service=CONST.SERVICE,
            section=CONST.SECTION,
        ).get_parameters()
        names = [parameter.get_name() for parameter in listed_parameters]
        get_logger().log_teardown_step(f"Cleaning up sysctl parameters: {names}")
        for parameter in listed_parameters:
            self.service_parameter_keywords.delete_service_parameter(
                uuid=parameter.get_uuid(),
            )

        names = [parameter.get_name() for parameter in self.current_parameters]
        get_logger().log_teardown_step(f"Restoring sysctl parameters: {names}")
        if self.current_parameters:
            parameters_list = [f'{parameter.get_name()}="{parameter.value}"' for parameter in self.current_parameters]
            parameters_str = " ".join(parameters_list)
            self.service_parameter_keywords.add_multiple_service_parameters(service=CONST.SERVICE, section=CONST.SECTION, parameters_str=parameters_str)
        lab_name = ConfigurationManager.get_lab_config().get_lab_name()
        get_logger().log_teardown_step(f"Disconnecting from lab: {lab_name}")
        SSHConnectionManager.remove_all()

    def _add_sysctl_parameter_expect_success(self, parameter: SystemServiceParameterObject) -> SystemServiceParameterObject:
        """Add a sysctl service parameter and validate that it was created successfully.

        Args:
            parameter (SystemServiceParameterObject): The service parameter object to add.

        Returns:
            SystemServiceParameterObject: The added service parameter object as returned by the API.
        """
        get_logger().log_info("Attempting to add sysctl service parameter " f"{parameter.get_name()}='{parameter.get_value()}' ")
        added_parameter = self.service_parameter_keywords.add_service_parameter(
            service=parameter.get_service(),
            section=parameter.get_section(),
            parameter_name=parameter.get_name(),
            parameter_value=parameter.get_value(),
        ).get_parameters()[0]
        get_logger().log_info(f"{added_parameter.get_name()} uuid='{added_parameter.get_uuid()}'")
        validate_equals(observed_value=added_parameter, expected_value=parameter, validation_description="Parameter was added and output matches")
        return added_parameter

    def _add_sysctl_parameter_expect_failure(self, parameter: SystemServiceParameterObject) -> str:
        """Attempt to add a sysctl service parameter and validate that the command is rejected.

        Args:
            parameter (SystemServiceParameterObject): The service parameter object expected to be rejected.

        Returns:
            str: The error output from the rejected add operation.
        """
        get_logger().log_info("Attempting to add sysctl service parameter (Should fail to add)" f"{parameter.get_name()}='{parameter.get_value()}' ")
        output_error_str = self.service_parameter_keywords.add_service_parameter_with_error(
            service=parameter.get_service(),
            section=parameter.get_section(),
            parameter_name=parameter.get_name(),
            parameter_value=parameter.get_value(),
        )
        get_logger().log_info(f"{parameter.get_name()} was not added as expected")
        return output_error_str

    def _modify_sysctl_parameter_expect_success(self, parameter: SystemServiceParameterObject) -> SystemServiceParameterObject:
        """Add a sysctl parameter then modify its value, validating both operations succeed.

        Args:
            parameter (SystemServiceParameterObject): The service parameter object containing initial and modified values.

        Returns:
            SystemServiceParameterObject: The modified service parameter object as returned by the API.
        """
        added_parameter = self._add_sysctl_parameter_expect_success(parameter=parameter)
        get_logger().log_info("Attempting to modify sysctl service parameter " f"{parameter.get_name()} " f'"{parameter.get_value()}" => "{parameter.get_modified_value()}"')
        modified_parameter = self.service_parameter_keywords.modify_service_parameter(
            service=parameter.get_service(),
            section=parameter.get_section(),
            parameter_name=parameter.get_name(),
            parameter_value=parameter.get_modified_value(),  # <=  modify value
        ).get_parameters()[0]
        get_logger().log_info(f"Modified {modified_parameter.get_name()} " f"value '{added_parameter.value}' => '{modified_parameter.value}' " f"uuid='{added_parameter.get_uuid()}'|'{modified_parameter.get_uuid()}'")
        validate_equals(observed_value=modified_parameter.get_uuid(), expected_value=added_parameter.get_uuid(), validation_description="uuid unchanged after modification")
        validate_equals(observed_value=modified_parameter, expected_value=modified_parameter, validation_description="Parameter was modified " "and output matches")
        return modified_parameter

    def _modify_sysctl_parameter_expect_failure(self, parameter: SystemServiceParameterObject) -> str:
        """Attempt to add and modify a sysctl parameter, validating both operations are rejected.

        Args:
            parameter (SystemServiceParameterObject): The service parameter object expected to be rejected.

        Returns:
            str: The error output from the rejected modify operation.
        """
        self._add_sysctl_parameter_expect_failure(parameter=parameter)
        get_logger().log_info("Attempting to modify sysctl service parameter (should fail)" f"{parameter.get_name()} " f'"{parameter.get_value()}" => "{parameter.get_modified_value()}"')
        output_error_str = self.service_parameter_keywords.modify_service_parameter_with_error(
            service=parameter.get_service(),
            section=parameter.get_section(),
            parameter_name=parameter.get_name(),
            parameter_value=parameter.get_modified_value(),  # <=  modify value
        )
        get_logger().log_info(f"{parameter.get_name()} was not modified as expected")
        return output_error_str

    def _redfish_power_cycle_virtual_lab(self, host_name: str) -> None:
        """Power-cycle a host in a virtual lab via Redfish and wait for it to come back online.

        Args:
            host_name (str): The name of the host to power-cycle.
        """
        credentials = ConfigurationManager.get_lab_config().get_admin_credentials()
        ssh_keywords = SSHKeywords(ssh_connection=self.ssh_oam_connection, ssh_username=credentials.get_user_name(), ssh_password=credentials.get_password())
        with ssh_keywords.tcp_forwarding_allowed():
            validate_equals_with_retry(function_to_execute=lambda: ssh_keywords.is_tcp_forwading_working(), expected_value=True, validation_description="TCP forwarding should be working", timeout=5, polling_sleep_time=1)
            with LabConnectionKeywords().create_bmc_ssh_tunnel(host_name) as ssh_tunnel:
                bmc_url = ssh_tunnel.get_tunnel_info().get_local_base_url()
                node = ConfigurationManager.get_lab_config().get_node(host_name)
                uptime = SystemHostListKeywords(self.ssh_oam_connection).get_uptime(host_name)
                redfish_power_keywords = RedFishChassisPowerKeywords(host=bmc_url, username=node.get_bm_username(), password=node.get_bm_password())
                redfish_power_keywords.power_cycle()
                SystemHostRebootKeywords(self.ssh_oam_connection).wait_for_force_reboot(host_name, uptime)

    def add_service_parameter_fails(self, unsupported_parameter: SystemServiceParameterObject) -> None:
        """Verify that adding an unsupported sysctl service parameter is rejected.

        Args:
            unsupported_parameter (SystemServiceParameterObject): The unsupported service parameter to attempt to add.
        """
        self._add_sysctl_parameter_expect_failure(parameter=unsupported_parameter)

    def modify_service_parameter_fails(self, unsupported_parameter: SystemServiceParameterObject) -> None:
        """Verify that modifying an unsupported sysctl service parameter is rejected.

        Args:
            unsupported_parameter (SystemServiceParameterObject): The unsupported service parameter to attempt to modify.
        """
        self._modify_sysctl_parameter_expect_failure(parameter=unsupported_parameter)

    def add_service_parameter_active_controller_success(
        self,
        supported_parameter: SystemServiceParameterObject,
    ) -> None:
        """Add a sysctl parameter and verify it takes effect on the active controller.

        If the current sysctl value already matches the parameter's value, the modified
        value is used instead to ensure a change is observable.

        Args:
            supported_parameter (SystemServiceParameterObject): The supported service parameter to add.
        """
        test_parameter = SystemServiceParameterObject(service=supported_parameter.get_service(), section=supported_parameter.get_section(), name=supported_parameter.get_name(), value=supported_parameter.get_value())
        sysctl_keywords = SysctlKeywords(self.ssh_oam_connection)

        def get_sysctl_value():
            return sysctl_keywords.get_sysctl_value(test_parameter.get_name())

        current_value = get_sysctl_value()
        get_logger().log_info(f"Value of '{test_parameter.get_name()}' on Active Controller is '{current_value}'")
        if test_parameter.get_value() == current_value:
            test_parameter.set_value(supported_parameter.get_modified_value())

        self._add_sysctl_parameter_expect_success(parameter=test_parameter)

        validate_equals_with_retry(
            function_to_execute=get_sysctl_value,
            expected_value=test_parameter.get_value(),
            validation_description="Sysctl value should match",
        )

    def modify_service_parameter_active_controller_success(
        self,
        supported_parameter: SystemServiceParameterObject,
    ) -> None:
        """Add then modify a sysctl parameter and verify the modified value takes effect on the active controller.

        Args:
            supported_parameter (SystemServiceParameterObject): The supported service parameter with initial and modified values.
        """
        test_parameter = SystemServiceParameterObject(
            service=supported_parameter.get_service(),
            section=supported_parameter.get_section(),
            name=supported_parameter.get_name(),
            value=supported_parameter.get_value(),  # <= initial value
            modified_value=supported_parameter.get_modified_value(),  # <= modify value
        )
        sysctl_keywords = SysctlKeywords(self.ssh_oam_connection)

        def get_sysctl_value():
            return sysctl_keywords.get_sysctl_value(test_parameter.get_name())

        current_value = get_sysctl_value()
        get_logger().log_info(f"Value of '{test_parameter.get_name()}' on Active Controller is '{current_value}'")
        self._modify_sysctl_parameter_expect_success(parameter=test_parameter)

        validate_equals_with_retry(
            function_to_execute=get_sysctl_value,
            expected_value=test_parameter.get_modified_value(),  # <= modify value
            validation_description="Sysctl value should match",
        )

    def add_service_parameter_standby_controller_success(
        self,
        supported_parameter: SystemServiceParameterObject,
    ) -> None:
        """Add a sysctl parameter and verify it takes effect on the standby controller.

        If the current sysctl value already matches the parameter's value, the modified
        value is used instead to ensure a change is observable.

        Args:
            supported_parameter (SystemServiceParameterObject): The supported service parameter to add.
        """
        test_parameter = SystemServiceParameterObject(service=supported_parameter.get_service(), section=supported_parameter.get_section(), name=supported_parameter.get_name(), value=supported_parameter.get_value())
        standby_connection = LabConnectionKeywords().get_standby_controller_ssh()
        sysctl_keywords = SysctlKeywords(standby_connection)

        def get_sysctl_value():
            return sysctl_keywords.get_sysctl_value(test_parameter.get_name())

        current_value = get_sysctl_value()
        get_logger().log_info(f"Value of '{test_parameter.get_name()}' on Standby Controller is '{current_value}'")
        if test_parameter.get_value() == current_value:
            test_parameter.set_value(supported_parameter.get_modified_value())

        self._add_sysctl_parameter_expect_success(parameter=test_parameter)

        validate_equals_with_retry(
            function_to_execute=get_sysctl_value,
            expected_value=test_parameter.get_value(),
            validation_description="Sysctl value should match",
        )

    def add_service_parameter_and_swact_success(
        self,
        supported_parameter: SystemServiceParameterObject,
    ) -> None:
        """Add a sysctl parameter, perform two swacts, and verify the parameter persists each time.

        If the current sysctl value already matches the parameter's value, the modified
        value is used instead to ensure a change is observable.

        Args:
            supported_parameter (SystemServiceParameterObject): The supported service parameter to add.
        """
        parameter = SystemServiceParameterObject(service=supported_parameter.get_service(), section=supported_parameter.get_section(), name=supported_parameter.get_name(), value=supported_parameter.get_value())
        sysctl_keywords = SysctlKeywords(self.ssh_oam_connection)

        def get_sysctl_value():
            return sysctl_keywords.get_sysctl_value(parameter.get_name())

        current_value = get_sysctl_value()
        get_logger().log_info(f"Value of '{parameter.get_name()}' on the Active Controller is '{current_value}'")
        if parameter.get_value() == current_value:
            parameter.set_value(supported_parameter.get_modified_value())

        added_parameter = self._add_sysctl_parameter_expect_success(parameter=parameter)

        def swact_and_validate():
            swact_success = SystemHostSwactKeywords(self.ssh_oam_connection).host_swact()
            validate_equals(observed_value=swact_success, expected_value=True, validation_description="Swact was successful")
            show_parameter = self.service_parameter_keywords.show_service_parameter(uuid=added_parameter.get_uuid()).get_parameters()[0]
            validate_equals(observed_value=show_parameter, expected_value=parameter, validation_description="Parameter present after swact")
            validate_equals_with_retry(
                function_to_execute=get_sysctl_value,
                expected_value=parameter.get_value(),
                validation_description="Sysctl value should match",
            )

        swact_and_validate()
        swact_and_validate()

    def modify_service_parameter_standby_controller_success(
        self,
        supported_parameter: SystemServiceParameterObject,
    ) -> None:
        """Add then modify a sysctl parameter and verify the modified value takes effect on the standby controller.

        Args:
            supported_parameter (SystemServiceParameterObject): The supported service parameter with initial and modified values.
        """
        parameter = SystemServiceParameterObject(
            service=supported_parameter.get_service(),
            section=supported_parameter.get_section(),
            name=supported_parameter.get_name(),
            value=supported_parameter.get_value(),  # <= initial value
            modified_value=supported_parameter.get_modified_value(),  # <= modify value
        )
        standby_connection = LabConnectionKeywords().get_standby_controller_ssh()
        sysctl_keywords = SysctlKeywords(standby_connection)

        def get_sysctl_value():
            return sysctl_keywords.get_sysctl_value(parameter.get_name())

        current_value = get_sysctl_value()
        get_logger().log_info(f"Value of '{parameter.get_name()}' on Standby Controller is '{current_value}'")
        self._modify_sysctl_parameter_expect_success(parameter=parameter)

        validate_equals_with_retry(
            function_to_execute=get_sysctl_value,
            expected_value=parameter.get_modified_value(),  # <= modify value
            validation_description="Sysctl value should match",
        )

    def add_service_parameter_and_lock_unlock_standby_success(
        self,
        supported_parameter: SystemServiceParameterObject,
    ) -> None:
        """Add a sysctl parameter, lock/unlock the standby controller, and verify the parameter persists.

        If the current sysctl value already matches the parameter's value, the modified
        value is used instead to ensure a change is observable.

        Args:
            supported_parameter (SystemServiceParameterObject): The supported service parameter to add.
        """
        test_parameter = SystemServiceParameterObject(service=supported_parameter.get_service(), section=supported_parameter.get_section(), name=supported_parameter.get_name(), value=supported_parameter.get_value())

        standby_connection = LabConnectionKeywords().get_standby_controller_ssh()
        sysctl_keywords = SysctlKeywords(standby_connection)

        def get_sysctl_value():
            return sysctl_keywords.get_sysctl_value(test_parameter.get_name())

        current_value = get_sysctl_value()
        get_logger().log_info(f"Value of '{test_parameter.get_name()}' on Standby Controller is '{current_value}'")
        if test_parameter.get_value() == current_value:
            test_parameter.set_value(supported_parameter.get_modified_value())

        self._add_sysctl_parameter_expect_success(parameter=test_parameter)

        validate_equals_with_retry(
            function_to_execute=get_sysctl_value,
            expected_value=test_parameter.get_value(),
            validation_description="Sysctl value should match",
        )

        standby_host_name = SystemHostListKeywords(self.ssh_oam_connection).get_standby_controller().get_host_name()
        SystemHostLockKeywords(self.ssh_oam_connection).lock_host(standby_host_name)
        SystemHostLockKeywords(self.ssh_oam_connection).unlock_host(standby_host_name)

        validate_equals(
            observed_value=get_sysctl_value(),
            expected_value=test_parameter.get_value(),
            validation_description="Sysctl value should match after force restart",
        )

    def add_service_parameter_redfish_reboot_standby_virtual_lab_success(
        self,
        supported_parameter: SystemServiceParameterObject,
    ) -> None:
        """Add a sysctl parameter, Redfish power-cycle the standby controller, and verify the parameter persists.

        If the current sysctl value already matches the parameter's value, the modified
        value is used instead to ensure a change is observable.

        Args:
            supported_parameter (SystemServiceParameterObject): The supported service parameter to add.
        """
        test_parameter = SystemServiceParameterObject(service=supported_parameter.get_service(), section=supported_parameter.get_section(), name=supported_parameter.get_name(), value=supported_parameter.get_value())

        standby_connection = LabConnectionKeywords().get_standby_controller_ssh()
        sysctl_keywords = SysctlKeywords(standby_connection)

        def get_sysctl_value():
            return sysctl_keywords.get_sysctl_value(test_parameter.get_name())

        current_value = get_sysctl_value()
        get_logger().log_info(f"Value of '{test_parameter.get_name()}' on Standby Controller is '{current_value}'")
        if test_parameter.get_value() == current_value:
            test_parameter.set_value(supported_parameter.get_modified_value())

        self._add_sysctl_parameter_expect_success(parameter=test_parameter)

        validate_equals_with_retry(
            function_to_execute=get_sysctl_value,
            expected_value=test_parameter.get_value(),
            validation_description="Sysctl value should match",
        )

        standby_host_name = SystemHostListKeywords(self.ssh_oam_connection).get_standby_controller().get_host_name()
        self._redfish_power_cycle_virtual_lab(standby_host_name)

        validate_equals(
            observed_value=get_sysctl_value(),
            expected_value=test_parameter.get_value(),
            validation_description="Sysctl value should match after force restart",
        )

    def add_service_parameter_compute_nodes_success(
        self,
        supported_parameter: SystemServiceParameterObject,
    ) -> None:
        """Add a sysctl parameter and verify it takes effect on all compute nodes.

        Args:
            supported_parameter (SystemServiceParameterObject): The supported service parameter to add.
        """
        test_parameter = SystemServiceParameterObject(service=supported_parameter.get_service(), section=supported_parameter.get_section(), name=supported_parameter.get_name(), value=supported_parameter.get_value())
        host_list_keywords = SystemHostListKeywords(self.ssh_oam_connection)
        compute_connections: dict[str, SSHConnection] = {compute.get_host_name(): LabConnectionKeywords().get_compute_ssh(compute.get_host_name()) for compute in host_list_keywords.get_computes()}

        for compute_name, compute_connection in compute_connections.items():
            sysctl_keywords = SysctlKeywords(compute_connection)

            def get_sysctl_value():
                return sysctl_keywords.get_sysctl_value(test_parameter.get_name())

            current_value = get_sysctl_value()
            get_logger().log_info(f"Value of '{test_parameter.get_name()}' on '{compute_name}' is '{current_value}'")

        self._add_sysctl_parameter_expect_success(parameter=test_parameter)

        for compute_name, compute_connection in compute_connections.items():
            sysctl_keywords = SysctlKeywords(compute_connection)

            def get_sysctl_value():
                return sysctl_keywords.get_sysctl_value(test_parameter.get_name())

            validate_equals_with_retry(
                function_to_execute=get_sysctl_value,
                expected_value=test_parameter.get_value(),
                validation_description=f"Sysctl value on '{compute_name}' should match",
            )

    def modify_service_parameter_compute_nodes_success(
        self,
        supported_parameter: SystemServiceParameterObject,
    ) -> None:
        """Add then modify a sysctl parameter and verify the modified value takes effect on all compute nodes.

        Args:
            supported_parameter (SystemServiceParameterObject): The supported service parameter with initial and modified values.
        """
        test_parameter = SystemServiceParameterObject(
            service=supported_parameter.get_service(),
            section=supported_parameter.get_section(),
            name=supported_parameter.get_name(),
            value=supported_parameter.get_value(),  # <= initial value
            modified_value=supported_parameter.get_modified_value(),  # <= modify value
        )
        host_list_keywords = SystemHostListKeywords(self.ssh_oam_connection)
        compute_connections: dict[str, SSHConnection] = {compute.get_host_name(): LabConnectionKeywords().get_compute_ssh(compute.get_host_name()) for compute in host_list_keywords.get_computes()}
        for compute_name, compute_connection in compute_connections.items():
            sysctl_keywords = SysctlKeywords(compute_connection)
            current_value = sysctl_keywords.get_sysctl_value(test_parameter.get_name())
            get_logger().log_info(f"Value of '{test_parameter.get_name()}' on '{compute_name}' is '{current_value}'")

        self._modify_sysctl_parameter_expect_success(parameter=test_parameter)

        for compute_name, compute_connection in compute_connections.items():
            sysctl_keywords = SysctlKeywords(compute_connection)

            def get_sysctl_value():
                return sysctl_keywords.get_sysctl_value(test_parameter.get_name())

            validate_equals_with_retry(
                function_to_execute=get_sysctl_value,
                expected_value=test_parameter.get_modified_value(),
                validation_description=f"Sysctl value on '{compute_name}' should match",
            )

    def add_service_parameter_storage_nodes_success(
        self,
        supported_parameter: SystemServiceParameterObject,
    ) -> None:
        """Add a sysctl parameter and verify it takes effect on all storage nodes.

        Args:
            supported_parameter (SystemServiceParameterObject): The supported service parameter to add.
        """
        test_parameter = SystemServiceParameterObject(service=supported_parameter.get_service(), section=supported_parameter.get_section(), name=supported_parameter.get_name(), value=supported_parameter.get_value())
        host_list_keywords = SystemHostListKeywords(self.ssh_oam_connection)
        storage_connections: dict[str, SSHConnection] = {storage.get_host_name(): LabConnectionKeywords().get_storage_ssh(storage.get_host_name()) for storage in host_list_keywords.get_storages()}

        for storage_name, storage_connection in storage_connections.items():
            sysctl_keywords = SysctlKeywords(storage_connection)

            def get_sysctl_value():
                return sysctl_keywords.get_sysctl_value(test_parameter.get_name())

            current_value = get_sysctl_value()
            get_logger().log_info(f"Value of '{test_parameter.get_name()}' on '{storage_name}' is '{current_value}'")

        self._add_sysctl_parameter_expect_success(parameter=test_parameter)

        for storage_name, storage_connection in storage_connections.items():
            sysctl_keywords = SysctlKeywords(storage_connection)

            def get_sysctl_value():
                return sysctl_keywords.get_sysctl_value(test_parameter.get_name())

            validate_equals_with_retry(
                function_to_execute=get_sysctl_value,
                expected_value=test_parameter.get_value(),
                validation_description=f"Sysctl value on '{storage_name}' should match",
            )

    def modify_service_parameter_storage_nodes_success(
        self,
        supported_parameter: SystemServiceParameterObject,
    ) -> None:
        """Add then modify a sysctl parameter and verify the modified value takes effect on all storage nodes.

        Args:
            supported_parameter (SystemServiceParameterObject): The supported service parameter with initial and modified values.
        """
        test_parameter = SystemServiceParameterObject(
            service=supported_parameter.get_service(),
            section=supported_parameter.get_section(),
            name=supported_parameter.get_name(),
            value=supported_parameter.get_value(),  # <= initial value
            modified_value=supported_parameter.get_modified_value(),  # <= modify value
        )
        host_list_keywords = SystemHostListKeywords(self.ssh_oam_connection)
        storage_connections: dict[str, SSHConnection] = {storage.get_host_name(): LabConnectionKeywords().get_storage_ssh(storage.get_host_name()) for storage in host_list_keywords.get_storages()}
        for storage_name, storage_connection in storage_connections.items():
            sysctl_keywords = SysctlKeywords(storage_connection)
            current_value = sysctl_keywords.get_sysctl_value(test_parameter.get_name())
            get_logger().log_info(f"Value of '{test_parameter.get_name()}' on '{storage_name}' is '{current_value}'")

        self._modify_sysctl_parameter_expect_success(parameter=test_parameter)

        for storage_name, storage_connection in storage_connections.items():
            sysctl_keywords = SysctlKeywords(storage_connection)

            def get_sysctl_value():
                return sysctl_keywords.get_sysctl_value(test_parameter.get_name())

            validate_equals_with_retry(
                function_to_execute=get_sysctl_value,
                expected_value=test_parameter.get_modified_value(),
                validation_description=f"Sysctl value on '{storage_name}' should match",
            )

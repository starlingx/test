"""Software deploy precheck keywords."""

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_show_keywords import SystemHostShowKeywords
from keywords.cloud_platform.upgrade.objects.software_deploy_precheck_output import SoftwareDeployPrecheckOutput
from keywords.k8s.node.kubectl_nodes_keywords import KubectlNodesKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class SoftwareDeployPrecheckKeywords(BaseKeyword):
    """
    Keywords for 'software deploy precheck' using the ACE object-output model.

    This class:
        - runs the 'software deploy precheck' command
        - wraps the CLI output into SoftwareDeployPrecheckOutput
        - performs additional cross-checks against system state
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Instance of the class.

        Args:
            ssh_connection (SSHConnection): An instance of SSH connection.
        """
        self.ssh_connection = ssh_connection
        self.usm_config = ConfigurationManager.get_usm_config()

    def _run_deploy_precheck(self, release_id: str, sudo: bool = False) -> SoftwareDeployPrecheckOutput:
        """
        Run the 'software deploy precheck' command and return its parsed output.

        Args:
            release_id (str): Release to be prechecked.
            sudo (bool): Option to pass the command with sudo.

        Returns:
            SoftwareDeployPrecheckOutput: Parsed precheck output.

        Raises:
            KeywordException: If the CLI command fails.
        """
        if not release_id:
            raise KeywordException("Missing release ID for software deploy precheck")

        get_logger().log_info(f"Prechecking deploy software release: {release_id}")
        base_cmd = f"software deploy precheck {release_id}"
        cmd = source_openrc(base_cmd)
        timeout = self.usm_config.get_precheck_timeout_sec()

        if sudo:
            output = self.ssh_connection.send_as_sudo(cmd, reconnect_timeout=timeout)
        else:
            output = self.ssh_connection.send(cmd, reconnect_timeout=timeout, get_pty=True)

        # Validate the return code using the base keyword helper.
        self.validate_success_return_code(self.ssh_connection)

        # Wrap the output into the object-output model.
        precheck_output = SoftwareDeployPrecheckOutput(output)
        return precheck_output

    def _validate_precheck_output(self, precheck_output: SoftwareDeployPrecheckOutput) -> bool:
        """
        Validate the precheck output by cross-checking with the actual system state.

        Args:
            precheck_output (SoftwareDeployPrecheckOutput): Parsed precheck output.

        Returns:
            bool: True if validation passes, False otherwise.
        """
        ceph_status = CephStatusKeywords(self.ssh_connection).ceph_status()
        alarm_list = AlarmListKeywords(self.ssh_connection).alarm_list()
        system_hosts = SystemHostListKeywords(self.ssh_connection)
        system_host_show = SystemHostShowKeywords(self.ssh_connection)
        hosts = system_hosts.get_system_host_list().get_hosts()

        status_dict = precheck_output.get_status_dict()

        for key, value in status_dict.items():
            if "[OK]" in value:
                get_logger().log_info(f"'{key}' is OK")

                if key == "Ceph Storage Healthy" and not ceph_status.is_ceph_healthy():
                    get_logger().log_warning(f"Ceph is not healthy  but '{key}' value is OK")
                    return False

                if key == "No alarms" and [] != alarm_list:
                    get_logger().log_warning(f"There are one or more alarms but '{key}' value is OK")
                    return False

                if key == "All hosts are provisioned":
                    for host in hosts:
                        system_host_show_object = system_host_show.get_system_host_show_output(host.get_host_name()).get_system_host_show_object()
                        provisioned = True if system_host_show_object.get_invprovision() == "provisioned" else False
                        # Don't remove this validation, to avoid bool failures.
                        if not provisioned:
                            get_logger().log_warning(f"The host {host} is not provisioned but {key} value is Ok")
                            return False

                if key == "All hosts are unlocked/enabled":
                    for host in hosts:
                        if host.get_administrative == "locked":
                            get_logger().log_warning(f"There are one or more locked hosts but '{key}' value is OK")
                            return False
                        if host.get_operational() == "disabled":
                            get_logger().log_warning(f"There are one or more disabled hosts but '{key}' value is OK")
                            return False

                if key == "All hosts have current configurations":
                    for host in hosts:
                        system_host_show_object = system_host_show.get_system_host_show_output(host.get_host_name()).get_system_host_show_object()
                        config_applied = system_host_show_object.get_config_applied()
                        config_target = system_host_show_object.get_config_target()
                        if config_applied != config_target:
                            get_logger().log_warning("There are one or host with failed " f"configuration but '{key}' value is OK")
                            return False

                if key == "All kubernetes nodes are ready":
                    nodes = KubectlNodesKeywords(self.ssh_connection).get_kubectl_nodes().get_nodes()
                    for node in nodes:
                        if node.get_status() != "Ready":
                            get_logger().log_warning("There are one or more kubernetes nodes not ready " f"but '{key}' value is OK")
                            return False

                if key == "All kubernetes control plane pods are ready":
                    kube_get_pods = KubectlGetPodsKeywords(self.ssh_connection)
                    if kube_get_pods.get_unhealthy_pods().get_pods():
                        get_logger().log_warning(f"There are one or more failed pods but '{key}' value is OK")
                        return False

                if key == "Active controller is controller-0" and system_hosts.get_active_controller().get_host_name() != "controller-0":
                    get_logger().log_warning(f"controller-0 is not active but '{key}' value is OK")
                    return False

            else:
                if key != "System Health":
                    get_logger().log_warning(f"The following check '{key}' is not OK")
                    return False

        return True

    def deploy_precheck(self, release_id: str, sudo: bool = False) -> SoftwareDeployPrecheckOutput:
        """
        Run the deploy precheck for a software release and validate its result.

        Args:
            release_id (str): Release to be prechecked.
            sudo (bool): Option to pass the command with sudo.

        Returns:
            SoftwareDeployPrecheckOutput: Parsed and validated precheck output.

        Raises:
            AssertionError: If any of the checks fail.
        """
        precheck_output = self._run_deploy_precheck(release_id, sudo=sudo)
        is_valid = self._validate_precheck_output(precheck_output)
        assert is_valid, f"There is failed resource in the deploy precheck. Output: {precheck_output.get_raw_output()}"

        get_logger().log_info("Deploy precheck completed:\n" + "\n".join(precheck_output.get_raw_output()))

        return precheck_output

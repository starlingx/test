from typing import List, Tuple, Union

import yaml

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.networking.sriov_fec.object.sriov_fec_device_config import FEC_POD_PREFIXES, SriovFecDeviceConfig
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_device_keywords import SystemHostDeviceKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_copy_to_pod_keywords import KubectlCopyToPodKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.sriov_fec_node_config.kubectl_get_sriov_fec_node_config_keywords import KubectlGetSriovFecNodeConfigKeywords


class SriovFecOperatorKeywords(BaseKeyword):
    """Reusable keywords for SR-IOV FEC operator test cases.

    Centralizes the logic shared across the ACC100, ACC200 and N3000 SR-IOV FEC
    test cases, parameterized by a SriovFecDeviceConfig so the same methods can
    be reused for every accelerator card type.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    @staticmethod
    def _as_text(output: Union[str, List[str]]) -> str:
        """Normalize a command/file output into a single string.

        Some base keywords (run_pod_exec_cmd, read_file) may return either a
        string or a list of lines. This helper centralizes that normalization
        so callers do not each have to handle both types.

        Args:
            output (Union[str, List[str]]): Raw output as a string or list of lines.

        Returns:
            str: The output joined into a single string.
        """
        return "".join(output) if isinstance(output, list) else output

    def get_devices_address(self, device: SriovFecDeviceConfig) -> List[Tuple[str, str]]:
        """Get accelerator device addresses for all hosts in the system.

        Args:
            device (SriovFecDeviceConfig): Device-specific configuration.

        Returns:
            List[Tuple[str, str]]: Tuples of hostname and device address.
        """
        system_host_list_output = SystemHostListKeywords(self.ssh_connection).get_system_host_list()
        devices = []
        for host_name in system_host_list_output.get_host_names():
            device_output = SystemHostDeviceKeywords(self.ssh_connection).get_system_host_device_list(host_name)
            for device_address in device_output.get_device_address_by_device_id(device.get_device_id()):
                devices.append((host_name, device_address))

        for host_name, address in devices:
            get_logger().log_info(f"Host: {host_name}, Address: {address}")

        return devices

    def generate_configuration_file(self, device: SriovFecDeviceConfig, devices: List[Tuple[str, str]], pf_driver: str, vf_driver: str, base_path: str) -> None:
        """Generate accelerator card configuration files from template.

        Args:
            device (SriovFecDeviceConfig): Device-specific configuration.
            devices (List[Tuple[str, str]]): Tuples of hostname and device address.
            pf_driver (str): PF driver name.
            vf_driver (str): VF driver name.
            base_path (str): Remote directory where files will be saved.
        """
        yaml_kw = YamlKeywords(self.ssh_connection)
        for index, (host_name, device_address) in enumerate(devices):
            template_path = get_stx_resource_path(device.get_operator_template())
            replacement_dict = {
                "name": f"{device.get_prefix()}-{index}",
                "hostName": host_name,
                "pfDriver": pf_driver,
                "vfDriver": vf_driver,
                "pciAddress": device_address,
            }
            remote_file = yaml_kw.generate_yaml_file_from_template(
                template_path,
                replacement_dict,
                f"sriov-fec-operator-{pf_driver}-{vf_driver}-{device.get_prefix()}-{index}.yaml",
                base_path,
                preserve_order=True,
            )
            get_logger().log_info(f"Generated operator config: {remote_file}")

    def generate_pod_file(self, device: SriovFecDeviceConfig, devices: List[Tuple[str, str]], pf_driver: str, vf_driver: str, base_path: str) -> None:
        """Generate accelerator pod YAML files from template.

        Args:
            device (SriovFecDeviceConfig): Device-specific configuration.
            devices (List[Tuple[str, str]]): Tuples of hostname and device address.
            pf_driver (str): PF driver name.
            vf_driver (str): VF driver name.
            base_path (str): Remote directory where files will be saved.
        """
        yaml_kw = YamlKeywords(self.ssh_connection)
        for index, (host_name, device_address) in enumerate(devices):
            template_path = get_stx_resource_path(device.get_pod_template())
            replacement_dict = {
                "podName": f"{device.get_prefix()}-{index}",
                "hostName": host_name,
            }
            remote_file = yaml_kw.generate_yaml_file_from_template(
                template_path,
                replacement_dict,
                f"sriov-pod-k8s-manifest-{pf_driver}-{vf_driver}-{device.get_prefix()}-{index}.yaml",
                base_path,
                preserve_order=True,
            )
            get_logger().log_info(f"Generated pod config: {remote_file}")

    def generate_bbdev_script(self, device: SriovFecDeviceConfig, pf_driver: str, vf_driver: str, base_path: str) -> str:
        """Generate a bbdev test script from template with driver configuration.

        Args:
            device (SriovFecDeviceConfig): Device-specific configuration.
            pf_driver (str): PF driver name.
            vf_driver (str): VF driver name.
            base_path (str): Remote directory where the file will be saved.

        Returns:
            str: Generated bbdev script file name.
        """
        file_kw = FileKeywords(self.ssh_connection)
        template_path = get_stx_resource_path("resources/cloud_platform/sriov-fec-operator/bbdev.sh")
        replacement_dict = {
            "vf_vendor_id": device.get_vf_vendor_id(),
            "vf_device_id": device.get_vf_device_id(),
            "pfDriver": pf_driver,
            "vfDriver": vf_driver,
        }
        bbdev_sh_name = f"bbdev_{pf_driver}_{vf_driver}.sh"
        bbdev_script_file = file_kw.generate_file_from_template(template_path, replacement_dict, bbdev_sh_name, base_path)
        get_logger().log_info(f"Generated bbdev script: {bbdev_script_file}")
        return bbdev_sh_name

    def upload_install_sriov_fec_operator(self) -> None:
        """Upload, apply sriov-fec-operator, and wait for its pods to be running."""
        app_config = ConfigurationManager.get_app_config()
        base_path = app_config.get_base_application_path()
        sriov_fec_name = app_config.get_sriov_fec_operator_app_name()
        sriov_fec_file_path = f"{base_path}{sriov_fec_name}*.tgz"

        get_logger().log_info(f"Uploading and applying {sriov_fec_name}")
        sriov_fec_app_output = SystemApplicationUploadKeywords(self.ssh_connection).system_application_upload_and_apply_app(sriov_fec_name, sriov_fec_file_path)
        sriov_fec_app_object = sriov_fec_app_output.get_system_application_object()
        validate_equals(sriov_fec_app_object.get_name(), sriov_fec_name, f"{sriov_fec_name} name validation")
        validate_equals(sriov_fec_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{sriov_fec_name} application status validation")
        get_logger().log_info("Waiting for sriov-fec-operator pods to be running")
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace="sriov-fec-system")

    def apply_configuration(self, device: SriovFecDeviceConfig, pf_driver: str, vf_driver: str, index: int, base_path: str, host_name: str) -> str:
        """Apply sriov-fec-operator configuration and verify it is applied.

        Args:
            device (SriovFecDeviceConfig): Device-specific configuration.
            pf_driver (str): PF driver name.
            vf_driver (str): VF driver name.
            index (int): Device index.
            base_path (str): Remote directory where the file was created.
            host_name (str): Host name.

        Returns:
            str: Path to the applied accelerator configuration file.
        """
        operator_file = f"{base_path}/sriov-fec-operator-{pf_driver}-{vf_driver}-{device.get_prefix()}-{index}.yaml"

        get_logger().log_info(f"Apply sriov-fec-operator {device.get_name()} card configuration file")
        KubectlFileApplyKeywords(self.ssh_connection).apply_resource_from_yaml(operator_file)
        get_logger().log_info(f"Verify if sriov-fec-operator {device.get_name()} card configuration file was applied")
        KubectlGetSriovFecNodeConfigKeywords(self.ssh_connection).wait_for_configured_status(
            host_name,
            expected_status="InProgress",
            timeout=90,
            poll_interval=15,
        )
        KubectlGetSriovFecNodeConfigKeywords(self.ssh_connection).wait_for_configured_status(host_name)
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace="sriov-fec-system")

        return operator_file

    def apply_pod(self, device: SriovFecDeviceConfig, pf_driver: str, vf_driver: str, index: int, base_path: str, host_name: str) -> str:
        """Apply accelerator pod configuration and verify it is running.

        Args:
            device (SriovFecDeviceConfig): Device-specific configuration.
            pf_driver (str): PF driver name.
            vf_driver (str): VF driver name.
            index (int): Device index.
            base_path (str): Remote directory where the file was created.
            host_name (str): Host name.

        Returns:
            str: Name of the created pod.
        """
        pod_file = f"{base_path}/sriov-pod-k8s-manifest-{pf_driver}-{vf_driver}-{device.get_prefix()}-{index}.yaml"
        get_logger().log_info(f"Run {device.get_name()} pod for accelerator card")
        KubectlApplyPodsKeywords(self.ssh_connection).apply_from_yaml(pod_file, namespace="default")
        get_pods_kw = KubectlGetPodsKeywords(self.ssh_connection)
        get_logger().log_info(f"Verify {device.get_name()} pod is running")
        pod_name = get_pods_kw.get_pods(namespace="default").get_unique_pod_matching_prefix(starts_with=device.get_prefix())
        pod_status = get_pods_kw.wait_for_pod_status(pod_name, "Running", "default")
        validate_equals(pod_status, True, f"{device.get_name()} pod status is running")

        return pod_name

    def run_and_verify_bbdev_test(self, pod_name: str, bbdev_sh_name: str, base_path: str) -> None:
        """Run bbdev script inside the pod and verify all tests passed.

        Args:
            pod_name (str): Name of the pod to execute the script in.
            bbdev_sh_name (str): Name of the bbdev script file.
            base_path (str): Remote directory where the file was created.
        """
        get_logger().log_info("Copy bbdev script inside the pod")
        KubectlCopyToPodKeywords(self.ssh_connection).copy_to_pod(local_filename=f"{base_path}/{bbdev_sh_name}", namespace="default", pod_name=pod_name, dest_filename=".")

        get_logger().log_info("Run bbdev script inside the pod")
        bbdev_output = KubectlExecInPodsKeywords(self.ssh_connection).run_pod_exec_cmd(pod_name, f"bash {bbdev_sh_name}", options="-n default")
        bbdev_output_str = self._as_text(bbdev_output)

        get_logger().log_info("Verify bbdev test executed and all tests passed")
        validate_str_contains(bbdev_output_str, "Test Suite Summary", "bbdev test suite was executed")
        validate_str_contains(bbdev_output_str, "Tests Failed :       0", "bbdev tests have no failures")

    def delete_pod(self, device: SriovFecDeviceConfig, base_path: str, pf_driver: str, vf_driver: str, index: int) -> None:
        """Delete accelerator pod.

        Args:
            device (SriovFecDeviceConfig): Device-specific configuration.
            base_path (str): Remote directory where files are located.
            pf_driver (str): PF driver name.
            vf_driver (str): VF driver name.
            index (int): Device index.
        """
        get_logger().log_info(f"Delete {device.get_name()} pod")
        KubectlFileDeleteKeywords(self.ssh_connection).delete_resources(f"{base_path}/sriov-pod-k8s-manifest-{pf_driver}-{vf_driver}-{device.get_prefix()}-{index}.yaml")

    def delete_configuration(self, device: SriovFecDeviceConfig, base_path: str, pf_driver: str, vf_driver: str, index: int, host_name: str) -> None:
        """Delete accelerator card configuration and verify operator pods are running.

        Args:
            device (SriovFecDeviceConfig): Device-specific configuration.
            base_path (str): Remote directory where files are located.
            pf_driver (str): PF driver name.
            vf_driver (str): VF driver name.
            index (int): Device index.
            host_name (str): Host name.
        """
        get_logger().log_info(f"Delete {device.get_name()} configuration")
        KubectlFileDeleteKeywords(self.ssh_connection).delete_resources(f"{base_path}/sriov-fec-operator-{pf_driver}-{vf_driver}-{device.get_prefix()}-{index}.yaml")
        get_logger().log_info(f"Verify {device.get_name()} card configuration was deleted and operator pods are running")
        KubectlGetSriovFecNodeConfigKeywords(self.ssh_connection).wait_for_configured_status(
            host_name,
            expected_status="InProgress",
            timeout=90,
            poll_interval=15,
        )
        KubectlGetSriovFecNodeConfigKeywords(self.ssh_connection).wait_for_configured_status(host_name)
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace="sriov-fec-system")

    def delete_generated_files(self, device: SriovFecDeviceConfig, base_path: str, delete_pod_files: bool = True) -> None:
        """Delete accelerator generated files from the remote host.

        Deletes sriov-fec-operator configuration YAML files. Optionally deletes
        pod YAML files and bbdev script files when delete_pod_files is True.

        Args:
            device (SriovFecDeviceConfig): Device-specific configuration.
            base_path (str): Remote directory where files were created.
            delete_pod_files (bool): Whether to also delete pod and bbdev files. Defaults to True.
        """
        get_logger().log_teardown_step(f"Delete {device.get_name()} generated configuration files")
        file_kw = FileKeywords(self.ssh_connection)
        patterns = [f"{base_path}/sriov-fec-operator-*.yaml"]
        if delete_pod_files:
            get_logger().log_info("Including pod and bbdev files for deletion")
            patterns.append(f"{base_path}/sriov-pod-k8s-manifest-*.yaml")
            patterns.append(f"{base_path}/bbdev_*.sh")
        for pattern in patterns:
            file_kw.delete_file(pattern)

    def cleanup_sriov_fec_operator(self) -> None:
        """Remove sriov-fec-operator application if previously installed or uploaded."""
        app_config = ConfigurationManager.get_app_config()
        sriov_fec_name = app_config.get_sriov_fec_operator_app_name()

        get_logger().log_setup_step("Verify if sriov-fec-operator is previously installed or uploaded")
        sriov_fec_applied = SystemApplicationApplyKeywords(self.ssh_connection).is_applied_or_failed(sriov_fec_name)

        if sriov_fec_applied:
            get_logger().log_setup_step("Remove and delete sriov-fec-operator application")
            sriov_fec_app_output = SystemApplicationRemoveKeywords(self.ssh_connection).system_application_remove_and_delete_app(sriov_fec_name)
            validate_equals(sriov_fec_app_output, f"Application {sriov_fec_name} deleted.\n", "SRIOV FEC deletion validation")
            KubectlGetPodsKeywords(self.ssh_connection).wait_for_pods_to_be_deleted(namespace="sriov-fec-system")
            return

        sriov_fec_uploaded = SystemApplicationUploadKeywords(self.ssh_connection).is_already_uploaded(sriov_fec_name)
        if sriov_fec_uploaded:
            get_logger().log_setup_step("Delete sriov-fec-operator application")
            system_application_delete_input = SystemApplicationDeleteInput()
            system_application_delete_input.set_app_name(sriov_fec_name)
            system_application_delete_input.set_force_deletion(False)
            sriov_fec_app_output = SystemApplicationDeleteKeywords(self.ssh_connection).get_system_application_delete(system_application_delete_input)
            validate_equals(sriov_fec_app_output, f"Application {sriov_fec_name} deleted.\n", "Application deletion message validation")
            return

        get_logger().log_info("sriov-fec-operator is not installed")

    def delete_fec_pods(self) -> None:
        """Delete all FEC pods matching known prefixes."""
        get_logger().log_setup_step("Delete FEC pods")
        get_pods_kw = KubectlGetPodsKeywords(self.ssh_connection)
        delete_pods_kw = KubectlDeletePodsKeywords(self.ssh_connection)

        for prefix in FEC_POD_PREFIXES:
            pods = get_pods_kw.get_pods(namespace="default").get_pods_start_with(starts_with=prefix)
            for pod in pods:
                delete_pods_kw.delete_pod(pod.get_name())
                get_logger().log_info(f"Deleted pod: {pod.get_name()}")

    def delete_remaining_node_config(self, last_configuration_file: str) -> None:
        """Delete SriovFecNodeConfig for the node targeted by the configuration file.

        Reads the configuration file and extracts the node name from its parsed
        nodeSelector before checking if that specific node has active
        configuration to delete.

        Args:
            last_configuration_file (str): Path to the accelerator configuration file to delete.
        """
        get_logger().log_teardown_step("Delete SriovFecNodeConfig resource from configuration file")

        # Extract node name from the configuration file's parsed nodeSelector
        file_kw = FileKeywords(self.ssh_connection)
        file_content = file_kw.read_file(last_configuration_file)
        parsed = yaml.safe_load(self._as_text(file_content)) or {}
        node_selector = parsed.get("spec", {}).get("nodeSelector", {})
        node_name = node_selector.get("kubernetes.io/hostname")

        if not node_name:
            get_logger().log_info(f"Could not extract node name from {last_configuration_file}, skipping deletion")
            return

        get_logger().log_info(f"Configuration file targets node: {node_name}")

        sriov_fec_kw = KubectlGetSriovFecNodeConfigKeywords(self.ssh_connection)
        config = sriov_fec_kw.get_sriov_fec_node_config_by_name(node_name)

        if config.get_configured() == "NotRequested":
            get_logger().log_info(f"Skipping {node_name}: status is NotRequested (no configuration loaded)")
            return

        yaml_output = sriov_fec_kw.get_sriov_fec_node_config_yaml(node_name)

        if not yaml_output.has_physical_functions():
            get_logger().log_info(f"Skipping {node_name}: no active physicalFunctions configured")
            return

        get_logger().log_info(f"Deleting SriovFecNodeConfig: {node_name} (status: {config.get_configured()})")
        KubectlFileDeleteKeywords(self.ssh_connection).delete_resources(last_configuration_file)

        KubectlGetSriovFecNodeConfigKeywords(self.ssh_connection).wait_for_configured_status(
            node_name,
            expected_status="InProgress",
            timeout=90,
            poll_interval=15,
        )
        KubectlGetSriovFecNodeConfigKeywords(self.ssh_connection).wait_for_configured_status(node_name)
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace="sriov-fec-system")

    def cleanup_sriov_fec_operator_and_pods(self) -> None:
        """Delete FEC pods and remove sriov-fec-operator."""
        self.delete_fec_pods()
        self.cleanup_sriov_fec_operator()

    def select_device_preferring_non_active_controller(self, devices: List[Tuple[str, str]], device_name: str) -> Tuple[SSHConnection, Tuple[str, str]]:
        """Select a single accelerator device, preferring one not on the active controller.

        If all devices are on the active controller and the system has multiple controllers,
        a swact is performed to move the active role away from the device host.

        Args:
            devices (List[Tuple[str, str]]): Tuples of hostname and device address.
            device_name (str): Device name for logging purposes.

        Returns:
            Tuple[SSHConnection, Tuple[str, str]]: Updated SSH connection and selected device tuple.
        """
        host_list_kw = SystemHostListKeywords(self.ssh_connection)
        active_controller_name = host_list_kw.get_active_controller().get_host_name()
        non_active_devices = []
        for host_name, device_address in devices:
            if host_name != active_controller_name:
                non_active_devices.append((host_name, device_address))
        if non_active_devices:
            selected_device = non_active_devices[0]
        elif len(host_list_kw.get_controllers()) > 1:
            get_logger().log_info(f"All {device_name} devices are on the active controller, performing swact")
            SystemHostSwactKeywords(self.ssh_connection).host_swact()
            self.ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
            selected_device = devices[0]
        else:
            get_logger().log_info(f"Simplex system, using {device_name} device on the active controller")
            selected_device = devices[0]
        get_logger().log_info(f"Selected {device_name} device: host={selected_device[0]}, address={selected_device[1]}")
        return self.ssh_connection, selected_device

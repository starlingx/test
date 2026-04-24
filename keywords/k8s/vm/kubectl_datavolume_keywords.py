"""Keywords for kubectl DataVolume operations."""

import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlDatavolumeKeywords(K8sBaseKeyword):
    """Keywords for managing CDI DataVolume resources via kubectl."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize DataVolume keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_datavolume_phase(self, dv_name: str, namespace: str = "default") -> str:
        """Get the current phase of a DataVolume.

        Args:
            dv_name (str): Name of the DataVolume.
            namespace (str): Kubernetes namespace. Defaults to "default".

        Returns:
            str: Current phase of the DataVolume (e.g., "UploadReady", "Succeeded").
        """
        cmd = f"kubectl get dv {dv_name} -n {namespace} -o jsonpath='{{.status.phase}}'"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        phase = output[0].strip("'\" \n") if output else ""
        return phase

    def wait_for_datavolume_phase(
        self,
        dv_name: str,
        expected_phase: str = "UploadReady",
        namespace: str = "default",
        timeout: int = 120,
        poll_interval: int = 5,
    ) -> str:
        """Wait for a DataVolume to reach an expected phase.

        Args:
            dv_name (str): Name of the DataVolume.
            expected_phase (str): Expected phase. Defaults to "UploadReady".
            namespace (str): Kubernetes namespace. Defaults to "default".
            timeout (int): Maximum time in seconds to wait. Defaults to 60.
            poll_interval (int): Seconds between status checks. Defaults to 5.

        Returns:
            str: The phase when it matches expected_phase.

        Raises:
            KeywordException: If the DataVolume does not reach the expected phase within timeout.
        """
        get_logger().log_info(f"Waiting for DataVolume {dv_name} to reach phase '{expected_phase}'")
        end_time = time.time() + timeout
        phase = ""

        while time.time() < end_time:
            phase = self.get_datavolume_phase(dv_name, namespace)
            get_logger().log_info(f"DataVolume {dv_name} current phase: {phase}")
            if phase == expected_phase:
                get_logger().log_info(f"DataVolume {dv_name} reached expected phase '{expected_phase}'")
                return phase
            time.sleep(poll_interval)

        raise KeywordException(f"DataVolume {dv_name} did not reach phase '{expected_phase}' within " f"{timeout}s. Current phase: {phase}")

    def create_datavolume(
        self,
        dv_yaml: str,
        dv_name: str,
        namespace: str = "default",
        wait_for_upload_ready: bool = True,
        timeout: int = 120,
    ) -> str:
        """Create a DataVolume from a YAML file and wait for it to be ready.

        Applies the given YAML file via kubectl and optionally waits for the
        DataVolume to reach UploadReady phase.

        Args:
            dv_yaml (str): Remote path to the DataVolume YAML file.
            dv_name (str): Name of the DataVolume (used for status polling).
            namespace (str): Kubernetes namespace. Defaults to "default".
            wait_for_upload_ready (bool): Wait for UploadReady phase. Defaults to True.
            timeout (int): Timeout in seconds for waiting. Defaults to 60.

        Returns:
            str: Command output from kubectl apply.

        Raises:
            AssertionError: If DataVolume creation fails.
            KeywordException: If DataVolume does not reach UploadReady within timeout.
        """
        get_logger().log_info(f"Creating DataVolume {dv_name} from {dv_yaml}")

        cmd = f"kubectl apply -f {dv_yaml} -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"DataVolume {dv_name} created successfully")

        if wait_for_upload_ready:
            self.wait_for_datavolume_phase(dv_name, "UploadReady", namespace, timeout)

        return output

    def delete_datavolume(self, dv_name: str, namespace: str = "default") -> str:
        """Delete a DataVolume.

        Args:
            dv_name (str): Name of the DataVolume to delete.
            namespace (str): Kubernetes namespace. Defaults to "default".

        Returns:
            str: Command output.

        Raises:
            AssertionError: If DataVolume deletion fails.
        """
        get_logger().log_info(f"Deleting DataVolume {dv_name}")
        cmd = f"kubectl delete dv {dv_name} -n {namespace} --ignore-not-found=true"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info(f"DataVolume {dv_name} deleted successfully")
        return output

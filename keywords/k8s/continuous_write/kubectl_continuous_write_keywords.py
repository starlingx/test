"""Keywords for driving a pod that continuously writes to a persistent volume.

These keywords create a PVC and a pod that rewrites a data file and bumps a
cycle counter on a fixed interval. They are used to prove that a volume stays
writable across disruptions such as host power cycles, lock/unlock, swact, etc.

The PVC/pod YAML resources live under RESOURCE_DIR so they can be reused by any
test. Supported storage types: 'cephfs' (ReadWriteMany) and 'rbd' (ReadWriteOnce).
"""

import os
import tempfile

import yaml

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pvc.kubectl_get_pvc_keywords import KubectlGetPvcKeywords

REMOTE_HOME = "/home/sysadmin"
RESOURCE_DIR = "resources/cloud_platform/storage/continuous_write"
WRITE_COUNT_FILE = "/data/write_count"


class KubectlContinuousWriteKeywords(K8sBaseKeyword):
    """Keywords to create and monitor a continuous-write pod on a PV."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def start_continuous_write_pod(self, storage_type: str, node_name: str = None) -> tuple[str, str]:
        """Create a PVC and a pod that continuously writes to the volume.

        Uploads the reusable PVC/pod YAML resources for the given storage type,
        creates the PVC (waits for Bound) and the pod (waits for Running). The pod
        runs a loop that rewrites a data file and bumps a cycle counter every ~10s.

        When node_name is provided, the pod is pinned to that node via spec.nodeName.
        This is used to keep the writer on a node that stays up during a disruption
        (e.g. pin to the active controller while the standby is power-cycled) so the
        pod keeps writing throughout.

        Args:
            storage_type (str): either 'cephfs' (RWX) or 'rbd' (RWO).
            node_name (str, optional): node to pin the pod to (spec.nodeName). If None,
                the scheduler places the pod on any eligible node.

        Returns:
            tuple[str, str]: the pod name and the pvc name created.
        """
        pvc_name = f"{storage_type}-writer-pvc"
        pod_name = f"{storage_type}-writer-pod"
        pvc_yaml_file = f"{storage_type}-writer-pvc.yaml"
        pod_yaml_file = f"{storage_type}-writer-pod.yaml"
        remote_pvc_yaml = f"{REMOTE_HOME}/{pvc_yaml_file}"
        remote_pod_yaml = f"{REMOTE_HOME}/{pod_yaml_file}"

        file_keywords = FileKeywords(self.ssh_connection)

        get_logger().log_info(f"Upload {storage_type} continuous-write PVC YAML to active controller")
        file_keywords.upload_file(get_stx_resource_path(f"{RESOURCE_DIR}/{pvc_yaml_file}"), remote_pvc_yaml, overwrite=True)

        # Build the pod YAML locally, injecting spec.nodeName when pinning is requested,
        # then upload the resulting file. Editing the parsed YAML (rather than an in-place
        # sed on the controller) is layout-independent and cannot silently no-op.
        local_pod_yaml = self._render_pod_yaml(pod_yaml_file, node_name)
        file_keywords.upload_file(local_pod_yaml, remote_pod_yaml, overwrite=True)

        # Remove any leftover pod from a previous run before recreating: a Pod is largely
        # immutable, so 'kubectl apply' fails if a pod with a different spec already exists.
        get_logger().log_info(f"Delete pre-existing {pod_name} if present (idempotent start)")
        self._delete_pod_and_wait_gone(pod_name)

        get_logger().log_info(f"Create {storage_type} continuous-write PVC and wait for Bound")
        KubectlFileApplyKeywords(self.ssh_connection).apply_resource_from_yaml(remote_pvc_yaml)
        KubectlGetPvcKeywords(self.ssh_connection).wait_for_pvcs_to_reach_status(expected_status="Bound", pvc_names=pvc_name)

        get_logger().log_info(f"Create {storage_type} continuous-write pod and wait for Running")
        KubectlFileApplyKeywords(self.ssh_connection).apply_resource_from_yaml(remote_pod_yaml)
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_pod_status(pod_name, "Running")

        return pod_name, pvc_name

    def get_write_cycle_count(self, pod_name: str) -> int:
        """Read the current write-cycle counter from a continuous-write pod.

        The pod increments /data/write_count after each write cycle. Returns 0 if
        the counter file does not exist yet (first cycle not completed).

        Args:
            pod_name (str): the continuous-write pod name.

        Returns:
            int: the number of completed write cycles.
        """
        output = KubectlExecInPodsKeywords(self.ssh_connection).run_pod_exec_cmd(pod_name, f"cat {WRITE_COUNT_FILE}", options="-i")
        text = "".join(output) if isinstance(output, list) else str(output)
        for token in text.split():
            if token.strip().isdigit():
                return int(token.strip())
        return 0

    def wait_for_write_progress(self, pod_name: str, previous_count: int, timeout: int = 180, polling_sleep_time: int = 10) -> int:
        """Wait until a continuous-write pod advances past a previous cycle count.

        Confirms the pod resumed writing (the counter increased), proving the
        volume is still writable after a disruption such as a power cycle.

        Args:
            pod_name (str): the continuous-write pod name.
            previous_count (int): the cycle count recorded before the disruption.
            timeout (int): maximum seconds to wait for progress.
            polling_sleep_time (int): seconds between checks.

        Returns:
            int: the new cycle count once it has advanced past previous_count.

        Raises:
            TimeoutError: if the counter does not advance within the timeout.
        """

        def has_write_progressed() -> ValidationResponse:
            current_count = self.get_write_cycle_count(pod_name)
            return ValidationResponse(current_count > previous_count, current_count)

        return validate_equals_with_retry(
            function_to_execute=has_write_progressed,
            expected_value=True,
            validation_description=f"Pod {pod_name} write-cycle count advanced past {previous_count}",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

    def _render_pod_yaml(self, pod_yaml_file: str, node_name: str = None) -> str:
        """Produce a local pod YAML, optionally pinned to a node via spec.nodeName.

        Reads the resource pod YAML, and when node_name is given, sets spec.nodeName
        by editing the parsed document (layout-independent, unlike an in-place sed).
        Returns the path to the local file to upload. When no pinning is requested,
        the original resource file path is returned unchanged.

        Args:
            pod_yaml_file (str): the pod YAML file name under RESOURCE_DIR.
            node_name (str, optional): node to pin the pod to (spec.nodeName).

        Returns:
            str: local path to the pod YAML to upload.
        """
        source_path = get_stx_resource_path(f"{RESOURCE_DIR}/{pod_yaml_file}")
        if not node_name:
            return source_path

        with open(source_path) as source_file:
            pod = yaml.safe_load(source_file)
        pod.setdefault("spec", {})["nodeName"] = node_name

        target_path = os.path.join(tempfile.gettempdir(), pod_yaml_file)
        with open(target_path, "w") as target_file:
            yaml.safe_dump(pod, target_file, default_flow_style=False, sort_keys=False)
        return target_path

    def _delete_pod_and_wait_gone(self, pod_name: str, timeout: int = 120, polling_sleep_time: int = 5) -> None:
        """Delete a pod (if present) and wait until it no longer exists.

        Reuses KubectlDeletePodsKeywords for the delete and validate_equals_with_retry
        for the wait, so the pod is fully gone before it is recreated. The delete is
        forced (grace_period=0) so a Terminating pod releases its attached volume
        immediately, preventing the recreated pod from being stuck Pending.

        Args:
            pod_name (str): the pod name to remove.
            timeout (int): maximum seconds to wait for the pod to disappear.
            polling_sleep_time (int): seconds between checks.
        """
        KubectlDeletePodsKeywords(self.ssh_connection).cleanup_pod(pod_name, force=True, grace_period=0)

        def is_pod_gone() -> bool:
            pods = KubectlGetPodsKeywords(self.ssh_connection).get_pods().get_pods()
            return not any(pod.get_name() == pod_name for pod in pods)

        validate_equals_with_retry(
            function_to_execute=is_pod_gone,
            expected_value=True,
            validation_description=f"Pod {pod_name} was deleted",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

    def cleanup_continuous_write_pod(self, pod_name: str, pvc_name: str) -> None:
        """Delete the continuous-write pod, its PVC, and the uploaded YAML files.

        Safe to use in a finalizer; does not fail the test on error.

        Args:
            pod_name (str): the continuous-write pod name.
            pvc_name (str): the continuous-write PVC name.
        """
        storage_type = pod_name.split("-")[0]
        KubectlDeletePodsKeywords(self.ssh_connection).cleanup_pod(pod_name)
        KubectlDeleteResourceKeywords(self.ssh_connection).delete_resource("pvc", pvc_name)
        KubectlGetPvcKeywords(self.ssh_connection).wait_for_pvc_to_be_deleted(pvc_name)

        file_keywords = FileKeywords(self.ssh_connection)
        for file_name in [f"{storage_type}-writer-pvc.yaml", f"{storage_type}-writer-pod.yaml"]:
            file_keywords.delete_file(f"{REMOTE_HOME}/{file_name}")

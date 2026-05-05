"""Kubernetes PersistentVolumeClaim kubectl keywords."""

import time
from typing import List, Optional, Union

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pvc.object.kubectl_get_pvcs_output import KubectlGetPvcsOutput


class KubectlGetPvcKeywords(K8sBaseKeyword):
    """Keywords for 'kubectl get pvc' operations."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize PVC keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path.
                If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_pvc(
        self,
        pvc_name: Optional[Union[str, List[str]]] = None,
        namespace: Optional[str] = None,
    ) -> KubectlGetPvcsOutput:
        """Get PVCs via 'kubectl get pvc -o wide'.

        Args:
            pvc_name (str or list, optional): One PVC name or list of PVC names
                to query. If None, returns all PVCs.
            namespace (str, optional): Namespace to query. If None,
                returns PVCs from all namespaces.

        Returns:
            KubectlGetPvcsOutput: Parsed PVC collection.
        """
        ns_arg = f"-n {namespace}" if namespace else ""
        pvc_name_arg = ""
        if isinstance(pvc_name, str):
            pvc_name_arg = pvc_name
        elif isinstance(pvc_name, list):
            pvc_name_arg = " ".join(pvc_name)
        output = self.ssh_connection.send(
            self.k8s_config.export(f"kubectl -o wide get pvc {pvc_name_arg} {ns_arg}")
        )
        self.validate_success_return_code(self.ssh_connection)
        return KubectlGetPvcsOutput(output)

    def wait_for_pvcs_to_reach_status(
        self,
        expected_status: str,
        pvc_names: Optional[Union[str, List[str]]] = None,
        namespace: Optional[str] = None,
        poll_interval: int = 10,
        timeout: int = 180,
    ) -> bool:
        """Wait for PVCs to reach expected status within timeout.

        Monitors PVCs and waits for them to reach the expected status.
        Can monitor specific PVCs by name or all PVCs in the namespace.

        Args:
            expected_status (str): Status string to wait for (e.g., 'Bound').
            pvc_names (str or list, optional): One PVC name or list of PVC names.
                If None, monitors all PVCs in the namespace.
            namespace (str, optional): Namespace to query. If None,
                searches all namespaces.
            poll_interval (int): Seconds between status checks. Defaults to 10.
            timeout (int): Maximum seconds to wait. Defaults to 180.

        Returns:
            bool: True if all PVCs reach expected status within timeout.

        Raises:
            KeywordException: If PVCs do not reach expected status
                within the timeout period.
        """
        pvc_status_timeout = time.time() + timeout

        get_logger().log_info(
            f"Waiting for pvcs {pvc_names} to reach {expected_status} status"
        )

        pending_pvcs = []
        if isinstance(pvc_names, str):
            pending_pvcs = [pvc_names]
        elif isinstance(pvc_names, list):
            pending_pvcs = pvc_names
        elif pvc_names is None:
            all_pvcs = self.get_pvc(namespace=namespace).get_pvcs()
            pending_pvcs = [pvc.get_name() for pvc in all_pvcs]

        while time.time() < pvc_status_timeout:
            pvcs_output = self.get_pvc(namespace=namespace)
            if not pvcs_output:
                time.sleep(poll_interval)
                continue
            pvcs = pvcs_output.get_pvcs()

            for pvc_name in pending_pvcs[:]:
                matching_pvcs = [
                    p for p in pvcs if p.get_name().startswith(pvc_name)
                ]
                if matching_pvcs and all(
                    p.get_status() in expected_status for p in matching_pvcs
                ):
                    get_logger().log_debug(
                        f"pvc:{pvc_name} reached {expected_status} status"
                    )
                    pending_pvcs.remove(pvc_name)

            if not pending_pvcs:
                get_logger().log_info(
                    f"All pvcs:{pvc_names} reached {expected_status} status"
                )
                return True
            else:
                get_logger().log_debug(
                    f"pvcs left to reach status: {pending_pvcs}"
                )

            time.sleep(poll_interval)

        raise KeywordException(
            f"pvcs {pending_pvcs} did not reach {expected_status} "
            f"status within {timeout} seconds"
        )

    def wait_for_pvc_to_be_deleted(
        self,
        pvc_name: str,
        namespace: str = "default",
        poll_interval: int = 10,
        timeout: int = 180,
    ) -> bool:
        """Wait for a PVC to be deleted within timeout.

        Args:
            pvc_name (str): Name of the PVC to wait for deletion.
            namespace (str): Namespace to search in. Defaults to 'default'.
            poll_interval (int): Seconds between checks. Defaults to 10.
            timeout (int): Maximum seconds to wait. Defaults to 180.

        Returns:
            bool: True if the PVC is deleted within timeout.

        Raises:
            KeywordException: If the PVC still exists after timeout.
        """

        def is_pvc_deleted() -> bool:
            ns_arg = f"-n {namespace}" if namespace else ""
            output = self.ssh_connection.send(
                self.k8s_config.export(f"kubectl get pvc {pvc_name} {ns_arg}")
            )
            return f'"{pvc_name}" not found' in output[0]

        validate_equals_with_retry(
            function_to_execute=is_pvc_deleted,
            expected_value=True,
            validation_description=f"The pvc {pvc_name} was deleted",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )

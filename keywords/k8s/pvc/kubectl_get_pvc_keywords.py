import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pvc.object.kubectl_get_pvcs_output import KubectlGetPvcsOutput


class KubectlGetPvcKeywords(K8sBaseKeyword):
    """
    Class for 'kubectl get pvc' keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize the KubectlGetPvcKeywords class.

        Args:
            ssh_connection (SSHConnection): An SSH connection object to the target system.
        """
        super().__init__(ssh_connection)

    def get_pvc(self, pvc_name: str | list = None, namespace: str = None) -> KubectlGetPvcsOutput:
        """
        Get the k8s pvcs that are available using '-o wide'.

        Args:
            pvc_name (str|list, optional): String of one pvc name or list of pvc names.
                                    (e.g., 'cephfs-pvc', ['cephfs-pvc', 'rbd-pvc']).
            namespace (str, optional): Kubernetes namespace to search in. If None, searches
                                     all namespaces. Defaults to None
        Returns:
            KubectlGetPvcsOutput: An object containing the parsed output of the command.
        """
        ns_arg = f"-n {namespace}" if namespace else ""
        pvc_name_arg = ""
        if isinstance(pvc_name, str):
            pvc_name_arg = pvc_name
        elif isinstance(pvc_name, list):
            pvc_name_arg = " ".join(pvc_name)
        kubectl_get_pvcs_output = self.ssh_connection.send(self.k8s_config.export(f"kubectl -o wide get pvc {pvc_name_arg} {ns_arg}"))
        self.validate_success_return_code(self.ssh_connection)
        pvcs_list_output = KubectlGetPvcsOutput(kubectl_get_pvcs_output)

        return pvcs_list_output

    def wait_for_pvcs_to_reach_status(self, expected_status: str, pvc_names: str | list = None, namespace: str = None, poll_interval: int = 10, timeout: int = 180) -> bool:
        """Wait for specified pvcs to reach expected status within timeout period.

        This function monitors pvcs in a given namespace and waits for them to reach
        one of the expected statuses. It can monitor specific pvcs by name or all pvcs
        in the namespace if no pvc names are provided.

        Args:
            expected_status (str): Single status string or list of acceptable statuses
            pvc_names (str|list, optional): String of one pvc name or list of pvc names.
                                    (e.g., 'cephfs-pvc', ['cephfs-pvc', 'rbd-pvc']).
            namespace (str, optional): Kubernetes namespace to search in. If None, searches
                                     all namespaces. Defaults to None.
            poll_interval (int): Time in seconds between status checks. Defaults to 5.
            timeout (int): Maximum time in seconds to wait for pvcs to reach expected
                         status. Defaults to 180.

        Returns:
            bool: True if all specified pvcs reach expected status within timeout.

        Raises:
            KeywordException: If pvcs are not found within timeout or don't reach
                            expected status within timeout period.
        """
        pvc_status_timeout = time.time() + timeout

        get_logger().log_info(f"Waiting for pvcs {pvc_names} to reach {expected_status} status")

        # Initialize pending pvcs - if no pvc_names given, get all pvcs in namespace
        pending_pvcs = []
        if isinstance(pvc_names, str):
            pending_pvcs = [pvc_names]
        elif isinstance(pvc_names, list):
            pending_pvcs = pvc_names
        elif pvc_names is None:
            all_pvcs = self.get_pvc(namespace).get_pvcs()
            pending_pvcs = [pvc.get_name() for pvc in all_pvcs]

        while time.time() < pvc_status_timeout:
            pvcs_output = self.get_pvc(namespace)
            if not pvcs_output:
                time.sleep(poll_interval)
                continue
            pvcs = pvcs_output.get_pvcs()
            # Check each pending pvc
            for pvc_name in pending_pvcs[:]:
                # Find pvcs matching the prefix (or exact name if no pvc_names specified)
                matching_pvcs = [p for p in pvcs if p.get_name().startswith(pvc_name)]

                # If all matching pvcs are in expected status, remove from pending list
                if matching_pvcs and all(p.get_status() in expected_status for p in matching_pvcs):
                    get_logger().log_debug(f"pvc:{pvc_name} reached {expected_status} status")
                    pending_pvcs.remove(pvc_name)

            # If no pending pvcs remain, all have reached expected status
            if not pending_pvcs:
                get_logger().log_info(f"All pvcs:{pvc_names} reached {expected_status} status")
                return True
            else:
                get_logger().log_debug(f"pvcs left to reach status: {pending_pvcs}")

            time.sleep(poll_interval)

        # Timeout reached - raise exception with pending pvcs
        raise KeywordException(f"pvcs {pending_pvcs} did not reach {expected_status} status within {timeout} seconds")

    def wait_for_pvc_to_be_deleted(self, pvc_name: str, namespace: str = "default", poll_interval: int = 10, timeout: int = 180) -> bool:
        """Wait for a pvcs belongs to a namespace be deleted

        This function monitors pvcs in a given namespace and waits for them to be deleted

        Args:
            pvc_name (str): PVC name
            namespace (str): Kubernetes namespace to search in.
            poll_interval (int): Time in seconds between status checks. Defaults to 10.
            timeout (int): Maximum time in seconds to waiting the pvcs be deleted.

        Returns:
            bool: True if all specified pvcs where deleted within timeout.

        Raises:
            KeywordException: If pvcs still exist within timeout
        """

        def is_pvc_deleted() -> bool:
            ns_arg = f"-n {namespace}" if namespace else ""
            output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get pvc {pvc_name} {ns_arg}"))
            return f'"{pvc_name}" not found' in output[0]

        validate_equals_with_retry(
            function_to_execute=is_pvc_deleted,
            expected_value=True,
            validation_description=f"The pvc {pvc_name} was deleted",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )

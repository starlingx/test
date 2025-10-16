import time

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.volumesnapshots.object.kubectl_get_volumesnapshots_output import KubectlGetVolumesnapshotsOutput


class KubectlGetVolumesnapshotsKeywords(BaseKeyword):
    """
    Class for 'kubectl get volumesnapshots.snapshot.storage.k8s.io' keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize the KubectlGetVolumesnapshotsKeywords class.

        Args:
            ssh_connection (SSHConnection): An SSH connection object to the target system.
        """
        self.ssh_connection = ssh_connection

    def get_volumesnapshots(self, namespace: str = None, label: str = None) -> KubectlGetVolumesnapshotsOutput:
        """
        Gets the k8s volumesnapshots that are available using '-o wide'.

        Args:
            namespace(str, optional): The namespace to search for volumesnapshots. If None, it will search in all namespaces.
            label (str, optional): The label to search for volumesnapshots.

        Returns:
            KubectlGetVolumesnapshotsOutput: An object containing the parsed output of the command.

        """
        arg_namespace = ""

        if namespace:
            arg_namespace = f"-n {namespace}"

        kubectl_get_volumesnapshots_output = self.ssh_connection.send(export_k8s_config(f"kubectl {arg_namespace} -o wide get volumesnapshots.snapshot.storage.k8s.io"))
        self.validate_success_return_code(self.ssh_connection)
        volumesnapshots_list_output = KubectlGetVolumesnapshotsOutput(kubectl_get_volumesnapshots_output)

        return volumesnapshots_list_output

    def wait_for_volumesnapshot_status(self, volumesnapshot_name: str, expected_status: str, namespace: str = None, timeout: int = 600) -> bool:
        """
        Waits timeout amount of time for the given volumesnapshot to be in the given status

        Args:
            volumesnapshot_name (str): the volumesnapshot name
            expected_status (str): the expected status
            namespace (str): the namespace
            timeout (int): the timeout in secs

        Returns:
            bool: True if the volumesnapshot is in the expected status

        """
        volumesnapshot_status_timeout = time.time() + timeout

        while time.time() < volumesnapshot_status_timeout:
            volumesnapshots_output = self.get_volumesnapshots()
            if volumesnapshots_output:
                volumesnapshot_status = self.get_volumesnapshots(namespace).get_volumesnapshot(volumesnapshot_name).get_ready_to_use()
                if volumesnapshot_status == expected_status:
                    return True
            time.sleep(5)

        raise ValueError(f"volumesnapshot is not at expected status {expected_status}, after {timeout}s.")

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlLabelNamespaceKeywords(K8sBaseKeyword):
    """Class for kubectl label namespace keywords.

    The framework could already label a node but not a namespace: this package had create, delete
    and get, and get_namespaces_by_label() reads labels without being able to write one. Anything
    driven by a namespace label - istio's sidecar injection being the first case - had no way to set
    it.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def label_namespace(self, namespace: str, label_key: str, label_value: str) -> None:
        """Label a Kubernetes namespace.

        The return code of the write is asserted rather than returned, so a namespace that does not
        exist, or a label the API server rejects, fails here. A caller that reads the label back to
        decide whether the write worked would be testing the read instead of the write, and a
        silently unlabelled namespace produces a failure much further away from its cause.

        --overwrite is passed so relabelling an already-labelled namespace is not an error, matching
        the node equivalent.

        Args:
            namespace (str): Name of the namespace to label.
            label_key (str): Label key.
            label_value (str): Label value.
        """
        get_logger().log_info(f"Labeling namespace {namespace} with {label_key}={label_value}")
        self.ssh_connection.send(self.k8s_config.export(f"kubectl label namespace {namespace} {label_key}={label_value} --overwrite"))
        self.validate_success_return_code(self.ssh_connection)

    def remove_label(self, namespace: str, label_key: str) -> None:
        """Remove a label from a Kubernetes namespace.

        Args:
            namespace (str): Name of the namespace.
            label_key (str): Label key to remove.
        """
        get_logger().log_info(f"Removing label {label_key} from namespace {namespace}")
        self.ssh_connection.send(self.k8s_config.export(f"kubectl label namespace {namespace} {label_key}-"))
        self.validate_success_return_code(self.ssh_connection)

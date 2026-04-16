from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.node.object.kubectl_node_taint_output import KubectlNodeTaintOutput


class KubectlNodeTaintKeywords(K8sBaseKeyword):
    """
    Class for kubectl node taint operations
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """
        Constructor

        Args:
            ssh_connection(SSHConnection): SSH Connection object
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_node_taints(self) -> KubectlNodeTaintOutput:
        """
        Gets node taints using kubectl

        Returns:
            KubectlNodeTaintOutput: Parsed taint output object
        """
        # Extract node names and their taints in tab-separated format
        # Example output:
        #   Node                                              Taint
        #   controller-0    node-role.kubernetes.io/control-plane=:NoSchedule
        #   worker-0
        # Note: Nodes without taints will only show the node name without taint data
        cmd = 'kubectl get nodes -o go-template=\'{{printf "%-50s %-12s\\n" "Node" "Taint"}}{{- range .items}}{{- if $taint := (index .spec "taints") }}{{- .metadata.name }}{{ "\\t" }}{{- range $taint }}{{- .key }}={{ .value }}:{{ .effect }}{{ "\\t" }}{{- end }}{{- "\\n" }}{{- end}}{{- end}}\''
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlNodeTaintOutput(output)

    def verify_taints_enabled(self, expected_taints: list[str]) -> bool:
        """
        Verify that expected taints are present on nodes

        Args:
            expected_taints (list[str]): List of expected taint keys

        Returns:
            bool: True if all expected taints are found
        """
        taint_output = self.get_node_taints()
        for expected_taint in expected_taints:
            if not taint_output.is_taints_enabled(expected_taint):
                return False
        return True

    def add_taint(self, node_name: str, taint: str) -> None:
        """Add a taint to a Kubernetes node.

        Args:
            node_name (str): Name of the node to taint.
            taint (str): Taint specification (e.g., 'key=value:NoSchedule').
        """
        cmd = f"kubectl taint nodes {node_name} {taint}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

    def remove_taint(self, node_name: str, taint: str) -> None:
        """Remove a taint from a Kubernetes node.

        Args:
            node_name (str): Name of the node to untaint.
            taint (str): Taint specification to remove (e.g., 'key=value:NoSchedule').
                A trailing '-' is appended automatically if not present.
        """
        if not taint.endswith("-"):
            taint = f"{taint}-"
        cmd = f"kubectl taint nodes {node_name} {taint}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

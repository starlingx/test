from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.node.object.kubectl_node_taint_output import KubectlNodeTaintOutput


class KubectlNodeTaintKeywords(BaseKeyword):
    """
    Class for kubectl node taint operations
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection(SSHConnection): SSH Connection object
        """
        self.ssh_connection = ssh_connection

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
        cmd = "kubectl get nodes -o go-template='{{printf \"%-50s %-12s\\n\" \"Node\" \"Taint\"}}{{- range .items}}{{- if $taint := (index .spec \"taints\") }}{{- .metadata.name }}{{ \"\\t\" }}{{- range $taint }}{{- .key }}={{ .value }}:{{ .effect }}{{ \"\\t\" }}{{- end }}{{- \"\\n\" }}{{- end}}{{- end}}'"
        output = self.ssh_connection.send(export_k8s_config(cmd))
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

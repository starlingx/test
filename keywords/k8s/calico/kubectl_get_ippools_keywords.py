"""Keywords for the 'kubectl get ippools' command."""

from framework.logging.automation_logger import get_logger
from keywords.k8s.calico.object.calicoctl_ippool_output import CalicoctlIppoolOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetIPPoolsKeywords(K8sBaseKeyword):
    """Class for the 'kubectl get ippools' keyword."""

    def get_ippools(self) -> CalicoctlIppoolOutput:
        """Get the Calico IP pools as a parsed output object.

        A single CLI call is parsed into a CalicoctlIppoolOutput; callers read the
        pools, look one up by name, read spec fields, or count them from that
        object rather than re-running the command or parsing text themselves.

        Returns:
            CalicoctlIppoolOutput: An object containing the parsed IP pools.
        """
        get_logger().log_debug("Getting the Calico IP pools")
        output = self.ssh_connection.send(self.k8s_config.export("kubectl get ippools -o yaml"))
        self.validate_success_return_code(self.ssh_connection)
        return CalicoctlIppoolOutput(output)

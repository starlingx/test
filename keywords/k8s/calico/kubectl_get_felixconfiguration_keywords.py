"""Keywords for querying the Calico FelixConfiguration CR."""

from framework.logging.automation_logger import get_logger
from keywords.k8s.calico.object.felixconfiguration_output import FelixConfigurationOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetFelixConfigurationKeywords(K8sBaseKeyword):
    """Keywords for the 'kubectl get felixconfiguration' command."""

    def get_felixconfiguration(self) -> FelixConfigurationOutput:
        """Get the default FelixConfiguration CR as a parsed output object.

        A single CLI call is parsed into a FelixConfigurationOutput; callers read
        the fields they need from that object's getters rather than re-running the
        command for each field.

        Returns:
            FelixConfigurationOutput: An object containing the parsed FelixConfiguration.
        """
        get_logger().log_debug("Getting the default FelixConfiguration CR")
        output = self.ssh_connection.send(self.k8s_config.export("kubectl get felixconfiguration default -o yaml"))
        self.validate_success_return_code(self.ssh_connection)
        return FelixConfigurationOutput(output)

"""Keywords for the calico-node pods and the installed Calico release."""

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.k8s.calico.kubectl_get_installation_keywords import KubectlGetInstallationKeywords
from keywords.k8s.calico.object.calico_node_status_output import CalicoNodeStatusOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.object.kubectl_pod_object import KubectlPodObject

CALICO_NODE_NAMESPACE = "calico-system"
CALICO_NODE_LABEL = "k8s-app=calico-node"
CALICO_NODE_CONTAINER = "calico-node"


class KubectlCalicoNodeKeywords(K8sBaseKeyword):
    """Keywords for the calico-node pods and the installed Calico release."""

    def get_calico_node_pods(self) -> list[KubectlPodObject]:
        """Get the calico-node pods.

        Returns:
            list[KubectlPodObject]: One calico-node pod per node.

        Raises:
            KeywordException: If no calico-node pod is found.
        """
        pods = KubectlGetPodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_pods_json(namespace=CALICO_NODE_NAMESPACE, label=CALICO_NODE_LABEL).get_pods()
        if not pods:
            raise KeywordException(f"No calico-node pod ({CALICO_NODE_LABEL}) found in namespace {CALICO_NODE_NAMESPACE}")
        return pods

    def get_calico_release(self) -> str:
        """Get the installed Calico release from the calico-node image tag.

        Returns:
            str: The Calico release (e.g. 'v3.31.5').
        """
        calico_release = self.get_calico_node_pods()[0].get_container_image_tag(CALICO_NODE_CONTAINER)
        get_logger().log_info(f"Installed Calico release: {calico_release}")
        return calico_release

    def get_calico_image(self, component: str) -> str:
        """Get the image of a Calico component that matches the installed release.

        The registry is read from the Installation CR and the tag from the calico-node
        image, so the reference follows the installed Calico version.

        Args:
            component (str): The Calico image name (e.g. 'envoy-proxy').

        Returns:
            str: The image reference (e.g. '<registry>/calico/envoy-proxy:v3.31.5').

        Raises:
            KeywordException: If the Installation CR has no registry.
        """
        registry = KubectlGetInstallationKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_installation().get_registry()
        if not registry:
            raise KeywordException("The Installation CR has no registry; cannot derive the Calico image reference")
        return f"{registry.rstrip('/')}/calico/{component}:{self.get_calico_release()}"

    def get_calico_node_status(self) -> CalicoNodeStatusOutput:
        """Get the bird status and BGP peers reported by 'calico-node -show-status'.

        The command runs inside a calico-node pod, so no calicoctl pod is needed.

        Returns:
            CalicoNodeStatusOutput: The parsed bird status and BGP peers.
        """
        pod_name = self.get_calico_node_pods()[0].get_name()
        output = KubectlExecInPodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).run_pod_exec_cmd(pod_name, "calico-node -show-status", options=f"-n {CALICO_NODE_NAMESPACE} -c {CALICO_NODE_CONTAINER}")
        return CalicoNodeStatusOutput(output)

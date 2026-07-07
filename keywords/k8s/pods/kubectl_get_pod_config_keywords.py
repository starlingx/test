"""Keywords for reading configuration values from running pods."""

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.configmap.kubectl_get_configmap_keywords import KubectlGetConfigmapKeywords
from keywords.k8s.configmap.object.kubectl_configmap_object import KubectlConfigmapObject
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pod_jsonpath_keywords import KubectlGetPodJsonpathKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.object.kubectl_pod_object import KubectlPodObject


class KubectlGetPodConfigKeywords(K8sBaseKeyword):
    """Keywords for reading configuration values from running pods."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize the KubectlGetPodConfigKeywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)
        self.pods_kw = KubectlGetPodsKeywords(ssh_connection, kubeconfig_path)
        self.exec_kw = KubectlExecInPodsKeywords(ssh_connection, kubeconfig_path)
        self.jsonpath_kw = KubectlGetPodJsonpathKeywords(ssh_connection, kubeconfig_path)
        self.configmap_kw = KubectlGetConfigmapKeywords(ssh_connection, kubeconfig_path)

    def _resolve_pod(self, namespace: str, pod_name: str = None, pod_label: str = None) -> KubectlPodObject:
        """Resolve a pod object from either a direct name or a label selector.

        Args:
            namespace (str): Kubernetes namespace.
            pod_name (str, optional): Direct pod name. If provided, finds the pod by name.
            pod_label (str, optional): Label selector to find the pod.

        Returns:
            KubectlPodObject: The resolved pod object.

        Raises:
            KeywordException: If neither pod_name nor pod_label is provided,
                or if no pod matches the criteria.
        """
        if pod_name:
            pods_output = self.pods_kw.get_pods(namespace=namespace)
            pods = pods_output.get_pods()
            matching = [p for p in pods if p.get_name() == pod_name]
            if not matching:
                raise KeywordException(f"Pod '{pod_name}' not found in namespace '{namespace}'")
            return matching[0]

        if pod_label:
            pods_output = self.pods_kw.get_pods(namespace=namespace, label=pod_label)
            pods = pods_output.get_pods()
            if not pods:
                raise KeywordException(f"No pod found matching label '{pod_label}' in namespace '{namespace}'")
            return pods[0]

        raise KeywordException("Either pod_name or pod_label must be provided")

    def get_pod_config_value(self, namespace: str, config_file_path: str, config_key: str, pod_name: str = None, pod_label: str = None) -> str:
        """Read a configuration value from a file inside a running pod.

        Executes into the pod and greps the config file for the specified key.
        Supports INI-style (key = value) and YAML-style (key: value) config files.

        Args:
            namespace (str): Kubernetes namespace where the pod runs.
            config_file_path (str): Absolute path to the config file inside the pod.
            config_key (str): Configuration key to search for.
            pod_name (str, optional): Direct pod name.
            pod_label (str, optional): Label selector to find the pod.

        Returns:
            str: The value associated with the config key.

        Raises:
            KeywordException: If the key is not found in the config file.
        """
        pod = self._resolve_pod(namespace, pod_name, pod_label)
        cmd = f"grep -E '^\\s*{config_key}\\s*[=:]' {config_file_path}"
        output = self.exec_kw.run_pod_exec_cmd(pod.get_name(), cmd, options=f"-n {namespace}")
        result = "\n".join(output) if isinstance(output, list) else str(output)
        result = result.strip()
        if "=" not in result and ":" not in result:
            raise KeywordException(f"Key '{config_key}' not found in {config_file_path} on pod '{pod.get_name()}'")
        separator = "=" if "=" in result else ":"
        value = result.split(separator, 1)[1].strip()
        return value

    def get_pod_env_value(self, namespace: str, env_name: str, pod_name: str = None, pod_label: str = None) -> str:
        """Read an environment variable value from a pod spec.

        Uses kubectl jsonpath to extract the environment variable from
        the pod's container spec.

        Args:
            namespace (str): Kubernetes namespace where the pod runs.
            env_name (str): Name of the environment variable to read.
            pod_name (str, optional): Direct pod name.
            pod_label (str, optional): Label selector to find the pod.

        Returns:
            str: The value of the environment variable.

        Raises:
            KeywordException: If the environment variable is not found.
        """
        pod = self._resolve_pod(namespace, pod_name, pod_label)
        jsonpath = f'{{.spec.containers[*].env[?(@.name=="{env_name}")].value}}'
        value = self.jsonpath_kw.get_pod_jsonpath_value(pod.get_name(), jsonpath, namespace)
        if not value:
            raise KeywordException(f"Env var '{env_name}' not found on pod '{pod.get_name()}' in namespace '{namespace}'")
        return value

    def get_configmap(self, namespace: str, configmap_name: str) -> KubectlConfigmapObject:
        """Get a ConfigMap as a parsed object.

        Args:
            namespace (str): Kubernetes namespace where the ConfigMap exists.
            configmap_name (str): Name of the ConfigMap.

        Returns:
            KubectlConfigmapObject: The parsed ConfigMap object with data accessible via getters.
        """
        output = self.configmap_kw.get_configmap(configmap_name, namespace)
        return output.get_configmap()

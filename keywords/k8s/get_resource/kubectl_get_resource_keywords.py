"""Keywords for generic kubectl get operations on any resource type."""

import shlex
from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetResourceKeywords(K8sBaseKeyword):
    """Keywords for generic kubectl get operations on any resource type."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: Optional[str] = None) -> None:
        """Initialize keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
            kubeconfig_path (Optional[str]): Custom KUBECONFIG path. If None, uses default.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_resource_field(self, resource_type: str, resource_name: str, jsonpath: str, namespace: Optional[str] = None) -> str:
        """Get a field from any Kubernetes resource using jsonpath.

        This is an escape hatch for resource types that do not yet have a
        dedicated Output object. Prefer typed keyword/Output pairs when available.

        Args:
            resource_type (str): Resource type (e.g., 'servicemonitor', 'pod', 'deployment').
            resource_name (str): Resource name.
            jsonpath (str): JSONPath expression (e.g., '{.metadata.name}', '{.spec.retention}').
            namespace (Optional[str]): Namespace. If None, uses default namespace.

        Returns:
            str: The field value.

        Raises:
            AssertionError: If kubectl get fails.
        """
        cmd = f"kubectl get {resource_type} {resource_name} -o jsonpath='{jsonpath}'"
        if namespace:
            cmd += f" -n {namespace}"

        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        output_text = "\n".join(output) if isinstance(output, list) else output
        return output_text.strip()

    def is_namespace_empty(self, namespace: str) -> bool:
        """Check whether a namespace has no common resources via 'kubectl get all'.

        Runs 'kubectl get all -n <namespace>' and returns True when kubectl
        reports that no resources are present. Note that 'kubectl get all'
        only lists common built-in resource types (pods, deployments,
        services, etc.) and not arbitrary custom resources.

        Args:
            namespace (str): Namespace to check.

        Returns:
            bool: True if no resources are found in the namespace, False otherwise.
        """
        cmd = f"kubectl get all -n {namespace}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        output_text = "\n".join(output) if isinstance(output, list) else output
        return "No resources found" in output_text

    def is_resource_present(self, resource_type: str, resource_name: str, namespace: Optional[str] = None) -> bool:
        """Check whether a Kubernetes resource exists.

        Uses --ignore-not-found so a missing resource returns no output, while
        any other kubectl failure still fails the command. Prefer this over
        KubectlCustomKeywords.is_custom_resource_present when the answer decides
        what is created or deleted, since that keyword reports any kubectl error
        as an absent resource.

        Args:
            resource_type (str): Resource type (e.g., 'statefulset', 'ingress').
            resource_name (str): Resource name.
            namespace (Optional[str]): Namespace. If None, uses default namespace.

        Returns:
            bool: True if the resource exists.
        """
        cmd = f"kubectl get {shlex.quote(resource_type)} {shlex.quote(resource_name)} --ignore-not-found -o name"
        if namespace:
            cmd += f" -n {shlex.quote(namespace)}"

        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)

        lines = output if isinstance(output, list) else output.splitlines()
        # -o name prints <kind>[.<group>]/<name> (for example statefulset.apps/keycloak),
        # so compare the part after the slash exactly.
        return any(line.strip().split("/", 1)[-1] == resource_name for line in lines if "/" in line)

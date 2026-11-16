"""Keywords for 'kubectl get' on Deployment Manager CRD resources."""

from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.k8s.crd.object.kubectl_dm_resources_output import KubectlDmResourcesOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword

EXPECTED_RESOURCE_VALUES = ("true", "principal", "true")

# With a principal scope the deployment manager playbook restarts the deployment manager pod and returns once
# the new pod is Ready. The resources are reconciled after that, so every check after a playbook run waits.
RECONCILE_TIMEOUT = 300
RECONCILE_POLLING_INTERVAL = 15


class KubectlDmResourcesKeywords(K8sBaseKeyword):
    """Keywords for reading any Deployment Manager CRD resource (DataNetwork, PtpInstance, PtpInterface, ...)."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: Optional[str] = None):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection object.
            kubeconfig_path (Optional[str]): Custom KUBECONFIG path.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_dm_resources(self, resource_type: str, resource_name: Optional[str] = None, namespace: str = "deployment") -> KubectlDmResourcesOutput:
        """Get Deployment Manager resources using the default printer columns (INSYNC, SCOPE, RECONCILED).

        Args:
            resource_type (str): Resource kind, e.g. "DataNetwork" or "PtpInstance".
            resource_name (Optional[str]): Name of a single resource. If None, all resources of the type are returned.
            namespace (str): Namespace to query. Defaults to "deployment".

        Returns:
            KubectlDmResourcesOutput: Parsed output of the command.
        """
        return self._get(resource_type, resource_name, namespace, "")

    def get_dm_resource_details(self, resource_type: str, resource_name: Optional[str] = None, namespace: str = "deployment") -> KubectlDmResourcesOutput:
        """Get Deployment Manager resources with their type, description, scope, reconciled and delta values.

        The resources are read as JSON, because the delta of a resource such as System spans several lines
        and cannot be read from a table column.

        Args:
            resource_type (str): Resource kind, e.g. "DataNetwork" or "PtpInstance".
            resource_name (Optional[str]): Name of a single resource. If None, all resources of the type are returned.
            namespace (str): Namespace to query. Defaults to "deployment".

        Returns:
            KubectlDmResourcesOutput: Parsed output of the command.
        """
        name_arg = f" {resource_name}" if resource_name else ""
        cmd = f"kubectl get {resource_type}{name_arg} -n {namespace} -o json"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlDmResourcesOutput(output, source="json")

    def get_deployment_scope(self, kind: str, name: str) -> Optional[str]:
        """Get the deployment scope of a resource.

        Args:
            kind (str): Kind of the resource.
            name (str): Name of the resource.

        Returns:
            Optional[str]: Deployment scope, or None if the resource does not exist.
        """
        resources = self.get_dm_resource_details(kind).get_resources()
        return next((resource.get_scope() for resource in resources if resource.get_name() == name), None)

    def get_resource_status(self, kind: str, name: str) -> tuple:
        """Get the INSYNC, SCOPE and RECONCILED values of a resource.

        Args:
            kind (str): Kind of the resource.
            name (str): Name of the resource.

        Returns:
            tuple: (INSYNC, SCOPE, RECONCILED).
        """
        resource = self.get_dm_resources(kind, name).get_resource(name)
        return resource.get_insync(), resource.get_scope(), resource.get_reconciled()

    def get_resource_values(self, kind: str, name: str, fields: tuple) -> dict:
        """Get the Type, Name, Description, Scope, Reconciled and DELTA values of a resource.

        Args:
            kind (str): Kind of the resource.
            name (str): Name of the resource.
            fields (tuple): Names of the values to return, e.g. ("Name", "Scope").

        Returns:
            dict: Value of each requested field.
        """
        resource = self.get_dm_resource_details(kind, name).get_resource(name)
        values = {
            "Type": resource.get_type(),
            "Name": resource.get_name(),
            "Description": resource.get_description(),
            "Scope": resource.get_scope(),
            "Reconciled": resource.get_reconciled(),
            "DELTA": resource.get_delta(),
        }
        return {field: values[field] for field in fields}

    def wait_for_principal_status(self, kind: str, name: str, description: str):
        """Wait until a resource is in sync, has the principal scope and is reconciled.

        Args:
            kind (str): Kind of the resource.
            name (str): Name of the resource.
            description (str): Description of the check, for logging.
        """
        resource_status = validate_equals_with_retry(lambda: self.get_resource_status(kind, name), EXPECTED_RESOURCE_VALUES, description, timeout=RECONCILE_TIMEOUT, polling_sleep_time=RECONCILE_POLLING_INTERVAL)
        get_logger().log_info(f"get {kind} resource values : {resource_status}")

    def wait_for_resource_values(self, kind: str, name: str, expected_values: dict, description: str):
        """Wait until the Type, Name, Description, Scope, Reconciled and DELTA values of a resource match.

        Args:
            kind (str): Kind of the resource.
            name (str): Name of the resource.
            expected_values (dict): Expected value of each field.
            description (str): Description of the check, for logging.
        """
        validate_equals_with_retry(lambda: self.get_resource_values(kind, name, tuple(expected_values)), expected_values, description, timeout=RECONCILE_TIMEOUT, polling_sleep_time=RECONCILE_POLLING_INTERVAL)

    def _get(self, resource_type: str, resource_name: Optional[str], namespace: str, extra_args: str) -> KubectlDmResourcesOutput:
        """Run 'kubectl get' for a Deployment Manager resource and parse the table.

        Args:
            resource_type (str): Resource kind.
            resource_name (Optional[str]): Resource name or None for all.
            namespace (str): Namespace to query.
            extra_args (str): Extra arguments appended to the command.

        Returns:
            KubectlDmResourcesOutput: Parsed output of the command.
        """
        name_arg = f" {resource_name}" if resource_name else ""
        cmd = f"kubectl get {resource_type}{name_arg} -n {namespace}{extra_args}"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return KubectlDmResourcesOutput(output)

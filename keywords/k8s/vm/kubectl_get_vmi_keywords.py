from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry, validate_not_equals_with_retry, validate_not_none_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword


class KubectlGetVmiKeywords(K8sBaseKeyword):
    """Keywords for kubectl get vmi operations."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None):
        """Initialize the KubectlGetVmiKeywords class.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
            kubeconfig_path (str, optional): Custom KUBECONFIG path. If None, uses default from config.
        """
        super().__init__(ssh_connection, kubeconfig_path)

    def get_vmi_ip(self, vmi_name: str, namespace: str = "default") -> str:
        """Get VMI IP address.

        Args:
            vmi_name (str): Name of the VMI.
            namespace (str): Namespace of the VMI. Defaults to 'default'.

        Returns:
            str: VMI IP address.
        """
        cmd = f"kubectl get vmi {vmi_name} -n {namespace} -o jsonpath='{{.status.interfaces[0].ipAddress}}'"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return output[0] if output else ""

    def get_vmi_node(self, vmi_name: str, namespace: str = "default") -> str:
        """Get VMI node name.

        Args:
            vmi_name (str): Name of the VMI.
            namespace (str): Namespace of the VMI. Defaults to 'default'.

        Returns:
            str: VMI node name.
        """
        cmd = f"kubectl get vmi {vmi_name} -n {namespace} -o jsonpath='{{.status.nodeName}}'"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return output[0] if output else ""

    def is_vmi_present(self, vmi_name: str, namespace: str = "default") -> bool:
        """Check whether a VMI exists.

        Args:
            vmi_name (str): Name of the VMI.
            namespace (str): Namespace of the VMI. Defaults to 'default'.

        Returns:
            bool: True if the VMI exists, False otherwise.
        """
        # 'kubectl get vmi' exits non-zero when the VMI does not exist, so the
        # return code alone tells us whether it is present without asserting.
        cmd = f"kubectl get vmi {vmi_name} -n {namespace}"
        self.ssh_connection.send(self.k8s_config.export(cmd))
        return self.ssh_connection.get_return_code() == 0

    def get_vmi_status(self, vmi_name: str, namespace: str = "default") -> str:
        """Get VMI phase using kubectl.

        Args:
            vmi_name (str): Name of the VMI.
            namespace (str): Namespace of the VMI. Defaults to 'default'.

        Returns:
            str: VMI phase (e.g. 'Running').
        """
        cmd = f"kubectl get vmi {vmi_name} -n {namespace} -o jsonpath='{{.status.phase}}'"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return output[0] if output else ""

    def get_vmi_uid(self, vmi_name: str, namespace: str = "default") -> str:
        """Get the VMI object UID using kubectl.

        The UID is regenerated when the VirtualMachineInstance is recreated (for
        example after a reboot restarts the guest), so callers can compare UIDs
        before and after an operation to confirm the VMI was recreated.

        Args:
            vmi_name (str): Name of the VMI.
            namespace (str): Namespace of the VMI. Defaults to 'default'.

        Returns:
            str: VMI UID, or empty string if the VMI does not exist.
        """
        cmd = f"kubectl get vmi {vmi_name} -n {namespace} -o jsonpath='{{.metadata.uid}}' --ignore-not-found=true"
        output = self.ssh_connection.send(self.k8s_config.export(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return output[0] if output else ""

    def wait_for_vmi_recreated(self, vmi_name: str, initial_uid: str, namespace: str = "default", timeout: int = 180, poll_interval: int = 5) -> str:
        """Wait for a VMI to be recreated (present with a new, non-empty UID).

        A soft reboot recreates the VirtualMachineInstance, giving it a new UID.
        The old VMI is deleted before the new one appears, so during that gap the
        UID is empty. Success therefore requires the observed UID to be both
        non-empty and different from initial_uid; an empty UID (VMI absent) keeps
        polling rather than being treated as a successful recreation. This guards
        against a reboot that never brings the VMI back reporting success.

        Args:
            vmi_name (str): Name of the VMI.
            initial_uid (str): UID captured before the operation that recreates the VMI.
            namespace (str): Namespace of the VMI. Defaults to 'default'.
            timeout (int): Maximum time to wait in seconds. Defaults to 180.
            poll_interval (int): Time between checks in seconds. Defaults to 5.

        Returns:
            str: The new (non-empty) VMI UID after recreation.

        Raises:
            TimeoutError: If a new non-empty UID does not appear within timeout.
        """
        # Build a ValidationResponse whose validated value is True only when the
        # VMI is present again with a UID that is non-empty AND differs from
        # initial_uid; the returned value is that new UID. The empty-UID window
        # while the old VMI is deleted validates as False, so it keeps polling
        # instead of falsely reporting a successful recreation.
        return validate_equals_with_retry(
            function_to_execute=lambda: self._build_uid_recreated_response(vmi_name, initial_uid, namespace),
            expected_value=True,
            validation_description=f"VMI {vmi_name} to be recreated with a new UID",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )

    def _build_uid_recreated_response(self, vmi_name: str, initial_uid: str, namespace: str) -> ValidationResponse:
        """Build a recreation-check ValidationResponse for the current VMI UID.

        Args:
            vmi_name (str): Name of the VMI.
            initial_uid (str): UID captured before the recreating operation.
            namespace (str): Namespace of the VMI.

        Returns:
            ValidationResponse: value_to_validate is True only when the current
                UID is non-empty and differs from initial_uid; value_to_return is
                the current UID.
        """
        uid = self.get_vmi_uid(vmi_name, namespace)
        return ValidationResponse(value_to_validate=bool(uid) and uid != initial_uid, value_to_return=uid)

    def wait_for_vmi_status(self, vmi_name: str, expected_status: str = "Running", namespace: str = "default", timeout: int = 60, poll_interval: int = 5) -> None:
        """Wait for VMI to reach expected phase.

        Args:
            vmi_name (str): Name of the VMI.
            expected_status (str): Expected VMI phase. Defaults to 'Running'.
            namespace (str): Namespace of the VMI. Defaults to 'default'.
            timeout (int): Maximum time to wait in seconds. Defaults to 60.
            poll_interval (int): Time between checks in seconds. Defaults to 5.

        Raises:
            TimeoutError: If VMI doesn't reach expected phase within timeout.
        """
        # Polls VMI phase until it matches the expected status.
        # Fails fast if VMI enters an error state.
        validate_equals_with_retry(
            function_to_execute=lambda: self.get_vmi_status(vmi_name, namespace),
            expected_value=expected_status,
            validation_description=f"VMI {vmi_name} to reach phase {expected_status}",
            timeout=timeout,
            polling_sleep_time=poll_interval,
            failure_values=["Failed", "ErrorUnschedulable"],
        )

    def wait_for_vmi_node_change(self, vmi_name: str, initial_node: str, namespace: str = "default", timeout: int = 180, poll_interval: int = 5) -> str:
        """Wait for VMI to migrate to a different node.

        Args:
            vmi_name (str): Name of the VMI.
            initial_node (str): The node the VMI is currently running on.
            namespace (str): Namespace of the VMI. Defaults to 'default'.
            timeout (int): Maximum time to wait in seconds. Defaults to 180.
            poll_interval (int): Time between checks in seconds. Defaults to 5.

        Returns:
            str: The new node name after migration.

        Raises:
            TimeoutError: If VMI does not migrate to a different node within timeout.
        """
        # Polls VMI node until it differs from initial_node, returns the new node name
        return validate_not_equals_with_retry(
            function_to_execute=lambda: self.get_vmi_node(vmi_name, namespace),
            not_expected_value=initial_node,
            validation_description=f"VMI {vmi_name} to migrate away from {initial_node}",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )

    def wait_for_vmi_ready(self, vmi_name: str, namespace: str = "default", timeout: int = 60, poll_interval: int = 5) -> None:
        """Wait for VMI to have IP and node assigned.

        Args:
            vmi_name (str): Name of the VMI.
            namespace (str): Namespace of the VMI. Defaults to 'default'.
            timeout (int): Maximum time to wait in seconds. Defaults to 60.
            poll_interval (int): Time between checks in seconds. Defaults to 5.

        Raises:
            TimeoutError: If VMI doesn't get IP and node within timeout.
        """
        # Polls until both IP and node are assigned, indicating the VMI is schedulable
        validate_not_none_with_retry(
            function_to_execute=lambda: (self.get_vmi_ip(vmi_name, namespace) or None) and (self.get_vmi_node(vmi_name, namespace) or None),
            validation_description=f"VMI {vmi_name} to have IP and node assigned",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )

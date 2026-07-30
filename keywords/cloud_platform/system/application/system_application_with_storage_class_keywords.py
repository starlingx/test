"""Keywords for ensuring a platform application reaches applied state.

Provides a precondition keyword that discovers the correct StorageClass,
sets the required helm override, applies the application, and polls
until it reaches the applied state. Designed for applications that
require persistent storage (e.g., prometheus, rook-ceph).
"""

from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.k8s.pvc.kubectl_get_pvc_keywords import KubectlGetPvcKeywords
from keywords.k8s.storageclass.kubectl_get_storageclass_keywords import KubectlGetStorageclassKeywords

DEFAULT_APPLY_TIMEOUT = 300
DEFAULT_APPLY_POLLING_INTERVAL = 30

TRANSITIONAL_STATES = ["applying", "removing", "uploading"]


class SystemApplicationWithStorageClassKeywords(BaseKeyword):
    """Keywords for ensuring a platform application is in applied state.

    Handles the precondition flow of discovering the correct StorageClass,
    setting the helm override, and applying the application if not already
    in applied state.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def ensure_applied(
        self,
        app_name: str,
        chart_name: str,
        namespace: str,
        storage_class_override_path: str,
        preferred_storage_class: Optional[str] = None,
        pvc_name_prefix: Optional[str] = None,
        timeout: int = DEFAULT_APPLY_TIMEOUT,
        polling_sleep_time: int = DEFAULT_APPLY_POLLING_INTERVAL,
    ) -> str:
        """Ensure an application is in applied state, applying if necessary.

        If the app is already applied, detects the StorageClass from the
        existing PVC (immutable once bound) and sets the override to match.
        If not applied, discovers available StorageClasses, picks the best
        one, sets the override, and applies.

        Args:
            app_name (str): Name of the application (e.g. 'prometheus').
            chart_name (str): Helm chart name (e.g. 'kube-prometheus-stack').
            namespace (str): Helm chart namespace (e.g. 'monitoring').
            storage_class_override_path (str): Full Helm --set key path for
                the storageClassName override.
            preferred_storage_class (Optional[str]): Preferred StorageClass name
                for fresh installs. If None, uses cluster default or first
                available. Defaults to None.
            pvc_name_prefix (Optional[str]): If provided, only consider PVCs
                whose name starts with this prefix when detecting the
                StorageClass. Prevents picking an unrelated PVC in a shared
                namespace. Defaults to None (use first available PVC).
            timeout (int): Maximum seconds to wait for applied state.
                Defaults to 300.
            polling_sleep_time (int): Seconds between status polls.
                Defaults to 30.

        Returns:
            str: The StorageClass name that was selected and used.

        Raises:
            TimeoutError: If application does not reach applied state within timeout.
            ValueError: If no StorageClasses are available in the cluster.
        """
        app_show_keywords = SystemApplicationShowKeywords(self.ssh_connection)

        app_output = app_show_keywords.get_system_application_show(app_name)
        current_status = app_output.get_system_application_object().get_status()
        get_logger().log_info(f"Application '{app_name}' current status: {current_status}")

        # If app is in a transitional state, wait for it to reach a terminal state
        if current_status in TRANSITIONAL_STATES:
            get_logger().log_info(f"Application '{app_name}' is in transitional state '{current_status}', waiting for completion")
            current_status = self._wait_for_terminal_state(app_name, timeout)
            get_logger().log_info(f"Application '{app_name}' reached terminal state: {current_status}")

        if current_status == "applied":
            # App is already applied — use the SC from existing PVC (immutable)
            selected_sc = self._get_storage_class_from_pvc(namespace, preferred_storage_class, pvc_name_prefix)
            get_logger().log_info(f"App already applied, using PVC StorageClass: {selected_sc}")
            self._set_storage_class_override(
                app_name,
                chart_name,
                namespace,
                storage_class_override_path,
                selected_sc,
            )
            return selected_sc

        # App not applied — check if PVC exists (e.g. apply-failed still has bound PVC)
        selected_sc = self._get_storage_class_from_pvc(namespace, preferred_storage_class, pvc_name_prefix)
        get_logger().log_info(f"Selected StorageClass: {selected_sc}")
        self._set_storage_class_override(
            app_name,
            chart_name,
            namespace,
            storage_class_override_path,
            selected_sc,
        )

        get_logger().log_info(f"Applying application '{app_name}'")
        SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply(
            app_name,
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )
        return selected_sc

    def _get_storage_class_from_pvc(self, namespace: str, fallback: Optional[str], pvc_name_prefix: Optional[str] = None) -> str:
        """Get the StorageClass from existing PVCs in the namespace.

        When the app is already applied, the PVC storageClassName is immutable.
        We must use whatever SC the PVC is currently bound to.

        Args:
            namespace (str): Namespace to query PVCs from.
            fallback (Optional[str]): Preferred SC name if no PVCs are found.
                If None, triggers auto-discovery.
            pvc_name_prefix (Optional[str]): If provided, only consider PVCs
                whose name starts with this prefix. Defaults to None.

        Returns:
            str: The StorageClass name from the first matching PVC, or discovered SC.
        """
        pvc_keywords = KubectlGetPvcKeywords(self.ssh_connection)
        sc_from_pvc = pvc_keywords.get_storage_class_from_pvcs(namespace, pvc_name_prefix)
        if sc_from_pvc:
            return sc_from_pvc

        get_logger().log_info(f"No PVCs found in namespace '{namespace}', falling back to discovery")
        return KubectlGetStorageclassKeywords(self.ssh_connection).select_storage_class(fallback)

    def _set_storage_class_override(
        self,
        app_name: str,
        chart_name: str,
        namespace: str,
        storage_class_override_path: str,
        storage_class_name: str,
    ) -> None:
        """Set the StorageClass helm override for the application.

        Args:
            app_name (str): Application name.
            chart_name (str): Helm chart name.
            namespace (str): Helm chart namespace.
            storage_class_override_path (str): Full Helm --set key path.
            storage_class_name (str): StorageClass name to set.
        """
        helm_keywords = SystemHelmOverrideKeywords(self.ssh_connection)
        override_value = f"{storage_class_override_path}={storage_class_name}"
        get_logger().log_info(f"Setting helm override: {override_value}")
        helm_keywords.update_helm_override_via_set(
            override_value,
            app_name,
            chart_name,
            namespace,
            reuse_values=True,
        )

    def _wait_for_terminal_state(
        self,
        app_name: str,
        timeout: int,
        polling_interval: int = 15,
    ) -> str:
        """Wait for an application to leave a transitional state.

        Polls the application status until it reaches a terminal state
        (applied, apply-failed, uploaded, removed) or times out.

        Args:
            app_name (str): Application name.
            timeout (int): Maximum seconds to wait.
            polling_interval (int): Seconds between polls. Defaults to 15.

        Returns:
            str: The terminal status reached.

        Raises:
            TimeoutError: If the application remains in a transitional state
                beyond the timeout.
        """
        app_show_keywords = SystemApplicationShowKeywords(self.ssh_connection)

        def get_status_if_terminal():
            """Return status if terminal, False otherwise."""
            app_output = app_show_keywords.get_system_application_show(app_name)
            status = app_output.get_system_application_object().get_status()
            if status not in TRANSITIONAL_STATES:
                return status
            get_logger().log_info(f"Application '{app_name}' still in '{status}' state")
            return False

        validate_equals_with_retry(
            function_to_execute=lambda: get_status_if_terminal() is not False,
            expected_value=True,
            validation_description=f"Application '{app_name}' reaches terminal state",
            timeout=timeout,
            polling_sleep_time=polling_interval,
        )

        # Get the final status after successful validation
        app_output = app_show_keywords.get_system_application_show(app_name)
        return app_output.get_system_application_object().get_status()

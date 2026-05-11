"""Object representing a TridentBackendConfig resource."""


class KubectlTridentBackendConfigObject:
    """Represents a single TridentBackendConfig from kubectl get tbc -o json."""

    def __init__(self) -> None:
        """Initialize KubectlTridentBackendConfigObject with default values."""
        self._name: str = ""
        self._namespace: str = ""
        self._storage_driver_name: str = ""
        self._last_operation_status: str = ""
        self._message: str = ""
        self._backend_name: str = ""

    def get_name(self) -> str:
        """Get the TBC resource name.

        Returns:
            str: TBC name.
        """
        return self._name

    def set_name(self, name: str) -> None:
        """Set the TBC resource name.

        Args:
            name (str): TBC name.
        """
        self._name = name

    def get_namespace(self) -> str:
        """Get the namespace.

        Returns:
            str: Namespace.
        """
        return self._namespace

    def set_namespace(self, namespace: str) -> None:
        """Set the namespace.

        Args:
            namespace (str): Namespace.
        """
        self._namespace = namespace

    def get_storage_driver_name(self) -> str:
        """Get the storage driver name.

        Returns:
            str: Driver name (e.g. 'ontap-nas', 'ontap-san', 'ontap-san-fc').
        """
        return self._storage_driver_name

    def set_storage_driver_name(self, driver: str) -> None:
        """Set the storage driver name.

        Args:
            driver (str): Driver name.
        """
        self._storage_driver_name = driver

    def get_last_operation_status(self) -> str:
        """Get the last operation status.

        Returns:
            str: Status (e.g. 'Success', 'Failed').
        """
        return self._last_operation_status

    def set_last_operation_status(self, status: str) -> None:
        """Set the last operation status.

        Args:
            status (str): Status string.
        """
        self._last_operation_status = status

    def get_message(self) -> str:
        """Get the status message.

        Returns:
            str: Status message.
        """
        return self._message

    def set_message(self, message: str) -> None:
        """Set the status message.

        Args:
            message (str): Status message.
        """
        self._message = message

    def get_backend_name(self) -> str:
        """Get the backend name from spec.

        Returns:
            str: Backend name.
        """
        return self._backend_name

    def set_backend_name(self, backend_name: str) -> None:
        """Set the backend name.

        Args:
            backend_name (str): Backend name.
        """
        self._backend_name = backend_name

    def is_healthy(self) -> bool:
        """Check if the backend is healthy (lastOperationStatus == Success).

        Returns:
            bool: True if backend is connected and healthy.
        """
        return self._last_operation_status == "Success"

    def __str__(self) -> str:
        """Human-readable representation.

        Returns:
            str: String representation.
        """
        return (
            f"TridentBackendConfig(name={self._name}, "
            f"driver={self._storage_driver_name}, "
            f"status={self._last_operation_status})"
        )

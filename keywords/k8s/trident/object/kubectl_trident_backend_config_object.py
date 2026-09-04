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
        self._phase: str = ""
        self._management_lif: str = ""
        self._data_lif: str = ""
        self._svm: str = ""
        self._nfs_mount_options: str = ""
        self._credentials_secret_name: str = ""

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

    def get_phase(self) -> str:
        """Get the backend phase from status.

        Returns:
            str: Phase (e.g. 'Bound', 'Lost', '').
        """
        return self._phase

    def set_phase(self, phase: str) -> None:
        """Set the backend phase.

        Args:
            phase (str): Phase string.
        """
        self._phase = phase

    def get_management_lif(self) -> str:
        """Get the managementLIF address from spec.

        Returns:
            str: managementLIF (e.g. '10.82.159.2' or '[fdff:10:82:194::2]').
        """
        return self._management_lif

    def set_management_lif(self, management_lif: str) -> None:
        """Set the managementLIF address.

        Args:
            management_lif (str): managementLIF address.
        """
        self._management_lif = management_lif

    def get_data_lif(self) -> str:
        """Get the dataLIF address from spec.

        Returns:
            str: dataLIF (e.g. '10.82.159.3' or '[fdff:10:82:194::3]').
        """
        return self._data_lif

    def set_data_lif(self, data_lif: str) -> None:
        """Set the dataLIF address.

        Args:
            data_lif (str): dataLIF address.
        """
        self._data_lif = data_lif

    def get_svm(self) -> str:
        """Get the SVM name from spec.

        Returns:
            str: SVM name (e.g. 'my-cluster-svm0-nfs').
        """
        return self._svm

    def set_svm(self, svm: str) -> None:
        """Set the SVM name.

        Args:
            svm (str): SVM name.
        """
        self._svm = svm

    def get_nfs_mount_options(self) -> str:
        """Get the NFS mount options from spec.

        Returns:
            str: NFS mount options (e.g. 'proto=tcp6,vers=4').
        """
        return self._nfs_mount_options

    def set_nfs_mount_options(self, nfs_mount_options: str) -> None:
        """Set the NFS mount options.

        Args:
            nfs_mount_options (str): NFS mount options string.
        """
        self._nfs_mount_options = nfs_mount_options

    def get_credentials_secret_name(self) -> str:
        """Get the credentials secret name from spec.

        The secret lives in the same namespace as this TridentBackendConfig
        and holds the backend login/password used by the ESB secretRef.

        Returns:
            str: Secret name (e.g. 'backend-secret'), or '' if unset.
        """
        return self._credentials_secret_name

    def set_credentials_secret_name(self, credentials_secret_name: str) -> None:
        """Set the credentials secret name.

        Args:
            credentials_secret_name (str): Secret name from spec.credentials.name.
        """
        self._credentials_secret_name = credentials_secret_name

    def is_healthy(self) -> bool:
        """Check if the backend is healthy (lastOperationStatus == Success).

        Returns:
            bool: True if backend is connected and healthy.
        """
        return self._last_operation_status == "Success"

    def is_bound(self) -> bool:
        """Check if the backend phase is Bound.

        Returns:
            bool: True if backend is in Bound phase.
        """
        return self._phase == "Bound"

    def __str__(self) -> str:
        """Human-readable representation.

        Returns:
            str: String representation.
        """
        return (
            f"TridentBackendConfig(name={self._name}, "
            f"driver={self._storage_driver_name}, "
            f"managementLIF={self._management_lif}, "
            f"dataLIF={self._data_lif}, "
            f"svm={self._svm}, "
            f"nfsMountOptions={self._nfs_mount_options}, "
            f"credentialsSecret={self._credentials_secret_name}, "
            f"phase={self._phase}, "
            f"status={self._last_operation_status})"
        )

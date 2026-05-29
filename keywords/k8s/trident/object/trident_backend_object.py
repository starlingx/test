"""Trident backend object representation."""


class TridentBackendObject:
    """Represents a single Trident storage backend.

    Stores parsed data from 'kubectl get tridentbackends -n trident'
    including dataLIF and SVM name.
    """

    def __init__(self) -> None:
        """Initialize TridentBackendObject with empty values."""
        self._data_lif = ""
        self._svm = ""
        self._backend_name = ""
        self._storage_driver = ""

    def get_data_lif(self) -> str:
        """Get the dataLIF address.

        Returns:
            str: Data LIF IP/hostname (e.g. '[fdff:10:81:146::3]').
        """
        return self._data_lif

    def set_data_lif(self, value: str) -> None:
        """Set the dataLIF address.

        Args:
            value (str): Data LIF IP/hostname.
        """
        self._data_lif = value

    def get_svm(self) -> str:
        """Get the SVM (Storage Virtual Machine) name.

        Returns:
            str: SVM name (e.g. 'yow_wrcp_dc_021_sc1_svm0').
        """
        return self._svm

    def set_svm(self, value: str) -> None:
        """Set the SVM name.

        Args:
            value (str): SVM name.
        """
        self._svm = value

    def get_backend_name(self) -> str:
        """Get the backend name.

        Returns:
            str: Backend name.
        """
        return self._backend_name

    def set_backend_name(self, value: str) -> None:
        """Set the backend name.

        Args:
            value (str): Backend name.
        """
        self._backend_name = value

    def get_storage_driver(self) -> str:
        """Get the storage driver name.

        Returns:
            str: Storage driver (e.g. 'ontap-nas').
        """
        return self._storage_driver

    def set_storage_driver(self, value: str) -> None:
        """Set the storage driver name.

        Args:
            value (str): Storage driver.
        """
        self._storage_driver = value

    def __str__(self) -> str:
        """Get string representation for logging.

        Returns:
            str: Human-readable representation.
        """
        return (
            f"TridentBackend(name={self._backend_name}, "
            f"dataLIF={self._data_lif}, svm={self._svm}, "
            f"driver={self._storage_driver})"
        )

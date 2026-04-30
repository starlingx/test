from typing import Optional


class KubectlSriovFecNodeConfigObject:
    """Class to hold attributes of a 'kubectl get sriovfecnodeconfigs.sriovfec.intel.com' entry."""

    def __init__(self, name: str):
        """Constructor.

        Args:
            name (str): Name of the SriovFecNodeConfig.
        """
        self.name = name
        self.configured: Optional[str] = None

    def get_name(self) -> str:
        """Getter for NAME entry.

        Returns:
            str: The name of the SriovFecNodeConfig.
        """
        return self.name

    def set_configured(self, configured: str) -> None:
        """Setter for CONFIGURED.

        Args:
            configured (str): Configured status of the SriovFecNodeConfig.
        """
        self.configured = configured

    def get_configured(self) -> Optional[str]:
        """Getter for CONFIGURED entry.

        Returns:
            Optional[str]: The configured status of the SriovFecNodeConfig.
        """
        return self.configured

    def __str__(self) -> str:
        """String representation.

        Returns:
            str: Human-readable representation of the SriovFecNodeConfig.
        """
        return f"SriovFecNodeConfig(name={self.name}, configured={self.configured})"

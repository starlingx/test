from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.rest.configuration.system.get_system_keywords import GetSystemKeywords
from keywords.cloud_platform.version_info.cloud_platform_software_version import CloudPlatformSoftwareVersion
from keywords.linux.cat.cat_os_keywords import CatOSKeywords
from keywords.python.product_version import ProductVersion


class CloudPlatformVersionManagerClass:
    """
    Singleton Class that keeps track of the current sw_version of the Cloud Platform
    """

    def __init__(self):
        """
        Constructor
        """
        self.sw_version: ProductVersion = None
        self._is_trixie: bool = None

    def get_product_version_object(self, version_name: str) -> ProductVersion:
        """
        This function will find the Product Version object that matches the version_name provided.

        Args:
            version_name (str): The version_name as a String

        Returns:
            ProductVersion: The value from CloudPlatformSoftwareVersion matching the version_name provided
        """
        # Build a list of all the ProductVersion available.
        cloud_platform_software_version_vars = vars(CloudPlatformSoftwareVersion)
        cloud_platform_product_version_names = [var_name for var_name in list(cloud_platform_software_version_vars.keys()) if "STARLINGX" in var_name]
        cloud_platform_product_versions = [cloud_platform_software_version_vars.get(version_name) for version_name in cloud_platform_product_version_names]

        # If the version is not in the list of versions, create a default value.
        product_version = ProductVersion(version_name, 9999)

        # Find and return the appropriate ProductVersion from the list if any.
        for version in cloud_platform_product_versions:
            if version_name == version.get_name():
                product_version = version
                break

        return product_version

    def _get_sw_version_from_system(self) -> ProductVersion:
        """
        This function will run the isystems API call to get the sw_version from the lab under test.

        Returns: The active ProductVersion.

        """
        system_output = GetSystemKeywords().get_system()
        system_object = system_output.get_system_object()
        sw_version = system_object.get_software_version()
        product_version = self.get_product_version_object(sw_version)

        return product_version

    def get_sw_version(self) -> ProductVersion:
        """Get Software Version.

        This function will return the Cloud Software Version observed on the system.

        Returns: Software version

        """
        if not self.sw_version:
            self.sw_version = self._get_sw_version_from_system()
        return self.sw_version

    def get_last_major_release(self) -> ProductVersion:
        """Get latest Product Version.

        This function will return the latest Product Version defined in CloudPlatformSoftwareVersion
        class.
        """
        return CloudPlatformSoftwareVersion.STARLINGX_11_0

    def get_second_last_major_release(self) -> ProductVersion:
        """Get second-latest Product Version.

        This function will return the second-latest Product Version defined in
        CloudPlatformSoftwareVersion class.
        """
        return CloudPlatformSoftwareVersion.STARLINGX_10_0

    def get_third_last_major_release(self) -> ProductVersion:
        """Get third-latest Product Version.

        This function will return the third-latest Product Version defined in
        CloudPlatformSoftwareVersion class.
        """
        return CloudPlatformSoftwareVersion.STARLINGX_9_0

    def resolve_release_token(self, token: Optional[str]) -> Optional[str]:
        """Resolve a relative release token into a concrete software version string.

        This is the single source of truth for interpreting the ``"N"``,
        ``"N-1"`` and ``"N-2"`` tokens so that every caller (subcloud picker,
        backup/restore helpers, etc.) resolves them identically.

        Resolution rules:
            - ``None`` is returned unchanged (no release requested).
            - ``"N"`` resolves to the version currently running on the system.
            - ``"N-1"`` resolves to the last major release, unless the running
              version already is the last major release, in which case it steps
              back to the second-last major release (so ``"N-1"`` is always the
              release before the one running).
            - ``"N-2"`` resolves to the second-last major release.
            - Any other value is treated as an explicit version and returned
              unchanged.

        Args:
            token (Optional[str]): Release token (``"N"``, ``"N-1"``, ``"N-2"``)
                or an explicit version string.

        Returns:
            Optional[str]: ``None`` when no token was supplied, else a concrete
            software version string.
        """
        if token is None:
            return None
        if token == "N":
            return self.get_sw_version().get_name()
        if token == "N-2":
            return self.get_second_last_major_release().get_name()
        if token != "N-1":
            return token

        sw_version_name = self.get_sw_version().get_name()
        last_major_name = self.get_last_major_release().get_name()
        if last_major_name != sw_version_name:
            return last_major_name
        return self.get_second_last_major_release().get_name()

    def is_trixie(self, ssh_connection: SSHConnection) -> bool:
        """Check if the system is running Debian Trixie (strongSwan 6.0).

        Result is cached after the first call.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.

        Returns:
            bool: True if running Trixie, False otherwise.
        """
        if self._is_trixie is None:
            codename = CatOSKeywords(ssh_connection).get_os_release().get_os_release().get_version_codename()
            self._is_trixie = codename.lower() == "trixie"
        return self._is_trixie


CloudPlatformVersionManager = CloudPlatformVersionManagerClass()

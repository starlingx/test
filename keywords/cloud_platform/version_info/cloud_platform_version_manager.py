from typing import List, Optional

from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.rest.configuration.system.get_system_keywords import GetSystemKeywords
from keywords.cloud_platform.version_info.cloud_platform_software_version import CloudPlatformSoftwareVersion
from keywords.linux.cat.cat_os_keywords import CatOSKeywords
from keywords.python.product_version import ProductVersion

# Version id assigned to a release observed on the system but not declared in
# CloudPlatformSoftwareVersion. Sorts after every known release.
UNKNOWN_VERSION_ID = 9999


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

    def get_all_product_versions(self) -> List[ProductVersion]:
        """Get every ProductVersion declared in CloudPlatformSoftwareVersion.

        The declaring class is the single source of truth for the set of known
        releases and their chronological order. Versions are returned sorted by
        ascending version id (oldest release first).

        Returns:
            List[ProductVersion]: All known product versions, oldest first.
        """
        cloud_platform_software_version_vars = vars(CloudPlatformSoftwareVersion)
        cloud_platform_product_version_names = [var_name for var_name in list(cloud_platform_software_version_vars.keys()) if "STARLINGX" in var_name]
        cloud_platform_product_versions = [cloud_platform_software_version_vars.get(version_name) for version_name in cloud_platform_product_version_names]

        return sorted(cloud_platform_product_versions, key=lambda version: version.get_id())

    def get_product_version_object(self, version_name: str) -> ProductVersion:
        """
        This function will find the Product Version object that matches the version_name provided.

        Args:
            version_name (str): The version_name as a String

        Returns:
            ProductVersion: The value from CloudPlatformSoftwareVersion matching the version_name provided
        """
        # If the version is not in the list of versions, create a default value.
        product_version = ProductVersion(version_name, UNKNOWN_VERSION_ID)

        # Find and return the appropriate ProductVersion from the list if any.
        for version in self.get_all_product_versions():
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

    def get_major_release_relative(self, releases_back: int) -> ProductVersion:
        """Get the major release a given number of releases before the running one.

        The target is derived from the version observed on the system rather
        than from a hardcoded constant, so a new release shipping does not
        require this method to be updated.

        Args:
            releases_back (int): How many releases to step back from the
                running version. ``0`` returns the running release, ``1`` the
                release before it (N-1), ``2`` the one before that (N-2).

        Returns:
            ProductVersion: The product version at the requested offset.

        Raises:
            ValueError: If releases_back is negative, if the running version is
                not declared in CloudPlatformSoftwareVersion, or if no declared
                release exists at the requested offset.
        """
        if releases_back < 0:
            raise ValueError(f"releases_back must be zero or positive, received {releases_back}")

        sw_version = self.get_sw_version()
        if sw_version.get_id() == UNKNOWN_VERSION_ID:
            raise ValueError(f"Running version '{sw_version.get_name()}' is not declared in CloudPlatformSoftwareVersion, so releases relative to it cannot be resolved. Add it to the enumeration.")

        target_id = sw_version.get_id() - releases_back
        for version in self.get_all_product_versions():
            if version.get_id() == target_id:
                return version

        known_versions = [version.get_name() for version in self.get_all_product_versions()]
        raise ValueError(f"No product version declared at {releases_back} release(s) before running version '{sw_version.get_name()}' (looked for version id {target_id}). Known versions: {known_versions}")

    def get_last_major_release(self) -> ProductVersion:
        """Get the release immediately before the running one (N-1).

        Returns:
            ProductVersion: The release one step before the running version.

        Raises:
            ValueError: If no declared release exists at that offset.
        """
        return self.get_major_release_relative(1)

    def get_second_last_major_release(self) -> ProductVersion:
        """Get the release two steps before the running one (N-2).

        Returns:
            ProductVersion: The release two steps before the running version.

        Raises:
            ValueError: If no declared release exists at that offset.
        """
        return self.get_major_release_relative(2)

    def get_third_last_major_release(self) -> ProductVersion:
        """Get the release three steps before the running one (N-3).

        Returns:
            ProductVersion: The release three steps before the running version.

        Raises:
            ValueError: If no declared release exists at that offset.
        """
        return self.get_major_release_relative(3)

    def resolve_release_token(self, token: Optional[str]) -> Optional[str]:
        """Resolve a relative release token into a concrete software version string.

        This is the single source of truth for interpreting the ``"N"``,
        ``"N-1"`` and ``"N-2"`` tokens so that every caller (subcloud picker,
        backup/restore helpers, etc.) resolves them identically.

        Resolution rules:
            - ``None`` is returned unchanged (no release requested).
            - ``"N"`` resolves to the version currently running on the system.
            - ``"N-1"`` resolves to the release before the running one.
            - ``"N-2"`` resolves to two releases before the running one.
            - Any other value is treated as an explicit version and returned
              unchanged.

        Args:
            token (Optional[str]): Release token (``"N"``, ``"N-1"``, ``"N-2"``)
                or an explicit version string.

        Returns:
            Optional[str]: ``None`` when no token was supplied, else a concrete
            software version string.

        Raises:
            ValueError: If a relative token is supplied and no declared release
                exists at that offset from the running version.
        """
        if token is None:
            return None
        if token == "N":
            return self.get_sw_version().get_name()
        if token == "N-1":
            return self.get_major_release_relative(1).get_name()
        if token == "N-2":
            return self.get_major_release_relative(2).get_name()
        return token

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

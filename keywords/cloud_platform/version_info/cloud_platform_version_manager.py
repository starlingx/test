from keywords.cloud_platform.rest.configuration.system.get_system_keywords import GetSystemKeywords
from keywords.cloud_platform.version_info.cloud_platform_software_version import CloudPlatformSoftwareVersion
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

    def _get_product_version_object(self, version_name) -> ProductVersion:
        """
        This function will find the Product Version object that matches the version_name provided.
        Args:
            version_name (str): The version_name as a String

        Returns (ProductVersion): The value from CloudPlatformSoftwareVersion matching the version_name provided
        """

        # Build a list of all the ProductVersion available.
        cloud_platform_software_version_vars = vars(CloudPlatformSoftwareVersion)
        cloud_platform_product_version_names = [
            var_name for var_name in list(cloud_platform_software_version_vars.keys()) if "STARLINGX" in var_name
        ]
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
        product_version = self._get_product_version_object(sw_version)

        return product_version

    def get_sw_version(self) -> ProductVersion:
        """
        This function will return the Cloud Software Version observed on the system.
        Returns:

        """
        if not self.sw_version:
            self.sw_version = self._get_sw_version_from_system()
        return self.sw_version

    def get_last_major_release(self) -> ProductVersion:
        """
        This function will return the latest Product Version defined in CloudPlatformSoftwareVersion
        class.
        """
        return CloudPlatformSoftwareVersion.STARLINGX_10_0

    def get_second_last_major_release(self) -> ProductVersion:
        """
        This function will return the second-latest Product Version defined in
         CloudPlatformSoftwareVersion class.
        """
        return CloudPlatformSoftwareVersion.STARLINGX_9_0


CloudPlatformVersionManager = CloudPlatformVersionManagerClass()

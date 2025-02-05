from keywords.python.product_version import ProductVersion


class CloudPlatformSoftwareVersion:
    """
    This class enumerates the different versions of the Cloud Platform as well as their chronological release order.
    """

    STARLINGX_9_0 = ProductVersion("24.03", 0)
    STARLINGX_10_0 = ProductVersion("24.09", 1)

    # Every new version must contain STARLINGX in the variable name.

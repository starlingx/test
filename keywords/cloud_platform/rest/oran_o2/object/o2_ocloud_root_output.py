from keywords.cloud_platform.rest.oran_o2.object.o2_rest_response import O2RestResponse


class O2OcloudRootOutput:
    """Parses the O2 IMS O-Cloud root response.

    Exposes the O-Cloud identity fields the tests assert: `oCloudId` (present and
    non-empty) and `globalcloudId` (present; the schema default is an empty
    string, so only presence is a safe signal).
    """

    def __init__(self, response: O2RestResponse):
        """Initialize from an O2 REST response.

        Args:
            response (O2RestResponse): The response from the O-Cloud root endpoint.
        """
        self.content = response.get_json_content() or {}

    def get_ocloud_id(self) -> str:
        """Get the O-Cloud id.

        Returns:
            str: The oCloudId value, or an empty string if absent.
        """
        return self.content.get("oCloudId", "")

    def has_global_cloud_id(self) -> bool:
        """Return whether the globalcloudId field is present.

        The field's schema default is an empty string, so presence (not
        non-emptiness) is the safe check.

        Returns:
            bool: True if the globalcloudId key is present in the response.
        """
        return "globalcloudId" in self.content

    def get_global_cloud_id(self) -> str:
        """Get the global cloud id.

        Returns:
            str: The globalcloudId value, or an empty string if absent.
        """
        return self.content.get("globalcloudId", "")

from keywords.cloud_platform.rest.oran_o2.object.o2_rest_response import O2RestResponse


class O2ApiVersionsOutput:
    """Parses the O2 IMS api_versions response.

    The response reports the supported API versions under `apiVersions`, each
    entry carrying a `version` string.
    """

    def __init__(self, response: O2RestResponse):
        """Initialize from an O2 REST response.

        Args:
            response (O2RestResponse): The response from the api_versions endpoint.
        """
        content = response.get_json_content() or {}
        self.versions = []
        for entry in content.get("apiVersions", []):
            version = entry.get("version")
            if version:
                self.versions.append(version)

    def get_versions(self) -> list[str]:
        """Get the list of supported API version strings.

        Returns:
            list[str]: The version strings reported under apiVersions.
        """
        return self.versions

    def is_empty(self) -> bool:
        """Return whether the api version list is empty.

        Returns:
            bool: True if no API versions were reported.
        """
        return len(self.versions) == 0

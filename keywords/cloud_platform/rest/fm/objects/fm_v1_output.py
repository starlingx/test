"""Output class for FM /v1 REST API response."""

from framework.rest.rest_response import RestResponse


class FmV1Output:
    """Parses FM /v1 REST API response."""

    def __init__(self, response: RestResponse):
        """Initialize FmV1Output from REST response.

        Args:
            response (RestResponse): The REST response from FM /v1 API.
        """
        self.json_content = response.get_json_content()
        self.links = self.json_content.get("links", [])
        self.media_types = self.json_content.get("media_types", [])
        self.id = self.json_content.get("id", "")

    def get_links(self) -> list:
        """Get the API links.

        Returns:
            list: List of API link dictionaries.
        """
        return self.links

    def get_id(self) -> str:
        """Get the API version ID.

        Returns:
            str: The API version ID.
        """
        return self.id

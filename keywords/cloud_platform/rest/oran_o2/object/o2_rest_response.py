import json


class O2RestResponse:
    """Response from an O2 IMS API request executed via curl on the controller.

    Exposes the HTTP status code and the parsed JSON body, mirroring the parts of
    the framework `RestResponse` that callers use, so they read a response the same
    way regardless of the underlying transport.
    """

    def __init__(self, status_code: int, body: str):
        """Constructor.

        Args:
            status_code (int): The HTTP status code returned by the server.
            body (str): The raw response body.
        """
        self.status_code = status_code
        self.body = body

    def get_status_code(self) -> int:
        """Get the HTTP status code.

        Returns:
            int: The HTTP status code.
        """
        return self.status_code

    def get_body(self) -> str:
        """Get the raw response body.

        Returns:
            str: The raw response body.
        """
        return self.body

    def get_json_content(self) -> dict | list | None:
        """Get the parsed JSON body.

        Returns:
            dict | list | None: The parsed JSON, or None if the body is empty or not JSON.
        """
        text = self.body.strip() if isinstance(self.body, str) else self.body
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

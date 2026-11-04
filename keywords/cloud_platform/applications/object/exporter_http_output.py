"""Checked response from a controller-side exporter HTTP request."""


class ExporterHttpOutput:
    """HTTP status and body retained for positive and negative endpoint checks."""

    def __init__(self, status_code: int, body: str):
        """Initialize the parsed response.

        Args:
            status_code (int): HTTP response status.
            body (str): Unparsed response body.
        """
        self.status_code = status_code
        self.body = body

    def get_status_code(self) -> int:
        """Return the HTTP status.

        Returns:
            int: HTTP response status.
        """
        return self.status_code

    def set_status_code(self, status_code: int) -> None:
        """Set the HTTP status.

        Args:
            status_code (int): HTTP response status.
        """
        self.status_code = status_code

    def get_body(self) -> str:
        """Return the unparsed body.

        Returns:
            str: Response body.
        """
        return self.body

    def set_body(self, body: str) -> None:
        """Set the response body.

        Args:
            body (str): Response body.
        """
        self.body = body

    @classmethod
    def from_curl(cls, output: str | list[str], return_code: int) -> "ExporterHttpOutput":
        """Decode curl output without confusing HTTP errors with transport failures.

        Args:
            output (str | list[str]): Body followed by a newline and curl's HTTP status.
            return_code (int): Exit status of the actual curl command.

        Returns:
            ExporterHttpOutput: Parsed response, including non-success HTTP responses.
        """
        if return_code != 0:
            raise ValueError(f"Exporter HTTP transport failed: curl exit {return_code}")
        if isinstance(output, list):
            output = "\n".join(line.rstrip("\r\n") for line in output)
        body, separator, status = output.rstrip("\r\n").rpartition("\n")
        if not separator or len(status) != 3 or not status.isascii() or not status.isdigit() or not 100 <= int(status) <= 599:
            raise ValueError("Missing or invalid exporter HTTP status")
        return cls(int(status), body)

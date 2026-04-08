class KubectlResultObject:
    """Represents the result of a kubectl command execution."""

    def __init__(self):
        """Constructor."""
        self.output = None

    def set_output(self, output: str) -> None:
        """Set the kubectl command output.

        Args:
            output (str): Raw kubectl output string.
        """
        self.output = output

    def get_output(self) -> str:
        """Get the kubectl command output.

        Returns:
            str: Raw kubectl output string.
        """
        return self.output

    def has_output(self) -> bool:
        """Check if kubectl returned non-empty output.

        Returns:
            bool: True if output is non-empty, False otherwise.
        """
        return self.output is not None and len(self.output.strip()) > 0

    def is_kubectl_successful(self) -> bool:
        """Check if kubectl output contains pod table data (not an error).

        Returns:
            bool: True if output contains the pods table header, False otherwise.
        """
        return self.output is not None and "NAME" in self.output and "STATUS" in self.output

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: String representation of the result.
        """
        return f"KubectlResultObject(output_length={len(self.output) if self.output else 0})"

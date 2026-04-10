class KubectlResultObject:
    """Represents the result of a kubectl command execution."""

    def __init__(self):
        """Constructor."""
        self.output = None
        self.browser_prompt_shown = False

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

    def is_kubectl_successful(self) -> bool:
        """Check if kubectl output contains pod table data (not an error).

        Returns:
            bool: True if output contains the pods table header, False otherwise.
        """
        return self.output is not None and "NAME" in self.output and "STATUS" in self.output

    def set_browser_prompt_shown(self, value: bool) -> None:
        """Set whether kubelogin showed a browser prompt.

        Args:
            value (bool): True if browser prompt was shown.
        """
        self.browser_prompt_shown = value

    def is_browser_prompt_shown(self) -> bool:
        """Check if kubelogin showed a browser URL prompt.

        Returns:
            bool: True if kubectl timed out waiting for browser interaction.
        """
        return self.browser_prompt_shown

    def __str__(self) -> str:
        """Return human-readable representation.

        Returns:
            str: String representation of the result.
        """
        return f"KubectlResultObject(output_length={len(self.output) if self.output else 0})"

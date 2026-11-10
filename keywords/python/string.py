class String:
    """
    Class for utility methods on the Python str type.
    """

    @staticmethod
    def is_empty(some_string: str) -> bool:
        """
        Checks if 'some_string' is an empty string.

        An empty string is either a sequence with zero characters or one that consists only of space characters.

        Args:
            some_string (str): the string to be checked.

        Returns:
            bool: True if 'some_string' is empty, False otherwise.
        """
        return not some_string or some_string.strip() == ""

    @staticmethod
    def normalize_command_output(output: str | list[str]) -> str:
        """Normalize SSH lines without adding blank lines or flattening content.

        Args:
            output (str | list[str]): SSH command output.

        Returns:
            str: Text with one newline separating returned lines.
        """
        return "\n".join(line.rstrip("\n") for line in output) if isinstance(output, list) else output

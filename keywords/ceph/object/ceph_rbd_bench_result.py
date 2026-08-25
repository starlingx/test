class CephRbdBenchResult:
    """Represents the outcome of a backgrounded 'rbd bench' write run.

    Holds the process exit code and the captured bench log so callers can
    assert the I/O completed without errors across an outage window.
    """

    def __init__(self, exit_code: int, log_text: str):
        """Constructor.

        Args:
            exit_code (int): Exit code of the 'rbd bench' process (0 on success).
            log_text (str): Captured stdout/stderr of the bench run.
        """
        self.exit_code = exit_code
        self.log_text = log_text

    def get_exit_code(self) -> int:
        """Getter for the bench process exit code.

        Returns:
            int: The exit code (0 on success).
        """
        return self.exit_code

    def get_log_text(self) -> str:
        """Getter for the captured bench log.

        Returns:
            str: The bench stdout/stderr text.
        """
        return self.log_text

    def is_successful(self) -> bool:
        """Check whether the bench completed with a zero exit code.

        Returns:
            bool: True if the exit code is 0, False otherwise.
        """
        return self.exit_code == 0

    def __str__(self) -> str:
        """Human-readable representation for logging.

        Returns:
            str: A summary of the exit code.
        """
        return f"CephRbdBenchResult(exit_code={self.exit_code})"

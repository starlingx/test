"""Output object for the kubectl auth whoami read.

The parsing lives here rather than in the keyword, so a caller asks the object a question instead
of slicing command text.
"""


class KubectlWhoamiOutput:
    """The identity the apiserver resolved for a session."""

    # kubectl writes its errors to stdout, so non-empty output is not evidence of an answer. These
    # are the markers that mean the question never reached an apiserver.
    FAILURE_MARKERS = ("error", "refused", "unable to connect", "unauthorized")

    def __init__(self, raw_output: str, return_code: int):
        """Parse the identity from the command output.

        Args:
            raw_output (str): what the command printed.
            return_code (int): the exit status, which must be zero for the answer to be trusted.

        """
        self.raw_output = raw_output
        self.return_code = return_code
        lines = [line.strip() for line in (raw_output or "").strip().splitlines() if line.strip()]
        self.username = lines[-1] if lines else ""

    def get_username(self) -> str:
        """Return the resolved username.

        A username may legitimately contain spaces, colons and slashes: it can be derived from a
        GECOS field, and the apiserver prefixes it with the issuer URL unless the configured claim
        is ``email``.

        Returns:
            str: the username, or an empty string when there was no answer.

        """
        return self.username

    def is_valid(self) -> bool:
        """Report whether this is an identity rather than a failure message.

        Returns:
            bool: True when the command succeeded and produced something that is not an error.

        """
        if self.return_code != 0 or not self.username:
            return False
        return not any(marker in self.raw_output.lower() for marker in self.FAILURE_MARKERS)

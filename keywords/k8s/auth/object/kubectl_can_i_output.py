"""Output object for the kubectl auth can-i read.

The parsing lives here rather than in the keyword, so a caller asks the object a question instead
of slicing command text.
"""


class KubectlCanIOutput:
    """The apiserver's answer to whether an operation is permitted."""

    def __init__(self, raw_output: str):
        """Parse the answer from the command output.

        Args:
            raw_output (str): what the command printed. kubectl answers "yes" or "no", and a
                denial may carry a reason, as in "no - no RBAC policy matched".

        """
        self.raw_output = raw_output
        lines = [line.strip() for line in (raw_output or "").strip().splitlines() if line.strip()]
        self.answer = lines[-1].lower() if lines else ""

    def is_allowed(self) -> bool:
        """Report whether the operation is permitted.

        Returns:
            bool: True when the answer is yes.

        """
        return self.answer.startswith("yes")

    def is_denied(self) -> bool:
        """Report whether the operation is refused.

        Matched by prefix rather than equality, because a denial may carry a reason.

        Returns:
            bool: True when the answer is no.

        """
        return self.answer.startswith("no")

    def is_answered(self) -> bool:
        """Report whether the question was evaluated at all.

        Anything that is neither yes nor no means the question never reached a working apiserver.
        Callers must check this before trusting a denial: treating an unreachable cluster as a
        denial would let an authorization assertion pass where authorization was never evaluated.

        Returns:
            bool: True when the answer is yes or no.

        """
        return self.is_allowed() or self.is_denied()

    def get_raw_output(self) -> str:
        """Return the unparsed output, for failure messages.

        Returns:
            str: the raw output.

        """
        return self.raw_output

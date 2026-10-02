"""Output object for parsing the kernel command line read from /proc/cmdline."""


class ProcCmdlineOutput:
    """Parses /proc/cmdline into queryable kernel-argument fields.

    The kernel command line is a single line of space-separated tokens, some of
    which are key=value (e.g. 'isolcpus=nohz,domain,managed_irq,2-5',
    'nohz_full=2-5'). This object parses that line once and exposes getters so
    callers do not parse raw text themselves.
    """

    def __init__(self, proc_cmdline_output: str):
        """Constructor.

        Args:
            proc_cmdline_output (str): Raw contents of /proc/cmdline.
        """
        self.tokens = proc_cmdline_output.split()

    def _get_arg_value(self, key: str) -> str:
        """Return the value of a 'key=value' kernel argument, or None if absent.

        Args:
            key (str): The argument name (without '=').

        Returns:
            str: The argument value, or None if the argument is not present.
        """
        prefix = f"{key}="
        for token in self.tokens:
            if token.startswith(prefix):
                return token.split("=", 1)[1]
        return None

    def get_isolcpus(self) -> str:
        """Return the value of the isolcpus= argument, or None if absent.

        Returns:
            str: The isolcpus= value (e.g. 'nohz,domain,managed_irq,2-5'), or None.
        """
        return self._get_arg_value("isolcpus")

    def has_isolcpus_nohz(self) -> bool:
        """Return True if the isolcpus= list contains the 'nohz' token.

        Returns:
            bool: True if 'nohz' is present in the isolcpus= comma list.
        """
        value = self.get_isolcpus()
        return value is not None and "nohz" in value.split(",")

    def has_nohz_full(self) -> bool:
        """Return True if a nohz_full= argument is present.

        Returns:
            bool: True if the command line contains a nohz_full= argument.
        """
        return self._get_arg_value("nohz_full") is not None

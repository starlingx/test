class CpuPowerSettingsObject:
    """Effective CPU power settings derived from sysfs.

    Each state is ``enabled``, ``disabled`` or ``unknown``. ``unknown`` means the
    host did not expose the files needed to decide, or the files disagreed.
    """

    def __init__(self):
        """Constructor."""
        self.p_state_management: str = "unknown"
        self.c_state_management: str = "unknown"
        self.turbo: str = "unknown"
        self.smt: str = "unknown"
        self.evidence: dict[str, str] = {}

    def get_p_state_management(self) -> str:
        """Get whether the OS manages CPU P-states.

        Returns:
            str: enabled, disabled or unknown.
        """
        return self.p_state_management

    def set_p_state_management(self, p_state_management: str) -> None:
        """Set whether the OS manages CPU P-states.

        Args:
            p_state_management (str): enabled, disabled or unknown.
        """
        self.p_state_management = p_state_management

    def get_c_state_management(self) -> str:
        """Get whether CPU idle C-states deeper than POLL are usable.

        Returns:
            str: enabled, disabled or unknown.
        """
        return self.c_state_management

    def set_c_state_management(self, c_state_management: str) -> None:
        """Set whether CPU idle C-states deeper than POLL are usable.

        Args:
            c_state_management (str): enabled, disabled or unknown.
        """
        self.c_state_management = c_state_management

    def get_turbo(self) -> str:
        """Get whether turbo/boost frequencies are allowed.

        Returns:
            str: enabled, disabled or unknown.
        """
        return self.turbo

    def set_turbo(self, turbo: str) -> None:
        """Set whether turbo/boost frequencies are allowed.

        Args:
            turbo (str): enabled, disabled or unknown.
        """
        self.turbo = turbo

    def get_smt(self) -> str:
        """Get whether simultaneous multithreading (hyper-threading) is active.

        Returns:
            str: enabled, disabled or unknown.
        """
        return self.smt

    def set_smt(self, smt: str) -> None:
        """Set whether simultaneous multithreading (hyper-threading) is active.

        Args:
            smt (str): enabled, disabled or unknown.
        """
        self.smt = smt

    def get_evidence(self) -> dict[str, str]:
        """Get the raw sysfs values the settings were derived from.

        Returns:
            dict[str, str]: Mapping of sysfs path to its contents.
        """
        return self.evidence

    def set_evidence(self, evidence: dict[str, str]) -> None:
        """Set the raw sysfs values the settings were derived from.

        Args:
            evidence (dict[str, str]): Mapping of sysfs path to its contents.
        """
        self.evidence = evidence

    def to_dictionary(self) -> dict:
        """Convert the settings to a serializable dictionary.

        Returns:
            dict: Derived states and the sysfs evidence behind them.
        """
        return {
            "derived": {
                "p_state_management": self.get_p_state_management(),
                "c_state_management": self.get_c_state_management(),
                "turbo": self.get_turbo(),
                "smt": self.get_smt(),
            },
            "evidence": self.get_evidence(),
        }

    def __str__(self) -> str:
        """Describe the effective CPU power settings.

        Returns:
            str: Derived state of each setting.
        """
        return f"P-states={self.get_p_state_management()}, C-states={self.get_c_state_management()}, turbo={self.get_turbo()}, SMT={self.get_smt()}"

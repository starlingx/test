"""Typed parameter object for a cyclictest run."""


class CyclictestParamsObject:
    """Holds the cyclictest CLI parameter set for an isolated-core KPI run.

    Attributes are fixed constants — they are not lab-configurable.
    Use :meth:`to_dict` to obtain the flat dict consumed by
    :meth:`~keywords.cloud_platform.cyclictest.cyclictest_keywords.CyclictestKeywords.run_cyclictest`
    when building CLI flags.
    """

    def __init__(self, priority: int, histofall: int, nsecs: bool = False, smi: bool = False) -> None:
        """Constructor.

        Args:
            priority (int): Real-time scheduling priority passed to ``--priority``.
            histofall (int): Histogram bucket count passed to ``--histofall``.
            nsecs (bool): Whether to pass ``--nsecs`` (nanosecond output). Defaults to False.
            smi (bool): Whether to pass ``--smi`` (SMI count). Defaults to False.
        """
        self._priority = priority
        self._histofall = histofall
        self._nsecs = nsecs
        self._smi = smi

    def get_priority(self) -> int:
        """Return the real-time scheduling priority.

        Returns:
            int: Priority value for ``--priority``.
        """
        return self._priority

    def get_histofall(self) -> int:
        """Return the histogram bucket count.

        Returns:
            int: Bucket count for ``--histofall``.
        """
        return self._histofall

    def has_nsecs(self) -> bool:
        """Return whether nanosecond output is enabled.

        Returns:
            bool: True if ``--nsecs`` should be passed.
        """
        return self._nsecs

    def has_smi(self) -> bool:
        """Return whether SMI counting is enabled.

        Returns:
            bool: True if ``--smi`` should be passed.
        """
        return self._smi

    def to_dict(self) -> dict:
        """Serialize to a flat dict suitable for CLI flag construction.

        Keys with empty-string values produce flags without an argument
        (e.g. ``--nsecs``). Keys absent from the dict are not emitted.

        Returns:
            dict: Mapping of CLI flag name to value.
        """
        params: dict = {
            "priority": self._priority,
            "histofall": self._histofall,
        }
        if self._nsecs:
            params["nsecs"] = ""
        if self._smi:
            params["smi"] = ""
        return params

import json5


class CyclictestConfig:
    """Configuration object for cyclictest KPI runs.

    Reads lab-specific settings from ``default.json5``. All cyclictest
    runtime flags (priority, histofall, etc.) are fixed constants in
    :class:`~keywords.cloud_platform.cyclictest.cyclictest_keywords.CyclictestKeywords`
    and are intentionally not lab-configurable.
    """

    def __init__(self, config_file: str):
        """Constructor.

        Args:
            config_file (str): Path to the JSON5 config file.

        Raises:
            FileNotFoundError: If the config file cannot be found.
        """
        try:
            with open(config_file, "r") as f:
                self._config = json5.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not find the cyclictest config file: {config_file}")

    def get_duration(self) -> int:
        """Return the cyclictest run duration in seconds.

        Returns:
            int: Duration in seconds (default: 1800).
        """
        return int(self._config.get("duration", 1800))

    def get_cores(self) -> str:
        """Return the user-specified CPU cores string.

        An empty string means auto-detect from ``system host-cpu-list``
        (Application-isolated or Application cores).  When non-empty the
        value is used directly as the ``--affinity`` argument.

        Returns:
            str: CPU range string, e.g. ``'4-6,8'``, or ``''``.
        """
        return str(self._config.get("cores", ""))

    def get_cpu_mon(self) -> bool:
        """Return whether CPU usage monitoring is enabled alongside the run.

        Returns:
            bool: ``True`` if the CPU monitor thread should be started.
        """
        return bool(self._config.get("cpu_mon", False))

    def get_cyclictest_dir(self) -> str:
        """Return the remote working directory on the target host.

        Returns:
            str: Absolute directory path, e.g. ``'/home/sysadmin/cyclictest'``.
        """
        return str(self._config.get("cyclictest_dir", "/home/sysadmin/cyclictest"))

    def get_cyclictest_exe(self) -> str:
        """Return the path to the cyclictest binary on the target host.

        Returns:
            str: Absolute path to the binary.
        """
        return str(self._config.get("cyclictest_exe", "/home/sysadmin/cyclictest/cyclictest"))

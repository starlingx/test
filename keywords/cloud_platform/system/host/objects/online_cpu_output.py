from typing import Optional


class OnlineCpuOutput:
    """Parses the output of 'cat /sys/devices/system/cpu/online' into a set of online CPU IDs."""

    def __init__(self, raw_output: str) -> None:
        """Constructor.

        Args:
            raw_output (str): Raw string from 'cat /sys/devices/system/cpu/online',
                e.g. '0-3,5,8-11'.
        """
        self._online_cpus: Optional[set] = None
        stripped = raw_output.strip()
        if not stripped:
            return
        online = set()
        for part in stripped.split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = part.split("-", 1)
                online.update(range(int(lo), int(hi) + 1))
            else:
                online.add(int(part))
        self._online_cpus = online

    def get_online_cpu_ids(self) -> Optional[set]:
        """Return the set of online CPU IDs.

        Returns:
            Optional[set]: Set of integer CPU IDs, or None if the output was empty
                or could not be parsed.
        """
        return self._online_cpus

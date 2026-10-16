class NumaOnlineNodesOutput:
    """Parses a Linux sysfs node-range string into NUMA node ids.

    The contents of ``/sys/devices/system/node/online`` (and the matching
    ``cpulist`` files) use the compact range form such as ``"0-1"``,
    ``"0,2"``, or ``"0-3,8"``. This object expands that string once in its
    constructor and exposes the online node ids and their count through
    getters.
    """

    def __init__(self, online_range: str) -> None:
        """Initialize NumaOnlineNodesOutput.

        Args:
            online_range (str): The sysfs range string (e.g. "0-1").
        """
        self._node_ids: list[int] = self._parse(online_range)

    def _parse(self, online_range: str) -> list[int]:
        """Expand a sysfs range string into a sorted list of ids.

        Args:
            online_range (str): The sysfs range string.

        Returns:
            list[int]: The expanded ids, sorted ascending (empty if the
            input is empty).
        """
        ids: set[int] = set()
        for part in (online_range or "").split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start, end = part.split("-", 1)
                ids.update(range(int(start), int(end) + 1))
            else:
                ids.add(int(part))
        return sorted(ids)

    def get_online_node_ids(self) -> list[int]:
        """Return the online NUMA node ids, sorted ascending.

        Returns:
            list[int]: The online node ids.
        """
        return self._node_ids

    def get_online_node_count(self) -> int:
        """Return the number of online NUMA nodes.

        Returns:
            int: The count of online NUMA nodes.
        """
        return len(self._node_ids)

    def get_online_node_ids_as_frozenset(self) -> frozenset[int]:
        """Return the parsed ids as a frozenset.

        Convenient when the range represents a CPU list to be compared as a
        set rather than iterated in order.

        Returns:
            frozenset[int]: The parsed ids.
        """
        return frozenset(self._node_ids)

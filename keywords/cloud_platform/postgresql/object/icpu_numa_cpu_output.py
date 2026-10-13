class IcpuNumaCpuOutput:
    """Parses sysinv ``i_icpu`` rows into per-NUMA-node CPU sets.

    Expects the output of a query that selects ``forinodeid, cpu`` from the
    ``i_icpu`` table (one row per CPU), as rendered by ``psql`` in its default
    aligned form::

         forinodeid | cpu
        ------------+-----
                  1 |   0
                  1 |   1
                  2 |  16

    Parses that output once in the constructor and exposes the CPU ids
    grouped by NUMA node. The sysinv NUMA node id is normalized to a 0-based
    id (sysinv numbers ``forinodeid`` from 1 while Linux sysfs numbers nodes
    from 0) so the result can be compared directly against a sysfs mapping.
    """

    def __init__(self, psql_output: str) -> None:
        """Initialize IcpuNumaCpuOutput.

        Args:
            psql_output (str): Raw output from the ``forinodeid, cpu`` query.
        """
        self._node_cpus: dict[int, frozenset[int]] = self._parse(psql_output)

    def _parse(self, psql_output: str) -> dict[int, frozenset[int]]:
        """Parse ``forinodeid | cpu`` rows into per-node CPU sets.

        Args:
            psql_output (str): Raw psql output.

        Returns:
            dict[int, frozenset[int]]: Mapping of 0-based node id to its set
            of CPU ids (empty if no data rows were found).
        """
        node_to_cpus: dict[int, set[int]] = {}
        for line in (psql_output or "").splitlines():
            line = line.strip()
            # Data rows look like "1 | 0"; skip the header, the "---+---"
            # separator, the "(N rows)" footer, and blank lines.
            if "|" not in line:
                continue
            left, _, right = line.partition("|")
            left = left.strip()
            right = right.strip()
            if not left.isdigit() or not right.isdigit():
                continue
            node_to_cpus.setdefault(int(left), set()).add(int(right))

        if not node_to_cpus:
            return {}

        min_node = min(node_to_cpus)
        return {node_id - min_node: frozenset(cpus) for node_id, cpus in node_to_cpus.items()}

    def get_node_cpu_sets(self) -> dict[int, frozenset[int]]:
        """Return the per-NUMA-node CPU sets (0-based node ids).

        Returns:
            dict[int, frozenset[int]]: Mapping of node id to its set of CPU
            ids.
        """
        return self._node_cpus

    def get_node_count(self) -> int:
        """Return the number of distinct NUMA nodes recorded.

        Returns:
            int: The count of NUMA nodes.
        """
        return len(self._node_cpus)

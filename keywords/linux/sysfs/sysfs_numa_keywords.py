from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.sysfs.object.numa_online_nodes_output import NumaOnlineNodesOutput


class SysfsNumaKeywords(BaseKeyword):
    """Keywords for reading NUMA topology from Linux sysfs.

    Owns the ``/sys/devices/system/node`` reads and their range parsing, so
    callers work with parsed objects/sets instead of raw ``cat`` output.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize SysfsNumaKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_online_nodes(self) -> NumaOnlineNodesOutput:
        """Read ``/sys/devices/system/node/online`` and return it parsed.

        Returns:
            NumaOnlineNodesOutput: The parsed online-node range, queried via
            getters.
        """
        raw = self.ssh_connection.send("cat /sys/devices/system/node/online")
        return NumaOnlineNodesOutput(self._first_nonempty_line(raw))

    def get_node_cpu_sets(self) -> dict[int, frozenset[int]]:
        """Return the per-online-node CPU sets from sysfs.

        Reads ``/sys/devices/system/node/node<N>/cpulist`` for each online
        node and expands it into a set of CPU ids.

        Returns:
            dict[int, frozenset[int]]: Mapping of node id to its set of CPU
            ids.
        """
        node_cpus: dict[int, frozenset[int]] = {}
        for node_id in self.get_online_nodes().get_online_node_ids():
            raw = self.ssh_connection.send(f"cat /sys/devices/system/node/node{node_id}/cpulist")
            node_cpus[node_id] = NumaOnlineNodesOutput(self._first_nonempty_line(raw)).get_online_node_ids_as_frozenset()
        return node_cpus

    @staticmethod
    def _first_nonempty_line(raw: object) -> str:
        """Return the first non-empty, stripped line of a command's output.

        Args:
            raw (object): The command output (a list of lines or a string).

        Returns:
            str: The first non-empty line, or an empty string.
        """
        lines = raw if isinstance(raw, list) else [raw]
        return next((str(entry).strip() for entry in lines if str(entry).strip()), "")

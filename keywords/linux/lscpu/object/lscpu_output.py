class LscpuOutput:
    """Parses the key:value output of the ``lscpu`` command.

    ``lscpu`` prints one ``Field: value`` pair per line, e.g.::

        Architecture:          x86_64
        CPU(s):                64
        Socket(s):             2
        NUMA node(s):          4

    This object parses that output once in its constructor and exposes the
    fields the test framework needs through getters. Add more getters as new
    tests need additional fields, rather than re-parsing inline.
    """

    def __init__(self, lscpu_output: str) -> None:
        """Initialize LscpuOutput.

        Args:
            lscpu_output (str): Raw stdout from the ``lscpu`` command (either
                a single string or the newline-joined command output).
        """
        self._fields: dict[str, str] = {}
        self._parse(lscpu_output)

    def _parse(self, lscpu_output: str) -> None:
        """Parse ``lscpu`` output into a field -> value mapping.

        Args:
            lscpu_output (str): Raw ``lscpu`` output.
        """
        for line in (lscpu_output or "").splitlines():
            if ":" not in line:
                continue
            name, _, value = line.partition(":")
            name = name.strip()
            value = value.strip()
            if name:
                self._fields[name] = value

    def get_field(self, name: str) -> str:
        """Return the raw value of an ``lscpu`` field by its exact label.

        Args:
            name (str): The field label as printed by lscpu (e.g. "Socket(s)").

        Returns:
            str: The field value, or an empty string if the field is absent.
        """
        return self._fields.get(name, "")

    def get_cpu_count(self) -> int:
        """Return the total number of logical CPUs (``CPU(s):``).

        Returns:
            int: The CPU count, or 0 if the field is absent or unparsable.
        """
        return self._as_int(self.get_field("CPU(s)"))

    def get_socket_count(self) -> int:
        """Return the number of physical sockets (``Socket(s):``).

        Returns:
            int: The socket count, or 0 if the field is absent or unparsable.
        """
        return self._as_int(self.get_field("Socket(s)"))

    def get_numa_node_count(self) -> int:
        """Return the number of NUMA nodes (``NUMA node(s):``).

        Returns:
            int: The NUMA node count, or 0 if the field is absent or
            unparsable.
        """
        return self._as_int(self.get_field("NUMA node(s)"))

    @staticmethod
    def _as_int(value: str) -> int:
        """Convert a field value to int, returning 0 when not a plain integer.

        Args:
            value (str): The raw field value.

        Returns:
            int: The parsed integer, or 0 if ``value`` is not a plain integer.
        """
        return int(value) if value.isdigit() else 0

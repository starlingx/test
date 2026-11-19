import re


class KubectlTopObject:
    """
    Represents one row of `kubectl top nodes` or `kubectl top pods` output.

    Stores the resource usage cells exactly as kubectl prints them (for example "445m",
    "8996Mi", or "<unknown>" when metrics are not being served) and exposes typed getters,
    plus convenience readers that report whether a cell is a real, positive reading.
    """

    # Leading numeric portion of a quantity cell: "445m" -> 445, "8996Mi" -> 8996, "2" -> 2.
    # A "<unknown>" cell has no leading number and so does not match.
    _LEADING_NUMBER = re.compile(r"^([0-9]+(?:\.[0-9]+)?)")

    def __init__(self, name: str):
        """
        Constructor.

        Args:
            name (str): the node or pod name.
        """
        self.name = name
        self.cpu: str = None
        self.memory: str = None

    def get_name(self) -> str:
        """
        Getter for name.

        Returns:
            str: the node or pod name.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """
        Setter for name.

        Args:
            name (str): the node or pod name.
        """
        self.name = name

    def get_cpu(self) -> str:
        """
        Getter for the CPU cell as kubectl printed it.

        Returns:
            str: the CPU usage cell, for example "445m", "2", or "<unknown>".
        """
        return self.cpu

    def set_cpu(self, cpu: str) -> None:
        """
        Setter for the CPU cell.

        Args:
            cpu (str): the CPU usage cell.
        """
        self.cpu = cpu

    def get_memory(self) -> str:
        """
        Getter for the memory cell as kubectl printed it.

        Returns:
            str: the memory usage cell, for example "8996Mi" or "<unknown>".
        """
        return self.memory

    def set_memory(self, memory: str) -> None:
        """
        Setter for the memory cell.

        Args:
            memory (str): the memory usage cell.
        """
        self.memory = memory

    def has_positive_cpu(self) -> bool:
        """
        Report whether the CPU cell is a real, strictly positive reading.

        Returns:
            bool: True when the leading numeric portion parses and is greater than zero. A
                "<unknown>" cell (printed when metrics are not served) returns False.
        """
        return self._is_positive(self.cpu)

    def has_positive_memory(self) -> bool:
        """
        Report whether the memory cell is a real, strictly positive reading.

        Returns:
            bool: True when the leading numeric portion parses and is greater than zero.
        """
        return self._is_positive(self.memory)

    def get_cpu_millicores(self) -> int:
        """
        Get the CPU cell as an integer number of millicores.

        Returns:
            int: CPU usage in millicores, e.g. "445m" -> 445 and "2" (cores) -> 2000.

        Raises:
            ValueError: if the cell is not a numeric reading (for example "<unknown>").
        """
        match = self._LEADING_NUMBER.match((self.cpu or "").strip())
        if not match:
            raise ValueError(f"CPU cell {self.cpu!r} of {self.name!r} is not a numeric reading")
        value = float(match.group(1))
        return int(value) if self.cpu.strip().endswith("m") else int(value * 1000)

    def get_memory_mebibytes(self) -> int:
        """
        Get the memory cell as an integer number of mebibytes.

        Returns:
            int: memory usage in Mi, e.g. "8996Mi" -> 8996, "2Gi" -> 2048 and "512Ki" -> 0.

        Raises:
            ValueError: if the cell is not a numeric reading or has an unsupported unit.
        """
        cell = (self.memory or "").strip()
        match = self._LEADING_NUMBER.match(cell)
        if not match:
            raise ValueError(f"Memory cell {self.memory!r} of {self.name!r} is not a numeric reading")
        value = float(match.group(1))
        unit = cell[len(match.group(1)) :]
        factors = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1024 * 1024}
        if unit not in factors:
            raise ValueError(f"Memory cell {self.memory!r} of {self.name!r} has unsupported unit {unit!r}")
        return int(value * factors[unit])

    @classmethod
    def _is_positive(cls, cell: str) -> bool:
        """
        Report whether a quantity cell has a leading number greater than zero.

        The unit suffix is not normalised; only whether a real non-zero value was served is
        of interest.

        Args:
            cell (str): the quantity cell, for example "445m", "8996Mi", "0m", "<unknown>".

        Returns:
            bool: True when the leading numeric portion parses and is greater than zero.
        """
        if not cell:
            return False
        match = cls._LEADING_NUMBER.match(cell.strip())
        return bool(match) and float(match.group(1)) > 0

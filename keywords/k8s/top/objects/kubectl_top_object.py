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

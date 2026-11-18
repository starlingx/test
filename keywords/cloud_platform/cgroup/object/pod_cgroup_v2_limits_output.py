from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.cgroup.object.pod_cgroup_v2_limits_object import PodCgroupV2LimitsObject


class PodCgroupV2LimitsOutput:
    """Parses the output of 'cat cpu.weight cpu.max memory.max' run inside a pod.

    The three files are read in that order, one line each (e.g. "4", "20000 100000", "134217728").
    """

    EXPECTED_LINE_COUNT = 3

    def __init__(self, raw_output: str | list[str]) -> None:
        """Initialize PodCgroupV2LimitsOutput.

        Args:
            raw_output (str | list[str]): The kubectl exec response, as a string or a list of strings.

        Raises:
            KeywordException: If the output is not exactly three lines, cpu.max is not "<quota> <period>",
                or a numeric value is not an integer.
        """
        lines = self._split_lines(raw_output)
        if len(lines) != self.EXPECTED_LINE_COUNT:
            raise KeywordException(f"Expected {self.EXPECTED_LINE_COUNT} lines (cpu.weight, cpu.max, memory.max) but got {len(lines)}: {lines}")

        cpu_weight, cpu_max, memory_max = lines
        cpu_max_fields = cpu_max.split()
        if len(cpu_max_fields) != 2:
            raise KeywordException(f"Expected cpu.max as '<quota> <period>' but got '{cpu_max}'")

        self._limits = PodCgroupV2LimitsObject(
            self._to_int("cpu.weight", cpu_weight),
            self._to_int("cpu.max quota", cpu_max_fields[0]),
            self._to_int("cpu.max period", cpu_max_fields[1]),
            self._to_int("memory.max", memory_max),
        )

    @staticmethod
    def _split_lines(raw_output: str | list[str]) -> list[str]:
        """Split a kubectl exec response into stripped, non-empty lines.

        Args:
            raw_output (str | list[str]): The kubectl exec response, as a string or a list of strings.

        Returns:
            list[str]: The non-empty lines, in order.
        """
        chunks = raw_output if isinstance(raw_output, list) else [raw_output]
        lines = []
        for chunk in chunks:
            lines.extend(line.strip() for line in chunk.splitlines() if line.strip())
        return lines

    @staticmethod
    def _to_int(name: str, value: str) -> int:
        """Convert a cgroup file value to an integer.

        Args:
            name (str): The cgroup file or field name, used in the error message.
            value (str): The value read from the file.

        Returns:
            int: The integer value.

        Raises:
            KeywordException: If the value is not an integer (for example "max", meaning no limit).
        """
        if not value.isdigit():
            raise KeywordException(f"Expected an integer for {name} but got '{value}'")
        return int(value)

    def get_limits(self) -> PodCgroupV2LimitsObject:
        """Get the parsed cgroup v2 limits.

        Returns:
            PodCgroupV2LimitsObject: The cpu.weight, cpu.max (quota and period) and memory.max values.
        """
        return self._limits

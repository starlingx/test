import re
from typing import List, Union

from keywords.linux.occtop.object.occtop_object import OcctopObject


class OcctopOutput:
    """A class to interact with and retrieve information from occtop command output.

    This class provides methods to parse and access CPU occupancy information
    from the occtop command output.
    """

    def __init__(self, occtop_output: Union[str, list]):
        """Constructor.

        Args:
            occtop_output (Union[str, list]): Raw output from running the occtop command.
        """
        self.occtop_object = self._parse_occtop_output(occtop_output)
        self.raw_output = occtop_output

    def _parse_occtop_output(self, output: Union[str, list]) -> OcctopObject:
        """Parse the raw occtop output into a structured object.

        Args:
            output (Union[str, list]): Raw output from occtop command.

        Returns:
            OcctopObject: Parsed occtop information.
        """
        occtop = OcctopObject()

        if isinstance(output, str):
            lines = output.strip().split('\n')
        else:
            lines = output

        # Filter empty lines
        lines = [line for line in lines if line.strip()]

        # Find the header start (line starting with 'occtop')
        header_index = self._find_header_start(lines)
        if header_index is None:
            return occtop

        # Parse header lines
        self._parse_line_1(lines[header_index], occtop)
        if header_index + 1 < len(lines):
            self._parse_line_2(lines[header_index + 1], occtop)
        if header_index + 2 < len(lines):
            self._parse_line_3(lines[header_index + 2], occtop)
        if header_index + 3 < len(lines):
            self._parse_line_4(lines[header_index + 3], occtop)

        # Parse sample data rows
        samples = self._parse_samples(lines, header_index + 4)
        occtop.set_samples(samples)

        return occtop

    def _find_header_start(self, lines: list) -> int:
        """Find the index of the first header line starting with 'occtop'.

        Args:
            lines (list): List of output lines.

        Returns:
            int: Index of the header line, or None if not found.
        """
        for i, line in enumerate(lines):
            if line.strip().startswith("occtop"):
                return i
        return None

    def _parse_line_1(self, line: str, occtop: OcctopObject) -> None:
        """Parse first header line: version, timestamp, load averages, system stats.

        Args:
            line (str): First header line.
            occtop (OcctopObject): Object to populate.
        """
        version_match = re.search(r"occtop\s+([\d.]+)", line)
        if version_match:
            occtop.set_version(version_match.group(1))

        timestamp_match = re.search(r"--\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)", line)
        if timestamp_match:
            occtop.set_timestamp(timestamp_match.group(1))

        ldavg_match = re.search(r"ldavg:([\d.]+),\s*([\d.]+),\s*([\d.]+)", line)
        if ldavg_match:
            occtop.set_load_avg_1min(float(ldavg_match.group(1)))
            occtop.set_load_avg_5min(float(ldavg_match.group(2)))
            occtop.set_load_avg_15min(float(ldavg_match.group(3)))

        runq_match = re.search(r"runq:(\d+)", line)
        if runq_match:
            occtop.set_run_queue_depth(int(runq_match.group(1)))

        blk_match = re.search(r"blk:(\d+)", line)
        if blk_match:
            occtop.set_blocked_count(int(blk_match.group(1)))

        nproc_match = re.search(r"nproc:(\d+)", line)
        if nproc_match:
            occtop.set_process_count(int(nproc_match.group(1)))

        up_match = re.search(r"up:(\S+)", line)
        if up_match:
            occtop.set_uptime(up_match.group(1))

    def _parse_line_2(self, line: str, occtop: OcctopObject) -> None:
        """Parse second header line: host, nodetype, subfunction.

        Args:
            line (str): Second header line.
            occtop (OcctopObject): Object to populate.
        """
        host_match = re.search(r"host:(\S+)", line)
        if host_match:
            occtop.set_hostname(host_match.group(1))

        nodetype_match = re.search(r"nodetype:(\S+)", line)
        if nodetype_match:
            occtop.set_node_type(nodetype_match.group(1))

        subfunction_match = re.search(r"subfunction:(\S+)", line)
        if subfunction_match:
            occtop.set_subfunction(subfunction_match.group(1))

    def _parse_line_3(self, line: str, occtop: OcctopObject) -> None:
        """Parse third header line: arch, processor, speed, CPU count.

        Args:
            line (str): Third header line.
            occtop (OcctopObject): Object to populate.
        """
        arch_match = re.search(r"arch:(\S+)", line)
        if arch_match:
            occtop.set_architecture(arch_match.group(1))

        processor_match = re.search(r"processor:(.+?)\s+speed:", line)
        if processor_match:
            occtop.set_processor_model(processor_match.group(1).strip())

        speed_match = re.search(r"speed:(\S+)", line)
        if speed_match:
            occtop.set_cpu_speed(speed_match.group(1))

        cpu_count_match = re.search(r"#CPUs:(\d+)", line)
        if cpu_count_match:
            occtop.set_cpu_count(int(cpu_count_match.group(1)))

    def _parse_line_4(self, line: str, occtop: OcctopObject) -> None:
        """Parse fourth header line: kernel version, build info.

        Args:
            line (str): Fourth header line.
            occtop (OcctopObject): Object to populate.
        """
        kernel_match = re.search(r"Linux\s+(\S+)", line)
        if kernel_match:
            occtop.set_kernel_version(kernel_match.group(1))

        build_match = re.search(r"build:(.+)$", line)
        if build_match:
            occtop.set_build_info(build_match.group(1).strip())

    def _parse_samples(self, lines: list, start_index: int) -> List[dict]:
        """Parse per-CPU occupancy data rows.

        Args:
            lines (list): All output lines.
            start_index (int): Index to start searching for data rows.

        Returns:
            List[dict]: List of sample dicts with 'timestamp', 'total', 'per_cpu' keys.
        """
        samples = []

        # Find the first data row (skip column header line)
        data_start = None
        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            if re.match(r"\d{4}-\d{2}-\d{2}", line):
                data_start = i
                break

        if data_start is None:
            return samples

        for i in range(data_start, len(lines)):
            line = lines[i].strip()
            if not line or line.startswith("done") or line.startswith("processing time:"):
                break

            sample = self._parse_data_row(line)
            if sample is not None:
                samples.append(sample)

        return samples

    def _parse_data_row(self, line: str) -> dict:
        """Parse a single data row into a sample dictionary.

        Args:
            line (str): A data row from occtop output.

        Returns:
            dict: Sample with 'timestamp', 'total', 'per_cpu' keys, or None if unparseable.
        """
        timestamp_match = re.match(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(.+)", line)
        if not timestamp_match:
            return None

        timestamp = timestamp_match.group(1)
        values_str = timestamp_match.group(2).strip()
        parts = values_str.split()

        if not parts:
            return None

        try:
            total = float(parts[0])
            per_cpu = []
            for part in parts[1:]:
                try:
                    per_cpu.append(float(part))
                except ValueError:
                    continue
            return {'timestamp': timestamp, 'total': total, 'per_cpu': per_cpu}
        except (ValueError, IndexError):
            return None

    def get_occtop_object(self) -> OcctopObject:
        """Get the parsed occtop object.

        Returns:
            OcctopObject: Parsed occtop information.
        """
        return self.occtop_object

    def get_raw_output(self) -> Union[str, list]:
        """Get the raw output from occtop.

        Returns:
            Union[str, list]: Raw command output.
        """
        return self.raw_output

    def get_hostname(self) -> str:
        """Get hostname.

        Returns:
            str: Hostname.
        """
        return self.occtop_object.get_hostname()

    def get_cpu_count(self) -> int:
        """Get CPU count.

        Returns:
            int: CPU count.
        """
        return self.occtop_object.get_cpu_count()

    def get_samples(self) -> List[dict]:
        """Get per-CPU occupancy samples.

        Returns:
            List[dict]: List of sample dictionaries.
        """
        return self.occtop_object.get_samples()

    def get_sample_count(self) -> int:
        """Get number of samples collected.

        Returns:
            int: Number of samples.
        """
        return self.occtop_object.get_sample_count()

    def get_kernel_version(self) -> str:
        """Get kernel version.

        Returns:
            str: Kernel version string.
        """
        return self.occtop_object.get_kernel_version()

    def get_node_type(self) -> str:
        """Get node type.

        Returns:
            str: Node type.
        """
        return self.occtop_object.get_node_type()

    def get_load_avg_1min(self) -> float:
        """Get 1-minute load average.

        Returns:
            float: 1-minute load average.
        """
        return self.occtop_object.get_load_avg_1min()

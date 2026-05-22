from typing import List


class OcctopObject:
    """Class to hold attributes of a parsed occtop execution result."""

    def __init__(self):
        """Constructor."""
        self.version = ""
        self.timestamp = ""
        self.load_avg_1min = 0.0
        self.load_avg_5min = 0.0
        self.load_avg_15min = 0.0
        self.run_queue_depth = 0
        self.blocked_count = 0
        self.process_count = 0
        self.uptime = ""
        self.hostname = ""
        self.node_type = ""
        self.subfunction = ""
        self.architecture = ""
        self.processor_model = ""
        self.cpu_speed = ""
        self.cpu_count = 0
        self.kernel_version = ""
        self.build_info = ""
        self.samples: List[dict] = []

    def get_version(self) -> str:
        """Getter for occtop version.

        Returns:
            str: Version string.
        """
        return self.version

    def set_version(self, version: str) -> None:
        """Setter for occtop version.

        Args:
            version (str): Version string.
        """
        self.version = version

    def get_timestamp(self) -> str:
        """Getter for execution timestamp.

        Returns:
            str: Timestamp string.
        """
        return self.timestamp

    def set_timestamp(self, timestamp: str) -> None:
        """Setter for execution timestamp.

        Args:
            timestamp (str): Timestamp string.
        """
        self.timestamp = timestamp

    def get_load_avg_1min(self) -> float:
        """Getter for 1-minute load average.

        Returns:
            float: 1-minute load average.
        """
        return self.load_avg_1min

    def set_load_avg_1min(self, value: float) -> None:
        """Setter for 1-minute load average.

        Args:
            value (float): 1-minute load average.
        """
        self.load_avg_1min = value

    def get_load_avg_5min(self) -> float:
        """Getter for 5-minute load average.

        Returns:
            float: 5-minute load average.
        """
        return self.load_avg_5min

    def set_load_avg_5min(self, value: float) -> None:
        """Setter for 5-minute load average.

        Args:
            value (float): 5-minute load average.
        """
        self.load_avg_5min = value

    def get_load_avg_15min(self) -> float:
        """Getter for 15-minute load average.

        Returns:
            float: 15-minute load average.
        """
        return self.load_avg_15min

    def set_load_avg_15min(self, value: float) -> None:
        """Setter for 15-minute load average.

        Args:
            value (float): 15-minute load average.
        """
        self.load_avg_15min = value

    def get_run_queue_depth(self) -> int:
        """Getter for run queue depth.

        Returns:
            int: Run queue depth.
        """
        return self.run_queue_depth

    def set_run_queue_depth(self, value: int) -> None:
        """Setter for run queue depth.

        Args:
            value (int): Run queue depth.
        """
        self.run_queue_depth = value

    def get_blocked_count(self) -> int:
        """Getter for blocked process count.

        Returns:
            int: Blocked process count.
        """
        return self.blocked_count

    def set_blocked_count(self, value: int) -> None:
        """Setter for blocked process count.

        Args:
            value (int): Blocked process count.
        """
        self.blocked_count = value

    def get_process_count(self) -> int:
        """Getter for total process count.

        Returns:
            int: Process count.
        """
        return self.process_count

    def set_process_count(self, value: int) -> None:
        """Setter for total process count.

        Args:
            value (int): Process count.
        """
        self.process_count = value

    def get_uptime(self) -> str:
        """Getter for system uptime.

        Returns:
            str: Uptime string.
        """
        return self.uptime

    def set_uptime(self, uptime: str) -> None:
        """Setter for system uptime.

        Args:
            uptime (str): Uptime string.
        """
        self.uptime = uptime

    def get_hostname(self) -> str:
        """Getter for hostname.

        Returns:
            str: Hostname.
        """
        return self.hostname

    def set_hostname(self, hostname: str) -> None:
        """Setter for hostname.

        Args:
            hostname (str): Hostname string.
        """
        self.hostname = hostname

    def get_node_type(self) -> str:
        """Getter for node type.

        Returns:
            str: Node type.
        """
        return self.node_type

    def set_node_type(self, node_type: str) -> None:
        """Setter for node type.

        Args:
            node_type (str): Node type string.
        """
        self.node_type = node_type

    def get_subfunction(self) -> str:
        """Getter for subfunction.

        Returns:
            str: Subfunction.
        """
        return self.subfunction

    def set_subfunction(self, subfunction: str) -> None:
        """Setter for subfunction.

        Args:
            subfunction (str): Subfunction string.
        """
        self.subfunction = subfunction

    def get_architecture(self) -> str:
        """Getter for system architecture.

        Returns:
            str: Architecture string.
        """
        return self.architecture

    def set_architecture(self, architecture: str) -> None:
        """Setter for system architecture.

        Args:
            architecture (str): Architecture string.
        """
        self.architecture = architecture

    def get_processor_model(self) -> str:
        """Getter for processor model.

        Returns:
            str: Processor model string.
        """
        return self.processor_model

    def set_processor_model(self, processor_model: str) -> None:
        """Setter for processor model.

        Args:
            processor_model (str): Processor model string.
        """
        self.processor_model = processor_model

    def get_cpu_speed(self) -> str:
        """Getter for CPU speed.

        Returns:
            str: CPU speed string.
        """
        return self.cpu_speed

    def set_cpu_speed(self, cpu_speed: str) -> None:
        """Setter for CPU speed.

        Args:
            cpu_speed (str): CPU speed string.
        """
        self.cpu_speed = cpu_speed

    def get_cpu_count(self) -> int:
        """Getter for CPU count.

        Returns:
            int: CPU count.
        """
        return self.cpu_count

    def set_cpu_count(self, cpu_count: int) -> None:
        """Setter for CPU count.

        Args:
            cpu_count (int): CPU count.
        """
        self.cpu_count = cpu_count

    def get_kernel_version(self) -> str:
        """Getter for kernel version.

        Returns:
            str: Kernel version string.
        """
        return self.kernel_version

    def set_kernel_version(self, kernel_version: str) -> None:
        """Setter for kernel version.

        Args:
            kernel_version (str): Kernel version string.
        """
        self.kernel_version = kernel_version

    def get_build_info(self) -> str:
        """Getter for build information.

        Returns:
            str: Build info string.
        """
        return self.build_info

    def set_build_info(self, build_info: str) -> None:
        """Setter for build information.

        Args:
            build_info (str): Build info string.
        """
        self.build_info = build_info

    def get_samples(self) -> List[dict]:
        """Getter for per-CPU occupancy samples.

        Each sample is a dict with keys: 'timestamp', 'total', 'per_cpu'.

        Returns:
            List[dict]: List of sample dictionaries.
        """
        return self.samples

    def set_samples(self, samples: List[dict]) -> None:
        """Setter for per-CPU occupancy samples.

        Args:
            samples (List[dict]): List of sample dictionaries.
        """
        self.samples = samples

    def get_sample_count(self) -> int:
        """Get the number of samples collected.

        Returns:
            int: Number of samples.
        """
        return len(self.samples)

    def __str__(self) -> str:
        """String representation of the occtop object.

        Returns:
            str: Hostname and CPU count.
        """
        return f"Occtop(host={self.hostname}, cpus={self.cpu_count}, samples={len(self.samples)})"

    def __repr__(self) -> str:
        """Representation of the occtop object.

        Returns:
            str: Hostname and CPU count.
        """
        return self.__str__()

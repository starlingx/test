from decimal import Decimal


class K8sQuantityConverter:
    """Converts Kubernetes resource quantities (CPU and memory) to plain numbers."""

    # Binary (Ki/Mi/Gi/...) and decimal (k/M/G/...) suffix multipliers for Kubernetes memory quantities.
    BINARY_SUFFIXES = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4, "Pi": 1024**5, "Ei": 1024**6}
    DECIMAL_SUFFIXES = {"k": 1000, "M": 1000**2, "G": 1000**3, "T": 1000**4, "P": 1000**5, "E": 1000**6}

    def cpu_quantity_to_millicpu(self, cpu: str) -> int:
        """Convert a Kubernetes CPU quantity to millicpu.

        Accepts the milli form (e.g. "200m") or whole/fractional cores (e.g. "2", "0.5").

        Args:
            cpu (str): A Kubernetes CPU quantity, such as "200m", "2" or "0.5".

        Returns:
            int: The quantity expressed in millicpu (e.g. "200m" -> 200, "2" -> 2000).
        """
        cpu = cpu.strip()
        if cpu.endswith("m"):
            return int(cpu[:-1])
        return int(round(float(cpu) * 1000))

    def cpu_limit_to_quota(self, cpu_limit: str, period_us: int) -> int:
        """Compute the CFS quota (microseconds per period) for a CPU limit.

        quota = millicpu * period / 1000, which is the first field of a cgroup v2 cpu.max value.

        Args:
            cpu_limit (str): A Kubernetes CPU limit, such as "200m" or "2".
            period_us (int): The CFS period in microseconds.

        Returns:
            int: The expected quota in microseconds (e.g. "200m" with a 100000 period -> 20000).
        """
        return self.cpu_quantity_to_millicpu(cpu_limit) * period_us // 1000

    def memory_quantity_to_bytes(self, memory: str) -> int:
        """Convert a Kubernetes memory quantity to bytes.

        Supports binary suffixes (Ki, Mi, Gi, ...), decimal suffixes (k, M, G, ...) and plain bytes.

        Args:
            memory (str): A Kubernetes memory quantity, such as "128Mi", "64M" or "1073741824".

        Returns:
            int: The quantity expressed in bytes (e.g. "128Mi" -> 134217728).
        """
        memory = memory.strip()
        for suffixes in (self.BINARY_SUFFIXES, self.DECIMAL_SUFFIXES):
            for suffix, multiplier in suffixes.items():
                if memory.endswith(suffix):
                    return int(Decimal(memory[: -len(suffix)]) * multiplier)
        return int(memory)

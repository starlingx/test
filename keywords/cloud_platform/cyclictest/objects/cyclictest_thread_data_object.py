from typing import Dict, List

from framework.logging.automation_logger import get_logger


class CyclictestThreadDataObject:
    """Per-thread histogram data from a cyclictest histfile."""

    def __init__(self, thread_num: int):
        """Initialize per-thread histogram data.

        Args:
            thread_num (int): Thread index.
        """
        self._thread_num = thread_num
        self._data: Dict[int, int] = {}
        self._elements: List[int] = []
        self._num_overflows: int = 0
        self._num_samples: int = 0
        self._accumulator: int = 0
        self._maximum: int = 0
        self._percentile: int = 0

    def get_thread_num(self) -> int:
        """Return the thread index.

        Returns:
            int: Thread index.
        """
        return self._thread_num

    def get_num_overflows(self) -> int:
        """Return the overflow count for this thread.

        Returns:
            int: Number of histogram overflows.
        """
        return self._num_overflows

    def set_num_overflows(self, value: int) -> None:
        """Set the overflow count for this thread.

        Args:
            value (int): Number of histogram overflows.
        """
        self._num_overflows = value

    def get_num_samples(self) -> int:
        """Return the total sample count for this thread.

        Returns:
            int: Total number of samples.
        """
        return self._num_samples

    def get_accumulator(self) -> int:
        """Return the accumulated latency sum (for average calculation).

        Returns:
            int: Sum of (delay * count) across all histogram buckets.
        """
        return self._accumulator

    def get_maximum(self) -> int:
        """Return the maximum latency observed.

        Returns:
            int: Maximum latency in ns.
        """
        return self._maximum

    def get_percentile(self) -> int:
        """Return the six-nines percentile latency.

        Returns:
            int: Six-nines percentile latency in ns.
        """
        return self._percentile

    def get_elements(self) -> List[int]:
        """Return the expanded list of all latency samples (delay repeated count times).

        Returns:
            List[int]: Flat list of individual latency values.
        """
        return self._elements

    def append(self, delay: int, count: int) -> None:
        """Add a histogram bucket.

        Args:
            delay (int): Latency value in ns.
            count (int): Sample count at this latency.
        """
        if count <= 0:
            return
        self._data[delay] = self._data.get(delay, 0) + count

    def _calculate_six_nines_percentile(self) -> int:
        """Calculate the 99.9999% percentile latency.

        Returns:
            int: Latency at six-nines percentile.
        """
        total_count = sum(self._data.values())
        throw_away = int(total_count / 1_000_000)
        delays: List[int] = []
        for delay in sorted(self._data.keys()):
            delays.extend([delay] * self._data[delay])
        expected = delays[-throw_away - 1]
        for delay in sorted(self._data.keys(), reverse=True):
            count = self._data[delay]
            if throw_away > 0 and throw_away >= count:
                throw_away -= count
            else:
                if expected and delay != expected:
                    get_logger().log_warning(f"Thread:{self._thread_num} expected:{expected} calculated:{delay}")
                return delay
        raise RuntimeError(f"Thread{self._thread_num:02d}: Internal error in percentile calculation")

    def calculate_statistics(self) -> "CyclictestThreadDataObject":
        """Compute statistics for this thread.

        Returns:
            CyclictestThreadDataObject: self with statistics populated.
        """
        self._num_samples = sum(self._data.values())
        self._accumulator = sum(d * c for d, c in self._data.items())
        self._maximum = max(self._data.keys())
        self._percentile = self._calculate_six_nines_percentile()
        for delay, count in self._data.items():
            self._elements.extend([delay] * count)
        return self

    def __str__(self) -> str:
        """Return a human-readable representation.

        Returns:
            str: Summary of per-thread statistics.
        """
        return f"CyclictestThreadDataObject(thread={self._thread_num}, samples={self._num_samples}, " f"max={self._maximum}, percentile={self._percentile}, overflows={self._num_overflows})"

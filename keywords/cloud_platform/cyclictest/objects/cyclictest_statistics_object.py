import statistics
from typing import List

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.cyclictest.objects.cyclictest_thread_data_object import CyclictestThreadDataObject


class CyclictestStatisticsObject:
    """Aggregated cyclictest statistics across all threads."""

    def __init__(self, filename: str, thread_data: List[CyclictestThreadDataObject]):
        """Initialize aggregated cyclictest statistics.

        Args:
            filename (str): Source histogram file path.
            thread_data (List[CyclictestThreadDataObject]): Per-thread data objects.
        """
        self._filename = filename
        self._num_threads = len(thread_data)
        self._thread_data = thread_data
        self._num_samples: int = 0
        self._average: int = 0
        self._maximum: int = 0
        self._median: int = 0
        self._percentile: int = 0
        self._num_overflows: int = 0

    def get_filename(self) -> str:
        """Return the source histogram file path.

        Returns:
            str: Histogram file path.
        """
        return self._filename

    def get_num_threads(self) -> int:
        """Return the number of threads.

        Returns:
            int: Thread count.
        """
        return self._num_threads

    def get_average(self) -> int:
        """Return the average latency across all threads.

        Returns:
            int: Average latency in ns.
        """
        return self._average

    def get_maximum(self) -> int:
        """Return the maximum latency observed across all threads.

        Returns:
            int: Maximum latency in ns.
        """
        return self._maximum

    def get_median(self) -> int:
        """Return the median latency across all threads.

        Returns:
            int: Median latency in ns.
        """
        return self._median

    def get_percentile(self) -> int:
        """Return the six-nines percentile latency across all threads.

        Returns:
            int: Six-nines percentile latency in ns.
        """
        return self._percentile

    def get_num_overflows(self) -> int:
        """Return the total overflow count across all threads.

        Returns:
            int: Total number of histogram overflows.
        """
        return self._num_overflows

    def calculate_statistics(self) -> "CyclictestStatisticsObject":
        """Aggregate statistics from all threads.

        Returns:
            CyclictestStatisticsObject: self with aggregated statistics populated.
        """
        accumulator = 0
        maximums = []
        percentiles = []
        all_elements: List[int] = []

        for td in self._thread_data:
            stats = td.calculate_statistics()
            self._num_samples += stats.get_num_samples()
            accumulator += stats.get_accumulator()
            maximums.append(stats.get_maximum())
            percentiles.append(stats.get_percentile())
            self._num_overflows += stats.get_num_overflows()
            all_elements.extend(stats.get_elements())

        self._average = accumulator // self._num_samples
        self._maximum = max(maximums)
        self._median = int(statistics.median(all_elements))
        self._percentile = max(percentiles)

        get_logger().log_info(f"Cyclictest results — samples:{self._num_samples} avg:{self._average} max:{self._maximum} 6nines:{self._percentile} median:{self._median} overflows:{self._num_overflows}")
        return self

    @staticmethod
    def from_hist_file(filename: str, histofall_mode: bool = True) -> "CyclictestStatisticsObject":
        """Parse a cyclictest histogram file and return a statistics object.

        Args:
            filename (str): Path to the local histogram file.
            histofall_mode (bool): True if --histofall was used (last column is total).

        Returns:
            CyclictestStatisticsObject: parsed object (call calculate_statistics() to compute).

        Raises:
            FileNotFoundError: If the histogram file does not exist at the given path.
            ValueError: If the histogram file is empty or contains no data lines.
        """
        try:
            with open(filename, "r") as fin:
                lines = fin.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f"Cyclictest histogram file not found: {filename}")

        overflow_lines = [line.strip() for line in lines if line.startswith("# Histogram Overflows:")]
        data_lines = [line.strip() for line in lines if line and line[0].isdigit()]

        if not data_lines:
            raise ValueError(f"No histogram data found in file: {filename}")

        thread_data: List[CyclictestThreadDataObject] = []
        initialized = False

        for line in data_lines:
            comps = line.split()
            if histofall_mode:
                comps.pop()
            if not initialized:
                thread_data = [CyclictestThreadDataObject(i) for i in range(len(comps) - 1)]
                initialized = True
            delay = int(comps[0])
            for i, count_str in enumerate(comps[1:]):
                thread_data[i].append(delay, int(count_str))

        if overflow_lines:
            overflow_comps = overflow_lines[0].split(":", 1)[1].split()
            if histofall_mode:
                overflow_comps.pop()
            for i, ov in enumerate(overflow_comps):
                thread_data[i].set_num_overflows(int(ov))

        return CyclictestStatisticsObject(filename, thread_data)

    def __str__(self) -> str:
        """Return a human-readable representation.

        Returns:
            str: Summary of aggregated cyclictest statistics.
        """
        return f"CyclictestStatisticsObject(threads={self._num_threads}, samples={self._num_samples}, " f"avg={self._average}, max={self._maximum}, median={self._median}, " f"6nines={self._percentile}, overflows={self._num_overflows})"

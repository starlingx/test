# Copyright (c) 2026 Wind River Systems, Inc.
# SPDX-License-Identifier: Apache-2.0
"""CPU usage statistics object returned by CyclictestCpuMonitor."""


class CpuUsageStatsObject:
    """CPU usage statistics (average, median, std_deviation) for a cyclictest run."""

    def __init__(self, average: float, median: float, std_deviation: float) -> None:
        """
        Constructor.

        Args:
            average (float): Average CPU usage percentage.
            median (float): Median CPU usage percentage.
            std_deviation (float): Standard deviation of CPU usage percentage.
        """
        self._average = average
        self._median = median
        self._std_deviation = std_deviation

    def get_average(self) -> float:
        """Return the average CPU usage percentage.

        Returns:
            float: Average CPU usage percentage.
        """
        return self._average

    def get_median(self) -> float:
        """Return the median CPU usage percentage.

        Returns:
            float: Median CPU usage percentage.
        """
        return self._median

    def get_std_deviation(self) -> float:
        """Return the standard deviation of CPU usage percentage.

        Returns:
            float: Standard deviation of CPU usage percentage.
        """
        return self._std_deviation

    def __str__(self) -> str:
        """Return a human-readable representation.

        Returns:
            str: Summary of CPU usage statistics.
        """
        return f"CpuUsageStatsObject(average={self._average}, median={self._median}, std_deviation={self._std_deviation})"

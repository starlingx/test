# Copyright (c) 2026 Wind River Systems, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Result object returned by CyclictestKeywords.run_cyclictest()."""


class CyclictestRunResultObject:
    """Encapsulates the output paths produced by a single cyclictest run."""

    def __init__(self, run_log: str, hist_file: str, histofall_mode: bool) -> None:
        """
        Constructor.

        Args:
            run_log (str): Remote path to the cyclictest run log file.
            hist_file (str): Remote path to the cyclictest histogram file.
            histofall_mode (bool): True when --histofall was used.
        """
        self._run_log = run_log
        self._hist_file = hist_file
        self._histofall_mode = histofall_mode

    def get_run_log(self) -> str:
        """Return the remote path to the cyclictest run log file.

        Returns:
            str: Remote run log path.
        """
        return self._run_log

    def get_hist_file(self) -> str:
        """Return the remote path to the cyclictest histogram file.

        Returns:
            str: Remote histogram file path.
        """
        return self._hist_file

    def is_histofall_mode(self) -> bool:
        """Return True if the run used --histofall.

        Returns:
            bool: True when --histofall was used and the last column is the total.
        """
        return self._histofall_mode

    def __str__(self) -> str:
        """Return a human-readable representation.

        Returns:
            str: Summary of the run result paths.
        """
        return f"CyclictestRunResultObject(run_log={self._run_log!r}, hist_file={self._hist_file!r}, histofall_mode={self._histofall_mode})"

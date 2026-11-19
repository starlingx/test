"""Output object for an 'iperf3 --client --json' run."""

import json
from typing import Optional


class Iperf3ClientOutput:
    """Parsed result of an 'iperf3 -c <server> -J' run."""

    def __init__(self, raw_output: str | list[str]):
        """Parse the iperf3 JSON report.

        Args:
            raw_output (str | list[str]): Raw SSH command output.

        Raises:
            ValueError: If the output is not an iperf3 JSON report.
        """
        content = "".join(raw_output) if isinstance(raw_output, list) else raw_output
        try:
            report = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError(f"iperf3 did not print a JSON report: {content[:300]}") from error
        end = report.get("end") or {}
        self.error = report.get("error")
        self.received_bits_per_second = (end.get("sum_received") or {}).get("bits_per_second")
        self.sent_bits_per_second = (end.get("sum_sent") or {}).get("bits_per_second")

    def get_error(self) -> Optional[str]:
        """Get the error iperf3 reported, if any.

        Returns:
            Optional[str]: The error message, or None when the run succeeded.
        """
        return self.error

    def get_received_bits_per_second(self) -> float:
        """Get the throughput measured at the receiver.

        Returns:
            float: Bits per second received by the server.

        Raises:
            ValueError: If the report has no receiver summary.
        """
        if self.received_bits_per_second is None:
            raise ValueError(f"iperf3 report has no receiver summary; error: {self.error}")
        return self.received_bits_per_second

    def __str__(self) -> str:
        """Human-readable representation of the iperf3 result.

        Returns:
            str: The sent and received throughput, and the error if any.
        """
        return f"Iperf3ClientOutput(sent_bps={self.sent_bits_per_second}, received_bps={self.received_bits_per_second}, error={self.error})"

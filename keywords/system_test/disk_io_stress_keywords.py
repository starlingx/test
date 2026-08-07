"""Keywords for generating controlled disk I/O stress on a target host.

Provides a reusable mechanism for writing files via dd to generate measurable
disk I/O activity. Useful for storage alarm tests, robustness testing, and
performance benchmarking.
"""

from datetime import datetime, timezone

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.system_test.disk_io_stress_result import DiskIOStressResult


# Default parameters (callers can override via method arguments)
DEFAULT_STRESS_DIR = "/tmp/disk_io_stress"
DEFAULT_FILE_SIZE_MB = 512
DEFAULT_ITERATIONS = 8


class DiskIOStressKeywords(BaseKeyword):
    """Keywords for generating and cleaning up disk I/O stress on a remote host."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize with SSH connection.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def generate_disk_io_stress(
        self,
        stress_dir: str = DEFAULT_STRESS_DIR,
        file_size_mb: int = DEFAULT_FILE_SIZE_MB,
        iterations: int = DEFAULT_ITERATIONS,
    ) -> DiskIOStressResult:
        """Generate controlled disk I/O stress by writing files via dd.

        Creates a temporary directory and writes multiple files using dd to
        generate measurable disk I/O activity. Uses oflag=dsync to ensure
        writes are flushed to disk.

        Args:
            stress_dir (str): Remote directory for stress files.
            file_size_mb (int): Size of each file in MB.
            iterations (int): Number of files to write.

        Returns:
            DiskIOStressResult: Structured result containing start/end timestamps
                and the hostname where stress was generated.

        Raises:
            AssertionError: If directory creation or hostname retrieval fails.
        """
        get_logger().log_info(f"Generating disk I/O stress: {iterations} x {file_size_mb}MB in {stress_dir}")

        # Get hostname
        hostname_output = self.ssh_connection.send("hostname")
        self.validate_success_return_code(self.ssh_connection)
        hostname = hostname_output[0].strip() if isinstance(hostname_output, list) else hostname_output.strip()
        get_logger().log_info(f"Target host: {hostname}")

        # Create /tmp directory for stress files
        self.ssh_connection.send(f"mkdir -p {stress_dir}")
        self.validate_success_return_code(self.ssh_connection)

        start_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        get_logger().log_info(f"Disk I/O stress start timestamp: {start_timestamp}")

        # Execute controlled disk I/O writes
        for i in range(1, iterations + 1):
            file_path = f"{stress_dir}/diskio_test_{i}"
            dd_cmd = f"dd if=/dev/zero of={file_path} bs=1M count={file_size_mb} oflag=dsync 2>&1"
            get_logger().log_info(f"Writing file {i}/{iterations}: {file_path} ({file_size_mb}MB)")
            output = self.ssh_connection.send(dd_cmd)
            output_text = "\n".join(output) if isinstance(output, list) else str(output)
            if "no space left on device" in output_text.lower():
                get_logger().log_warning(f"Disk I/O write {i} hit space limit, stopping early")
                break
            self.validate_success_return_code(self.ssh_connection)

        end_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        get_logger().log_info(f"Disk I/O stress completed. End timestamp: {end_timestamp}")
        get_logger().log_info(f"Total written: up to {iterations * file_size_mb}MB")

        result = DiskIOStressResult()
        result.set_start_timestamp(start_timestamp)
        result.set_end_timestamp(end_timestamp)
        result.set_hostname(hostname)
        return result

    def cleanup_disk_io_stress_files(self, stress_dir: str = DEFAULT_STRESS_DIR) -> None:
        """Remove the temporary disk I/O stress files.

        Args:
            stress_dir (str): Remote directory to remove.
        """
        get_logger().log_info(f"Cleaning up disk I/O stress files: {stress_dir}")
        self.ssh_connection.send(f"rm -rf {stress_dir}")
        self.validate_success_return_code(self.ssh_connection)

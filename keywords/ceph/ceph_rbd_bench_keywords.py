from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.ceph.object.ceph_rbd_bench_result import CephRbdBenchResult


class CephRbdBenchKeywords(BaseKeyword):
    """Keywords for driving continuous RBD write I/O via 'rbd bench'.

    Used by storage-resilience tests to prove that client I/O at the Ceph RBD
    layer survives a storage-node outage. The bench runs as a backgrounded
    process on the controller so the test can trigger a power fault while I/O
    is in flight, then confirm the run completed with a zero exit code.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to a host with Ceph/RBD CLI access.
        """
        self.ssh_connection = ssh_connection

    def create_image(self, pool: str, image: str, size_mb: int) -> None:
        """Create an RBD image in the given pool.

        Args:
            pool (str): Ceph pool name (e.g. 'kube-rbd').
            image (str): Image name to create.
            size_mb (int): Image size in mebibytes.
        """
        self.ssh_connection.send(f"rbd create {pool}/{image} --size {size_mb}")
        self.validate_success_return_code(self.ssh_connection)

    def cleanup_image(self, pool: str, image: str) -> None:
        """Remove an RBD image if it exists.

        Safe to call even when the image was never created.

        Args:
            pool (str): Ceph pool name.
            image (str): Image name to remove.
        """
        self.ssh_connection.send(f"rbd rm {pool}/{image} || true")

    def start_background_write_bench(self, pool: str, image: str, io_total_mb: int, log_file: str, rc_file: str) -> str:
        """Start a backgrounded 'rbd bench' write run.

        Launches the bench detached so the caller can perform a disruptive
        operation (e.g. power-cycle a storage node) while I/O is in flight.
        The process exit code is written to ``rc_file`` on completion and its
        output to ``log_file``.

        Args:
            pool (str): Ceph pool name.
            image (str): Target RBD image.
            io_total_mb (int): Total bytes to write, in mebibytes. Size this to
                comfortably exceed the expected outage window.
            log_file (str): Remote path for the bench stdout/stderr.
            rc_file (str): Remote path where the exit code will be written.

        Returns:
            str: The PID of the backgrounded bench process.
        """
        bench_cmd = f"rbd bench --io-type write --io-size 4096 --io-threads 16 --io-total {io_total_mb}M --io-pattern rand {pool}/{image}"
        wrapper = f"nohup sh -c '{bench_cmd} > {log_file} 2>&1; echo $? > {rc_file}' >/dev/null 2>&1 & echo $!"
        output = self.ssh_connection.send(wrapper)
        pid = "".join(output).strip() if isinstance(output, list) else str(output).strip()
        get_logger().log_info(f"Started rbd bench (pid={pid}) writing to {pool}/{image}")
        return pid

    def is_bench_running(self, pid: str) -> bool:
        """Check whether the backgrounded bench process is still running.

        Args:
            pid (str): The bench process PID.

        Returns:
            bool: True if the process is still running, False otherwise.
        """
        self.ssh_connection.send(f"kill -0 {pid}")
        return self.ssh_connection.get_return_code() == 0

    def wait_for_bench_completion(self, pid: str, rc_file: str, log_file: str, timeout: int = 900, polling_sleep_time: int = 15) -> CephRbdBenchResult:
        """Wait for the backgrounded bench to finish and return its result.

        Args:
            pid (str): The bench process PID.
            rc_file (str): Remote path holding the exit code.
            log_file (str): Remote path holding the bench output.
            timeout (int): Maximum time to wait in seconds.
            polling_sleep_time (int): Time between checks in seconds.

        Returns:
            CephRbdBenchResult: The exit code and captured log of the bench run.

        Raises:
            ValidationFailureError: If the bench process does not exit within
            the specified timeout.
        """
        validate_equals_with_retry(
            function_to_execute=lambda: not self.is_bench_running(pid),
            expected_value=True,
            validation_description=f"rbd bench (pid={pid}) has completed",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

        rc_output = self.ssh_connection.send(f"cat {rc_file}")
        rc_text = "".join(rc_output).strip() if isinstance(rc_output, list) else str(rc_output).strip()
        exit_code = int(rc_text) if rc_text.isdigit() else 1
        log_output = self.ssh_connection.send(f"cat {log_file}")
        log_text = "".join(log_output) if isinstance(log_output, list) else str(log_output)
        get_logger().log_info(f"rbd bench (pid={pid}) completed with exit code {exit_code}")
        return CephRbdBenchResult(exit_code, log_text)

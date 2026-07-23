import statistics
import threading
import time
from typing import Dict, List, Optional, Tuple

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.cyclictest.objects.cpu_usage_stats_object import CpuUsageStatsObject


class CyclictestCpuMonitor:
    """Monitors system and process CPU usage during a cyclictest run.

    The monitoring loop runs on an internal daemon thread (composition rather
    than subclassing ``threading.Thread``), matching the framework convention
    used by the keyword layer (e.g. keycloak_mfa_keywords, remote_cli_keywords).
    Use :meth:`start`, :meth:`stop` and :meth:`wait_until_stopped` to control it.
    """

    def __init__(self, ssh_connection: SSHConnection, process_name: str = "cyclictest", interval: int = 30):
        """Initialize the CPU monitor.

        Args:
            ssh_connection (SSHConnection): Active SSH connection to the target host.
            process_name (str): Name of the process to monitor.
            interval (int): Sampling interval in seconds.
        """
        self._ssh_connection = ssh_connection
        self._process_name = process_name
        self._pid: Optional[int] = None
        self._interval = interval
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._system_cpu_usages: List[float] = []
        self._process_cpu_usages: List[float] = []
        self._last_total_cpu_times: Dict[int, float] = {}
        self._last_elapsed_time_secs: Dict[int, float] = {}
        self._clock_ticks: Optional[int] = None

    def get_pid(self) -> Optional[int]:
        """Return the monitored process ID.

        Returns:
            Optional[int]: PID of the monitored process, or None if not set.
        """
        return self._pid

    def set_pid(self, pid: int) -> None:
        """Set the monitored process ID.

        Args:
            pid (int): PID of the cyclictest process to monitor.
        """
        self._pid = pid

    def get_interval(self) -> int:
        """Return the sampling interval in seconds.

        Returns:
            int: Sampling interval in seconds.
        """
        return self._interval

    def get_process_name(self) -> str:
        """Return the name of the monitored process.

        Returns:
            str: Process name.
        """
        return self._process_name

    def start(self) -> None:
        """Start the monitoring loop on an internal daemon thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, name=f"{self._process_name}-cpu-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the monitor thread to stop."""
        self._stop_event.set()

    def wait_until_stopped(self, timeout: Optional[float] = None) -> None:
        """Block until the monitoring thread has finished.

        Args:
            timeout (Optional[float]): Maximum seconds to wait. None waits forever.
        """
        if self._thread is not None:
            self._thread.join(timeout)

    def _is_process_running(self) -> bool:
        """Check whether the monitored process is still alive on the remote host.

        Returns:
            bool: True if the process is running, False otherwise.
        """
        if not self._pid:
            return False
        try:
            output = "".join(self._ssh_connection.send(f"ps --noheadings -o comm -p {self._pid} | xargs"))
            return output.strip() == self._process_name
        except Exception:
            return False

    def _get_system_cpu_times(self) -> Tuple[bool, Optional[List[int]]]:
        """Read aggregate CPU time counters from /proc/stat.

        Returns:
            Tuple[bool, Optional[List[int]]]: (success, list of CPU time values) where
                the list contains the fields from the 'cpu' line of /proc/stat
                (user, nice, system, idle, iowait, …), or None on failure.
        """
        try:
            output = "".join(self._ssh_connection.send("cat /proc/stat | grep 'cpu '"))
            return True, [int(x) for x in output.split()[1:]]
        except Exception as e:
            get_logger().log_warning(f"Failed to get system CPU times: {e}")
            return False, None

    def _calculate_system_cpu_percent(self, prev: List[int], curr: List[int]) -> float:
        """Calculate system-wide CPU utilisation between two /proc/stat snapshots.

        Args:
            prev (List[int]): Previous CPU time counters from /proc/stat.
            curr (List[int]): Current CPU time counters from /proc/stat.

        Returns:
            float: CPU utilisation percentage in the interval [0.0, 100.0].
        """
        prev_idle = prev[3] + prev[4]
        curr_idle = curr[3] + curr[4]
        prev_total = sum(prev)
        curr_total = sum(curr)
        total_diff = curr_total - prev_total
        if total_diff == 0:
            return 0.0
        return 100.0 * (1.0 - (curr_idle - prev_idle) / total_diff)

    def _get_process_cpu_percent(self) -> Tuple[bool, Optional[float]]:
        """Calculate per-thread CPU utilisation for the monitored process.

        Reads /proc/<pid>/task/<tid>/stat for each thread and computes
        CPU usage relative to elapsed wall-clock time since the last sample.

        Returns:
            Tuple[bool, Optional[float]]: (success, average CPU % across all threads),
                or (False, None) if the process is not running or an error occurred.
        """
        if not self._pid or not self._is_process_running():
            return False, None
        try:
            thread_dirs = "".join(self._ssh_connection.send(f"ls -1 /proc/{self._pid}/task/"))
            tids = sorted({int(t) for t in thread_dirs.split() if int(t) != self._pid})
            stat_paths = " ".join(f"/proc/{self._pid}/task/{t}/stat" for t in tids)
            data = "".join(self._ssh_connection.send(f"cat /proc/uptime {stat_paths}"))
            lines = data.strip().splitlines()
            uptime = float(lines[0].split()[0])
            cpu_util: Dict[int, float] = {}
            for line in lines[1:]:
                parts = line.split()
                if not parts:
                    continue
                try:
                    tid = int(parts[0])
                except ValueError:
                    continue
                if tid not in tids:
                    continue
                user_time = int(parts[13]) / self._clock_ticks
                sys_time = int(parts[14]) / self._clock_ticks
                start_secs = int(parts[21]) / self._clock_ticks
                total_cpu = user_time + sys_time
                elapsed = uptime - start_secs
                last_elapsed = self._last_elapsed_time_secs.get(tid, 0)
                last_cpu = self._last_total_cpu_times.get(tid, 0)
                if elapsed - last_elapsed > 0:
                    cpu_util[tid] = (total_cpu - last_cpu) * 100 / (elapsed - last_elapsed)
                self._last_elapsed_time_secs[tid] = elapsed
                self._last_total_cpu_times[tid] = total_cpu
            avg = sum(cpu_util.values()) / len(cpu_util) if cpu_util else 0.0
            return True, avg
        except Exception as e:
            get_logger().log_warning(f"Error fetching process CPU usage: {e}")
            return False, None

    def _monitor_loop(self) -> None:
        """Main monitoring loop (runs on the internal daemon thread)."""
        self._clock_ticks = int("".join(self._ssh_connection.send("getconf CLK_TCK")).strip())
        ok, prev_sys = self._get_system_cpu_times()
        while not self._stop_event.is_set():
            if not self._is_process_running():
                get_logger().log_info("Monitored process no longer running — stopping CPU monitor.")
                break
            proc_ok, proc_pct = self._get_process_cpu_percent()
            if proc_ok:
                self._process_cpu_usages.append(round(proc_pct, 2))
            sys_ok, curr_sys = self._get_system_cpu_times()
            if sys_ok and ok:
                self._system_cpu_usages.append(self._calculate_system_cpu_percent(prev_sys, curr_sys))
                prev_sys = curr_sys
            ok = sys_ok
            time.sleep(self._interval)
        get_logger().log_info(f"CPU monitor stopped — process samples:{len(self._process_cpu_usages)} system samples:{len(self._system_cpu_usages)}")

    def get_all_process_stats(self) -> CpuUsageStatsObject:
        """Return average, median, std_deviation for process CPU usage.

        Returns:
            CpuUsageStatsObject: Process CPU usage statistics.
        """
        data = self._process_cpu_usages
        try:
            return CpuUsageStatsObject(
                average=round(statistics.mean(data), 2),
                median=round(statistics.median(data), 2),
                std_deviation=round(statistics.stdev(data), 2) if len(data) > 1 else 0.0,
            )
        except statistics.StatisticsError:
            return CpuUsageStatsObject(average=0.0, median=0.0, std_deviation=0.0)

    def get_all_system_stats(self) -> CpuUsageStatsObject:
        """Return average, median, std_deviation for system CPU usage.

        Returns:
            CpuUsageStatsObject: System CPU usage statistics.
        """
        data = self._system_cpu_usages
        try:
            return CpuUsageStatsObject(
                average=round(statistics.mean(data), 2),
                median=round(statistics.median(data), 2),
                std_deviation=round(statistics.stdev(data), 2) if len(data) > 1 else 0.0,
            )
        except statistics.StatisticsError:
            return CpuUsageStatsObject(average=0.0, median=0.0, std_deviation=0.0)

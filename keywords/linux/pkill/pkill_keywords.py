import shlex

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class PkillKeywords(BaseKeyword):
    """Keywords for pkill process management."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize pkill keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection for command execution.
        """
        self.ssh_connection = ssh_connection

    def pkill_by_pattern(self, pattern: str, send_as_sudo: bool = False, signal: str = None) -> None:
        """Kill processes matching the specified pattern.

        Args:
            pattern (str): Pattern to match processes against.
            send_as_sudo (bool): Send command as sudo
            signal (str): Optional signal to send (e.g. '9' for SIGKILL, 'TERM'). Defaults to pkill's default (SIGTERM) when None.
        """
        signal_option = f"-{signal} " if signal is not None else ""
        cmd = f"pkill {signal_option}-f {pattern} || true"
        if send_as_sudo:
            self.ssh_connection.send_as_sudo(cmd)
        else:
            self.ssh_connection.send(cmd)

    def start_background_pkill_loop(self, pattern: str, pid_file: str, interval: int = 1, signal: str = None) -> None:
        """Start a detached background loop that continuously kills a matching process.

        Launches a 'setsid' loop on the target host that runs
        'pkill -<signal> -f <pattern>' every 'interval' seconds and never pauses,
        recording its PID in pid_file and its output in '<pid_file>.log'. Because
        the loop runs detached in its own session, the caller can poll status in
        the foreground while the process is being killed without interruption —
        required for fast-respawning processes such as etcd (restarted by systemd
        within about a second). Always pair with stop_background_pkill_loop.

        Args:
            pattern (str): Pattern to match processes against (passed to pkill -f).
            pid_file (str): Remote path where the loop's PID is written for later cleanup. The loop's output is written to '<pid_file>.log'.
            interval (int): Seconds between kills inside the loop.
            signal (str): Optional signal to send (e.g. '9' for SIGKILL). Defaults to SIGTERM when None.
        """
        signal_option = f"-{signal} " if signal is not None else ""
        # Use the non-interactive sudo path: it feeds the sudo password via stdin
        # through exec_command, avoiding the interactive PTY that corrupts long
        # commands (fixed-width line wrapping duplicates characters, e.g.
        # '/binn/etcd'), which silently makes pkill match nothing. The whole
        # command already runs as root via that path, so the loop body does not
        # prefix pkill with sudo. setsid fully detaches the loop into its own
        # session so it survives the SSH exec channel closing (no SIGHUP), and its
        # PID is stored for later cleanup. All interpolated values are shell-quoted
        # and each nesting level is quoted with shlex.quote, so patterns/paths
        # containing spaces or metacharacters cannot break the command.
        log_file = f"{pid_file}.log"
        loop_body = f"while true; do pkill {signal_option}-f {shlex.quote(pattern)}; sleep {interval}; done"
        inner = f"setsid sh -c {shlex.quote(loop_body)} >{shlex.quote(log_file)} 2>&1 & echo $! > {shlex.quote(pid_file)}"
        self.ssh_connection.send_as_sudo_non_interactive(f"sh -c {shlex.quote(inner)}")

    def stop_background_pkill_loop(self, pid_file: str) -> None:
        """Stop a background kill loop started by start_background_pkill_loop.

        Terminates the loop's process group (started via setsid) whose leader PID
        was recorded in pid_file, and removes the pid_file. Best-effort and
        idempotent: does nothing if the file is absent or the process already
        exited.

        Args:
            pid_file (str): Remote path holding the loop's PID (as written by start_background_pkill_loop).
        """
        # kill -<pgid> targets the whole process group created by setsid (the
        # leader PID equals the PGID), so the loop and its child sleep/pkill are
        # all terminated. Non-interactive path avoids PTY echo corruption, and all
        # interpolated paths are shell-quoted. Best-effort: 'test -f' guards a
        # missing file and the trailing 'true' keeps the exit code zero.
        quoted_pid_file = shlex.quote(pid_file)
        quoted_log_file = shlex.quote(f"{pid_file}.log")
        inner = f"test -f {quoted_pid_file} && kill -- -$(cat {quoted_pid_file}) 2>/dev/null; rm -f {quoted_pid_file} {quoted_log_file}; true"
        self.ssh_connection.send_as_sudo_non_interactive(f"sh -c {shlex.quote(inner)}")

    def pkill_by_name(self, process_name: str) -> None:
        """Kill processes by exact process name.

        Args:
            process_name (str): Exact process name to kill.
        """
        cmd = f"pkill {process_name} || true"
        self.ssh_connection.send(cmd)

    def pkill_signal(self, signal: str, process_name: str) -> None:
        """Kill processes by exact process name.

        Args:
            signal (str): Signal to send to process.
            process_name (str): Exact process name to kill.
        """
        cmd = f"pkill -{signal} {process_name} || true"
        self.ssh_connection.send_as_sudo(cmd)

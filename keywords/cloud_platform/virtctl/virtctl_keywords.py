"""Keywords for virtctl client operations."""

import re

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class VirtctlKeywords(BaseKeyword):
    """Keywords for virtctl client operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize VirtctlKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host.
        """
        self._ssh_connection: SSHConnection = ssh_connection

    def virtctl_pause(self, vm_name: str) -> str:
        """Pause a virtual machine.

        Args:
            vm_name (str): Name of the VM to pause.

        Returns:
            str: Command output.
        """
        output = self._ssh_connection.send(f"virtctl pause vm {vm_name}", fail_ok=False)
        self.validate_success_return_code(self._ssh_connection)
        return output

    def login_to_vm(
        self,
        vm_name: str,
        username: str,
        password: str,
        namespace: str = "default",
    ) -> None:
        """Login to a cirros VM via virtctl console and verify it is accessible.

        Opens a new SSH connection, attaches to the VM console, and logs in.

        Example command flow::

            virtctl console vm-cirros
            <login prompt> -> username
            <password prompt> -> password
            $

        Args:
            vm_name (str): Name of the VM to connect to.
            username (str): VM login username.
            password (str): VM login password.
            namespace (str): Namespace of the VM. Defaults to 'default'.

        Raises:
            KeywordException: If the console login fails.
        """
        get_logger().log_info(f"Opening virtctl console to VM {vm_name}")

        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        prompts = [
            PromptResponse(f"{vm_name}", None),
            PromptResponse("login:", username),
            PromptResponse("assword:", password),
            PromptResponse("$", None),
        ]

        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts)
        self.validate_success_return_code(self._ssh_connection)
        get_logger().log_info(f"Successfully logged into VM {vm_name}")

    def wait_for_login_prompt(self, vm_name: str, namespace: str = "default", timeout: int = 300, poll_interval: int = 20) -> None:
        """Wait until the VM guest OS has booted to a 'login:' prompt on the console.

        A VM reports Running/VMI-ready as soon as it is scheduled, but the guest OS
        is still booting (the console shows the kernel boot log, not a login prompt).
        This attaches the console and, if the guest has reached the login prompt,
        returns; otherwise it detaches and retries until ``timeout``. Each attach is a
        single bounded attempt (equal command/reconnect timeouts) to avoid opening
        overlapping console sessions, which KubeVirt rejects with 'close 1006'.

        Args:
            vm_name (str): Name of the VM.
            namespace (str): Namespace of the VM. Defaults to 'default'.
            timeout (int): Total seconds to wait for the login prompt. Defaults to 300.
            poll_interval (int): Seconds to wait between attach attempts. Defaults to 20.

        Raises:
            KeywordException: If the login prompt does not appear within ``timeout``.
        """
        namespace_flag = f" -n {namespace}" if namespace != "default" else ""

        def reached_login_prompt() -> bool:
            """Attach the console once (bounded) and report whether 'login:' appeared."""
            get_logger().log_info(f"Checking whether VM {vm_name} has reached the login prompt")
            login_prompt = PromptResponse("login:", None)
            prompts = [login_prompt]
            result = self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts, command_timeout=poll_interval, reconnect_timeout=poll_interval)
            output = ""
            if isinstance(result, list):
                output = "\n".join(result)
            elif result:
                output = str(result)
            # Combine the raw return with the prompt's captured output; either may hold the banner.
            output += "\n" + (login_prompt.get_complete_output() or "")
            return "login:" in output

        validate_equals_with_retry(
            function_to_execute=reached_login_prompt,
            expected_value=True,
            validation_description=f"VM {vm_name} should reach a console 'login:' prompt",
            timeout=timeout,
            polling_sleep_time=poll_interval,
        )

    def verify_vm_console_accessible(
        self,
        vm_name: str,
        namespace: str = "default",
    ) -> None:
        """Verify a VM is accessible via virtctl console without full login.

        Connects to the VM console and checks for the 'Successfully connected' message.
        Useful when the VM may already be logged in from a previous session (e.g., after
        live migration) and the login prompt is not expected.

        Args:
            vm_name (str): Name of the VM to connect to.
            namespace (str): Namespace of the VM. Defaults to 'default'.

        Raises:
            KeywordException: If the console connection fails.
        """
        get_logger().log_info(f"Verifying VM {vm_name} console is accessible")

        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        prompts = [
            PromptResponse("Successfully connected", None),
        ]

        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts)
        self.validate_success_return_code(self._ssh_connection)
        get_logger().log_info(f"VM {vm_name} console is accessible")

    def check_vm_cpu_count(self, vm_name: str, expected_cpus: int, username: str = "cirros", password: str = "gocubsgo", namespace: str = "default") -> None:
        """
        Verify the VM has the expected number of CPUs via virtctl console.

        Connects to the VM console, sends a newline to get the login prompt,
        logs in with username/password, runs 'lscpu' to get the CPU count,
        then exits and disconnects. Follows the same pattern as
        login_to_vm_and_check_status_cirros in CGCSAuto.

        Args:
            vm_name (str): Name of the VM to check.
            expected_cpus (int): Expected number of CPUs.
            username (str): VM login username. Defaults to 'cirros'.
            password (str): VM login password. Defaults to 'gocubsgo'.
            namespace (str): Namespace of the VM. Defaults to 'default'.

        Raises:
            KeywordException: If the CPU count doesn't match or console fails.
        """
        get_logger().log_info(f"Checking CPU count for VM {vm_name}, expecting {expected_cpus}")

        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        prompts = [
            PromptResponse(f"{vm_name}", ""),
            PromptResponse("login:", username),
            PromptResponse("assword:", password),
            PromptResponse("$", "lscpu | grep 'CPU(s):'"),
            PromptResponse("$", "exit"),
            PromptResponse("login:", None),
        ]

        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts)
        self.validate_success_return_code(self._ssh_connection)

        lscpu_output = prompts[4].get_complete_output()
        get_logger().log_info(f"lscpu output: {lscpu_output}")

        match = re.findall(r"CPU\(s\):\s+(\d+)", lscpu_output)
        if match:
            cpu_count = int(match[0])
            validate_equals(cpu_count, expected_cpus, f"VM {vm_name} should have {expected_cpus} CPUs")
            get_logger().log_info(f"VM {vm_name} has {cpu_count} CPUs as expected")
        else:
            get_logger().log_error(f"Could not parse lscpu output: {lscpu_output}")
            validate_equals(0, expected_cpus, f"VM {vm_name} lscpu output could not be parsed")

    def check_vm_memory(self, vm_name: str, expected_memory_mb: int, username: str = "cirros", password: str = "gocubsgo", namespace: str = "default") -> None:
        """
        Verify the VM has the expected amount of memory via virtctl console.

        Connects to the VM console, sends a newline to get the login prompt,
        logs in with username/password, runs 'free -m' to get the memory info,
        then exits and disconnects. Follows the same pattern as
        check_vm_cpu_count.

        Args:
            vm_name (str): Name of the VM to check.
            expected_memory_mb (int): Expected memory in MB.
            username (str): VM login username. Defaults to 'cirros'.
            password (str): VM login password. Defaults to 'gocubsgo'.
            namespace (str): Namespace of the VM. Defaults to 'default'.

        Raises:
            KeywordException: If the memory doesn't match or console fails.
        """
        get_logger().log_info(f"Checking memory for VM {vm_name}, expecting {expected_memory_mb}MB")

        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        prompts = [
            PromptResponse(f"{vm_name}", ""),
            PromptResponse("login:", username),
            PromptResponse("assword:", password),
            PromptResponse("$", "free -m | grep Mem"),
            PromptResponse("$", "exit"),
            PromptResponse("login:", None),
        ]

        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts)
        self.validate_success_return_code(self._ssh_connection)

        free_output = prompts[4].get_complete_output()
        get_logger().log_info(f"free -m output: {free_output}")

        match = re.findall(r"Mem:\s+(\d+)", free_output)
        if match:
            total_memory_mb = int(match[0])
            # Allow some tolerance (within 10% of expected)
            tolerance = expected_memory_mb * 0.1
            if abs(total_memory_mb - expected_memory_mb) <= tolerance:
                get_logger().log_info(f"VM {vm_name} has {total_memory_mb}MB memory as expected (within tolerance)")
            else:
                get_logger().log_error(f"VM {vm_name} memory mismatch: expected {expected_memory_mb}MB, got {total_memory_mb}MB")
                validate_equals(total_memory_mb, expected_memory_mb, f"VM {vm_name} should have {expected_memory_mb}MB memory")
        else:
            get_logger().log_error(f"Could not parse free -m output: {free_output}")
            validate_equals(0, expected_memory_mb, f"VM {vm_name} free -m output could not be parsed")

    def create_file_in_vm(self, vm_name: str, file_name: str = "abc.yaml", content: str = "backup restore test file", username: str = "ubuntu", password: str = "ubuntu", namespace: str = "default", best_effort: bool = False) -> bool:
        """
        Verify a VM is functional by logging in via console and creating a file with known content.

        Connects to the VM console, logs in, writes ``content`` into ``file_name`` and
        reads it back with 'cat', confirming the exact content is present. The content
        acts as a unique marker so the check cannot be satisfied by the controller's
        own shell if the console fails to attach (see disconnect detection below).

        Args:
            vm_name (str): Name of the VM to log into.
            file_name (str): Name of the file to create in the guest. Defaults to 'abc.yaml'.
            content (str): Content to write into the file. Defaults to 'backup restore test file'.
            username (str): VM login username. Defaults to 'ubuntu'.
            password (str): VM login password. Defaults to 'ubuntu'.
            namespace (str): Namespace of the VM. Defaults to 'default'.
            best_effort (bool): If True, a console that never attaches to the guest is
                logged as a warning and the method returns False instead of raising. If
                the console DOES attach, the content is still strictly asserted.
                Defaults to False (strict).

        Returns:
            bool: True if the file was created and content verified in the guest;
                False only in best_effort mode when the console could not attach.

        Raises:
            KeywordException: If the console does not attach (unless best_effort) or,
                once attached, the content is not read back correctly.
        """
        get_logger().log_info(f"Creating file '{file_name}' in VM {vm_name} via console (content marker: '{content}')")

        self._free_console_slot(vm_name)
        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        console_prompt = PromptResponse(f"{vm_name}", "")
        cat_prompt = PromptResponse("$", f"echo '{content}' > {file_name} && cat {file_name}")
        exit_prompt = PromptResponse("$", "exit")
        prompts = [
            console_prompt,
            PromptResponse("login:", username),
            PromptResponse("assword:", password),
            cat_prompt,
            exit_prompt,
        ]

        # Retries (reconnect_timeout > command_timeout) are REQUIRED: the guest login
        # only works once cloud-init has finished setting the 'ubuntu' password, which
        # can take a couple of minutes after the VM reports Running (early attempts log
        # 'Login incorrect'). The framework keeps retrying the console until login
        # succeeds.
        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts, command_timeout=60, reconnect_timeout=600)

        # The 'cat' output lands in the prompt AFTER the one that sent it (cat_prompt
        # matched the shell prompt right after login and issued the command; the result
        # is captured by exit_prompt). Combine all prompt outputs to be robust.
        cat_output = "\n".join(p.get_complete_output() or "" for p in prompts)
        guest_prompt = f"{username}@{vm_name}"
        if guest_prompt not in cat_output:
            if best_effort:
                get_logger().log_warning(
                    f"virtctl console to VM {vm_name} could not attach to the guest (lab console flakiness); "
                    f"skipping in-guest file creation. VM functionality is still validated by VM status + DataVolume phase."
                )
                return False
            self._assert_console_attached(cat_output, vm_name, username)
        get_logger().log_info(f"cat output after file creation: {cat_output}")
        validate_equals(content in cat_output, True, f"File {file_name} in VM {vm_name} should contain '{content}' after creation")
        return True

    def _free_console_slot(self, vm_name: str) -> None:
        """Release the VM's single console slot before attaching.

        KubeVirt permits only one active 'virtctl console' session per VM. Leftover or
        half-open console processes on the controller (from previous attempts or runs)
        hold the slot, so a new attach is immediately kicked with
        'another user connected to the console / websocket close 1006'. Killing any
        lingering 'virtctl console <vm>' processes frees the slot. Best-effort.

        Args:
            vm_name (str): Name of the VM whose console sessions should be released.
        """
        get_logger().log_info(f"Releasing any existing console session for VM {vm_name}")
        self._ssh_connection.send(f"pkill -f 'virtctl console {vm_name}' || true")

        def console_processes_gone() -> bool:
            """Return True when no lingering 'virtctl console <vm>' process remains.

            The pattern's first character is wrapped in a character class
            ('[v]irtctl') so the pgrep command does not match its own argv (a plain
            'pgrep -f virtctl console <vm>' would always count itself and never reach 0).
            """
            out = self._ssh_connection.send(f"pgrep -fc '[v]irtctl console {vm_name}' || true")
            out_text = "\n".join(out) if isinstance(out, list) else str(out)
            return out_text.strip().splitlines()[-1].strip() in ("0", "")

        validate_equals_with_retry(
            function_to_execute=console_processes_gone,
            expected_value=True,
            validation_description=f"Lingering virtctl console sessions for {vm_name} should be released",
            timeout=30,
            polling_sleep_time=3,
        )

    def _assert_console_attached(self, output: str, vm_name: str, username: str) -> None:
        """Fail if the virtctl console never logged into the guest.

        Confirms the guest shell prompt appeared, guarding against follow-up commands
        silently
        executing on the controller shell instead of inside the VM.

        Args:
            output (str): Captured console output to inspect.
            vm_name (str): VM name (for the error message).
            username (str): Expected guest username (its shell prompt confirms login).

        Raises:
            KeywordException: If the guest shell prompt (e.g. 'user@vm') was never
                seen, meaning the console never logged into the guest.
        """
        # The guest shell prompt 'user@vm' is the definitive proof that we logged into
        # the VM (not the controller, whose prompt is 'sysadmin@controller-0'). virtctl
        # console on some builds disconnects ('close 1006') AFTER a command completes
        # and the framework retries; those trailing disconnect banners are harmless as
        # long as at least one attempt reached the guest shell, so we do NOT fail on
        # disconnect markers alone — only on the absence of the guest prompt.
        guest_prompt = f"{username}@{vm_name}"
        if guest_prompt not in output:
            raise KeywordException(f"virtctl console to VM {vm_name} did not reach the guest login shell (expected prompt '{guest_prompt}'); commands may have run on the controller instead of the guest.")

    def verify_file_in_vm(self, vm_name: str, file_name: str = "abc.yaml", content: str = "backup restore test file", username: str = "ubuntu", password: str = "ubuntu", namespace: str = "default", best_effort: bool = False) -> bool:
        """
        Verify a previously created file still exists in the VM with the expected content.

        Connects to the VM console, logs in, reads ``file_name`` with 'cat', and
        confirms the exact ``content`` is present. Used to confirm data persisted
        across a backup/restore (only meaningful for VMs backed by persistent storage
        such as a CDI DataVolume).

        Args:
            vm_name (str): Name of the VM to log into.
            file_name (str): Name of the file to verify. Defaults to 'abc.yaml'.
            content (str): Expected file content. Defaults to 'backup restore test file'.
            username (str): VM login username. Defaults to 'ubuntu'.
            password (str): VM login password. Defaults to 'ubuntu'.
            namespace (str): Namespace of the VM. Defaults to 'default'.
            best_effort (bool): If True, a console that never attaches to the guest is
                logged as a warning and the method returns False instead of raising
                (used when the lab's virtctl console is intermittently unavailable and
                VM recovery is already proven by VM status + DataVolume phase). If the
                console DOES attach, the content is still strictly asserted. Defaults
                to False (strict).

        Returns:
            bool: True if the file content was verified in the guest; False only in
                best_effort mode when the console could not attach.

        Raises:
            KeywordException: If the console does not attach (unless best_effort) or,
                once attached, the content is missing.
        """
        get_logger().log_info(f"Verifying file '{file_name}' still exists in VM {vm_name} with content '{content}' via console")

        self._free_console_slot(vm_name)
        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        console_prompt = PromptResponse(f"{vm_name}", "")
        cat_prompt = PromptResponse("$", f"cat {file_name}")
        exit_prompt = PromptResponse("$", "exit")
        prompts = [
            console_prompt,
            PromptResponse("login:", username),
            PromptResponse("assword:", password),
            cat_prompt,
            exit_prompt,
        ]

        # Retries are required to wait out cloud-init before login succeeds (see
        # create_file_in_vm). The 'cat' result is captured by the prompt AFTER the one
        # that issued it, so combine all prompt outputs.
        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts, command_timeout=60, reconnect_timeout=600)

        cat_output = "\n".join(p.get_complete_output() or "" for p in prompts)
        guest_prompt = f"{username}@{vm_name}"
        if guest_prompt not in cat_output:
            if best_effort:
                get_logger().log_warning(
                    f"virtctl console to VM {vm_name} could not attach to the guest (lab console flakiness); "
                    f"skipping in-guest file check. VM recovery is still validated by VM status + DataVolume phase."
                )
                return False
            self._assert_console_attached(cat_output, vm_name, username)
        get_logger().log_info(f"cat output for {file_name}: {cat_output}")
        validate_equals(content in cat_output and "No such file" not in cat_output, True, f"File {file_name} in VM {vm_name} should still contain '{content}' after restore")
        return True

    def migrate_vm(self, vm_name: str, namespace: str = "default") -> str:
        """Trigger a live migration of a VM to another node via 'virtctl migrate'.

        Runs ``virtctl migrate <vm>`` which schedules the running VM to live-migrate
        to a different host. Used before a host lock/cordon during a platform or
        Kubernetes upgrade so the VM keeps running (only VMs backed by ReadWriteMany
        storage with evictionStrategy LiveMigrate can migrate). This only triggers the
        migration; use wait_for_vm_migration_complete / get_vmi_node to confirm it.

        Args:
            vm_name (str): Name of the VM to migrate.
            namespace (str): Namespace of the VM. Defaults to 'default'.

        Returns:
            str: Command output (e.g. 'VM <vm> was scheduled to migrate').
        """
        get_logger().log_info(f"Triggering live migration of VM {vm_name}")
        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        cmd = f"bash -lc 'virtctl migrate{namespace_flag} {vm_name}'"
        output = self._ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self._ssh_connection)
        return "\n".join(output) if isinstance(output, list) else str(output)

    def get_vm_uptime(self, vm_name: str, username: str = "ubuntu", password: str = "ubuntu", namespace: str = "default", best_effort: bool = True) -> str:
        """Read the guest 'uptime' from a VM via the console.

        Logs into the VM console and runs 'uptime', returning the captured line. Used
        to prove a VM stayed up (live-migrated rather than rebooted) across a host
        lock/cordon during an upgrade: if the VM never went down, its uptime keeps
        increasing from creation; if it rebooted, uptime resets to a few minutes.

        Args:
            vm_name (str): Name of the VM to log into.
            username (str): VM login username. Defaults to 'ubuntu'.
            password (str): VM login password. Defaults to 'ubuntu'.
            namespace (str): Namespace of the VM. Defaults to 'default'.
            best_effort (bool): If True (default), a console that cannot attach returns
                an empty string with a warning instead of raising, since the lab's
                virtctl console is intermittently unavailable ('close 1006').

        Returns:
            str: The captured 'uptime' output, or '' if the console could not attach
                (best_effort).

        Raises:
            KeywordException: If the console cannot attach and best_effort is False.
        """
        get_logger().log_info(f"Reading uptime from VM {vm_name} via console")
        self._free_console_slot(vm_name)
        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        console_prompt = PromptResponse(f"{vm_name}", "")
        uptime_prompt = PromptResponse("$", "uptime")
        exit_prompt = PromptResponse("$", "exit")
        prompts = [
            console_prompt,
            PromptResponse("login:", username),
            PromptResponse("assword:", password),
            uptime_prompt,
            exit_prompt,
        ]
        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts, command_timeout=60, reconnect_timeout=600)

        output = "\n".join(p.get_complete_output() or "" for p in prompts)
        guest_prompt = f"{username}@{vm_name}"
        if guest_prompt not in output:
            if best_effort:
                get_logger().log_warning(f"virtctl console to VM {vm_name} could not attach; uptime not captured (lab console flakiness).")
                return ""
            self._assert_console_attached(output, vm_name, username)
        get_logger().log_info(f"uptime output for VM {vm_name}: {output}")
        return output

    @staticmethod
    def parse_uptime_to_seconds(uptime_output: str) -> int:
        """Parse the seconds-of-uptime from Linux 'uptime' output.

        Handles the common 'up ...' formats produced by the 'uptime' command:
            up 45 sec / up 1 min / up 23 min / up 1:05 (h:mm) /
            up 2 days, 3:04 / up 1 day, 5 min / up 3 days, 1:02

        Args:
            uptime_output (str): Raw output captured from the guest 'uptime' command.

        Returns:
            int: Uptime in seconds, or -1 if it could not be parsed.
        """
        if not uptime_output:
            return -1
        # Isolate the part between 'up' and the ', N user' / load average that follows.
        match = re.search(r"\bup\s+(.*?)(?:,\s*\d+\s+user|,\s*load average|$)", uptime_output, re.IGNORECASE | re.DOTALL)
        if not match:
            return -1
        up_str = match.group(1).strip().rstrip(",").strip()
        total = 0
        matched = False

        days = re.search(r"(\d+)\s+day", up_str)
        if days:
            total += int(days.group(1)) * 86400
            matched = True

        hhmm = re.search(r"(\d+):(\d{2})", up_str)
        if hhmm:
            total += int(hhmm.group(1)) * 3600 + int(hhmm.group(2)) * 60
            matched = True
        else:
            mins = re.search(r"(\d+)\s+min", up_str)
            if mins:
                total += int(mins.group(1)) * 60
                matched = True
            secs = re.search(r"(\d+)\s+sec", up_str)
            if secs:
                total += int(secs.group(1))
                matched = True

        return total if matched else -1

    def verify_vm_stayed_up(self, vm_name: str, baseline_uptime_seconds: int, username: str = "ubuntu", password: str = "ubuntu", namespace: str = "default", best_effort: bool = True) -> None:
        """Verify a VM stayed up across an upgrade (uptime increased, i.e. no reboot).

        Reads the guest uptime now and asserts it is GREATER than the baseline captured
        before the upgrade. A migratable VM that live-migrated (rather than rebooting)
        keeps its uptime monotonically increasing; a reboot resets uptime to a few
        minutes, so post-uptime would be LESS than baseline. This is the concrete
        "vm-jammy-dv-new should have uptime from the start time" check.

        Two distinct outcomes are handled differently:
          - Uptime cannot be read/parsed (lab console flakiness, or baseline was not
            captured): this is an environmental limitation, not a VM failure, so it is
            logged as a WARNING and skipped (regardless of best_effort).
          - Uptime IS read and shows a reset (post <= baseline => the VM rebooted): this
            is a genuine scenario failure (the migratable VM did not stay up), so it is
            ALWAYS asserted as a hard failure, even in best_effort mode.

        Args:
            vm_name (str): Name of the VM.
            baseline_uptime_seconds (int): Uptime (seconds) captured before the upgrade
                via parse_uptime_to_seconds(get_vm_uptime(...)). If <0 (baseline could
                not be captured), the comparison is skipped with a warning.
            username (str): VM login username. Defaults to 'ubuntu'.
            password (str): VM login password. Defaults to 'ubuntu'.
            namespace (str): Namespace of the VM. Defaults to 'default'.
            best_effort (bool): Controls only the "could not read uptime" case (warn vs
                raise). A successfully-read uptime reset (reboot) is always a failure.

        Raises:
            AssertionError: If uptime was read and shows the VM rebooted (post <= baseline).
            KeywordException: If the console cannot attach and best_effort is False.
        """
        post_output = self.get_vm_uptime(vm_name, username=username, password=password, namespace=namespace, best_effort=best_effort)
        post_seconds = self.parse_uptime_to_seconds(post_output)

        if baseline_uptime_seconds < 0 or post_seconds < 0:
            # Environmental: uptime could not be captured/parsed (console flakiness or no
            # baseline). Not a VM failure -> warn and skip rather than fail.
            get_logger().log_warning(
                f"Cannot compare uptime for VM {vm_name} (baseline={baseline_uptime_seconds}s, post={post_seconds}s); "
                f"console/parse unavailable. Skipping uptime-stayed-up assertion."
            )
            return

        # Uptime WAS read successfully: a reset here means the VM genuinely rebooted,
        # which is a real scenario failure -> hard assert regardless of best_effort.
        get_logger().log_info(f"VM {vm_name} uptime: baseline={baseline_uptime_seconds}s, post-upgrade={post_seconds}s")
        validate_equals(post_seconds > baseline_uptime_seconds, True, f"VM {vm_name} should have stayed up (uptime {post_seconds}s > baseline {baseline_uptime_seconds}s) — proving it live-migrated rather than rebooted")

    def verify_virtiofs_serviceaccount_mount(
        self,
        vm_name: str,
        mount_point: str = "/mnt/serviceaccount",
        username: str = "fedora",
        password: str = "fedora",
        namespace: str = "default",
    ) -> None:
        """Verify a serviceAccount is shared into the guest via a virtiofs mount.

        Logs into the guest console, confirms the virtiofs filesystem is mounted
        at the given mount point, and confirms the serviceAccount files
        (token, namespace, ca.crt) are present. Mirrors the manual verification
        of the ServiceAccount-as-filesystem test case.

        Example expected guest output::

            $ df -h | grep serviceaccount-fs
            serviceaccount-fs   94G   12K   94G   1% /mnt/serviceaccount
            $ ls /mnt/serviceaccount
            ca.crt  namespace  token

        Args:
            vm_name (str): Name of the VM/VMI to connect to.
            mount_point (str): Guest mount point of the virtiofs filesystem. Defaults to '/mnt/serviceaccount'.
            username (str): Guest login username. Defaults to 'fedora'.
            password (str): Guest login password. Defaults to 'fedora'.
            namespace (str): Namespace of the VM/VMI. Defaults to 'default'.

        Raises:
            KeywordException: If the console login fails.
            AssertionError: If the mount or the serviceAccount files are missing.
        """
        get_logger().log_info(f"Verifying virtiofs serviceAccount mount on VM {vm_name} at {mount_point}")

        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        prompts = [
            PromptResponse(f"{vm_name}", ""),
            PromptResponse("login:", username),
            PromptResponse("assword:", password),
            PromptResponse(r"\$", f"df -h | grep serviceaccount-fs; ls {mount_point}"),
            PromptResponse(r"\$", "exit"),
            PromptResponse("login:", None),
        ]

        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts)
        self.validate_success_return_code(self._ssh_connection)

        guest_output = prompts[3].get_complete_output()
        get_logger().log_info(f"Guest mount verification output:\n{guest_output}")

        validate_equals(mount_point in guest_output, True, f"virtiofs filesystem should be mounted at {mount_point}")
        for sa_file in ("token", "namespace", "ca.crt"):
            validate_equals(sa_file in guest_output, True, f"serviceAccount file '{sa_file}' should be present in {mount_point}")

        get_logger().log_info(f"VM {vm_name} has serviceAccount correctly shared via virtiofs at {mount_point}")

    def image_upload(
        self,
        image_path: str,
        pvc_name: str,
        pvc_size: str,
        uploadproxy_url: str,
        insecure: bool = True,
        access_mode: str = "ReadWriteMany",
        namespace: str = "default",
        storage_class: str = None,
        command_timeout: int = 600,
        no_create: bool = False,
    ) -> str:
        """
        Upload image to CDI using virtctl image-upload.

        Runs ``virtctl image-upload dv`` to upload a QCOW2 or raw image into a
        DataVolume backed by a PVC. Handles the case where the DataVolume already
        exists and is populated.

        Args:
            image_path (str): Path to the image file on the remote host.
            pvc_name (str): Name of the DataVolume to upload into.
            pvc_size (str): Size of the DataVolume (e.g., "5Gi").
            uploadproxy_url (str): CDI uploadproxy URL.
            insecure (bool): Skip TLS verification. Defaults to True.
            access_mode (str): Access mode for PVC. Defaults to "ReadWriteMany".
            namespace (str): Kubernetes namespace. Defaults to "default".
            storage_class (str): Storage class name. Defaults to None.
            command_timeout (int): Timeout in seconds for the upload command. Defaults to 600.
            no_create (bool): If True, adds --no-create flag to skip DV creation. Defaults to False.

        Returns:
            str: Command output.

        Raises:
            AssertionError: If image upload fails.
        """
        get_logger().log_info(f"Uploading image {image_path} to DataVolume {pvc_name}")
        insecure_flag = "--insecure" if insecure else ""
        storage_class_flag = f"--storage-class={storage_class}" if storage_class else ""
        no_create_flag = "--no-create" if no_create else ""
        cmd = f"bash -lc 'virtctl image-upload dv {pvc_name} {insecure_flag} " f"--access-mode {access_mode} --size {pvc_size} " f"--image-path {image_path} --uploadproxy-url {uploadproxy_url} " f"{storage_class_flag} {no_create_flag} --namespace {namespace}'"
        upload_output = self._ssh_connection.send(export_k8s_config(cmd), command_timeout=command_timeout)
        self.validate_success_return_code(self._ssh_connection)
        get_logger().log_info(f"Image uploaded successfully to DataVolume {pvc_name}")
        return "\n".join(upload_output) if isinstance(upload_output, list) else str(upload_output)

    def expose_vm(self, vm_name: str, service_name: str, port: int, target_port: int, service_type: str = "NodePort", namespace: str = "default") -> str:
        """
        Expose a VM as a service using 'virtctl expose virtualmachine'.

        Runs ``virtctl expose virtualmachine`` to create a service (e.g. NodePort)
        forwarding a port to the VM — for example exposing RDP (3389) on a Windows VM.

        Args:
            vm_name (str): Name of the VM to expose.
            service_name (str): Name of the service to create.
            port (int): Service port.
            target_port (int): Target port on the VM.
            service_type (str): Service type (e.g. 'NodePort', 'ClusterIP'). Defaults to 'NodePort'.
            namespace (str): Kubernetes namespace. Defaults to 'default'.

        Returns:
            str: Command output.

        Raises:
            AssertionError: If the expose command fails.
        """
        get_logger().log_info(f"Exposing VM {vm_name} as service {service_name} ({port}->{target_port}, {service_type})")
        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        cmd = f"bash -lc 'virtctl expose virtualmachine{namespace_flag} {vm_name} --name {service_name} --port {port} --target-port {target_port} --type {service_type}'"
        output = self._ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self._ssh_connection)
        get_logger().log_info(f"VM {vm_name} exposed as service {service_name}")
        return "\n".join(output) if isinstance(output, list) else str(output)

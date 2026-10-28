"""IPMI SOL serial-console keywords for local-site subcloud operations.

Drives a subcloud serial console over IPMI SOL to power reset the node, select
the "Local Factory Restore" GRUB entry, and wait for the factory restore to
boot to a login prompt.
"""

import re
import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.base_keyword import BaseKeyword
from keywords.bmc.ipmitool.bmc_credentials import resolve_bmc_credentials
from keywords.bmc.ipmitool.chassis.power.ipmitool_chassis_power_keywords import IPMIToolChassisPowerKeywords

from config.configuration_manager import ConfigurationManager

# GRUB arrow-key escape sequences sent over the serial console. Down/Up move the
# highlighted entry; Enter boots the highlighted entry.
GRUB_KEY_DOWN = "\x1b[B"
GRUB_KEY_UP = "\x1b[A"
GRUB_KEY_ENTER = "\r"
# Marker printed by the BIOS just before the GRUB menu is drawn on the serial
# console. Seeing it tells us the menu is (about to be) on screen.
BIOS_SERIAL_CONSOLE_MARKER = "For access via BIOS Serial Console"
# Plain-text anchor that GRUB prints as the menu header, BEFORE the ANSI/ncurses
# menu box is drawn. This is far more reliable to wait on than any entry text,
# which is rendered inside the escape-sequence-positioned box.
GRUB_MENU_ANCHOR = "GNU GRUB"
# First plain-text evidence that GRUB (as opposed to earlier BIOS output) is
# about to draw its menu. "GNU" is the leading token of the "GNU GRUB" header,
# so matching it lets us send a halt keystroke on the FIRST menu byte, before
# the full header (let alone the ANSI menu box) has finished arriving. This is
# the critical change for the autoboot-countdown race: the old code waited for
# the full "GNU GRUB" match (potentially a whole 5s read window late) before
# sending any key, by which time GRUB had often already auto-booted the default.
GRUB_FIRST_EVIDENCE_TOKENS = ("GNU", "GRUB")
# Known, fixed menu order for the local factory restore image. Entry 0 is the
# default-highlighted entry; "Local Factory Restore" is entry index 2.
GRUB_FACTORY_RESTORE_INDEX = 2
# Regex that strips ANSI/VT100 escape sequences (CSI "\x1b[...<final>") so the
# raw serial stream can be matched as plain text.
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
# Default per-read window (seconds) when draining the serial console channel.
_CONSOLE_READ_WINDOW = 5
# Tight continuous-reader poll interval (seconds). Much smaller than the old
# 0.2s drain sleep so a pre-armed reader catches the GRUB menu's first byte with
# minimal latency rather than up to a full read-window late.
_TIGHT_POLL_INTERVAL = 0.02
# Inter-keystroke delay (seconds) when navigating the GRUB menu. Long enough for
# GRUB to register the key and redraw, short enough not to burn countdown time.
_GRUB_INTERKEY_DELAY = 0.4
# How long (seconds) to wait for GRUB to redraw after a keystroke before giving
# up on seeing the moved highlight.
_GRUB_REDRAW_WINDOW = 2
# Substrings ipmitool prints when there is no active SOL payload to deactivate.
# These make a `sol deactivate` a successful no-op rather than a failure, so
# setup pre-clean and teardown are idempotent.
_SOL_ALREADY_DEACTIVATED_MARKERS = ("already de-activated", "SOL payload already de-activated")
# Plain-text markers that prove the DEFAULT StarlingX entry booted (i.e. the
# factory-restore selection was MISSED). Seen in the post-GRUB boot output when
# the autoboot countdown expired before navigation landed. These are kept
# DISTINCT from the factory-restore boot: generic kernel strings like "ostree"
# and "vmlinuz-" were removed because the Local Factory Restore entry boots its
# own ostree/vmlinuz kernel too, so matching them wrongly classified a genuine
# factory-restore HIT as a MISS (which then power-reset the node mid-restore).
_DEFAULT_BOOT_MARKERS = ("Loading StarlingX", "Loading Starling")
# Positive evidence that the "Local Factory Restore" entry booted (a HIT): the
# factory-restore kernel is launched with the factory backup install paths /
# kickstart that the default StarlingX boot never uses. Presence of ANY of these
# in the post-Enter output means the factory restore is underway.
_FACTORY_RESTORE_BOOT_MARKERS = (
    "platform_backup:factory",
    "platform-backup/factory",
    "factory/26",
    "ostree_repo",
    "miniboot.cfg",
    "onsite_restore",
    "install ks",
)


class IpmitoolSolConsoleKeywords(BaseKeyword):
    """Drives a subcloud serial console over IPMI SOL for local-site operations.

    The console session is an ``ipmitool ... sol activate`` process launched on
    the automation host (localhost) through an ACE SSH connection, driven via a
    paramiko ``invoke_shell`` channel. This is the same interactive-channel
    primitive the framework uses in ``SSHConnection._send_expect_prompts``; no
    external expect library is used.

    SOL is an exclusive single-session payload. Callers must run
    :meth:`sol_deactivate` in test teardown (and optionally at setup) so a stale
    session never blocks the next ``sol activate``; that method is idempotent and
    non-fatal.

    The BMC connection details (IP, user, password) are read from the lab
    configuration for the target subcloud controller, never hardcoded.
    """

    def __init__(self, subcloud_name: str, host_name: str = "controller-0"):
        """Initialize the SOL console keyword for a subcloud controller.

        Args:
            subcloud_name (str): Name of the target subcloud (as defined in the
                lab config) whose controller BMC the console attaches to.
            host_name (str): Controller whose BMC to target. Defaults to
                "controller-0" (simplex subcloud).

        Raises:
            ValueError: If the BMC IP for the target controller is not set.
        """
        self.subcloud_name = subcloud_name
        self.host_name = host_name
        subcloud_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
        node = subcloud_config.get_node(host_name)
        # Reuse the shared BMC credential resolver (node creds with subcloud-level
        # password fallback + IP validation) so this logic is not duplicated.
        bmc = resolve_bmc_credentials(node, password_fallback_config=subcloud_config)
        self.bm_ip = bmc.get_bm_ip()
        self.bm_username = bmc.get_bm_username()
        self.bm_password = bmc.get_bm_password()
        self.local_ssh = SSHConnectionManager.create_local_ssh()
        self.channel = None
        # Monotonic time (time.monotonic()) of the most recent power reset, used
        # to timestamp GRUB events relative to the reset for latency analysis.
        self._power_reset_at = None
        # Rolling buffer of raw bytes seen by the pre-armed continuous reader
        # since it was last armed. Kept so GRUB navigation can check the '*'
        # marker against everything seen, not a one-shot read.
        self._reader_buffer = ""

    def _log_timed_event(self, event: str) -> None:
        """Log a GRUB/boot event with elapsed time since the last power reset.

        Used for latency analysis of the autoboot-countdown race (e.g. how long
        after the menu appears the first halt keystroke is sent). When no power
        reset has been recorded yet, the elapsed value is omitted.

        Args:
            event (str): Short description of the event being timestamped.
        """
        if self._power_reset_at is not None:
            elapsed = time.monotonic() - self._power_reset_at
            get_logger().log_info(f"[t+{elapsed:7.3f}s since power reset] {event}")
        else:
            get_logger().log_info(f"[t+  ?.???s since power reset] {event}")

    def sol_deactivate(self) -> None:
        """Deactivate any active SOL session for this BMC (idempotent, non-fatal).

        Runs ``ipmitool ... sol deactivate`` on the local host. SOL is an
        exclusive single-session payload, so this is run both at setup (to clear a
        stale session from a previous aborted run) and in teardown (so the next
        run can activate). When there is no active session ipmitool returns
        non-zero with an "already de-activated" message; that is treated as
        success so setup/teardown never fail on it.
        """
        get_logger().log_info(f"Deactivating any SOL session for {self.subcloud_name} ({self.bm_ip})")
        try:
            output = self.local_ssh.send(f"ipmitool -I lanplus -H {self.bm_ip} -U {self.bm_username} -P {self.bm_password} sol deactivate")
        except Exception as deactivate_error:
            get_logger().log_warning(f"SOL deactivate encountered a non-fatal error: {deactivate_error}")
            self.channel = None
            return
        output_str = output if isinstance(output, str) else "\n".join(output)
        if self.local_ssh.get_return_code() != 0 and not any(marker in output_str for marker in _SOL_ALREADY_DEACTIVATED_MARKERS):
            # Non-zero without the "already de-activated" marker is still only a
            # warning: teardown must never fail the test on a cleanup step.
            get_logger().log_warning(f"SOL deactivate returned non-zero for {self.subcloud_name} ({self.bm_ip}): {output_str}")
        self.channel = None

    def activate(self) -> None:
        """Open the SOL console session on the local host.

        Clears any stale session first (best-effort), then launches
        ``ipmitool ... sol activate`` through a paramiko ``invoke_shell`` channel
        and waits for the SOL session banner.

        Raises:
            KeywordException: If the SOL session banner is not seen in time.
        """
        get_logger().log_info(f"Activating IPMI SOL console for {self.subcloud_name}/{self.host_name} ({self.bm_ip})")
        # Best-effort pre-clean of any stale session left by an aborted run.
        self.sol_deactivate()
        self.channel = self.local_ssh.client.invoke_shell()
        self._send_line(f"ipmitool -I lanplus -H {self.bm_ip} -U {self.bm_username} -P {self.bm_password} sol activate")
        if not self._wait_for_text("SOL Session operational", timeout=60):
            raise KeywordException(f"Failed to activate SOL console for {self.subcloud_name} ({self.bm_ip}).")
        get_logger().log_info("SOL console session is operational.")

    def power_reset(self) -> None:
        """Reset the target controller's power via IPMI.

        Runs ``ipmitool ... power reset`` on the local host (independent of the
        open SOL channel) so the node reboots into GRUB. ACE's existing power
        keywords only wrap on/off/cycle, so reset is issued here.

        Raises:
            KeywordException: If the ipmitool power reset command fails.
        """
        get_logger().log_info(f"Power resetting {self.subcloud_name}/{self.host_name} ({self.bm_ip}) via IPMI")
        # Delegate to the shared localhost power path in IPMIToolChassisPowerKeywords
        # (reset_from_localhost), so the ipmitool power invocation is not
        # duplicated here. host_name=None skips its lab-level credential
        # derivation; the subcloud controller's BMC is resolved via subcloud_name.
        IPMIToolChassisPowerKeywords(self.local_ssh, None).reset_from_localhost(self.host_name, subcloud_name=self.subcloud_name)
        # Anchor subsequent GRUB timing deltas to the moment of the reset.
        self._power_reset_at = time.monotonic()
        self._log_timed_event("power reset sent")

    def wait_for_bios_serial_console(self, timeout: int = 1200) -> None:
        """Wait for the BIOS serial-console marker that precedes the GRUB menu.

        This is only an early milestone on the way to GRUB. The authoritative
        GRUB anchor is handled by :meth:`wait_for_grub_menu`.

        Args:
            timeout (int): Maximum time in seconds to wait for the marker.

        Raises:
            KeywordException: If the marker is not seen within the timeout.
        """
        get_logger().log_info(f"Waiting for '{BIOS_SERIAL_CONSOLE_MARKER}' on the serial console")
        if not self._wait_for_text(BIOS_SERIAL_CONSOLE_MARKER, timeout=timeout):
            raise KeywordException(f"'{BIOS_SERIAL_CONSOLE_MARKER}' not seen within {timeout}s for {self.subcloud_name}.")
        get_logger().log_info("BIOS serial console reached; the GRUB menu should be drawn shortly.")

    def wait_for_grub_menu(self, timeout: int = 600) -> None:
        """Wait for the first GRUB menu byte and IMMEDIATELY halt its countdown.

        The GRUB autoboot-countdown race is the core problem this method solves:
        if we wait for the full "GNU GRUB" header (or the ANSI menu box) to be
        fully parsed before sending a key, GRUB can auto-boot the default entry
        in the meantime and the keystroke lands in the already-booting kernel.

        So this uses a pre-armed, tight-loop continuous reader and sends a halt
        keystroke on the FIRST plain-text menu evidence ("GNU"/"GRUB" token),
        BEFORE the full header is matched and before any menu parsing. Every raw
        byte read is captured with ``repr()`` and timestamped so the transcript
        shows exactly how long after reset the menu appeared and the exact
        latency from menu-appearance to the halt keystroke.

        Args:
            timeout (int): Maximum time in seconds to wait for GRUB evidence.

        Raises:
            KeywordException: If no GRUB menu evidence is seen within timeout.
        """
        get_logger().log_info(f"Pre-armed continuous reader waiting for first GRUB evidence {GRUB_FIRST_EVIDENCE_TOKENS} on the serial console")
        # Arm the rolling buffer fresh for this attempt.
        self._reader_buffer = ""
        deadline = time.time() + timeout
        first_byte_logged = False
        while time.time() < deadline:
            chunk = self._read_available()
            if chunk:
                if not first_byte_logged:
                    self._log_timed_event("first menu byte seen")
                    first_byte_logged = True
                self._log_raw_bytes("grub-pre-halt", chunk)
                self._reader_buffer += chunk
                haystack = self._strip_ansi(self._reader_buffer)
                if any(token in haystack for token in GRUB_FIRST_EVIDENCE_TOKENS):
                    menu_appear_at = time.monotonic()
                    self._log_timed_event(f"GRUB menu matched ({GRUB_FIRST_EVIDENCE_TOKENS})")
                    # IMMEDIATE halt keystroke on first evidence, BEFORE parsing
                    # the menu. Any arrow key stops the countdown; Down then Up
                    # leaves the highlight on the default (top) entry so the
                    # subsequent positional navigation is predictable.
                    self._send_raw(GRUB_KEY_DOWN)
                    halt_at = time.monotonic()
                    self._log_timed_event("first halt keystroke sent (Down)")
                    get_logger().log_info(f"CRITICAL LATENCY menu-appear -> first halt keystroke: {halt_at - menu_appear_at:.3f}s")
                    time.sleep(_GRUB_INTERKEY_DELAY)
                    self._reader_buffer += self._read_window(_GRUB_REDRAW_WINDOW, tag="grub-after-halt-down")
                    self._send_raw(GRUB_KEY_UP)
                    self._log_timed_event("halt keystroke sent (Up, back to default)")
                    time.sleep(_GRUB_INTERKEY_DELAY)
                    self._reader_buffer += self._read_window(_CONSOLE_READ_WINDOW, tag="grub-after-halt-up")
                    return
            else:
                time.sleep(_TIGHT_POLL_INTERVAL)
        raise KeywordException(f"GRUB menu evidence {GRUB_FIRST_EVIDENCE_TOKENS} not seen within {timeout}s for {self.subcloud_name}.")

    def select_grub_entry(self, entry_label: str, target_index: int = GRUB_FACTORY_RESTORE_INDEX, max_correction_presses: int = 6) -> bool:
        """Navigate the GRUB menu to a known entry, verifying after each Down.

        The highlighted entry is marked with a leading '*' on the serial console.
        Rather than sending a blind run of Down keystrokes and only checking at
        the end, this sends ONE Down at a time and RE-READS the '*' position
        after each (against the accumulated reader buffer, ANSI-stripped), so a
        dropped or extra keystroke is caught immediately. Enter is sent ONLY when
        the ANSI-stripped buffer shows ``*<entry_label>``. Every keystroke and
        redraw is captured with ``repr()`` and timestamped for the transcript.

        Args:
            entry_label (str): The GRUB entry text to select (e.g.
                "Local Factory Restore").
            target_index (int): Zero-based index of the entry from the top.
            max_correction_presses (int): Safety cap on extra Down presses used
                when the highlight has not yet reached the target.

        Returns:
            bool: True if '*' was confirmed on ``entry_label`` and Enter sent;
                False if the highlight could not be confirmed (caller decides
                whether to retry with a power reset).
        """
        get_logger().log_info(f"Selecting GRUB entry '{entry_label}' (fixed index {target_index}); verifying '*' after each Down")
        # The autoboot halt already captured the initial draw into the reader
        # buffer. Fold in anything still pending before the first Down.
        self._reader_buffer += self._read_window(_GRUB_REDRAW_WINDOW, tag="grub-pre-nav")

        # Already on the target? (e.g. target_index 0, or the halt left it there.)
        if self._highlight_in_buffer(self._reader_buffer, entry_label):
            get_logger().log_info(f"'*' already confirmed in front of '{entry_label}' before navigation; booting it.")
            return self._boot_confirmed_entry(entry_label)

        # One Down at a time, re-reading the '*' position after every keystroke.
        total_presses = target_index + max_correction_presses
        for press in range(1, total_presses + 1):
            self._send_raw(GRUB_KEY_DOWN)
            self._log_timed_event(f"Down #{press} sent")
            time.sleep(_GRUB_INTERKEY_DELAY)
            self._reader_buffer += self._read_window(_GRUB_REDRAW_WINDOW, tag=f"grub-after-down-{press}")
            star_pos = self._highlighted_entry_text(self._reader_buffer)
            get_logger().log_info(f"After Down #{press}: '*' now in front of -> {star_pos!r}")
            if self._highlight_in_buffer(self._reader_buffer, entry_label):
                get_logger().log_info(f"'*' confirmed in front of '{entry_label}' after {press} Down press(es); booting it.")
                return self._boot_confirmed_entry(entry_label)

        snapshot = re.sub(r"\s+", " ", self._strip_ansi(self._reader_buffer))
        get_logger().log_warning(f"Could not confirm '*' highlight on GRUB entry '{entry_label}' for {self.subcloud_name} after {total_presses} Down press(es). Buffer tail: {snapshot[-1500:]!r}")
        return False

    def _boot_confirmed_entry(self, entry_label: str) -> bool:
        """Send Enter to boot the confirmed-highlighted entry and log evidence.

        Args:
            entry_label (str): The entry confirmed highlighted (for the log).

        Returns:
            bool: Always True (the entry was confirmed before this is called).
        """
        self._log_grub_highlight_evidence(self._reader_buffer, entry_label)
        self._send_raw(GRUB_KEY_ENTER)
        self._log_timed_event("Enter sent (boot selected entry)")
        return True

    def boot_local_factory_restore_with_retries(self, entry_label: str, max_attempts: int = 4) -> None:
        """Select the factory-restore GRUB entry, retrying on a missed selection.

        Orchestrates the full GRUB handling with a power-reset retry loop: wait
        for the menu (halt-key-first), navigate to the entry with per-Down
        verification, then classify HIT vs MISS. On a MISS, capture the
        post-GRUB boot output that proves the default booted, power reset, and
        try again (bounded by ``max_attempts``). The per-attempt timing and raw
        byte transcript are produced regardless of the final outcome.

        Args:
            entry_label (str): The GRUB entry to select.
            max_attempts (int): Maximum GRUB selection attempts (power resets).

        Raises:
            KeywordException: If the entry could not be selected within the
                attempt budget.
        """
        for attempt in range(1, max_attempts + 1):
            get_logger().log_info(f"===== GRUB selection attempt {attempt}/{max_attempts} for '{entry_label}' =====")
            if attempt > 1:
                # Retry: power reset to get back to GRUB quickly.
                self.power_reset()
            self.wait_for_bios_serial_console()
            self.wait_for_grub_menu()
            confirmed = self.select_grub_entry(entry_label)
            if confirmed and self._confirm_selection_hit(entry_label):
                self._log_timed_event(f"HIT: '{entry_label}' selected on attempt {attempt}")
                get_logger().log_info(f"GRUB selection HIT for '{entry_label}' on attempt {attempt}.")
                return
            self._log_timed_event(f"MISS on attempt {attempt}")
            get_logger().log_warning(f"GRUB selection MISS for '{entry_label}' on attempt {attempt}; capturing default-boot evidence before retry.")
            self._capture_missed_selection_evidence()
        raise KeywordException(f"Could not select GRUB entry '{entry_label}' for {self.subcloud_name} within {max_attempts} attempts.")

    def _confirm_selection_hit(self, entry_label: str) -> bool:
        """Classify whether the factory restore booted (HIT) or the default did (MISS).

        After Enter, reads the post-GRUB boot output and classifies it using
        POSITIVE factory-restore evidence first, because both the factory restore
        and the default StarlingX entry boot an ostree/vmlinuz kernel - so the
        generic kernel strings cannot tell them apart. Only the factory restore
        boots with the factory backup install paths / kickstart
        (:data:`_FACTORY_RESTORE_BOOT_MARKERS`).

        Classification order:
          1. Any factory-restore marker present -> HIT (restore is underway).
          2. Else a default-boot marker present -> MISS (default StarlingX
             booted; the selection was missed).
          3. Else inconclusive -> treated as a MISS so the retry loop re-attempts
             rather than proceeding against an unverified boot.

        This fixes a false MISS where a genuine factory-restore boot (showing
        'ostree'/'vmlinuz-') was classified as the default and the node was
        power-reset mid-restore.

        Args:
            entry_label (str): The entry that was supposed to boot.

        Returns:
            bool: True if the factory restore appears to have booted.
        """
        post = self._read_window(_CONSOLE_READ_WINDOW * 3, tag="post-enter")
        self._reader_buffer += post
        stripped = self._strip_ansi(post)
        factory_markers = [marker for marker in _FACTORY_RESTORE_BOOT_MARKERS if marker in stripped]
        if factory_markers:
            get_logger().log_info(f"Post-Enter output shows factory-restore boot markers {tuple(factory_markers)} -> HIT (restore underway).")
            return True
        booted_default = any(marker in stripped for marker in _DEFAULT_BOOT_MARKERS)
        if booted_default:
            get_logger().log_warning(f"Post-Enter output shows default-boot markers {_DEFAULT_BOOT_MARKERS} and no factory-restore markers -> MISS.")
            return False
        get_logger().log_warning("Post-Enter output shows neither factory-restore nor default-boot markers; treating as MISS so the selection is retried.")
        return False

    def _capture_missed_selection_evidence(self) -> None:
        """Capture post-GRUB output proving the default booted after a MISS."""
        evidence = self._read_window(_CONSOLE_READ_WINDOW * 2, tag="miss-default-boot-evidence")
        self._log_raw_bytes("miss-default-boot-evidence", evidence)

    def wait_for_login_prompt(self, timeout: int = 1800) -> None:
        """Wait for the node to reach a login prompt after factory restore.

        The GRUB "Local Factory Restore" path runs a factory install first, so
        this can take a while; the default timeout is 30 minutes.

        Args:
            timeout (int): Maximum time in seconds to wait for the login prompt.
                Defaults to 1800 (30 minutes).

        Raises:
            KeywordException: If no login prompt appears within the timeout.
        """
        get_logger().log_info("Waiting up to 30 minutes for the node to reach a login prompt after factory restore")
        if not self._wait_for_text("login:", timeout=timeout):
            raise KeywordException(f"Login prompt not reached within {timeout}s for {self.subcloud_name}.")
        get_logger().log_info("Login prompt reached; factory restore has booted to login.")

    def _send_line(self, text: str) -> None:
        """Send a command line (text + newline) on the SOL channel.

        Args:
            text (str): The command text to send.
        """
        self._send_raw(f"{text}\n")

    def _send_raw(self, data: str) -> None:
        """Send raw characters (no appended newline) on the SOL channel.

        Args:
            data (str): Raw characters to write to the channel.

        Raises:
            KeywordException: If the SOL channel has not been activated.
        """
        if self.channel is None:
            raise KeywordException("SOL console channel is not active; call activate() first.")
        while not self.channel.send_ready():
            time.sleep(0.009)
        self.channel.send(data)

    def _drain(self, timeout: int) -> str:
        """Read whatever is currently available on the SOL channel.

        Args:
            timeout (int): Seconds to keep reading before returning.

        Returns:
            str: The decoded console output read during the window.
        """
        buffer = ""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.channel is not None and self.channel.recv_ready():
                chunk = self.channel.recv(8192).decode("utf-8", errors="ignore")
                buffer += chunk
                get_logger().log_info(chunk.replace("\r", "").rstrip())
            else:
                time.sleep(0.2)
        return buffer

    def _read_available(self) -> str:
        """Non-blocking read of whatever is currently on the SOL channel.

        Returns immediately (no sleep) with any bytes currently buffered, or an
        empty string if nothing is ready. The caller's tight polling loop paces
        itself via ``_TIGHT_POLL_INTERVAL``; this method must not block so the
        GRUB menu's first byte is caught with minimal latency.

        Returns:
            str: The decoded console output currently available (possibly empty).
        """
        if self.channel is not None and self.channel.recv_ready():
            return self.channel.recv(8192).decode("utf-8", errors="ignore")
        time.sleep(_TIGHT_POLL_INTERVAL)
        return ""

    def _log_raw_bytes(self, tag: str, data: str) -> None:
        """Log raw console bytes with ``repr()`` for the diagnostic transcript.

        Escape sequences and control characters are preserved (via ``repr``) so
        the transcript shows exactly what arrived on the wire around the GRUB
        menu - essential for diagnosing the ANSI/ncurses menu and the autoboot
        countdown race.

        Args:
            tag (str): Short label identifying the capture point.
            data (str): The raw decoded bytes to log.
        """
        if data:
            get_logger().log_info(f"[raw:{tag}] {data!r}")

    def _read_window(self, timeout: int, tag: str = "read") -> str:
        """Read the SOL channel for a fixed window, logging the raw bytes.

        Thin wrapper over :meth:`_drain` that also emits the raw-byte transcript
        under ``tag`` so each GRUB redraw/navigation step is captured verbatim.

        Args:
            timeout (int): Seconds to keep reading before returning.
            tag (str): Short label identifying this capture point in the logs.

        Returns:
            str: The decoded console output read during the window.
        """
        data = self._drain(timeout=timeout)
        self._log_raw_bytes(tag, data)
        return data

    def _highlighted_entry_text(self, buffer: str) -> str:
        """Return the GRUB menu entry text currently marked with ``*``.

        GRUB marks the highlighted entry with a leading ``*`` inside the ncurses
        menu box, and redraws the whole menu (re-emitting every ``*``/unmarked
        line) on each keystroke. The authoritative "current" highlight is
        therefore the ``*``-prefixed entry in the LAST (most recent) redraw.

        GRUB positions each line with cursor-movement escapes rather than real
        newlines, so after ANSI stripping the ``*entry`` token is not reliably at
        the start of a split line (that is why the old per-line ``re.match``
        returned ''). This instead finds the LAST ``*<entry text>`` token
        anywhere in the ANSI-stripped, whitespace-collapsed buffer and returns
        the entry text immediately following that marker, truncated at the next
        menu entry / box boundary.

        Args:
            buffer (str): The accumulated raw serial buffer to inspect.

        Returns:
            str: The highlighted entry's text, or an empty string if none found.
        """
        # Preserve runs of spaces (do NOT collapse to single spaces): GRUB pads
        # each entry with multiple trailing spaces, and that padding is the
        # boundary used to cut the highlighted entry from the next one.
        stripped = self._strip_ansi(buffer).replace("|", " ")
        stripped = re.sub(r"[^\S ]+", " ", stripped)  # turn tabs/newlines into single spaces, keep space runs
        # Each '*' immediately precedes the highlighted entry text. Take the LAST
        # one (most recent redraw). The entry text ends at the next '*' (next
        # marker in this or a later frame) or a run of 2+ spaces (column padding
        # separating it from the following entry) - whichever comes first.
        matches = list(re.finditer(r"\*\s*([^*]+)", stripped))
        if not matches:
            return ""
        last_text = matches[-1].group(1)
        last_text = re.split(r"\s{2,}", last_text, maxsplit=1)[0]
        return last_text.strip()

    def _wait_for_text(self, text: str, timeout: int, strip_ansi: bool = False) -> bool:
        """Poll the SOL console until the given text appears or time runs out.

        Args:
            text (str): Substring to wait for in the console output.
            timeout (int): Maximum time in seconds to wait.
            strip_ansi (bool): When True, ANSI/VT100 escape sequences are removed
                from the accumulated buffer before matching, so text drawn inside
                an ncurses box (like the GRUB menu) can be found.

        Returns:
            bool: True if the text appeared within the timeout; False otherwise.
        """
        deadline = time.time() + timeout
        accumulated = ""
        while time.time() < deadline:
            accumulated += self._drain(timeout=_CONSOLE_READ_WINDOW)
            haystack = self._strip_ansi(accumulated) if strip_ansi else accumulated
            if text in haystack:
                return True
            # Keep only the tail to bound memory on very long installs.
            accumulated = accumulated[-8192:]
        return False

    def _strip_ansi(self, text: str) -> str:
        """Strip ANSI/VT100 escape sequences from serial console text.

        The GRUB menu is drawn with cursor-positioning and color escape
        sequences; removing them exposes the plain entry text (including the
        leading '*' highlight marker) for matching.

        Args:
            text (str): Raw console text possibly containing escape sequences.

        Returns:
            str: The text with ANSI escape sequences removed.
        """
        return _ANSI_ESCAPE_RE.sub("", text.replace("\r", ""))

    def _highlight_in_buffer(self, buffer: str, entry_label: str) -> bool:
        """Check whether the CURRENT GRUB highlight is on the target entry.

        GRUB marks the highlighted entry with a leading '*' and redraws the whole
        menu on each keystroke, so the accumulated buffer contains many frames
        with the '*' in different positions. A buffer-wide ``*<label>`` regex
        therefore gives false positives: a stale earlier frame (or a wrapped
        redraw) where '*' happened to precede the label matches even when the
        LIVE highlight sits on a different (default) entry. That false positive
        caused the test to press Enter while the default was still highlighted,
        booting the default (observed as a MISS on every attempt).

        This instead resolves the single entry the '*' sits in front of in the
        most recent redraw (via :meth:`_highlighted_entry_text`) and checks that
        it matches ``entry_label``. The comparison is case-insensitive and allows
        ``entry_label`` to be a prefix of the resolved entry (GRUB pads entry
        text with trailing spaces), but it will NOT match when the current
        highlight is on another entry.

        Args:
            buffer (str): Accumulated raw console output to inspect.
            entry_label (str): The entry text to check (e.g. "Local Factory
                Restore"). A partial such as "Factory Restore" also works.

        Returns:
            bool: True only if the current highlight is on ``entry_label``.
        """
        current = self._highlighted_entry_text(buffer)
        if not current:
            return False
        current_norm = re.sub(r"\s+", " ", current).strip().casefold()
        label_norm = re.sub(r"\s+", " ", entry_label).strip().casefold()
        return current_norm == label_norm or current_norm.startswith(label_norm)

    def _log_grub_highlight_evidence(self, buffer: str, entry_label: str) -> None:
        """Log the ANSI-stripped menu line that confirms the '*' highlight.

        Captures evidence of which entry was highlighted when Enter was pressed,
        for the test transcript.

        Args:
            buffer (str): Accumulated raw console output that matched.
            entry_label (str): The entry text that was confirmed highlighted.
        """
        collapsed = re.sub(r"\s+", " ", self._strip_ansi(buffer))
        match = re.search(r"\*\s*" + re.escape(entry_label), collapsed, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 5)
            get_logger().log_info(f"GRUB highlight evidence (ANSI-stripped): {collapsed[start:match.end() + 5]!r}")

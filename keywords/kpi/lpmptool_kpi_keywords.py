"""Keywords for running the native lpmptool binary to calculate KPI timings.

This module provides an alternative to LogPatternKpiKeywords by installing and
running the lpmptool .deb package directly on the target system. The native tool
reads log files locally and performs pattern matching using a YAML model file,
which is more efficient than parsing logs over SSH from Python.
"""

import re
import time
from typing import List, Optional

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.kpi.kpi_result import KpiResult

# Resource paths (relative to starlingx repo root)
LPMPTOOL_DEB_RESOURCE = "resources/cloud_platform/kpi/tools/lpmp_1.0-1.stx.0_amd64.deb"
UNLOCK_MODEL_RESOURCE = "resources/cloud_platform/kpi/unlock_model.yaml"

# Remote paths on the controller
REMOTE_DEB_PATH = "/home/sysadmin/lpmp_1.0-1.stx.0_amd64.deb"
REMOTE_MODEL_PATH = "/home/sysadmin/unlock_model.yaml"

# lpmptool result row: "<delta>  <host>  <label>  <file>.log  <data>"
ROW_RE = re.compile(r"^(?P<delta>[0-9?]{2}:[0-9?]{2}:[0-9?]{2}\.[0-9?]{3})\s+(?P<host>\S+)\s+(?P<label>.+?)\s+(?P<log>\S+\.log\S*)\s+(?P<data>.*)$")
# Pair blocks end with ": <n>s", optionally followed by the matched stop pattern in brackets.
DURATION_RE = re.compile(r":\s*([0-9]+(?:\.[0-9]+)?)s(?:\s+\[.*\])?\s*$")
DELTA_RE = re.compile(r"^(\d+):(\d{2}):(\d{2}(?:\.\d+)?)$")
# Blocks that are part of the model but not reported as unlock KPI phases.
EXCLUDED_LABELS = ["LOCK HOST"]


class LpmptoolKpiKeywords(BaseKeyword):
    """Keywords for calculating KPI using the native lpmptool CLI utility.

    This installs the lpmptool .deb on the target, uploads a KPI model YAML,
    and runs the tool on-host. It is an alternative to the pure-Python
    LogPatternKpiKeywords engine.

    Workflow:
        1. Upload the .deb package to the controller
        2. Unlock ostree and install the package
        3. Upload the model YAML file
        4. Run lpmptool with the desired start time and model
        5. Parse and return results
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize LpmptoolKpiKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target controller.
        """
        self.ssh_connection = ssh_connection

    def install_lpmptool(self) -> None:
        """Upload and install the lpmptool .deb package on the target system.

        Steps:
            1. Upload the .deb file to the controller
            2. Run ostree admin unlock to allow package installation
            3. Install the .deb package with dpkg
        """
        get_logger().log_info("Installing lpmptool on target system")

        file_keywords = FileKeywords(self.ssh_connection)
        local_deb_path = get_stx_resource_path(LPMPTOOL_DEB_RESOURCE)
        file_keywords.upload_file(local_deb_path, REMOTE_DEB_PATH, overwrite=True)
        get_logger().log_info(f"Uploaded lpmptool .deb to {REMOTE_DEB_PATH}")

        get_logger().log_info("Running ostree admin unlock")
        self.ssh_connection.send_as_sudo("ostree admin unlock")

        get_logger().log_info("Installing lpmptool .deb package")
        output = self.ssh_connection.send_as_sudo(f"dpkg -i {REMOTE_DEB_PATH}")
        get_logger().log_info(f"dpkg install output: {''.join(output)}")

    def upload_model(self, model_resource: str = UNLOCK_MODEL_RESOURCE, remote_path: str = REMOTE_MODEL_PATH) -> str:
        """Upload the KPI model YAML file to the target system.

        Args:
            model_resource (str): Local resource path to the model YAML file.
            remote_path (str): Remote destination path on the controller.

        Returns:
            str: The remote path where the model was uploaded.
        """
        file_keywords = FileKeywords(self.ssh_connection)
        local_model_path = get_stx_resource_path(model_resource)
        file_keywords.upload_file(local_model_path, remote_path, overwrite=True)
        get_logger().log_info(f"Uploaded model to {remote_path}")
        return remote_path

    def calculate_kpi(self, start_time: str, model_path: str = REMOTE_MODEL_PATH, loops: int = 1) -> List[str]:
        """Run lpmptool once to calculate KPI timings.

        Args:
            start_time (str): Start time in ISO format (e.g., "2026-05-20T10:00:20").
            model_path (str): Remote path to the model YAML file on the controller.
            loops (int): Number of loops to run (default: 1).

        Returns:
            List[str]: Raw output lines from lpmptool.
        """
        cmd = f"lpmptool -s {start_time} -m {model_path} -n {loops}"
        get_logger().log_info(f"Running lpmptool: {cmd}")

        output = self.ssh_connection.send_as_sudo(cmd)

        if output:
            get_logger().log_info("=== lpmptool Raw Output ===")
            for line in output:
                get_logger().log_info(f"  {line.rstrip()}")
        else:
            get_logger().log_info("lpmptool returned no output")

        return output if output else []

    @staticmethod
    def has_missing_blocks(output: List[str]) -> bool:
        """Check whether lpmptool reported any REQUIRED block as not found.

        lpmptool distinguishes required from optional blocks by severity:
            - A REQUIRED block that is not found is reported as an Error:
                "Error: block 'K8s STARTUP PHASE' stop pattern ... not found in ..."
            - An OPTIONAL block that is not found is reported as a Warn:
                "Warn: block 'test-service-no-pvc ready' stop pattern ... not found in ..."

        Only a missing REQUIRED block (Error) means we should keep retrying.
        Missing OPTIONAL blocks (Warn) are expected - e.g. the PVC test-service
        blocks when the PVC pod is not installed - and are ignored.

        Args:
            output (List[str]): Raw output lines from lpmptool.

        Returns:
            bool: True if at least one required block is still missing (Error present).
        """
        for line in output:
            if not line:
                continue
            # An Error line for a not-found block means a REQUIRED block is missing.
            if "Error:" in line and "not found" in line:
                return True
        return False

    def calculate_kpi_until_complete(self, start_time: str, model_path: str = REMOTE_MODEL_PATH, loops: int = 1, timeout: int = 300, poll_interval: int = 15) -> List[str]:
        """Run lpmptool repeatedly until every REQUIRED block is found or timeout.

        Rather than pre-waiting for a specific log line, this treats lpmptool as
        the source of truth: it re-runs the tool while any REQUIRED block is
        reported as an Error/"not found" (e.g. the final K8s STARTUP PHASE stop
        line that is written only after pod recovery completes). Warnings for
        optional blocks are ignored, so a missing PVC test-service (when the PVC
        pod is not installed) does not cause a failure. Once all required blocks
        are found, the output is returned. If the timeout is reached with required
        blocks still missing, a TimeoutError is raised so the test fails.

        Args:
            start_time (str): Start time in ISO format (e.g., "2026-05-20T10:00:20").
            model_path (str): Remote path to the model YAML file on the controller.
            loops (int): Number of loops per lpmptool run (default: 1).
            timeout (int): Maximum total time in seconds to keep retrying. Defaults to 300.
            poll_interval (int): Seconds to wait between retries. Defaults to 15.

        Returns:
            List[str]: Raw output lines from the successful lpmptool run.

        Raises:
            TimeoutError: If lpmptool still reports missing required blocks after the timeout.
        """
        end_time = time.time() + timeout
        attempt = 0
        last_output: List[str] = []

        while time.time() < end_time:
            attempt += 1
            get_logger().log_info(f"lpmptool attempt {attempt} (retrying until all required blocks are found, timeout={timeout}s)")
            last_output = self.calculate_kpi(start_time, model_path, loops)

            if last_output and not self.has_missing_blocks(last_output):
                get_logger().log_info(f"lpmptool found all required blocks on attempt {attempt}")
                return last_output

            get_logger().log_info(f"lpmptool still reports missing required blocks, retrying in {poll_interval}s")
            time.sleep(poll_interval)

        raise TimeoutError(f"lpmptool did not find all required blocks within {timeout}s ({attempt} attempts)")

    def parse_and_display_results(self, results: List[str]) -> None:
        """Log lpmptool results line by line for visibility in the test report.

        Args:
            results (List[str]): Raw output lines from lpmptool.
        """
        for line in results:
            if line and line.strip():
                get_logger().log_info(line.rstrip())
        get_logger().log_info(f"lpmptool output: {len(results)} lines")

    def parse_results(self, raw_output: List[str], hostname: str) -> List[KpiResult]:
        """Parse lpmptool output into KpiResult objects.

        Each result row has the form "<delta>  <host>  <label>  <file>.log  <data>".
        Pair blocks report their duration at the end of the data column
        ("Start -> Stop: ...: 45.1s"). Pattern-only blocks (e.g. Kubelet startup)
        have no duration, so the Delta column is used. Rows for blocks that were
        not found, and excluded labels such as LOCK HOST, are skipped.

        Args:
            raw_output (List[str]): Raw output lines from lpmptool.
            hostname (str): Hostname of the unlocked host.

        Returns:
            List[KpiResult]: Parsed KPI phases with label and duration.
        """
        kpi_results = []
        for line in raw_output:
            if not line or not line.strip():
                continue
            row = ROW_RE.match(line.strip())
            if not row:
                continue
            label = row.group("label").strip()
            if label in EXCLUDED_LABELS:
                continue
            duration_seconds = self._get_row_duration(row.group("delta"), row.group("data"))
            if duration_seconds is None:
                continue
            kpi_results.append(KpiResult(label, duration_seconds, hostname))

        get_logger().log_info(f"Parsed {len(kpi_results)} KPI phases from lpmptool output")
        return kpi_results

    def _get_row_duration(self, delta: str, data: str) -> Optional[float]:
        """Get the duration in seconds for one lpmptool row.

        Args:
            delta (str): Delta(HH:MM:SS.mmm) column.
            data (str): Data column.

        Returns:
            Optional[float]: Duration in seconds, or None if the block was not found.
        """
        duration_match = DURATION_RE.search(data)
        if duration_match:
            return float(duration_match.group(1))
        if "Start -> Stop" not in data:
            clock = DELTA_RE.match(delta)
            if clock:
                return int(clock.group(1)) * 3600 + int(clock.group(2)) * 60 + float(clock.group(3))
        return None

    def setup_and_calculate_kpi(self, start_time: str, loops: int = 1, model_resource: str = UNLOCK_MODEL_RESOURCE, retry_until_complete: bool = True, timeout: int = 300, poll_interval: int = 15) -> List[str]:
        """Full workflow: install lpmptool, upload model, and calculate KPI.

        By default, lpmptool is re-run until it reports every block found or the
        timeout expires. This handles the final unlock phase (K8s STARTUP PHASE),
        whose stop line is written to the logs only after pod recovery completes -
        typically a few minutes after all pods report Running.

        Args:
            start_time (str): Start time in ISO format (e.g., "2026-05-20T10:00:20").
            loops (int): Number of loops per lpmptool run (default: 1).
            model_resource (str): Local resource path to the model YAML file.
            retry_until_complete (bool): If True, re-run lpmptool until all blocks
                are found or the timeout is hit. If False, run once. Defaults to True.
            timeout (int): Max seconds to keep retrying lpmptool. Defaults to 300.
            poll_interval (int): Seconds between retries. Defaults to 15.

        Returns:
            List[str]: Raw output lines from lpmptool.

        Raises:
            TimeoutError: If retry_until_complete is True and blocks are still
                missing after the timeout.
        """
        self.install_lpmptool()
        remote_model = self.upload_model(model_resource)

        if retry_until_complete:
            # lpmptool reports missing REQUIRED blocks as Error and missing OPTIONAL
            # blocks as Warn, so the retry loop keys off Error lines only - no need
            # to inspect the model for optional labels.
            return self.calculate_kpi_until_complete(start_time, remote_model, loops, timeout=timeout, poll_interval=poll_interval)

        return self.calculate_kpi(start_time, remote_model, loops)

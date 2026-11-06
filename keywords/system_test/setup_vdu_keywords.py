"""VDU (Virtual Deployment Unit) Setup Keywords.

Provides reusable methods for downloading VDU test data and running
the install scripts on system test labs.
"""

import time

from config.system_test.objects.vdu_config import VduConfig
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class SetupVduKeywords:
    """Keywords for setting up VDU workload on labs.

    Downloads VDU test data from a remote server and runs the install scripts
    to deploy images, apps, and VDU workloads.

    Args:
        ssh_connection: SSH connection to the target host (central cloud or subcloud).
    """

    # Test-data folders whose install.sh runs in each mode, in execution order.
    MODE_FOLDERS = {
        "vdu_only": ["vdu"],
        "stx_apps": ["stx-apps"],
        "all_data": ["cpu-metrics", "stx-apps", "vdu"],
    }

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection
        self.file_keywords = FileKeywords(ssh_connection)

    def __str__(self) -> str:
        return "SetupVduKeywords"

    def deploy_vdu(self, fail_ok_override: bool = None, mode_override: str = None) -> None:
        """Download VDU test data and run the install scripts for the mode set in the config.

        The mode is the VDU_MODE value in default_vdu.json5 (vdu_only, stx_apps or all_data).

        Args:
            fail_ok_override: If provided, overrides the fail_ok value from config.
                              Useful for DC deployments where the SC should always be fail_ok=True.
            mode_override: If provided, overrides the VDU_MODE value from config.
                           Useful for DC deployments where the SC only needs stx_apps.

        Raises:
            ValueError: If the mode is not a valid install mode.
        """
        vdu_config = self._load_vdu_config()
        mode = mode_override or vdu_config.get_vdu_mode()
        if mode not in self.MODE_FOLDERS:
            raise ValueError(f"Invalid VDU install mode '{mode}'. Expected one of {list(self.MODE_FOLDERS)}.")

        destination = vdu_config.get_destination_path()
        if mode == "stx_apps":
            # The full test-data folder is 5+ GB, so this mode downloads only its own folder
            subfolder, scripts_dir = "stx-apps", destination
        else:
            subfolder, scripts_dir = None, f"{destination}/test-data"

        get_logger().log_info(f"Deploying VDU test data (mode={mode})")
        self._download_vdu_files(vdu_config, subfolder=subfolder)
        self._run_install_script(vdu_config, mode, scripts_dir, fail_ok_override=fail_ok_override)

    def _load_vdu_config(self) -> VduConfig:
        """Load the VDU configuration from the config file.

        Returns:
            VduConfig: VDU configuration object.
        """
        config_path = get_stx_resource_path("config/system_test/files/default_vdu.json5")
        get_logger().log_info(f"Loading VDU config from: {config_path}")
        return VduConfig(config_path)

    def _download_vdu_files(self, vdu_config: VduConfig, subfolder: str = None) -> None:
        """Download VDU test data from the remote server.

        The test-data folder can be large (5+ GB) and may take several minutes to copy.
        Use subfolder to download only a specific directory (e.g. 'stx-apps').

        Args:
            vdu_config: VDU configuration object.
            subfolder: If provided, only download this subfolder from test-data.
        """
        server = vdu_config.get_server()
        base_path = vdu_config.get_base_path()
        destination = vdu_config.get_destination_path()
        download_timeout = vdu_config.get_download_timeout()

        if subfolder:
            remote_path = f"{base_path}/{subfolder}/"
            local_path = f"{destination}/{subfolder}/"
        else:
            remote_path = f"{base_path}/"
            local_path = f"{destination}/test-data/"

        get_logger().log_info(f"Downloading VDU files from {server}:{remote_path} (timeout={download_timeout}s)")

        self.file_keywords.rsync_from_remote_server(
            remote_server=server,
            remote_user=vdu_config.get_user(),
            remote_password=vdu_config.get_password(),
            remote_path=remote_path,
            local_dest_path=local_path,
            recursive=True,
            command_timeout=download_timeout,
        )

        get_logger().log_info(f"VDU files downloaded to {local_path}")

    def _run_install_script(self, vdu_config: VduConfig, mode: str, scripts_dir: str, fail_ok_override: bool = None) -> None:
        """Run the install scripts for the selected mode.

        The scripts take 10-15 minutes to complete. They load container images,
        push them to the local registry, optionally upload and apply platform apps,
        and deploy VDU workloads. Output is redirected to a log file and
        monitored periodically.

        Args:
            vdu_config: VDU configuration object.
            mode: One of vdu_only, stx_apps, all_data.
            scripts_dir: Directory on the lab that holds the downloaded install folders.
            fail_ok_override: If provided, overrides the fail_ok value from config.
        """
        fail_ok = fail_ok_override if fail_ok_override is not None else vdu_config.get_fail_ok()
        log_file = f"{scripts_dir}/install.log"
        rc_file = f"{log_file}.rc"

        steps = []
        for folder in self.MODE_FOLDERS[mode]:
            self.file_keywords.make_executable(f"{scripts_dir}/{folder}/install.sh")
            steps.append(f"cd {scripts_dir}/{folder} && ./install.sh" + (" -i" if folder == "vdu" else ""))
        get_logger().log_info(f"Executing install steps {steps} (output: {log_file})")

        # Source openrc and set KUBECONFIG so kubectl/system commands have proper auth context
        install_cmd = f"source /etc/platform/openrc && export KUBECONFIG=/etc/kubernetes/admin.conf && {'; '.join(steps)}"

        # Launch script in background, write exit code to .rc file when done
        self.ssh_connection.send(f"rm -f {rc_file}")
        self.ssh_connection.send(f"nohup bash -c '({install_cmd}) > {log_file} 2>&1; echo $? > {rc_file}' </dev/null >/dev/null 2>&1 &")

        rc = self._monitor_install_progress(log_file, rc_file, timeout=1200, interval=60)

        get_logger().log_info(f"Script output saved to: {log_file}")
        get_logger().log_info(f"Script exit code: {rc}")

        # Log the last 30 lines of the install log for visibility
        tail_output = self.ssh_connection.send(f"tail -30 {log_file} 2>/dev/null")
        get_logger().log_info(f"[install final output]\n{tail_output}")

        if not fail_ok:
            validate_equals(0, rc, f"script failed, check log output in {log_file}")

            get_logger().log_info("Verifying VDU pods reach Running state in default namespace (timeout=300s)")
            KubectlGetPodsKeywords(self.ssh_connection).wait_for_pods_to_reach_status(
                expected_status=["Running", "Completed"],
                namespace="default",
                timeout=300,
            )
            get_logger().log_info("All VDU pods are in Running state")

    def _monitor_install_progress(self, log_file: str, rc_file: str, timeout: int, interval: int) -> int:
        """Monitor the install script by checking for the rc file and tailing the log.

        The script writes its exit code to rc_file when it finishes.
        This method polls every `interval` seconds until the rc_file appears
        or the timeout is reached.

        Args:
            log_file: Path to the install log file.
            rc_file: Path to the exit code file (created when script finishes).
            timeout: Maximum time to wait in seconds.
            interval: Time between checks in seconds.

        Returns:
            int: Exit code of the script (0 = success).
        """
        elapsed = 0
        while elapsed < timeout:
            time.sleep(interval)
            elapsed += interval

            # Print last 10 lines of the log for progress visibility
            tail_output = self.ssh_connection.send(f"tail -10 {log_file} 2>/dev/null")
            get_logger().log_info(f"[install progress]\n{tail_output}")

            # Check if rc file exists (script finished)
            if self.file_keywords.file_exists(rc_file):
                get_logger().log_info(f"Install finished after {elapsed}s")
                return self._read_exit_code(rc_file)

            get_logger().log_info(f"Install still running... ({elapsed}s elapsed)")

        get_logger().log_warning(f"Install monitoring timed out after {timeout}s")
        return 1

    def _read_exit_code(self, rc_file: str) -> int:
        """Read the exit code from the rc file.

        Args:
            rc_file: Path to the file containing the exit code.

        Returns:
            int: Exit code (0 = success, non-zero = failure).
        """
        output = self.ssh_connection.send(f"cat {rc_file}")
        return int(output[0].strip())

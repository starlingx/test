"""VDU (Virtual Deployment Unit) Setup Keywords.

Provides reusable methods for downloading VDU test data and running
the install_all.sh script on system test labs.
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

    Downloads VDU test data from a remote server and runs the install script
    to deploy images, apps, and VDU workloads.

    Args:
        ssh_connection: SSH connection to the target host (central cloud or subcloud).
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection
        self.file_keywords = FileKeywords(ssh_connection)

    def __str__(self) -> str:
        return "SetupVduKeywords"

    def deploy_vdu(self, fail_ok_override: bool = None, stx_apps_only: bool = False) -> None:
        """Download VDU test data and run the install script.

        Downloads the test-data folder from the configured server,
        then runs install_all.sh -i to deploy VDU workloads.

        Args:
            fail_ok_override: If provided, overrides the fail_ok value from config.
                              Useful for DC deployments where the SC should always be fail_ok=True.
            stx_apps_only: If True, only run stx-apps/install.sh (upload/apply platform apps).
                           Useful for system controller where only app images are needed.
        """
        vdu_config = self._load_vdu_config()

        if stx_apps_only:
            get_logger().log_info("Downloading stx-apps folder only (SC mode)")
            self._download_vdu_files(vdu_config, subfolder="stx-apps")
        else:
            get_logger().log_info("Downloading full VDU test data")
            self._download_vdu_files(vdu_config)

        get_logger().log_info("Running install scripts")
        self._run_install_script(vdu_config, fail_ok_override=fail_ok_override, stx_apps_only=stx_apps_only)

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
        user = vdu_config.get_user()
        password = vdu_config.get_password()
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
            remote_user=user,
            remote_password=password,
            remote_path=remote_path,
            local_dest_path=local_path,
            recursive=True,
            command_timeout=download_timeout,
        )

        get_logger().log_info(f"VDU files downloaded to {local_path}")

    def _run_install_script(self, vdu_config: VduConfig, fail_ok_override: bool = None, stx_apps_only: bool = False) -> None:
        """Run the install scripts.

        The scripts take 10-15 minutes to complete. They load container images,
        push them to the local registry, upload and apply platform apps,
        and deploy VDU workloads. Output is redirected to a log file and
        monitored periodically.

        Args:
            vdu_config: VDU configuration object.
            fail_ok_override: If provided, overrides the fail_ok value from config.
            stx_apps_only: If True, only run stx-apps/install.sh.
        """
        destination = vdu_config.get_destination_path()
        fail_ok = fail_ok_override if fail_ok_override is not None else vdu_config.get_fail_ok()
        if stx_apps_only:
            log_file = f"{destination}/stx-apps/install.log"
        else:
            log_file = f"{destination}/test-data/install_all.log"
        rc_file = f"{log_file}.rc"

        self.ssh_connection.send(f"rm -f {rc_file}")

        # Launch script in background, write exit code to .rc file when done
        # Source openrc and set KUBECONFIG so kubectl/system commands have proper auth context
        # Pass -i to each sub-script individually since install_all.sh doesn't forward args
        if stx_apps_only:
            script_path = f"{destination}/stx-apps/install.sh"
            get_logger().log_info(f"Making script executable: {script_path}")
            self.file_keywords.make_executable(script_path)

            get_logger().log_info(f"Executing: stx-apps/install.sh only (output: {log_file})")
            install_cmd = (
                f"source /etc/platform/openrc && export KUBECONFIG=/etc/kubernetes/admin.conf && "
                f"cd {destination}/stx-apps && ./install.sh"
            )
        else:
            script_path = f"{destination}/test-data/install_all.sh"
            get_logger().log_info(f"Making script executable: {script_path}")
            self.file_keywords.make_executable(script_path)

            get_logger().log_info(f"Executing: all install scripts with -i (output: {log_file})")
            install_cmd = (
                f"source /etc/platform/openrc && export KUBECONFIG=/etc/kubernetes/admin.conf && "
                f"cd {destination}/test-data && "
                f"cd cpu-metrics && ./install.sh; "
                f"cd ../stx-apps && ./install.sh; "
                f"cd ../vdu && ./install.sh -i; "
                f"cd ../"
            )
        self.ssh_connection.send(
            f"nohup bash -c '({install_cmd}) > {log_file} 2>&1; echo $? > {rc_file}' </dev/null >/dev/null 2>&1 &"
        )

        rc = self._monitor_install_progress(log_file, rc_file, timeout=1200, interval=60)

        get_logger().log_info(f"Script output saved to: {log_file}")
        get_logger().log_info(f"Script exit code: {rc}")

        # Log the last 30 lines of the install log for visibility
        tail_output = self.ssh_connection.send(f"tail -30 {log_file} 2>/dev/null")
        get_logger().log_info(f"[install_all.sh final output]\n{tail_output}")

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
                get_logger().log_info(f"install_all.sh finished after {elapsed}s")
                return self._read_exit_code(rc_file)

            get_logger().log_info(f"install_all.sh still running... ({elapsed}s elapsed)")

        get_logger().log_warning(f"install_all.sh monitoring timed out after {timeout}s")
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



import json5
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.system_test.timing_logger import PatchingTimingLogger

class PatchingKeywords:
    """
    Keywords for StarlingX software patching operations.

    Provides methods for build info validation, patch downloading,
    timing analysis, and system health verification.
    """

    def __init__(self, ssh_connection):
        """
        Initialize PatchingKeywords.

        Args:
            ssh_connection: SSH connection to the system
        """
        self.ssh_connection = ssh_connection

    def get_and_validate_build_info(self) -> Dict[str, str]:
        """
        Get and validate build information from /etc/build.info.

        Returns:
            Dict[str, str]: Build information containing SW_VERSION, BUILD_ID, and JOB
        """
        get_logger().log_test_case_step("Verify build version and ID from /etc/build.info")
        build_info_output = self.ssh_connection.send('cat /etc/build.info')
        validate_equals(self.ssh_connection.get_return_code(), 0, "Failed to read /etc/build.info")

        build_info = self.parse_build_info(build_info_output)

        validate_equals("SW_VERSION" in build_info, True, "SW_VERSION should be present in build info")
        validate_equals("BUILD_ID" in build_info, True, "BUILD_ID should be present in build info")
        validate_equals("JOB" in build_info, True, "JOB should be present in build info")

        get_logger().log_info(f"System build info - SW_VERSION: {build_info['SW_VERSION']}, BUILD_ID: {build_info['BUILD_ID']}, JOB: {build_info['JOB']}")

        return build_info

    def parse_build_info(self, build_info_output: List[str]) -> Dict[str, str]:
        """
        Parse the output of 'cat /etc/build.info' command.

        Args:
            build_info_output (List[str]): Output lines from cat /etc/build.info

        Returns:
            Dict[str, str]: Parsed build information
        """
        build_info = {}
        for line in build_info_output:
            line = line.strip()
            if '=' in line:
                key, value = line.split('=', 1)
                build_info[key] = value.strip('"')
        return build_info

    def download_patch_files(self, job: str, build_id: str) -> List[str]:
        """
        Download patch files from the configured patch server.

        Args:
            job (str): Job name from build info
            build_id (str): Build ID from build info

        Returns:
            List[str]: List of downloaded patch file paths
        """
        get_logger().log_info(f"Downloading patches for job: {job}, build_id: {build_id}")

        patch_server_config_path = get_stx_resource_path("config/system_test/default_patch.json5")
        with open(patch_server_config_path, 'r') as config_file:
            patch_config = json5.load(config_file)

        remote_path = f"{patch_config['base_path']}/{job}/{build_id}/{patch_config['patch_subpath']}/{patch_config['patch_pattern']}"
        destination_path = patch_config['destination_path']

        file_keywords = FileKeywords(self.ssh_connection)
        file_keywords.rsync_from_remote_server(
            local_dest_path=destination_path,
            remote_server=patch_config['server'],
            remote_user=patch_config['user'],
            remote_password=patch_config['password'],
            remote_path=remote_path,
            recursive=False,
            rsync_options="--timeout=300"
        )
        get_logger().log_info("Patch files download completed")

        file_keywords = FileKeywords(self.ssh_connection)
        all_files = file_keywords.get_files_in_dir(destination_path)
        patch_files = [f"{destination_path}/{f}" for f in all_files if f.endswith('-software-rr.patch')]

        if patch_files:
            get_logger().log_info(f"Downloaded patch files: {patch_files}")
            return patch_files

        get_logger().log_warning("No patch files found after download")
        return []

    def get_available_release_for_apply(self, software_list_output) -> Optional[str]:
        """
        Get the release ID that is in 'available' state for patch apply.

        Args:
            software_list_output: SoftwareListOutput object

        Returns:
            Optional[str]: Release ID in available state, or None if not found
        """
        available_releases = software_list_output.get_release_name_by_state("available")
        return available_releases[0] if available_releases else None

    def get_deployed_release_for_remove(self, software_list_output) -> Optional[str]:
        """
        Get the previous release ID for patch removal.

        Args:
            software_list_output: SoftwareListOutput object

        Returns:
            Optional[str]: Previous release ID for removal, or None if not found
        """
        deployed_releases = software_list_output.get_release_name_by_state("deployed")

        if len(deployed_releases) >= 2:
            deployed_releases.sort()
            return deployed_releases[0]

        return None

    def parse_sw_deploy_details(self, details_output: List[str]) -> List[Dict[str, any]]:
        """
        Parse sw-deploy-strategy show --details output to extract stage and step timing information.

        Args:
            details_output (List[str]): Raw output from the command

        Returns:
            List[Dict]: List of stages with their steps and timing data
        """
        stages = []
        current_stage = None

        for i, line in enumerate(details_output):
            stripped = line.strip()

            if stripped.startswith("stage-name:"):
                if current_stage and current_stage.get('steps'):
                    stages.append(current_stage)
                current_stage = {'stage_name': stripped.split(':', 1)[1].strip(), 'steps': []}

            elif stripped.startswith("step-id:") and current_stage is not None:
                step_info = self._extract_step_info(details_output, i)
                if step_info:
                    current_stage['steps'].append(step_info)

        if current_stage and current_stage.get('steps'):
            stages.append(current_stage)

        return stages

    def _extract_step_info(self, details_output: List[str], start_index: int) -> Optional[Dict[str, any]]:
        """
        Extract step information starting from a step-id line.

        Args:
            details_output (List[str]): Raw output lines
            start_index (int): Index of the step-id line

        Returns:
            Optional[Dict]: Step info with name and duration, or None if parsing fails
        """
        step_data = {}

        for j in range(start_index + 1, min(start_index + 20, len(details_output))):
            current_line = details_output[j].strip()

            if current_line.startswith("step-name:"):
                step_data['step_name'] = current_line.split(':', 1)[1].strip()
            elif current_line.startswith("start-date-time:"):
                step_data['start_time'] = current_line.split(':', 1)[1].strip()
            elif current_line.startswith("end-date-time:"):
                step_data['end_time'] = current_line.split(':', 1)[1].strip()

            if len(step_data) == 3:
                break

        if len(step_data) == 3:
            try:
                start_dt = datetime.strptime(step_data['start_time'], '%Y-%m-%d %H:%M:%S')
                end_dt = datetime.strptime(step_data['end_time'], '%Y-%m-%d %H:%M:%S')
                duration = (end_dt - start_dt).total_seconds()
                return {'step_name': step_data['step_name'], 'duration': duration}
            except ValueError as e:
                get_logger().log_warning(f"Failed to parse datetime for step {step_data.get('step_name', 'unknown')}: {e}")

        return None

    def extract_and_log_timings(self, details_output: List[str], operation_type: str, timing_logger) -> List[Dict[str, any]]:
        """
        Extract timing information from sw-deploy details output and log to files.

        Args:
            details_output (List[str]): Raw output from sw-deploy-strategy show --details
            operation_type (str): Either "apply" or "remove"
            timing_logger: PatchingTimingLogger instance

        Returns:
            List[Dict]: List of stages with their steps and timing data
        """
        timing_logger.save_raw_output(operation_type, details_output)
        stages = self.parse_sw_deploy_details(details_output)
        timing_logger.log_patch_timings(operation_type, stages)
        return stages

    def verify_system_health(self, timeout: int = 300):
        """
        Verify system health by checking pods status and alarms.

        Args:
            timeout (int): Timeout for health checks
        """
        pod_keywords = KubectlGetPodsKeywords(self.ssh_connection)
        pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=timeout)

        alarm_keywords = AlarmListKeywords(self.ssh_connection)
        alarm_keywords.set_timeout_in_seconds(timeout)
        alarm_keywords.wait_for_all_alarms_cleared()

    def collect_logs(self, output_dir: str = "benchmark_results", fail_ok: bool = True) -> str:
        """
        Collect system logs using collect all command and download to local directory.

        Args:
            output_dir (str): Local directory to download the tar file
            fail_ok (bool): If True, log warning and return empty string on failure. If False, raise exception.

        Returns:
            str: Local path to the downloaded tar file, or empty string if failed and fail_ok=True
        """
        get_logger().log_info("Running collect all command (this may take several minutes)")

        try:
            output = self.ssh_connection.send("collect all", reconnect_timeout=900)

            tar_files = [line.strip().split()[-1] for line in output if ".tar" in line]
            remote_tar_file = tar_files[0]
            local_tar_file = os.path.join(output_dir, os.path.basename(remote_tar_file))

            FileKeywords(self.ssh_connection).download_file(remote_tar_file, local_tar_file)
            get_logger().log_info(f"Downloaded {remote_tar_file} to {local_tar_file}")
            return local_tar_file

        except Exception as e:
            message = f"Failed to collect logs: {e}"
            if fail_ok:
                get_logger().log_warning(message)
                return ""
            else:
                get_logger().log_error(message)
                raise

    def collect_and_upload_results(self, timing_logger):
        """
        Collect system logs and upload all results to remote server.

        Args:
            timing_logger: PatchingTimingLogger instance with output directory and execution counter
        """
        self.collect_logs(output_dir=timing_logger.output_dir)
        patch_server_config_path = get_stx_resource_path("config/system_test/default_patch.json5")
        with open(patch_server_config_path, 'r') as config_file:
            patch_config = json5.load(config_file)
        self.copy_results_to_server(timing_logger.output_dir, patch_config)

    def copy_results_to_server(self, local_dir: str, patch_config: Dict[str, str]):
        """
        Copy all files from local directory to remote server.

        Args:
            local_dir (str): Local directory containing files to copy
            patch_config (Dict[str, str]): Patch server configuration
        """
        remote_server = patch_config['server']
        if ":" in remote_server and not remote_server.startswith("["):
            remote_server = f"[{remote_server}]"

        cmd = [
            "sshpass", "-p", patch_config['password'],
            "rsync", "-avzr",
            "-e", "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10",
            f"{local_dir}/",
            f"{patch_config['user']}@{remote_server}:{patch_config['log_path']}"
        ]

        get_logger().log_info(f"Copying files from {local_dir} to {remote_server}:{patch_config['log_path']}")
        subprocess.run(cmd, check=True)
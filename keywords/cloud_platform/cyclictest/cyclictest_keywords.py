import os
import random
import time
from typing import Optional

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_greater_than, validate_list_contains, validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.cyclictest.cyclictest_cpu_monitor import CyclictestCpuMonitor
from keywords.cloud_platform.cyclictest.objects.cyclictest_params_object import CyclictestParamsObject
from keywords.cloud_platform.cyclictest.objects.cyclictest_run_result_object import CyclictestRunResultObject
from keywords.cloud_platform.cyclictest.objects.cyclictest_statistics_object import CyclictestStatisticsObject
from keywords.cloud_platform.cyclictest.objects.suitable_hypervisors_output import SuitableHypervisorsOutput
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.objects.online_cpu_output import OnlineCpuOutput
from keywords.cloud_platform.system.host.objects.platform_conf_output import PlatformConfOutput
from keywords.cloud_platform.system.host.objects.system_host_cpu_output import SystemHostCPUOutput
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.host.system_host_task_affinity_keywords import SystemHostTaskAffinityKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.process_status.process_status_psr_keywords import ProcessStatusPsrKeywords

# CPU function labels
CPU_APPLICATION = "Application"
CPU_APPLICATION_ISOLATED = "Application-isolated"
CPU_PLATFORM = "Platform"

# Valid kernel modes accepted by get_suitable_hypervisors / cyclictest_isol_cpus.
_VALID_KERNEL_MODES = ("rt", "std")

# Kernel uname flags used to verify the running kernel matches the requested mode.
_KERNEL_MODE_FLAGS = {
    "rt": "PREEMPT_RT",
    "std": "PREEMPT_DYNAMIC",
}


# CPU policy labels required for valid KPI results. Both must be set on the
# hypervisor that runs the KPI; if wrong they are assigned via lock/unlock.
KPI_LABEL_EXPECTED = {
    "kube-cpu-mgr-policy": "static",
    "kube-topology-mgr-policy": "restricted",
}
KPI_LABELS = [f"{k}={v}" for k, v in KPI_LABEL_EXPECTED.items()]

# Shell script template
_SCRIPT_TEMPLATE = "( rm -rf {local_path}/*.txt && touch {start_file} && {program} &> {run_log} && touch {end_file} ) < /dev/null > /dev/null &"

# Time to wait after writing the launch script before starting it, to ensure the
# filesystem flushes the new script file before nohup executes it.
_SCRIPT_LAUNCH_DELAY_SECONDS = 60

# Polling constants for _wait_for_results.
# _START_SENTINEL_MAX_RETRIES: cyclictest writes the start sentinel immediately
# on launch, but nohup + background execution introduces a brief delay between
# the send() returning and the file appearing on disk.  A short retry loop
# (with _START_SENTINEL_RETRY_INTERVAL_SECONDS between attempts) handles this
# race without requiring an arbitrarily long initial sleep.
_START_SENTINEL_INITIAL_WAIT_SECONDS = 10
_START_SENTINEL_MAX_RETRIES = 5
_START_SENTINEL_RETRY_INTERVAL_SECONDS = 2


class CyclictestKeywords(BaseKeyword):
    """Keywords for running cyclictest and collecting KPI results."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self._ssh_connection = ssh_connection
        self._cyclictest_cfg = ConfigurationManager.get_cyclictest_config()

    def _build_cyclictest_params(self) -> CyclictestParamsObject:
        """Build the cyclictest parameter object for isolated-core runs.

        Cyclictest runtime flags are fixed constants — they are not
        lab-configurable.  Only ``duration`` is read from ``default.json5``
        via :meth:`~config.cyclictest.objects.cyclictest_config.CyclictestConfig.get_duration`.

        Returns:
            CyclictestParamsObject: Typed parameter object for Application-isolated-core runs.
        """
        return CyclictestParamsObject(priority=95, histofall=40000, nsecs=True, smi=True)

    def get_online_cpus(self) -> Optional[OnlineCpuOutput]:
        """Return the online CPU output object from ``/sys/devices/system/cpu/online``.

        Uses the SSH connection stored on this keyword instance
        (``self._ssh_connection``).  Output is parsed by
        :class:`~keywords.cloud_platform.system.host.objects.online_cpu_output.OnlineCpuOutput`.

        Returns:
            Optional[OnlineCpuOutput]: Parsed online CPU output object,
                or ``None`` if the file cannot be read or the return code is
                non-zero.
        """
        try:
            output = "".join(self._ssh_connection.send("cat /sys/devices/system/cpu/online"))
            if self._ssh_connection.get_return_code() != 0:
                return None
            return OnlineCpuOutput(output)
        except Exception as e:
            get_logger().log_warning(f"Failed to read online CPUs: {e}")
            return None

    def get_suitable_hypervisors(self, kernel_mode: str) -> SuitableHypervisorsOutput:
        """Find hosts that match the requested kernel mode.

        Steps:
        1. Validate *kernel_mode* against :data:`_VALID_KERNEL_MODES` using
           :func:`~framework.validation.validation.validate_list_contains`.
        2. For each host: read ``/etc/platform/platform.conf`` via
           :class:`~keywords.cloud_platform.system.host.objects.platform_conf_output.PlatformConfOutput`
           to obtain the subfunction; for RT mode the host must declare
           ``lowlatency`` in its subfunctions.
        3. Verify the running kernel via ``uname -a`` using
           :func:`~framework.validation.validation.validate_str_contains` — fails
           immediately if the kernel flag is not found.
        4. Collect CPU function assignments, filter to online CPUs, and register
           the host in a :class:`~keywords.cloud_platform.cyclictest.objects.suitable_hypervisors_output.SuitableHypervisorsOutput`
           object.

        Args:
            kernel_mode (str): One of ``"rt"``, ``"std"``, or ``"any"``.  Validated
                against :data:`_VALID_KERNEL_MODES` before any host is processed.

        Returns:
            SuitableHypervisorsOutput: Typed output object containing each
                matching hostname and its associated :class:`SystemHostCPUOutput`.

        Raises:
            Exception: If *kernel_mode* is not in :data:`_VALID_KERNEL_MODES`
                (raised by :func:`validate_list_contains`).
            Exception: If a host's running kernel does not contain the expected
                uname flag (raised by :func:`validate_str_contains`).
            Exception: If no suitable hypervisors are found (raised by
                :func:`validate_greater_than`).
        """
        validate_list_contains(kernel_mode, _VALID_KERNEL_MODES, f"kernel_mode '{kernel_mode}' is a recognised mode")

        result = SuitableHypervisorsOutput()
        hosts = SystemHostListKeywords(self._ssh_connection).get_system_host_list().get_hosts()
        for host in hosts:
            hostname = host.get_host_name()
            get_logger().log_debug(f"Processing hypervisor {hostname}")
            host_ssh = LabConnectionKeywords().get_ssh_for_hostname(hostname)

            # Step 1 — read platform.conf via output object.
            platform_conf_raw = "".join(host_ssh.send("cat /etc/platform/platform.conf"))
            subfunction = PlatformConfOutput(platform_conf_raw).get_subfunction()
            get_logger().log_debug(f"{hostname} subfunction: '{subfunction}'")

            # For RT mode, the host must have 'lowlatency' in its subfunctions.
            if kernel_mode == "rt" and "lowlatency" not in subfunction:
                get_logger().log_debug(f"{hostname}: 'lowlatency' not in subfunction — skipping")
                continue

            # Step 2 — verify the running kernel via uname -a.
            kernel_output = "".join(host_ssh.send("uname -a"))
            get_logger().log_info(f"KERNEL VERSION on {hostname}: {kernel_output.strip()}")

            if kernel_mode in _KERNEL_MODE_FLAGS:
                expected_flag = _KERNEL_MODE_FLAGS[kernel_mode]
                validate_str_contains(kernel_output, expected_flag, f"{hostname} kernel contains '{expected_flag}' flag for kernel_mode='{kernel_mode}'")

            # Step 3 — collect CPU function assignments and filter to online CPUs.
            cpu_output = SystemHostCPUKeywords(self._ssh_connection).get_system_host_cpu_list(hostname)

            num_threads = cpu_output.get_thread_count()
            num_cores = len(cpu_output.get_system_host_cpu_objects())
            get_logger().log_info(f"{hostname}: num_cores={num_cores}, per_core_threads={num_threads}")

            app_cores = [c.get_log_core() for c in cpu_output.get_system_host_cpu_objects(assigned_function=CPU_APPLICATION)]
            isol_cores = [c.get_log_core() for c in cpu_output.get_system_host_cpu_objects(assigned_function=CPU_APPLICATION_ISOLATED)]

            host_kw = CyclictestKeywords(host_ssh)
            online = host_kw.get_online_cpus()
            if online is not None:
                get_logger().log_info(f"{hostname} online_cpus={sorted(online.get_online_cpu_ids())}")
                app_cores = [c for c in app_cores if c in online.get_online_cpu_ids()]
                isol_cores = [c for c in isol_cores if c in online.get_online_cpu_ids()]

            get_logger().log_info(f"{hostname} app_cores={app_cores}")
            get_logger().log_info(f"{hostname} app_isolated_cores={isol_cores}")

            # Attach test-run metadata as typed attributes on the output object.
            cpu_output.personalities = f"{subfunction}{host.get_personality()}"
            cpu_output.vm_cores = app_cores
            cpu_output.isolated_cores = isol_cores
            cpu_output.num_threads = num_threads
            cpu_output.num_cores = num_cores
            cpu_output.for_host_test = False

            result.add_hypervisor(hostname, cpu_output)

        validate_greater_than(len(result), 0, f"At least one hypervisor found matching kernel_mode='{kernel_mode}'")
        get_logger().log_info(f"Testable Hypervisors: {result.get_hostnames()}")
        return result

    @staticmethod
    def get_hypervisor(testable_hypervisors: SuitableHypervisorsOutput) -> str:
        """Randomly select a hypervisor not already in use for testing.

        Args:
            testable_hypervisors (SuitableHypervisorsOutput): Output from
                :meth:`get_suitable_hypervisors`.

        Returns:
            str: Selected hostname.

        Raises:
            Exception: If no candidates are available (raised by
                :func:`~framework.validation.validation.validate_greater_than`).
        """
        candidates = [h for h in testable_hypervisors if not testable_hypervisors.get_cpu_output(h).for_host_test]
        validate_greater_than(len(candidates), 0, "At least one hypervisor candidate is available for selection")
        chosen = random.choice(candidates)
        get_logger().log_info(f"Hypervisor chosen: {chosen}")
        return chosen

    def wait_for_task_affinity(self) -> None:
        """Wait for CPU task-affining to complete on the active controller.

        Best-effort gate run before a KPI test: dumps CPU topology /
        platform config, then polls the task-affinity sentinel. Logs a
        warning and proceeds if the sentinel is permanently stale rather
        than blocking the test.
        """
        active_controller_name = SystemHostListKeywords(self._ssh_connection).get_active_controller().get_host_name()
        get_logger().log_setup_step(f"Wait for CPU task-affining to complete on {active_controller_name}")
        SystemHostTaskAffinityKeywords(self._ssh_connection).wait_for_tasks_affined_or_warn(active_controller_name)

    def select_label_target_host(self, testable_hypervisors: SuitableHypervisorsOutput) -> str:
        """Select the hypervisor to receive the KPI CPU-policy labels.

        cyclictest runs on the active controller, so that host is
        preferred when it is itself a testable hypervisor. Otherwise the
        first testable hypervisor is used (multi-node topologies).

        Args:
            testable_hypervisors (SuitableHypervisorsOutput): Output from
                :meth:`get_suitable_hypervisors`.

        Returns:
            str: Hostname to apply the CPU/topology manager labels to.

        Raises:
            Exception: If *testable_hypervisors* is empty (raised by
                :func:`~framework.validation.validation.validate_greater_than`).
        """
        validate_greater_than(len(testable_hypervisors), 0, "At least one testable hypervisor available for label assignment")
        active_controller_name = SystemHostListKeywords(self._ssh_connection).get_active_controller().get_host_name()
        if active_controller_name in testable_hypervisors:
            return active_controller_name
        return next(iter(testable_hypervisors))

    def ensure_kpi_labels_and_isolated_cpus(self, hostname: str) -> None:
        """Ensure KPI CPU-policy labels and Application-isolated cores are both correct in a single lock/unlock.

        Verifies ``kube-cpu-mgr-policy=static``, ``kube-topology-mgr-policy=restricted``,
        and the Application-isolated core count on processor 0. Configures only what
        is wrong:

        - If both are already correct the lock is skipped entirely.
        - If either needs a change the host is locked once, all required
          changes are applied, then the host is unlocked.
        - On duplex systems where *hostname* is the active controller, a swact
          is performed before locking (the active controller cannot be locked
          directly), and a swact back is performed after unlock to restore the
          original active.
        - On simplex systems the host is locked and unlocked directly.

        The caller is responsible for registering an ``ensure_host_unlocked``
        finalizer **before** calling this method so the host is always
        recovered if this method is interrupted mid-lock.

        Formula for target isolated core count (counting only the primary hyperthread sibling):

        .. code-block:: text

            config_cores = p0_app_cores + p0_isolated_cores - 1
            target       = (config_cores + 1) // 2

        Args:
            hostname (str): Target hypervisor to verify and configure, e.g. ``"controller-0"``.

        Raises:
            Exception: If ``p0_app_cores`` is 0 or ``config_cores`` is not positive
                (raised by :func:`~framework.validation.validation.validate_greater_than`) —
                there is no valid Application/Application-isolated split to compute,
                typically because proc0 cores are already fully assigned to
                Application-isolated from a prior run. Proceeding in this state would
                silently run the KPI test against a stale, incorrect core count instead
                of the correct mid-point split.
            Exception: If locking, label assignment, CPU modification, or swact fails
                (propagated from :class:`SystemHostLockKeywords`,
                :class:`SystemHostLabelKeywords`, :class:`SystemHostCPUKeywords`,
                or :class:`SystemHostSwactKeywords`).
        """
        get_logger().log_setup_step(f"Ensure KPI labels and isolated CPUs are correct on {hostname}")

        # --- Verify labels ---
        label_list = SystemHostLabelKeywords(self._ssh_connection).get_system_host_label_list(hostname)
        labels_ok = all(label_list.get_label_value(k) == v for k, v in KPI_LABEL_EXPECTED.items())

        # --- Verify CPU assignment ---
        # Counts are restricted to thread 0 (primary HT sibling) — on a hyperthreaded host,
        # counting both HT siblings would double config_cores and produce a target_isolated
        # value roughly 2x too large relative to the number of distinct physical cores.
        cpu_output = SystemHostCPUKeywords(self._ssh_connection).get_system_host_cpu_list(hostname)
        p0_app_cores = len(cpu_output.get_system_host_cpu_objects(processor_id=0, assigned_function=CPU_APPLICATION, thread=0))
        p0_isolated_cores = len(cpu_output.get_system_host_cpu_objects(processor_id=0, assigned_function=CPU_APPLICATION_ISOLATED, thread=0))
        get_logger().log_info(f"{hostname}: p0_app_cores={p0_app_cores} p0_isolated_cores={p0_isolated_cores}")

        # Reserve one core for the platform; the rest are available for Application / Application-isolated.
        config_cores = p0_app_cores + p0_isolated_cores - 1

        # p0_app_cores == 0 means all proc0 cores are already assigned to Application-isolated
        # (e.g. left over from a prior run) and there is no valid split to compute — proceeding
        # would silently run the KPI against a stale/incorrect core count instead of the correct
        # mid-point split. config_cores must also be positive, since a value of 0 or less means
        # there aren't enough proc0 cores to reserve one for platform and split the remainder.
        validate_greater_than(p0_app_cores, 0, f"{hostname}: p0_app_cores is available for computing an Application-isolated core split")
        validate_greater_than(config_cores, 0, f"{hostname}: config_cores is positive and a valid isolated-core split can be computed")

        target_isol = (config_cores + 1) // 2
        cpu_ok = target_isol == p0_isolated_cores
        get_logger().log_info(f"{hostname}: config_cores={config_cores} target_isolated={target_isol} current_isolated={p0_isolated_cores}")

        # --- Short-circuit if both already correct ---
        if labels_ok and cpu_ok:
            get_logger().log_info(f"{hostname}: labels and CPU assignment already correct — skipping lock/unlock")
            return

        # --- Determine if a swact is needed before locking ---
        # SX: lock directly. DX/Std: if hostname is active controller, swact first then lock.
        controllers = SystemHostListKeywords(self._ssh_connection).get_controllers()
        active_name = SystemHostListKeywords(self._ssh_connection).get_active_controller().get_host_name()
        needs_swact = len(controllers) > 1 and hostname == active_name

        get_logger().log_info(f"{hostname}: labels_ok={labels_ok} cpu_ok={cpu_ok} needs_swact={needs_swact} — locking once to apply required changes")

        # Use a local ssh_connection variable — never mutate self._ssh_connection (side-effect risk on shared instance)
        ssh_connection = self._ssh_connection

        if needs_swact:
            get_logger().log_info(f"{hostname} is the active controller on a duplex system — swacting before lock")
            SystemHostSwactKeywords(ssh_connection).host_swact()
            ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
            get_logger().log_info("SSH re-established on new active controller after swact")

        SystemHostLockKeywords(ssh_connection).lock_host(hostname)

        if not labels_ok:
            get_logger().log_info(f"{hostname}: assigning KPI labels {KPI_LABELS}")
            SystemHostLabelKeywords(ssh_connection).system_host_label_assign(hostname, " ".join(KPI_LABELS), overwrite=True)

        if not cpu_ok:
            get_logger().log_info(f"{hostname}: assigning {target_isol} Application-isolated cores on proc0")
            SystemHostCPUKeywords(ssh_connection).system_host_cpu_modify(hostname, "application-isolated", num_cores_on_processor_0=target_isol)

        SystemHostLockKeywords(ssh_connection).unlock_host(hostname)

        if needs_swact:
            get_logger().log_info(f"Swacting back to restore {hostname} as active controller")
            SystemHostSwactKeywords(ssh_connection).host_swact()
            get_logger().log_info(f"{hostname} restored as active controller")

        get_logger().log_info(f"{hostname}: KPI labels and isolated CPU assignment complete")

    def ensure_host_unlocked(self, hostname: str) -> None:
        """Unlock *hostname* if it is not already unlocked.

        Intended for use in a teardown finalizer so a host left locked by
        an interrupted label-assignment step is always recovered.

        Args:
            hostname (str): Host to check and unlock, e.g. ``"controller-0"``.
        """
        get_logger().log_teardown_step(f"Ensure {hostname} is unlocked after label assignment setup")
        host = SystemHostListKeywords(self._ssh_connection).get_system_host_list().get_host(hostname)
        if host.get_administrative() != "unlocked":
            get_logger().log_teardown_step(f"{hostname} is still locked — attempting unlock")
            SystemHostLockKeywords(self._ssh_connection).unlock_host(hostname)

    def prep_host(self, host_ssh: SSHConnection, target: str) -> None:
        """Copy the cyclictest binary from its configured source path to the work directory.

        On AIO-SX / same-controller runs the source and destination are both on
        the active controller so ``FileKeywords.copy_file`` is used.  For
        separate worker nodes the binary is transferred from the active
        controller using ``FileKeywords.rsync_from_remote_server``.

        Args:
            host_ssh (SSHConnection): SSH connection to the *target hypervisor*.
                This may differ from ``self._ssh_connection`` (the active
                controller) on multi-node topologies.
            target (str): Target hostname, e.g. ``"controller-0"``.

        Raises:
            ValueError: If the configured cyclictest directory is empty or
                unsafe (to prevent accidental disk wipe on ``rm -f <dir>/*``).
            RuntimeError: If the cyclictest binary is not found at its
                configured source path, or if the copy to the destination fails.
        """
        cyclictest_dir = self._cyclictest_cfg.get_cyclictest_dir()
        cyclictest_exe = self._cyclictest_cfg.get_cyclictest_exe()

        if not cyclictest_dir or cyclictest_dir.strip() in ("", "/"):
            raise ValueError(f"cyclictest_dir is empty or unsafe: '{cyclictest_dir}'. Check the cyclictest config.")

        get_logger().log_test_case_step(f"Prepare host {target}: copy cyclictest binary")
        exe_name = os.path.basename(cyclictest_exe)
        dest = os.path.join(cyclictest_dir, exe_name)

        file_kw = FileKeywords(host_ssh)
        file_kw.create_directory(cyclictest_dir)
        host_ssh.send(f"rm -f {cyclictest_dir}/*.*")

        if not file_kw.file_exists(dest):
            active_controller = SystemHostListKeywords(self._ssh_connection).get_active_controller().get_host_name()
            if target == active_controller:
                # Upload binary from automation runner (cyclictest_exe) to the
                # controller via SFTP. This handles the case where the binary
                # is missing after a lock/unlock cycle wipes the controller
                # filesystem, without requiring the binary to be pre-deployed.
                get_logger().log_info(f"Uploading cyclictest binary from runner {cyclictest_exe} → {dest} on {target}")
                FileKeywords(host_ssh).upload_file(cyclictest_exe, dest)
            else:
                # Different host — transfer from active controller via rsync.
                lab_cfg = ConfigurationManager.get_lab_config()
                user = lab_cfg.get_admin_credentials().get_user_name()
                password = lab_cfg.get_admin_credentials().get_password()
                FileKeywords(host_ssh).rsync_from_remote_server(
                    remote_server=active_controller,
                    remote_user=user,
                    remote_password=password,
                    remote_path=cyclictest_exe,
                    local_dest_path=dest,
                )
            validate_equals(file_kw.file_exists(dest), True, f"cyclictest binary successfully copied to {target}:{dest}")

        file_kw.make_executable(dest)

    def run_cyclictest(
        self,
        host_ssh: SSHConnection,
        target: str,
        cpu_output: SystemHostCPUOutput,
        settings: Optional[CyclictestParamsObject] = None,
        duration: Optional[int] = None,
        cpu_monitor: Optional[CyclictestCpuMonitor] = None,
    ) -> CyclictestRunResultObject:
        """Execute cyclictest on the target host and wait for completion.

        Args:
            host_ssh (SSHConnection): SSH connection to the *target hypervisor*.
                This may differ from ``self._ssh_connection`` (the active
                controller) on multi-node topologies.
            target (str): Target hostname.
            cpu_output (SystemHostCPUOutput): CPU output object from
                :meth:`get_suitable_hypervisors`.  Used to derive affinity
                and thread counts; the ``isolated_cores`` and ``vm_cores``
                attributes set by :meth:`get_suitable_hypervisors` are read
                via :meth:`~SystemHostCPUOutput.get_cpu_ids_as_range_string`.
            settings (Optional[CyclictestParamsObject]): Override cyclictest params.  ``None``
                uses :meth:`_build_cyclictest_params`.
            duration (Optional[int]): Override the run duration in seconds.
            cpu_monitor (Optional[CyclictestCpuMonitor]): If provided, started
                and stopped around the run to collect CPU usage samples.

        Returns:
            CyclictestRunResultObject: Paths to the run log and histogram file,
                plus the histofall flag.
        """
        get_logger().log_test_case_step(f"Run cyclictest on {target}")
        cyclictest_exe = self._cyclictest_cfg.get_cyclictest_exe()
        cyclictest_dir = self._cyclictest_cfg.get_cyclictest_dir()
        exe_name = os.path.basename(cyclictest_exe)
        program = os.path.join(cyclictest_dir, exe_name)

        params = dict(settings.to_dict() if settings is not None else self._build_cyclictest_params().to_dict())
        # Duration: explicit argument → config file (default.json5).
        # The explicit argument exists only for per-test overrides.
        params["duration"] = duration if duration is not None else self._cyclictest_cfg.get_duration()
        histofall_mode = "histofall" in params

        timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
        run_log = f"{cyclictest_dir}/runlog-{target}-{timestamp}.txt"
        hist_file = f"{cyclictest_dir}/hist-file-{target}-{timestamp}.txt"
        start_file = f"{cyclictest_dir}/start-{timestamp}.txt"
        end_file = f"{cyclictest_dir}/end-{timestamp}.txt"
        params["histfile"] = hist_file

        # Build --affinity and --threads options via SystemHostCPUOutput helpers.
        options = " ".join(f"--{k} {v}" for k, v in params.items())
        # Use proc0 Platform cores, thread 0 only, for --mainaffinity. Without the thread
        # filter this would include the HT sibling (e.g. "0,64" instead of "0"), which is
        # not the intended set of Platform-affined threads for cyclictest's main thread.
        plat_cores = [c.get_log_core() for c in SystemHostCPUKeywords(self._ssh_connection).get_system_host_cpu_list(target).get_system_host_cpu_objects(processor_id=0, assigned_function=CPU_PLATFORM, thread=0)]
        main_affinity = f" --mainaffinity {SystemHostCPUOutput.normalize_cpu_list(plat_cores)}" if plat_cores else ""

        isol = getattr(cpu_output, "isolated_cores", [])
        user_cores = self._cyclictest_cfg.get_cores()
        if isol:
            options += f" --affinity {SystemHostCPUOutput.normalize_cpu_list(isol)} --threads {len(isol)}{main_affinity}"
        elif user_cores:
            count = SystemHostCPUOutput.calculate_range_length(user_cores)
            options += f" --affinity {user_cores} --threads {count}{main_affinity}"
        else:
            raise ValueError("No CPU affinity source available: 'isolated_cores' is empty and " "'cores' is not set in the cyclictest config. Cannot run cyclictest.")

        cmd = f"{program} {options}"
        script = f"{cyclictest_dir}/runcyclictest.sh"
        script_body = _SCRIPT_TEMPLATE.format(
            local_path=cyclictest_dir,
            start_file=start_file,
            end_file=end_file,
            program=cmd,
            run_log=run_log,
        )
        # Use a heredoc to write the script — avoids shell-injection issues that arise
        # when the script body is passed via echo "..." and contains quotes or
        # special characters from config-supplied paths and options.
        host_ssh.send(f"cat > {script} << 'CYCLICTEST_EOF'\n{script_body}\nCYCLICTEST_EOF")
        host_ssh.send(f"chmod +x {script}; cat {script}")
        time.sleep(_SCRIPT_LAUNCH_DELAY_SECONDS)

        host_ssh.send_as_sudo(f"nohup {script}")

        # Obtain PID via keyword rather than raw ps pipeline.
        pid = ProcessStatusPsrKeywords(host_ssh).get_pid_by_process_name("cyclictest")
        if cpu_monitor and pid is not None:
            cpu_monitor.set_pid(pid)
            cpu_monitor.start()

        self._wait_for_results(run_log, hist_file, start_file, end_file, params["duration"])

        if cpu_monitor:
            cpu_monitor.stop()
            cpu_monitor.wait_until_stopped()

        return CyclictestRunResultObject(run_log, hist_file, histofall_mode)

    def fetch_results(
        self,
        host_ssh: SSHConnection,
        target: str,
        run_log: str,
        hist_file: str,
    ) -> str:
        """Copy histogram and run-log files from the target host to the local log directory.

        Uses the framework SFTP client so that no out-of-band SSH key setup is
        required.  If the target is not the active controller the files are
        first transferred to the active controller via
        ``FileKeywords.rsync_to_remote_server``, then downloaded via SFTP.

        Args:
            host_ssh (SSHConnection): SSH connection to the *target hypervisor*.
                This may differ from ``self._ssh_connection`` (the active
                controller) on multi-node topologies.
            target (str): Target hostname.
            run_log (str): Remote run log path.
            hist_file (str): Remote histogram file path.

        Returns:
            str: Local path to the downloaded histogram file.

        Raises:
            RuntimeError: If the histogram or run-log file cannot be found
                locally after the transfer.
        """
        get_logger().log_test_case_step("Fetch cyclictest results to localhost")

        cyclictest_dir = self._cyclictest_cfg.get_cyclictest_dir()

        # chmod so root-owned files are readable for SFTP download.
        host_ssh.send_as_sudo(f"chmod -R 755 {cyclictest_dir}/*.txt")

        active_controller = SystemHostListKeywords(self._ssh_connection).get_active_controller().get_host_name()
        if target != active_controller:
            lab_cfg = ConfigurationManager.get_lab_config()
            user = lab_cfg.get_admin_credentials().get_user_name()
            password = lab_cfg.get_admin_credentials().get_password()
            get_logger().log_info(f"Copying results from {target} to active controller {active_controller}")
            FileKeywords(host_ssh).rsync_to_remote_server(
                local_dest_path=f"{cyclictest_dir}/*.txt",
                remote_server=active_controller,
                remote_user=user,
                remote_password=password,
                remote_path=f"{cyclictest_dir}/",
            )
            host_ssh.send(f"rm -f {cyclictest_dir}/*.txt")
            fetch_ssh = LabConnectionKeywords().get_ssh_for_hostname(active_controller)
        else:
            fetch_ssh = host_ssh

        local_dir = os.path.join(get_logger().get_test_case_log_dir(), "system_logs")
        os.makedirs(local_dir, exist_ok=True)

        get_logger().log_info(f"Downloading cyclictest results via SFTP to {local_dir}")
        sftp = fetch_ssh.get_sftp_client()
        _transport = getattr(getattr(fetch_ssh, "client", None), "get_transport", lambda: None)()
        if _transport is not None and _transport.is_active():
            _transport.set_keepalive(0)
            if hasattr(_transport, "_thread") and _transport._thread is not None:
                _transport._thread.daemon = True
        try:
            remote_files = sftp.listdir(cyclictest_dir)
            for fname in remote_files:
                if fname.endswith(".txt"):
                    remote_path = os.path.join(cyclictest_dir, fname)
                    local_path = os.path.join(local_dir, fname)
                    get_logger().log_debug(f"SFTP get: {remote_path} → {local_path}")
                    sftp.get(remote_path, local_path)
        finally:
            sftp.close()

        local_hist = os.path.join(local_dir, os.path.basename(hist_file))
        if not os.path.isfile(local_hist):
            raise RuntimeError(f"Histogram file not found locally after fetch: {local_hist}")

        local_run_log = os.path.join(local_dir, os.path.basename(run_log))
        if not os.path.isfile(local_run_log):
            raise RuntimeError(f"Run log not found locally after fetch: {local_run_log}")

        self._ssh_connection.send(f"rm -f {cyclictest_dir}/*.txt")
        return local_hist

    def calculate_results(
        self,
        local_hist_file: str,
        histofall_mode: bool = True,
    ) -> CyclictestStatisticsObject:
        """Parse histogram file and compute statistics.

        Args:
            local_hist_file (str): Local path to the histogram file.
            histofall_mode (bool): True if --histofall was used.

        Returns:
            CyclictestStatisticsObject: computed statistics object.
        """
        get_logger().log_test_case_step("Calculate cyclictest statistics")
        stats = CyclictestStatisticsObject.from_hist_file(local_hist_file, histofall_mode=histofall_mode)
        return stats.calculate_statistics()

    def cyclictest_isol_cpus(
        self,
        kernel_mode: str,
        duration: Optional[int] = None,
        cpu_monitor: Optional[CyclictestCpuMonitor] = None,
    ) -> CyclictestStatisticsObject:
        """Run cyclictest on application-isolated cores of the active controller.

        Args:
            kernel_mode (str): ``"rt"``, ``"std"``, or ``"any"``.
            duration (Optional[int]): Duration override in seconds.
            cpu_monitor (Optional[CyclictestCpuMonitor]): CPU monitor instance.

        Returns:
            CyclictestStatisticsObject: Computed latency statistics.
        """
        testable = self.get_suitable_hypervisors(kernel_mode)
        chosen = SystemHostListKeywords(self._ssh_connection).get_active_controller().get_host_name()
        cpu_output = testable.get_cpu_output(chosen)
        if cpu_output is None:
            # Fallback: fetch CPU output for chosen host directly.
            cpu_output = SystemHostCPUKeywords(self._ssh_connection).get_system_host_cpu_list(chosen)
            cpu_output.isolated_cores = []
            cpu_output.vm_cores = []
            cpu_output.for_host_test = False

        # Re-read isolated cores from system host-cpu-list after
        # ensure_kpi_labels_and_isolated_cpus has run so the fresh assignment
        # is picked up. The cpu_output from get_suitable_hypervisors was
        # populated before the assignment and must not be used here.
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(chosen)
        fresh_cpu_output = SystemHostCPUKeywords(self._ssh_connection).get_system_host_cpu_list(chosen)
        isol_cores = [c.get_log_core() for c in fresh_cpu_output.get_system_host_cpu_objects(assigned_function=CPU_APPLICATION_ISOLATED)]
        online = CyclictestKeywords(host_ssh).get_online_cpus()
        if online is not None:
            isol_cores = [c for c in isol_cores if c in online.get_online_cpu_ids()]
        get_logger().log_info(f"{chosen} app_isolated_cores={isol_cores}")
        cpu_output.isolated_cores = isol_cores
        cpu_output.for_host_test = True

        self.prep_host(host_ssh, chosen)
        run_result = self.run_cyclictest(
            host_ssh,
            chosen,
            cpu_output,
            settings=self._build_cyclictest_params(),
            duration=duration,
            cpu_monitor=cpu_monitor,
        )
        local_hist = self.fetch_results(host_ssh, chosen, run_result.get_run_log(), run_result.get_hist_file())

        cpu_output.for_host_test = False
        return self.calculate_results(local_hist, histofall_mode=run_result.is_histofall_mode())

    def _wait_for_results(
        self,
        run_log: str,
        hist_file: str,
        start_file: str,
        end_file: str,
        check_duration: int,
    ) -> None:
        """Poll until cyclictest writes its end-file sentinel, then return.

        Uses ``self._ssh_connection`` to poll the remote host.  The start
        sentinel is checked with a short retry loop to handle the brief race
        between ``nohup`` returning and cyclictest writing the file to disk.

        Args:
            run_log (str): Remote run log path (tailed on completion for logging).
            hist_file (str): Remote histogram path (tailed on completion for logging).
            start_file (str): Sentinel file created immediately when cyclictest
                starts.
            end_file (str): Sentinel file created when cyclictest finishes.
            check_duration (int): Expected run duration in seconds; used to
                set the poll interval and total timeout.

        Raises:
            RuntimeError: If the start sentinel is never created (cyclictest
                failed to start) or if the end sentinel is not created before
                the total timeout expires.
        """
        wait_per_check = max(check_duration / 20, 120)
        total_timeout = check_duration + 3600
        deadline = time.time() + total_timeout
        start_time = time.time()

        # Wait for start sentinel with a short retry loop.
        # cyclictest writes this file immediately on launch, but nohup +
        # background execution introduces a brief delay between send() returning
        # and the sentinel appearing on disk — hence the small retry window.
        time.sleep(_START_SENTINEL_INITIAL_WAIT_SECONDS)
        for _ in range(_START_SENTINEL_MAX_RETRIES):
            self._ssh_connection.send(f"test -f {start_file}")
            if self._ssh_connection.get_return_code() == 0:
                get_logger().log_info("Cyclictest started.")
                break
            time.sleep(_START_SENTINEL_RETRY_INTERVAL_SECONDS)
        else:
            raise RuntimeError("Cyclictest failed to start (start sentinel not created)")

        while time.time() < deadline:
            self._ssh_connection.send(f"test -f {end_file}")
            if self._ssh_connection.get_return_code() == 0:
                get_logger().log_info("Cyclictest run completed.")
                output = "".join(self._ssh_connection.send(f"tail -n 30 {run_log} {hist_file}"))
                get_logger().log_info(f"\n{output}\n")
                return
            elapsed = int(time.time() - start_time)
            get_logger().log_info(f"Cyclictest still running — elapsed ~{elapsed}s / {check_duration}s expected duration")
            time.sleep(wait_per_check)

        raise RuntimeError(f"Cyclictest timed out after {total_timeout}s")

    def compress_results(self, local_dir: str) -> Optional[str]:
        """Archive a cyclictest results directory to a ``.tar.gz`` and remove the raw dir.

        Delegates to
        :meth:`~keywords.files.file_keywords.FileKeywords.compress_and_remove_directory`,
        which calls ``shutil.make_archive`` followed by ``shutil.rmtree``.
        If *local_dir* does not exist the call is a no-op and ``None`` is
        returned — making this safe to call idempotently from both the
        setup step (compress stale results) and the teardown step (compress
        the current run's results).

        Args:
            local_dir (str): Absolute path to the local results directory,
                e.g. ``/var/log/automation/<run-id>/<test>/system_logs``.

        Returns:
            Optional[str]: Absolute path to the created ``.tar.gz`` file,
                or ``None`` if *local_dir* did not exist.
        """
        return FileKeywords(self._ssh_connection).compress_and_remove_directory(local_dir)

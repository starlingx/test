import os

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.cyclictest.cyclictest_cpu_monitor import CyclictestCpuMonitor
from keywords.cloud_platform.cyclictest.cyclictest_keywords import CyclictestKeywords
from keywords.cloud_platform.cyclictest.objects.cpu_usage_kpi_helper_object import CpuUsageKpiHelperObject
from keywords.cloud_platform.cyclictest.objects.cyclictest_kpi_helper_object import CyclictestKpiHelperObject
from keywords.cloud_platform.cyclictest.objects.suitable_hypervisors_output import SuitableHypervisorsOutput
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_kernel_keywords import SystemHostKernelKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.kernel.kernel_keywords import KernelKeywords

# Application / label constants
NODE_FEATURE_DISCOVERY_APP = "node-feature-discovery"
KUBERNETES_POWER_MANAGER_APP = "kubernetes-power-manager"
POWER_MANAGEMENT_LABEL = "power-management=enabled"
POWER_MANAGEMENT_LABEL_KEY = "power-management"
HELM_APP_BASE_PATH = "/usr/local/share/applications/helm/"
CSTATE_YAML_FILE = "/home/sysadmin/cstate-c1-enabled.yaml"

# CPU-state combinations
CPU_STATES_C1P0 = {"c_state": "Enable", "p_state": "Disable"}
CPU_STATES_C0P0 = {"c_state": "Disable", "p_state": "Disable"}


# ---------------------------------------------------------------------------
# Module-level helpers (ACE rule: no pytest fixtures)
# ---------------------------------------------------------------------------


def _prepare_platform(request: FixtureRequest, kernel_mode: str) -> SuitableHypervisorsOutput:
    """Prepare the platform for a KPI run, in the required order.

    Order of operations (all delegated to :class:`CyclictestKeywords`):

    1. Wait for CPU task-affining to complete on the active controller.
    2. Determine the testable hypervisor(s) for *kernel_mode*
       (logs ``Testable Hypervisors: [...]``).
    3. Assign the kube CPU/topology manager labels on the hypervisor that
       will run cyclictest, registering an unlock finalizer first so the
       host is recovered even if label assignment is interrupted.

    Args:
        request (FixtureRequest): pytest request object for addfinalizer.
        kernel_mode (str): "rt" or "std".

    Returns:
        SuitableHypervisorsOutput: testable hypervisors from :meth:`~keywords.cloud_platform.cyclictest.cyclictest_keywords.CyclictestKeywords.get_suitable_hypervisors`.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    cyclictest_kw = CyclictestKeywords(ssh_connection)

    # 1. Task-affinity gate.
    cyclictest_kw.wait_for_task_affinity()

    # 2. Determine testable hypervisors (emits 'Testable Hypervisors: [...]').
    get_logger().log_setup_step(f"Verify lab has {kernel_mode}-kernel hypervisors")
    targets = cyclictest_kw.get_suitable_hypervisors(kernel_mode=kernel_mode)

    # 3. Assign CPU/topology manager labels on the hypervisor that will run
    #    the KPI. Register the unlock finalizer BEFORE assigning so the host
    #    is always recovered even if label assignment fails mid-lock.
    target_host = cyclictest_kw.select_label_target_host(targets)
    request.addfinalizer(lambda: cyclictest_kw.ensure_host_unlocked(target_host))
    cyclictest_kw.assign_cpu_policy_labels(target_host)

    return targets


def _run_cyclictest_and_record_kpis(cpu_states: dict, kernel_mode: str) -> None:
    """Run cyclictest on isolated cores and record latency + CPU-usage KPIs.

    Args:
        cpu_states (dict): e.g. {"c_state": "Enable", "p_state": "Disable"}.
        kernel_mode (str): "rt" or "std".
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    cyclictest_kpi = CyclictestKpiHelperObject(cpu_states, kernel_mode=kernel_mode)
    cpu_usage_kpi = CpuUsageKpiHelperObject(cpu_states, kernel_mode=kernel_mode)

    isolated_cpu_mon = CyclictestCpuMonitor(ssh_connection, process_name="cyclictest")
    duration = ConfigurationManager.get_cyclictest_config().get_duration()
    get_logger().log_info(f"Running cyclictest on isolated cores — duration {duration}s")
    isol_results = CyclictestKeywords(ssh_connection).cyclictest_isol_cpus(kernel_mode=kernel_mode, duration=duration, cpu_monitor=isolated_cpu_mon)

    cyclictest_kpi.set_kpi(
        {
            "iso_avg": isol_results.get_average(),
            "iso_6nines_percentile": isol_results.get_percentile(),
            "iso_max": isol_results.get_maximum(),
            "iso_median": isol_results.get_median(),
            "iso_overflows": isol_results.get_num_overflows(),
        }
    )

    cpu_stats = isolated_cpu_mon.get_all_process_stats()
    sys_stats = isolated_cpu_mon.get_all_system_stats()
    get_logger().log_info(f"PROCESS CPU Usage: {cpu_stats}")
    get_logger().log_info(f"SYSTEM CPU Usage: {sys_stats}")
    cpu_usage_kpi.set_kpi(
        {
            "iso_avg": cpu_stats.get_average(),
            "iso_median": cpu_stats.get_median(),
            "iso_deviation": cpu_stats.get_std_deviation(),
        }
    )


# ---------------------------------------------------------------------------
# RT kernel tests
# ---------------------------------------------------------------------------


@mark.p2
@mark.lab_has_low_latency
def test_cyclictest_rt_c1p0(request: FixtureRequest):
    """Collect latency KPI on RT kernel with C-State enabled / P-State disabled (isolated cores, 1800s).

    Preconditions:
        - Lab has RT-kernel (lowlatency) hypervisors.
        - Lab is configured for low latency.

    Setup:
        - Establish active controller SSH connection.
        - Verify platform readiness (task-affinity, CPU label policy).
        - Verify lab has RT-kernel hypervisors.
        - Compress any stale cyclictest results from a prior run.

    Test Steps:
        1. Run cyclictest on isolated cores for 1800s with C-State enabled and P-State disabled.
        2. Record latency KPIs (iso_avg, iso_6nines_percentile, iso_max, iso_median, iso_overflows).
        3. Record CPU usage KPIs (iso_avg, iso_median, iso_deviation).

    Teardown:
        - Compress cyclictest execution logs from this run.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    _prepare_platform(request, kernel_mode="rt")

    cyclictest_kw = CyclictestKeywords(ssh)

    # Setup Step 6 (mirrors TIS): compress stale results from a prior run (idempotent).
    get_logger().log_setup_step("Compress stale cyclictest execution logs from prior run (if any)")
    cyclictest_kw.compress_results(os.path.join(get_logger().get_test_case_log_dir(), "system_logs"))

    # Register teardown finalizer BEFORE the run so it always fires.
    # local_dir is resolved inside the lambda so it uses the logger state at teardown time.
    request.addfinalizer(
        lambda: (
            get_logger().log_teardown_step("Compress cyclictest execution logs from this run"),
            cyclictest_kw.compress_results(os.path.join(get_logger().get_test_case_log_dir(), "system_logs")),
        )
    )

    _run_cyclictest_and_record_kpis(CPU_STATES_C1P0, kernel_mode="rt")


@mark.p2
@mark.lab_has_low_latency
def test_cyclictest_rt_c1p0_per_core_configuration(request: FixtureRequest):
    """Collect latency KPI on RT kernel with C-State enabled / P-State disabled — per-core configuration.

    Identical to test_cyclictest_rt_c1p0. Lab marks intentionally omitted to allow this variant
    to run on labs that do not satisfy the no-hyperthreading / low-latency constraints.

    Preconditions:
        - Lab has RT-kernel (lowlatency) hypervisors.

    Setup:
        - Establish active controller SSH connection.
        - Verify platform readiness (task-affinity, CPU label policy).
        - Verify lab has RT-kernel hypervisors.
        - Compress any stale cyclictest results from a prior run.

    Test Steps:
        1. Run cyclictest on isolated cores for 1800s with C-State enabled and P-State disabled.
        2. Record latency and CPU usage KPIs.

    Teardown:
        - Compress cyclictest execution logs from this run.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    _prepare_platform(request, kernel_mode="rt")

    cyclictest_kw = CyclictestKeywords(ssh)

    get_logger().log_setup_step("Compress stale cyclictest execution logs from prior run (if any)")
    cyclictest_kw.compress_results(os.path.join(get_logger().get_test_case_log_dir(), "system_logs"))

    request.addfinalizer(
        lambda: (
            get_logger().log_teardown_step("Compress cyclictest execution logs from this run"),
            cyclictest_kw.compress_results(os.path.join(get_logger().get_test_case_log_dir(), "system_logs")),
        )
    )

    _run_cyclictest_and_record_kpis(CPU_STATES_C1P0, kernel_mode="rt")


@mark.p2
@mark.lab_has_low_latency
def test_cyclictest_rt_c0p0(request: FixtureRequest):
    """Collect latency KPI on RT kernel with C-State disabled / P-State disabled (isolated cores, 1800s).

    Preconditions:
        - Lab has RT-kernel (lowlatency) hypervisors.
        - Lab is configured for low latency.

    Setup:
        - Establish active controller SSH connection.
        - Verify platform readiness (task-affinity, CPU label policy).
        - Verify lab has RT-kernel hypervisors.
        - Compress any stale cyclictest results from a prior run.

    Test Steps:
        1. Run cyclictest on isolated cores for 1800s with C-State disabled and P-State disabled.
        2. Record latency and CPU usage KPIs.

    Teardown:
        - Compress cyclictest execution logs from this run.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    _prepare_platform(request, kernel_mode="rt")

    cyclictest_kw = CyclictestKeywords(ssh)

    get_logger().log_setup_step("Compress stale cyclictest execution logs from prior run (if any)")
    cyclictest_kw.compress_results(os.path.join(get_logger().get_test_case_log_dir(), "system_logs"))

    request.addfinalizer(
        lambda: (
            get_logger().log_teardown_step("Compress cyclictest execution logs from this run"),
            cyclictest_kw.compress_results(os.path.join(get_logger().get_test_case_log_dir(), "system_logs")),
        )
    )

    _run_cyclictest_and_record_kpis(CPU_STATES_C0P0, kernel_mode="rt")


# ---------------------------------------------------------------------------
# STD kernel tests
# ---------------------------------------------------------------------------


@mark.p2
@mark.lab_has_non_low_latency
def test_cyclictest_std_c0p0(request: FixtureRequest):
    """Collect latency KPI on std kernel with C-State disabled / P-State disabled (isolated cores, 1800s).

    Preconditions:
        - Lab has std-kernel hypervisors.
        - Lab is not configured for low latency.

    Setup:
        - Establish active controller SSH connection.
        - Verify platform readiness (task-affinity, CPU label policy).
        - Verify lab has std-kernel hypervisors.
        - Compress any stale cyclictest results from a prior run.

    Test Steps:
        1. Run cyclictest on isolated cores for 1800s with C-State disabled and P-State disabled.
        2. Record latency and CPU usage KPIs.

    Teardown:
        - Compress cyclictest execution logs from this run.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    _prepare_platform(request, kernel_mode="std")

    cyclictest_kw = CyclictestKeywords(ssh)

    get_logger().log_setup_step("Compress stale cyclictest execution logs from prior run (if any)")
    cyclictest_kw.compress_results(os.path.join(get_logger().get_test_case_log_dir(), "system_logs"))

    request.addfinalizer(
        lambda: (
            get_logger().log_teardown_step("Compress cyclictest execution logs from this run"),
            cyclictest_kw.compress_results(os.path.join(get_logger().get_test_case_log_dir(), "system_logs")),
        )
    )

    _run_cyclictest_and_record_kpis(CPU_STATES_C0P0, kernel_mode="std")


# ---------------------------------------------------------------------------
# Kernel modification helpers
# ---------------------------------------------------------------------------


def _modify_controllers_kernel(request: FixtureRequest, kernel_value: str, expected_uname_flag: str) -> None:
    """Lock, modify kernel, unlock and verify each controller.

    Args:
        request (FixtureRequest): pytest request object for addfinalizer.
        kernel_value (str): "lowlatency" or "standard".
        expected_uname_flag (str): grep token to confirm kernel (e.g. 'PREEMPT_RT').
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    controllers = SystemHostListKeywords(ssh_connection).get_controllers()
    cyclictest_kw = CyclictestKeywords(ssh_connection)

    for ctrl in controllers:
        hostname = ctrl.get_host_name()

        # Register unlock recovery BEFORE locking so a controller left locked
        # by an interrupted modify/unlock sequence is always recovered.
        request.addfinalizer(lambda name=hostname: cyclictest_kw.ensure_host_unlocked(name))

        get_logger().log_test_case_step(f"Lock {hostname}")
        SystemHostLockKeywords(ssh_connection).lock_host(hostname)

        get_logger().log_test_case_step(f"Modify {hostname} kernel to {kernel_value}")
        SystemHostKernelKeywords(ssh_connection).modify_kernel_config(hostname, kernel_value)

        get_logger().log_test_case_step(f"Unlock {hostname} and wait for it to become available")
        SystemHostLockKeywords(ssh_connection).unlock_host(hostname)

        get_logger().log_test_case_step(f"Verify {hostname} runs {kernel_value} kernel")
        host_ssh = LabConnectionKeywords().get_ssh_for_hostname(hostname)
        is_correct_kernel = KernelKeywords(host_ssh).verify_kernel_flag(expected_uname_flag)
        validate_equals(
            is_correct_kernel,
            True,
            f"{hostname} is not running {kernel_value} kernel",
        )
        get_logger().log_info(f"{hostname} confirmed running {kernel_value} kernel")


@mark.p2
@mark.lab_has_low_latency
def test_modify_controllers_to_lowlatency(request: FixtureRequest):
    """Modify all controllers to lowlatency (RT) kernel.

    Preconditions:
        - Lab is configured for low latency.
        - All controllers are accessible and unlocked.

    Setup:
        - None.

    Test Steps:
        1. For each controller: lock, modify kernel to lowlatency, unlock, wait for availability.
        2. Verify PREEMPT_RT is present in uname output for each controller.

    Teardown:
        - Ensure each controller is unlocked.
    """
    _modify_controllers_kernel(request, "lowlatency", "PREEMPT_RT")


@mark.p2
@mark.lab_has_non_low_latency
def test_modify_controllers_to_standard(request: FixtureRequest):
    """Modify all controllers to standard kernel.

    Preconditions:
        - Lab is not configured for low latency.
        - All controllers are accessible and unlocked.

    Setup:
        - None.

    Test Steps:
        1. For each controller: lock, modify kernel to standard, unlock, wait for availability.
        2. Verify PREEMPT_DYNAMIC is present in uname output for each controller.

    Teardown:
        - Ensure each controller is unlocked.
    """
    _modify_controllers_kernel(request, "standard", "PREEMPT_DYNAMIC")


# ---------------------------------------------------------------------------
# Kubernetes power manager setup
# ---------------------------------------------------------------------------


@mark.p2
@mark.lab_has_low_latency
def test_kubernetes_power_manager_setup(request: FixtureRequest):
    """Upload, apply and configure kubernetes-power-manager for C-state management.

    Preconditions:
        - Lab is configured for low latency.
        - Helm application tarballs are present in the configured helm app base path.
        - Active controller has Application-isolated CPU cores.

    Setup:
        - Establish active controller SSH connection.
        - Retrieve controller list.

    Test Steps:
        1. Upload and apply node-feature-discovery.
        2. Upload and apply kubernetes-power-manager.
        3. Assign power-management=enabled label to all controllers (lock/assign/unlock).
        4. Get Application-isolated CPU cores on controller-0.
        5. Create cstate-c1-enabled.yaml for isolated cores.
        6. Update helm override with C-state config.
        7. Remove node-feature-discovery and re-apply kubernetes-power-manager.

    Teardown:
        - Remove kubernetes-power-manager and node-feature-discovery.
        - Remove power-management label from each controller.
        - Delete C-state YAML file.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh).get_active_controller().get_host_name()
    controllers = SystemHostListKeywords(ssh).get_controllers()

    def _teardown():
        get_logger().log_teardown_step("Remove kubernetes-power-manager and node-feature-discovery")
        SystemApplicationRemoveKeywords(ssh).cleanup_app_if_present(NODE_FEATURE_DISCOVERY_APP, force_removal=True)
        SystemApplicationRemoveKeywords(ssh).cleanup_app_if_present(NODE_FEATURE_DISCOVERY_APP, force_removal=True)
        for ctrl in controllers:
            hostname = ctrl.get_host_name()
            get_logger().log_teardown_step(f"Remove power-management label from {hostname}")
            SystemHostLabelKeywords(ssh).lock_host_remove_labels_and_unlock(hostname, [POWER_MANAGEMENT_LABEL_KEY])
        get_logger().log_teardown_step("Delete C-state YAML file")
        FileKeywords(ssh).delete_file(CSTATE_YAML_FILE)

    request.addfinalizer(_teardown)

    get_logger().log_test_case_step(f"Upload and apply {NODE_FEATURE_DISCOVERY_APP}")
    SystemApplicationUploadKeywords(ssh).system_application_upload_and_apply_app(
        app_name=NODE_FEATURE_DISCOVERY_APP,
        tar_file_path=f"{HELM_APP_BASE_PATH}{NODE_FEATURE_DISCOVERY_APP}*.tgz",
    )

    SystemApplicationUploadKeywords(ssh).system_application_upload_and_apply_app(
        app_name=KUBERNETES_POWER_MANAGER_APP,
        tar_file_path=f"{HELM_APP_BASE_PATH}{KUBERNETES_POWER_MANAGER_APP}*.tgz",
    )

    get_logger().log_test_case_step("Assign power-management=enabled label to controllers")
    for ctrl in controllers:
        hostname = ctrl.get_host_name()
        SystemHostLabelKeywords(ssh).lock_host_assign_labels_and_unlock(hostname, [POWER_MANAGEMENT_LABEL])

    get_logger().log_test_case_step(f"Get application-isolated CPU cores on {active_controller}")
    cpu_output = SystemHostCPUKeywords(ssh).get_system_host_cpu_list(active_controller)
    isol_cores = [c.get_log_core() for c in cpu_output.get_system_host_cpu_objects(assigned_function="Application-isolated")]
    if not isol_cores:
        raise RuntimeError(f"No Application-isolated cores found on {active_controller}")
    get_logger().log_info(f"Application-isolated cores: {isol_cores}")

    get_logger().log_test_case_step("Create cstate-c1-enabled.yaml for isolated cores")
    yaml_lines = ["cstatesProfile:", f"  {active_controller}:", "    individualCoreCStates:"]
    for core in isol_cores:
        yaml_lines += [
            f'      "{core}":',
            "        C1: true",
            "        C1E: false",
            "        C6: false",
            "        POLL: true",
        ]
    yaml_lines.append("nfd-required: false")
    yaml_content = "\n".join(yaml_lines)
    FileKeywords(ssh).create_file_with_heredoc(CSTATE_YAML_FILE, yaml_content)

    get_logger().log_test_case_step("Update helm override with C-state config")
    SystemHelmOverrideKeywords(ssh).update_helm_override(
        yaml_file=CSTATE_YAML_FILE,
        app_name=KUBERNETES_POWER_MANAGER_APP,
        chart_name=KUBERNETES_POWER_MANAGER_APP,
        namespace="intel-power",
    )

    get_logger().log_test_case_step("Remove node-feature-discovery and re-apply kubernetes-power-manager")
    SystemApplicationRemoveKeywords(ssh).cleanup_app_if_present(NODE_FEATURE_DISCOVERY_APP, force_removal=True)

    SystemApplicationApplyKeywords(ssh).system_application_apply(KUBERNETES_POWER_MANAGER_APP)
    get_logger().log_info("Kubernetes power manager setup completed successfully")

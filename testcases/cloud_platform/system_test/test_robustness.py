import math
import time
from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.system_test.timing_logger import TimingLogger
from keywords.system_test.kpi_extractor import KpiExtractor
from keywords.system_test.setup_stress_pods import SetupStressPods

@mark.p0
@mark.lab_has_standby_controller
def test_standby_controller_lock_unlock() -> None:
    """Test lock and unlock operations on standby controller.

    This test verifies that the standby controller can be successfully
    locked and unlocked, measuring timing from logs and pod readiness time.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    host_keywords = SystemHostLockKeywords(ssh_connection)
    pod_keywords = KubectlGetPodsKeywords(ssh_connection)
    timing_logger = TimingLogger("standby_controller_lock_unlock", 
                                 column_headers=["Lock Time (s)", "Unlock Time (s)", "Pod Recovery Time (s)"])
    log_extractor = KpiExtractor(ssh_connection)

    standby_controller = host_list_keywords.get_standby_controller()
    validate_equals(standby_controller is not None, True, "No standby controller available for testing")

    stress_pods = SetupStressPods(ssh_connection)
    stress_pods.setup_stress_pods(benchmark="mixed") 

    standby_name = standby_controller.get_host_name()
    get_logger().log_info(f"Testing lock/unlock on standby controller: {standby_name}")

    get_logger().log_info(f"Locking standby controller {standby_name}...")
    host_keywords.lock_host(standby_name)
    get_logger().log_info(f"Standby controller {standby_name} locked successfully")

    get_logger().log_info(f"Unlocking standby controller {standby_name}...")
    host_keywords.unlock_host(standby_name)
    get_logger().log_info(f"Standby controller {standby_name} unlocked successfully")

    get_logger().log_info("Measuring time for all pods to be running...")
    start_pod_check = time.time()
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=600)
    pod_readiness_time = time.time() - start_pod_check
    get_logger().log_info(f"All pods ready in {pod_readiness_time:.2f} seconds")

    get_logger().log_info("Extracting lock/unlock timings from logs...")
    lock_time = log_extractor.extract_lock_timing(standby_name)
    unlock_time = log_extractor.extract_unlock_timing(standby_name)

    get_logger().log_info(f"Lock operation completed in {lock_time:.2f} seconds (from logs)")
    get_logger().log_info(f"Unlock operation completed in {unlock_time:.2f} seconds (from logs)")
    timing_logger.log_timings(lock_time, unlock_time, pod_readiness_time)
    get_logger().log_info(f"Standby controller {standby_name} lock/unlock test completed successfully")
    

@mark.p0
@mark.lab_is_simplex
def test_lock_unlock_simplex() -> None:
    """Test lock and unlock operations on active controller for simplex systems only.

    This test verifies that the active controller can be successfully
    locked and unlocked on AIO-SX systems, measuring timing from logs and pod readiness time.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_show_keywords = SystemShowKeywords(ssh_connection)
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    host_keywords = SystemHostLockKeywords(ssh_connection)
    pod_keywords = KubectlGetPodsKeywords(ssh_connection)
    timing_logger = TimingLogger("active_controller_lock_unlock_simplex", column_headers=["Lock Time (s)", "Unlock Time (s)", "Pod Recovery Time (s)"])
    log_extractor = KpiExtractor(ssh_connection)

    stress_pods = SetupStressPods(ssh_connection)
    stress_pods.setup_stress_pods(benchmark="mixed") 

    # Check if system is simplex
    system_type = system_show_keywords.system_show().get_system_show_object().get_system_type()
    validate_equals(system_type, "All-in-one", "Test only valid for simplex systems")

    active_controller = host_list_keywords.get_active_controller()
    active_name = active_controller.get_host_name()
    get_logger().log_info(f"Testing lock/unlock on active controller (simplex): {active_name}")

    get_logger().log_info(f"Locking active controller {active_name}...")
    host_keywords.lock_host(active_name)
    get_logger().log_info(f"Active controller {active_name} locked successfully")

    get_logger().log_info(f"Unlocking active controller {active_name}...")
    host_keywords.unlock_host(active_name)
    get_logger().log_info(f"Active controller {active_name} unlocked successfully")

    get_logger().log_info("Measuring time for all pods to be running...")
    start_pod_check = time.time()
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=600)
    pod_readiness_time = time.time() - start_pod_check
    get_logger().log_info(f"All pods ready in {pod_readiness_time:.2f} seconds")

    get_logger().log_info("Extracting lock/unlock timings from logs...")
    lock_time = log_extractor.extract_lock_timing(active_name)
    unlock_time = log_extractor.extract_unlock_timing(active_name)

    get_logger().log_info(f"Lock operation completed in {lock_time:.2f} seconds (from logs)")
    get_logger().log_info(f"Unlock operation completed in {unlock_time:.2f} seconds (from logs)")
    timing_logger.log_timings(lock_time, unlock_time, pod_readiness_time)

def _execute_worker_lock_unlock(worker_names: list[str], timing_logger: TimingLogger) -> None:
    """Execute lock/unlock operations on worker nodes and measure timing metrics.

    Args:
        worker_names: List of worker hostnames to lock/unlock.
        timing_logger: TimingLogger instance to record metrics.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_keywords = SystemHostLockKeywords(ssh_connection)
    pod_keywords = KubectlGetPodsKeywords(ssh_connection)
    log_extractor = KpiExtractor(ssh_connection)

    get_logger().log_test_case_step(f"Locking worker(s) {worker_names}...")
    lock_start = time.time()
    for worker_name in worker_names:
        host_keywords.lock_host(worker_name)

    get_logger().log_test_case_step("Measuring time for pod migration...")
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=600)
    pod_migration_time = time.time() - lock_start
    get_logger().log_info(f"Pods migrated in {pod_migration_time:.2f} seconds")

    get_logger().log_test_case_step(f"Unlocking worker(s) {worker_names}...")
    for worker_name in worker_names:
        host_keywords.unlock_host(worker_name)
    get_logger().log_info(f"Worker(s) {worker_names} unlocked successfully")

    get_logger().log_test_case_step("Waiting for hosts to be unlocked (available and enabled)...")
    for worker_name in worker_names:
        validate_equals(
            host_keywords.wait_for_host_unlocked(worker_name, unlock_wait_timeout=600),
            True,
            f"Host {worker_name} should be unlocked after unlock operation"
        )

    get_logger().log_info("Waiting for all pods to be running...")
    recovery_start = time.time()
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=600)
    pod_recovery_time = time.time() - recovery_start
    get_logger().log_info(f"All pods recovered in {pod_recovery_time:.2f} seconds")

    get_logger().log_info("Extracting timing from logs...")
    if len(worker_names) > 1:
        hosts_available_time = log_extractor.extract_max_timing_for_hosts(worker_names, 'extract_unlock_to_available_timing')
        hosts_enabled_time = log_extractor.extract_max_timing_for_hosts(worker_names, 'extract_unlock_to_enabled_timing')
        get_logger().log_info(f"Max host available time: {hosts_available_time:.2f} seconds (from logs)")
        get_logger().log_info(f"Max host enabled time: {hosts_enabled_time:.2f} seconds (from logs)")
    else:
        hosts_available_time = log_extractor.extract_unlock_to_available_timing(worker_names[0])
        hosts_enabled_time = log_extractor.extract_unlock_to_enabled_timing(worker_names[0])
        get_logger().log_info(f"Host available time: {hosts_available_time:.2f} seconds (from logs)")
        get_logger().log_info(f"Host enabled time: {hosts_enabled_time:.2f} seconds (from logs)")

    timing_logger.log_timings(pod_migration_time, hosts_available_time, hosts_enabled_time, pod_recovery_time)
    get_logger().log_info(f"Worker(s) {worker_names} lock/unlock test completed successfully")


def _execute_worker_reboot(worker_names: list[str], timing_logger: TimingLogger) -> None:
    """Execute hard reboot operations on worker nodes and measure timing metrics.

    Args:
        worker_names: List of worker hostnames to reboot.
        timing_logger: TimingLogger instance to record metrics.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    pod_keywords = KubectlGetPodsKeywords(ssh_connection)
    log_extractor = KpiExtractor(ssh_connection)

    get_logger().log_test_case_step(f"Hard rebooting worker(s) {worker_names}...")
    reboot_start = time.time()
    lab_connection = LabConnectionKeywords()
    for worker_name in worker_names:
        worker_ssh = lab_connection.get_compute_ssh(worker_name)
        worker_ssh.send_as_sudo("reboot")
    get_logger().log_info(f"Reboot command issued for worker(s) {worker_names}")

    get_logger().log_test_case_step("Waiting for pod migration...")
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed", "Pending"], timeout=600)
    pod_migration_time = time.time() - reboot_start
    get_logger().log_info(f"Pods migrated in {pod_migration_time:.2f} seconds")

    time.sleep(30)
    get_logger().log_test_case_step("Waiting for hosts to be unlocked (available and enabled)...")
    for worker_name in worker_names:
        validate_equals(
            host_lock_keywords.wait_for_host_unlocked(worker_name, unlock_wait_timeout=600),
            True,
            f"Host {worker_name} should be unlocked after reboot"
        )

    recovery_start = time.time()
    get_logger().log_test_case_step("Waiting for all pods to be running...")
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=600)
    pod_recovery_time = time.time() - recovery_start
    get_logger().log_info(f"All pods recovered in {pod_recovery_time:.2f} seconds")

    get_logger().log_test_case_step("Extracting timing from logs...")
    if len(worker_names) > 1:
        hosts_available_time = log_extractor.extract_max_timing_for_hosts(worker_names, 'extract_reboot_to_available_timing')
        hosts_enabled_time = log_extractor.extract_max_timing_for_hosts(worker_names, 'extract_reboot_to_enabled_timing')
    else:
        hosts_available_time = log_extractor.extract_reboot_to_available_timing(worker_names[0])
        hosts_enabled_time = log_extractor.extract_reboot_to_enabled_timing(worker_names[0])
        get_logger().log_info(f"Host available time: {hosts_available_time:.2f} seconds (from logs)")
        get_logger().log_info(f"Host enabled time: {hosts_enabled_time:.2f} seconds (from logs)")

    timing_logger.log_timings(pod_migration_time, hosts_available_time, hosts_enabled_time, pod_recovery_time)


@mark.p0
@mark.lab_has_compute
def test_lock_unlock_multiple_workers() -> None:
    """Test lock/unlock operations on multiple worker nodes.
    
    Steps:
    1. Setup stress pods with mixed benchmark
    2. Lock multiple worker nodes (1/3 of total workers)
    3. Measure pod migration time during lock
    4. Unlock worker nodes
    5. Wait for hosts to become available and enabled
    6. Measure pod recovery time
    7. Extract timing metrics from system logs
    8. Log all timing measurements
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    workers = host_list_keywords.get_computes()
    validate_equals(bool(workers), True, "No worker nodes available for testing")

    num_workers = math.ceil(len(workers) / 3)
    worker_names = [w.get_host_name() for w in workers[:num_workers]]
    get_logger().log_info(f"Testing lock/unlock on {num_workers} worker(s): {worker_names}")

    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")
    timing_logger = TimingLogger("worker_lock_unlock", 
                                 column_headers=["Pod Migration Time (s)", "Hosts Available Time (s)", 
                                                "Hosts Enabled Time (s)", "Pod Recovery Time (s)"])
    _execute_worker_lock_unlock(worker_names, timing_logger)


@mark.p0
@mark.lab_has_compute
def test_reboot_multiple_workers() -> None:
    """Test hard reboot operations on multiple worker nodes.
    
    Steps:
    1. Setup stress pods with mixed benchmark
    2. Issue hard reboot command to multiple workers (1/3 of total)
    3. Measure pod migration time during reboot
    4. Wait for hosts to become available and enabled after reboot
    5. Measure pod recovery time
    6. Extract timing metrics from system logs
    7. Log all timing measurements
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    workers = host_list_keywords.get_computes()
    validate_equals(bool(workers), True, "No worker nodes available for testing")

    num_workers = math.ceil(len(workers) / 3)
    worker_names = [w.get_host_name() for w in workers[:num_workers]]

    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")
    timing_logger = TimingLogger("worker_reboot", 
                                 column_headers=["Pod Migration Time (s)", "Hosts Available Time (s)", 
                                                "Hosts Enabled Time (s)", "Pod Recovery Time (s)"])
    _execute_worker_reboot(worker_names, timing_logger)


@mark.p0
@mark.lab_has_compute
def test_lock_unlock_single_workers() -> None:
    """Test lock/unlock operations on a single worker node.
    
    Steps:
    1. Setup stress pods with mixed benchmark
    2. Lock a single worker node
    3. Measure pod migration time during lock
    4. Unlock the worker node
    5. Wait for host to become available and enabled
    6. Measure pod recovery time
    7. Extract timing metrics from system logs
    8. Log all timing measurements
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    workers = host_list_keywords.get_computes()
    validate_equals(bool(workers), True, "No worker nodes available for testing")
    
    worker_names = [workers[0].get_host_name()]
    get_logger().log_info(f"Testing lock/unlock on single worker: {worker_names[0]}")

    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")
    timing_logger = TimingLogger("worker_lock_unlock_single", 
                                 column_headers=["Pod Migration Time (s)", "Host Available Time (s)", 
                                                "Host Enabled Time (s)", "Pod Recovery Time (s)"])
    _execute_worker_lock_unlock(worker_names, timing_logger)


@mark.p0
@mark.lab_has_compute
def test_reboot_single_worker() -> None:
    """Test hard reboot operation on a single worker node.
    
    Steps:
    1. Setup stress pods with mixed benchmark
    2. Issue hard reboot command to a single worker
    3. Measure pod migration time during reboot
    4. Wait for host to become available and enabled after reboot
    5. Measure pod recovery time
    6. Extract timing metrics from system logs
    7. Log all timing measurements
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    workers = host_list_keywords.get_computes()
    validate_equals(bool(workers), True, "No worker nodes available for testing")

    worker_names = [workers[0].get_host_name()]
    get_logger().log_info(f"Testing reboot on single worker: {worker_names[0]}")

    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")
    timing_logger = TimingLogger("worker_reboot_single", 
                                 column_headers=["Pod Migration Time (s)", "Host Available Time (s)", 
                                                "Host Enabled Time (s)", "Pod Recovery Time (s)"])
    _execute_worker_reboot(worker_names, timing_logger)



@mark.p0
@mark.lab_is_simplex
def test_reboot_simplex() -> None:
    """Test hard reboot on active controller for simplex systems only.

    Steps:
    1. Validate system is simplex (All-in-one)
    2. Setup stress pods with mixed benchmark
    3. Issue hard reboot command to active controller
    4. Wait for host to become available and enabled after reboot
    5. Measure pod recovery time
    6. Extract timing metrics from system logs (host available, host enabled)
    7. Log all timing measurements
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_show_keywords = SystemShowKeywords(ssh_connection)
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    pod_keywords = KubectlGetPodsKeywords(ssh_connection)
    timing_logger = TimingLogger("active_controller_reboot_simplex", 
                                 column_headers=["Host Available Time (s)", 
                                                "Host Enabled Time (s)",
                                                "Pod Recovery Time (s)"])
    log_extractor = KpiExtractor(ssh_connection)

    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")

    system_type = system_show_keywords.system_show().get_system_show_object().get_system_type()
    validate_equals(system_type, "All-in-one", "Test only valid for simplex systems")

    active_controller = host_list_keywords.get_active_controller()
    active_name = active_controller.get_host_name()

    get_logger().log_test_case_step(f"Hard rebooting active controller {active_name}...")
    reboot_start = time.time()
    ssh_connection.send_as_sudo("reboot")

    time.sleep(30)
    get_logger().log_test_case_step("Waiting for host to be unlocked (available and enabled)...")
    validate_equals(
        host_lock_keywords.wait_for_host_unlocked(active_name, unlock_wait_timeout=600),
        True,
        f"Host {active_name} should be unlocked after reboot"
    )

    recovery_start = time.time()
    get_logger().log_test_case_step("Waiting for all pods to be running...")
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=600)
    pod_recovery_time = time.time() - recovery_start
    get_logger().log_info(f"All pods recovered in {pod_recovery_time:.2f} seconds")

    get_logger().log_test_case_step("Extracting timing from logs...")
    host_available_time = log_extractor.extract_reboot_to_available_timing(active_name)
    host_enabled_time = log_extractor.extract_reboot_to_enabled_timing(active_name)
    get_logger().log_info(f"Host available time: {host_available_time:.2f} seconds (from logs)")
    get_logger().log_info(f"Host enabled time: {host_enabled_time:.2f} seconds (from logs)")

    timing_logger.log_timings(host_available_time, host_enabled_time, pod_recovery_time)
    get_logger().log_info(f"Active controller {active_name} reboot test completed successfully")

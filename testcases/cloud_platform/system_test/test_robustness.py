import math
import random
import time
from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.system_test.timing_logger import TimingLogger
from keywords.system_test.kpi_extractor import KpiExtractor
from keywords.system_test.setup_stress_pods import SetupStressPods
from config.configuration_manager import ConfigurationManager
from keywords.cloud_platform.command_wrappers import source_openrc
from framework.ssh.ssh_connection_manager import SSHConnectionManager

def wait_for_ssh_connection_drop(ssh_connection: SSHConnection, timeout: int = 60) -> bool:
    """
    Wait for SSH connection to drop after reboot command.

    Args:
        ssh_connection (SSHConnection): SSH connection to monitor.
        timeout (int): Maximum time to wait for connection drop in seconds.

    Returns:
        bool: True if connection dropped, False if timeout reached.

    """
    start_time = time.time()
    check_interval = 10
    get_logger().log_info(f"Waiting for SSH connection to drop (timeout: {timeout}s)...")
    
    while time.time() - start_time < timeout:
        time.sleep(check_interval)
        try:
            ssh_connection.client.exec_command("echo test", timeout=3)
            get_logger().log_debug("Connection still active, checking again...")
        except Exception as e:
            get_logger().log_info(f"SSH connection dropped: {str(e)}")
            return True
        

    get_logger().log_warning(f"SSH connection did not drop within {timeout}s")
    return False


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

    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")

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

    get_logger().log_test_case_step("Counting pods before lock...")
    pods_output = pod_keywords.get_pods(namespace="mixed-benchmark")
    expected_pod_count = len(pods_output.get_pods_with_status("Running"))
    get_logger().log_info(f"Found {expected_pod_count} Running pods in mixed-benchmark namespace before reboot")

    get_logger().log_test_case_step(f"Locking worker(s) {worker_names}...")
    lock_start = time.time()
    for worker_name in worker_names:
        host_keywords.lock_host(worker_name)
    

    get_logger().log_test_case_step("Waiting for pod migration...")
    while time.time() < lock_start + 1200:
        pods_output = pod_keywords.get_pods(namespace="mixed-benchmark")
        pods_in_valid_status = (
            pods_output.get_pods_with_status("Running") +
            pods_output.get_pods_with_status("Succeeded") +
            pods_output.get_pods_with_status("Completed") +
            pods_output.get_pods_with_status("Pending")
        )
        current_count = len(pods_in_valid_status)
        terminating_count = len(pods_output.get_pods_with_status("Terminating"))
        get_logger().log_info(f"Expected pods: {expected_pod_count}, Current pods in valid status: {current_count}, Terminating: {terminating_count}")
        if current_count == expected_pod_count:
            break
        time.sleep(5)
    pod_migration_time = time.time() - lock_start
    get_logger().log_info(f"Pods migrated in {pod_migration_time:.2f} seconds")
    validate_equals(current_count, expected_pod_count, f"Expected {expected_pod_count} pods in valid status after migration")


    get_logger().log_test_case_step(f"Unlocking worker(s) {worker_names}...")
    for worker_name in worker_names:
        ssh_connection.send(source_openrc(f"system host-unlock {worker_name}"))
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
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=1200)
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

    
    get_logger().log_test_case_step("Counting pods before reboot...")
    pods_output = pod_keywords.get_pods(namespace="mixed-benchmark")
    expected_pod_count = len(pods_output.get_pods_with_status("Running"))
    get_logger().log_info(f"Found {expected_pod_count} Running pods in mixed-benchmark namespace before reboot")

    
    get_logger().log_test_case_step(f"Hard rebooting worker(s) {worker_names}...")
    reboot_start = time.time()
    lab_connection = LabConnectionKeywords()
    for worker_name in worker_names:
        worker_ssh = lab_connection.get_compute_ssh(worker_name)
        worker_ssh.send_as_sudo("reboot")
    get_logger().log_info(f"Reboot command issued for worker(s) {worker_names}")

    get_logger().log_test_case_step("Waiting for worker(s) to go offline or degraded...")
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    
    def is_worker_offline_or_degraded(worker_name: str) -> bool:
        availability = host_list_keywords.get_system_host_list().get_host(worker_name).get_availability()
        return availability in ["offline", "degraded"]
    
    for worker_name in worker_names:
        validate_equals_with_retry(
            lambda name=worker_name: is_worker_offline_or_degraded(name),
            expected_value=True,
            validation_description=f"Waiting for {worker_name} to go offline or degraded",
            timeout=300
        )

    get_logger().log_test_case_step("Waiting for pod migration...")
    while time.time() < reboot_start + 1200:
        pods_output = pod_keywords.get_pods(namespace="mixed-benchmark")
        pods_in_valid_status = (
            pods_output.get_pods_with_status("Running") +
            pods_output.get_pods_with_status("Succeeded") +
            pods_output.get_pods_with_status("Completed") +
            pods_output.get_pods_with_status("Pending")
        )
        current_count = len(pods_in_valid_status)
        terminating_count = len(pods_output.get_pods_with_status("Terminating"))
        get_logger().log_info(f"Expected pods: {expected_pod_count}, Current pods in valid status: {current_count}, Terminating: {terminating_count}")
        if current_count == expected_pod_count:
            break
        time.sleep(5)
    pod_migration_time = time.time() - reboot_start
    get_logger().log_info(f"Pods migrated in {pod_migration_time:.2f} seconds")
    validate_equals(current_count, expected_pod_count, f"Expected {expected_pod_count} pods in valid status after migration")

    get_logger().log_test_case_step("Waiting for hosts to be unlocked (available and enabled)...")
    for worker_name in worker_names:
        validate_equals(
            host_lock_keywords.wait_for_host_unlocked(worker_name, unlock_wait_timeout=1200),
            True,
            f"Host {worker_name} should be unlocked after reboot"
        )

    recovery_start = time.time()
    get_logger().log_test_case_step("Waiting for all pods to be running...")
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=1200)
    pod_recovery_time = time.time() - recovery_start
    get_logger().log_info(f"All pods recovered in {pod_recovery_time:.2f} seconds")
    
    get_logger().log_test_case_step("Extracting timing from logs...")
    if len(worker_names) > 1:
        hosts_available_time = log_extractor.extract_max_timing_for_hosts(worker_names, 'extract_worker_reboot_to_available_timing')
        hosts_enabled_time = log_extractor.extract_max_timing_for_hosts(worker_names, 'extract_worker_reboot_to_enabled_timing')
    else:
        hosts_available_time = log_extractor.extract_worker_reboot_to_available_timing(worker_names[0])
        hosts_enabled_time = log_extractor.extract_worker_reboot_to_enabled_timing(worker_names[0])
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
    selected_workers = random.sample(workers, num_workers)
    worker_names = [w.get_host_name() for w in selected_workers]
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
    selected_workers = random.sample(workers, num_workers)
    worker_names = [w.get_host_name() for w in selected_workers]
    get_logger().log_info(f"Testing reboot on {num_workers} worker(s): {worker_names}")

    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")
    timing_logger = TimingLogger("worker_reboot", 
                                 column_headers=["Pod Migration Time (s)", "Hosts Available Time (s)", 
                                                "Hosts Enabled Time (s)", "Pod Recovery Time (s)"])
    _execute_worker_reboot(worker_names, timing_logger)


@mark.p0
@mark.lab_has_compute
def test_lock_unlock_single_worker() -> None:
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
    
    worker_name = [random.choice(workers).get_host_name()]
    get_logger().log_info(f"Testing lock/unlock on single worker: {worker_name[0]}")

    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")
    timing_logger = TimingLogger("worker_lock_unlock_single", 
                                 column_headers=["Pod Migration Time (s)", "Host Available Time (s)", 
                                                "Host Enabled Time (s)", "Pod Recovery Time (s)"])
    _execute_worker_lock_unlock(worker_name, timing_logger)


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

    worker_names = [random.choice(workers).get_host_name()]
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
    ssh_connection.send_as_sudo("reboot")
    wait_for_ssh_connection_drop(ssh_connection)

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


@mark.p0
def test_dead_office_recovery() -> None:
    """Test dead office recovery by powering off all hosts and measuring recovery time.
    
    Steps:
    1. Setup stress pods with mixed benchmark
    2. Validate BMC configuration for all hosts
    3. Power off all hosts using ipmitool
    4. Wait 1 minute
    5. Power on all hosts using ipmitool
    6. Measure time for all hosts to become unlocked/available
    7. Measure time for all pods to reach Running/Completed/Succeeded status
    8. Log timing measurements to CSV and HTML
    """
    
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    pod_keywords = KubectlGetPodsKeywords(ssh_connection)
    lab_config = ConfigurationManager.get_lab_config()
    timing_logger = TimingLogger("dead_office_recovery", 
                                 column_headers=["All Hosts Recovery Time (s)", "Pod Recovery Time (s)"])
    
    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")
    all_hosts = host_list_keywords.get_system_host_list().get_hosts()
    all_nodes = lab_config.get_nodes()
    get_logger().log_info(f"Found {len(all_nodes)} nodes in lab configuration")
    
    get_logger().log_test_case_step("Validating BMC configuration for all hosts...")
    for node in all_nodes:
        node_name = node.get_name()
        bm_ip = node.get_bm_ip()
        bm_username = node.get_bm_username()
        bm_password = lab_config.get_bm_password()
        
        validate_equals(bool(bm_ip and bm_ip != "None"), True, f"Node {node_name} has valid BMC IP")
        validate_equals(bool(bm_username), True, f"Node {node_name} has valid BMC username")
        validate_equals(bool(bm_password), True, f"Node {node_name} has valid BMC password")
    
    validate_equals(lab_config.is_use_jump_server(), True, "Jump server required for dead office recovery")
    jump_host_config = lab_config.get_jump_host_configuration()
    jump_ssh = SSHConnectionManager.create_ssh_connection(
        jump_host_config.get_host(),
        jump_host_config.get_credentials().get_user_name(),
        jump_host_config.get_credentials().get_password(),
        name="jump_host"
    )
    
    get_logger().log_test_case_step("Powering off all hosts from jump server...")
    for node in all_nodes:
        node_name = node.get_name()
        bm_ip = node.get_bm_ip()
        bm_username = node.get_bm_username()
        bm_password = lab_config.get_bm_password()
        
        get_logger().log_info(f"Powering off {node_name} (BMC: {bm_ip})")
        jump_ssh.send(f"ipmitool -I lanplus -H {bm_ip} -U {bm_username} -P {bm_password} chassis power off")
    
    get_logger().log_info("Simulating 1 minute of energy loss...")
    time.sleep(60)

    get_logger().log_test_case_step("Powering on all hosts from jump server...")
    recovery_start = time.time()
    for node in all_nodes:
        node_name = node.get_name()
        bm_ip = node.get_bm_ip()
        bm_username = node.get_bm_username()
        bm_password = lab_config.get_bm_password()
        
        get_logger().log_info(f"Powering on {node_name} (BMC: {bm_ip})")
        jump_ssh.send(f"ipmitool -I lanplus -H {bm_ip} -U {bm_username} -P {bm_password} chassis power on")
    
    get_logger().log_test_case_step("Waiting for all hosts to be unlocked...")
    for host in all_hosts:
        host_name = host.get_host_name()
        get_logger().log_info(f"Waiting for {host_name} to be unlocked...")
        validate_equals(
            host_lock_keywords.wait_for_host_unlocked(host_name, unlock_wait_timeout=1800),
            True,
            f"Host {host_name} should be unlocked after power on"
        )
    
    all_hosts_recovery_time = time.time() - recovery_start
    get_logger().log_info(f"All hosts recovered in {all_hosts_recovery_time:.2f} seconds")
    
    get_logger().log_test_case_step("Waiting for all pods to be running...")
    pod_recovery_start = time.time()
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed", "Unknown"], timeout=2400)
    pod_recovery_time = time.time() - pod_recovery_start
    get_logger().log_info(f"All pods recovered in {pod_recovery_time:.2f} seconds")
    
    timing_logger.log_timings(all_hosts_recovery_time, pod_recovery_time)
    get_logger().log_info("Dead office recovery test completed successfully")


@mark.p0
@mark.lab_has_standby_controller
def test_controllers_power_cycle() -> None:
    """Test controllers power cycle by powering off both controllers and measuring recovery time.
    
    Steps:
    1. Setup stress pods with mixed benchmark
    2. Validate BMC configuration for controllers
    3. Power off both controllers using ipmitool from jump server
    4. Wait 1 minute
    5. Power on both controllers using ipmitool from jump server
    6. Measure time for controllers to become unlocked/available
    7. Measure time for all pods to reach Running/Completed/Succeeded status
    8. Log timing measurements to CSV and HTML
    """
    
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    pod_keywords = KubectlGetPodsKeywords(ssh_connection)
    lab_config = ConfigurationManager.get_lab_config()
    timing_logger = TimingLogger("controllers_power_cycle", 
                                 column_headers=["Controllers Recovery Time (s)", "Pod Recovery Time (s)"])
    
    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")
    
    controllers = lab_config.get_controllers()
    bm_password = lab_config.get_bm_password()
    
    get_logger().log_test_case_step("Validating BMC configuration for controllers...")
    for controller in controllers:
        validate_equals(bool(controller.get_bm_ip() and controller.get_bm_ip() != "None"), True, f"Controller {controller.get_name()} has valid BMC IP")
        validate_equals(bool(controller.get_bm_username()), True, f"Controller {controller.get_name()} has valid BMC username")

    validate_equals(lab_config.is_use_jump_server(), True, "Jump server required for controllers power cycle")
    jump_host_config = lab_config.get_jump_host_configuration()
    jump_ssh = SSHConnectionManager.create_ssh_connection(
        jump_host_config.get_host(),
        jump_host_config.get_credentials().get_user_name(),
        jump_host_config.get_credentials().get_password(),
        name="jump_host"
    )
    
    get_logger().log_test_case_step("Powering off both controllers from jump server...")
    for controller in controllers:
        get_logger().log_info(f"Powering off {controller.get_name()} (BMC: {controller.get_bm_ip()})")
        jump_ssh.send(f"ipmitool -I lanplus -H {controller.get_bm_ip()} -U {controller.get_bm_username()} -P {bm_password} chassis power off")
    
    get_logger().log_info("Simulating 1 minute of energy loss...")
    time.sleep(60)
    
    get_logger().log_test_case_step("Powering on both controllers from jump server...")
    recovery_start = time.time()
    for controller in controllers:
        get_logger().log_info(f"Powering on {controller.get_name()} (BMC: {controller.get_bm_ip()})")
        jump_ssh.send(f"ipmitool -I lanplus -H {controller.get_bm_ip()} -U {controller.get_bm_username()} -P {bm_password} chassis power on")

    get_logger().log_test_case_step("Waiting for controllers to be unlocked...")
    for controller in controllers:
        get_logger().log_info(f"Waiting for {controller.get_name()} to be unlocked...")
        validate_equals(
            host_lock_keywords.wait_for_host_unlocked(controller.get_name(), unlock_wait_timeout=1800),
            True,
            f"Controller {controller.get_name()} should be unlocked after power on"
        )
    
    controllers_recovery_time = time.time() - recovery_start
    get_logger().log_info(f"Controllers recovered in {controllers_recovery_time:.2f} seconds")
    
    time.sleep(15)
    get_logger().log_test_case_step("Waiting for all pods to be running...")
    pod_recovery_start = time.time()
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed", "Unknown"], timeout=1800)
    pod_recovery_time = time.time() - pod_recovery_start
    get_logger().log_info(f"All pods recovered in {pod_recovery_time:.2f} seconds")
    
    timing_logger.log_timings(controllers_recovery_time, pod_recovery_time)
    get_logger().log_info("Controllers power cycle test completed successfully")


@mark.p0
@mark.lab_has_standby_controller
def test_controlled_swact() -> None:
    """Test controlled swact operation and measure timing.
    
    Steps:
    1. Setup stress pods with mixed benchmark
    2. Ensure standby controller is unlocked
    3. Perform controlled swact
    4. Wait for swact to complete
    5. Measure pod recovery time
    6. Extract swact timing from sm-customer.log
    7. Log timing measurements to CSV and HTML
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    swact_keywords = SystemHostSwactKeywords(ssh_connection)
    pod_keywords = KubectlGetPodsKeywords(ssh_connection)
    log_extractor = KpiExtractor(ssh_connection)
    timing_logger = TimingLogger("controlled_swact", 
                                 column_headers=["Swact Time (s)", "Pod Recovery Time (s)"])
    
    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")
    
    standby_controller = host_list_keywords.get_standby_controller()
    validate_equals(standby_controller is not None, True, "No standby controller available for testing")
    standby_name = standby_controller.get_host_name()
    
    get_logger().log_test_case_step(f"Ensuring standby controller {standby_name} is unlocked...")
    if not host_lock_keywords.is_host_unlocked(standby_name):
        host_lock_keywords.unlock_host(standby_name)
    
    get_logger().log_test_case_step("Performing controlled swact...")
    swact_keywords.host_swact()
    get_logger().log_info("Swact completed successfully")
    recovery_start = time.time()

    get_logger().log_test_case_step("Waiting for all pods to be running...")
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=600)
    pod_recovery_time = time.time() - recovery_start
    get_logger().log_info(f"All pods recovered in {pod_recovery_time:.2f} seconds")
    
    get_logger().log_test_case_step("Extracting swact timing from logs...")
    swact_time = log_extractor.extract_swact_timing(standby_name)
    get_logger().log_info(f"Swact completed in {swact_time:.2f} seconds (from logs)")
    
    timing_logger.log_timings(swact_time, pod_recovery_time)
    get_logger().log_info("Controlled swact test completed successfully")


@mark.p0
@mark.lab_has_standby_controller
def test_uncontrolled_swact() -> None:
    """Test uncontrolled swact by rebooting active controller and measure timing.
    
    Steps:
    1. Setup stress pods with mixed benchmark
    2. Ensure standby controller is unlocked
    3. Reboot active controller to trigger uncontrolled swact
    4. Wait for standby to become active
    5. Wait for both controllers to be ready
    6. Measure pod recovery time
    7. Extract uncontrolled swact timing from sm-customer.log
    8. Log timing measurements to CSV and HTML
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    pod_keywords = KubectlGetPodsKeywords(ssh_connection)
    log_extractor = KpiExtractor(ssh_connection)
    timing_logger = TimingLogger("uncontrolled_swact", 
                                 column_headers=["Uncontrolled Swact Time (s)", "Pod Recovery Time (s)"])
    
    SetupStressPods(ssh_connection).setup_stress_pods(benchmark="mixed")
    
    active_controller = host_list_keywords.get_active_controller()
    standby_controller = host_list_keywords.get_standby_controller()
    validate_equals(standby_controller is not None, True, "No standby controller available for testing")
    
    active_name = active_controller.get_host_name()
    standby_name = standby_controller.get_host_name()
    
    get_logger().log_test_case_step(f"Ensuring standby controller {standby_name} is unlocked...")
    if not host_lock_keywords.is_host_unlocked(standby_name):
        host_lock_keywords.unlock_host(standby_name)
    
    get_logger().log_test_case_step(f"Rebooting active controller {active_name} to trigger uncontrolled swact...")
    ssh_connection.send_as_sudo("reboot")
    wait_for_ssh_connection_drop(ssh_connection)
    
    get_logger().log_test_case_step("Waiting for standby to become active...")
    validate_equals(
        host_lock_keywords.wait_for_host_unlocked(standby_name, unlock_wait_timeout=1800),
        True,
        f"Host {standby_name} should become active after uncontrolled swact"
    )
    
    time.sleep(60)
    get_logger().log_test_case_step(f"Waiting for {active_name} to be ready...")
    validate_equals(
        host_lock_keywords.wait_for_host_unlocked(active_name, unlock_wait_timeout=1800),
        True,
        f"Host {active_name} should be ready after reboot"
    )
    
    get_logger().log_test_case_step("Waiting for all pods to be running...")
    recovery_start = time.time()
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed","ContainerStatusUnknown"], timeout=1200)
    pod_recovery_time = time.time() - recovery_start
    get_logger().log_info(f"All pods recovered in {pod_recovery_time:.2f} seconds")
    
    get_logger().log_test_case_step("Extracting uncontrolled swact timing from logs...")
    uncontrolled_swact_time = log_extractor.extract_uncontrolled_swact_timing()
    get_logger().log_info(f"Uncontrolled swact completed in {uncontrolled_swact_time:.2f} seconds (from logs)")
    
    timing_logger.log_timings(uncontrolled_swact_time, pod_recovery_time)
    get_logger().log_info("Uncontrolled swact test completed successfully")

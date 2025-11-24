from time import time
from pytest import mark

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.system_test.timing_logger import TimingLogger
from keywords.system_test.kpi_extractor import KpiExtractor
from keywords.system_test.setup_stress_pods import SetupStressPods

@mark.p0
def test_standby_controller_lock_unlock():
    """
    Test lock and unlock operations on standby controller.

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
    assert standby_controller is not None, "No standby controller available for testing"

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
    start_pod_check = time()
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=600)
    pod_readiness_time = time() - start_pod_check
    get_logger().log_info(f"All pods ready in {pod_readiness_time:.2f} seconds")

    get_logger().log_info("Extracting lock/unlock timings from logs...")
    lock_time = log_extractor.extract_lock_timing(standby_name)
    unlock_time = log_extractor.extract_unlock_timing(standby_name)

    get_logger().log_info(f"Lock operation completed in {lock_time:.2f} seconds (from logs)")
    get_logger().log_info(f"Unlock operation completed in {unlock_time:.2f} seconds (from logs)")
    timing_logger.log_timings(lock_time, unlock_time, pod_readiness_time)
    get_logger().log_info(f"Standby controller {standby_name} lock/unlock test completed successfully")
    

@mark.p0
def test_lock_unlock_simplex():
    """
    Test lock and unlock operations on active controller for simplex systems only.

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
    assert system_type == "All-in-one", f"Test only valid for simplex systems"

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
    start_pod_check = time()
    pod_keywords.wait_for_all_pods_status(["Running", "Succeeded", "Completed"], timeout=600)
    pod_readiness_time = time() - start_pod_check
    get_logger().log_info(f"All pods ready in {pod_readiness_time:.2f} seconds")

    get_logger().log_info("Extracting lock/unlock timings from logs...")
    lock_time = log_extractor.extract_lock_timing(active_name)
    unlock_time = log_extractor.extract_unlock_timing(active_name)

    get_logger().log_info(f"Lock operation completed in {lock_time:.2f} seconds (from logs)")
    get_logger().log_info(f"Unlock operation completed in {unlock_time:.2f} seconds (from logs)")
    timing_logger.log_timings(lock_time, unlock_time, pod_readiness_time)
    get_logger().log_info(f"Active controller {active_name} lock/unlock test completed successfully")
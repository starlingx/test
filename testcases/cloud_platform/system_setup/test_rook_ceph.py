from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_list_contains_with_retry
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.controllerfs.system_controllerfs_keywords import SystemControllerFSKeywords
from keywords.cloud_platform.system.controllerfs.system_controllerfs_show_keywords import SystemControllerFSShowKeywords
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_disk_keywords import SystemHostDiskKeywords
from keywords.cloud_platform.system.host.system_host_fs_keywords import SystemHostFSKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_stor_keywords import SystemHostStorageKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.storage.system_storage_backend_keywords import SystemStorageBackendKeywords


def _setup_rook_ceph():
    """
    - Check if each host has at least 4 CPUs dedicated to 'platform'
    - Add the CPUs if needed
    - Check if there are no active alarms
    - Check if no storage backend is configured
    - Create rook-ceph storage backend
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    alarm_list_keyword = AlarmListKeywords(ssh_connection)
    alarm_host_cpu_keywords = SystemHostCPUKeywords(ssh_connection)
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    system_host_swact_keywords = SystemHostSwactKeywords(ssh_connection)

    full_host_list = system_host_list_keywords.get_system_host_list()
    host_controllers = full_host_list.get_controller_names()
    lab_type = ConfigurationManager.get_lab_config().get_lab_type()

    get_logger().log_setup_step("Checking if each host has at least 4 CPUs dedicated to 'platform'")

    for host_controller in host_controllers:
        cpu_platform_count = alarm_host_cpu_keywords.get_system_host_cpu_list(host_controller).get_function_count("platform")
        active_host = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

        if cpu_platform_count < 4:
            missing_cpus = 4 - cpu_platform_count
            get_logger().log_setup_step(f"Adding {missing_cpus} CPUs dedicated to 'platform'")
            if host_controller == active_host and lab_type != "Simplex":
                system_host_swact_keywords.host_swact()

            system_host_lock_keywords.lock_host(host_controller)
            alarm_host_cpu_keywords.system_host_cpu_modify(hostname=host_controller, function="platform", num_cores_on_processor_0=missing_cpus)
            system_host_lock_keywords.unlock_host(host_controller)
            validate_equals(alarm_host_cpu_keywords.get_system_host_cpu_list(host_controller).get_function_count("platform"), 4, "Checking how many CPUs are dedicated to the platform")

    get_logger().log_setup_step("Checking if there are any active alarms...")
    alarms = alarm_list_keyword.alarm_list()

    validate_equals(alarms, [], "Checking if there are any active alarms...")

    get_logger().log_setup_step("Check if no storage back end is configured")

    validate_equals(system_storage_backend_keywords.get_system_storage_backend_list().is_backend_empty(), True, "Check if no storage back end is configured")

    get_logger().log_test_case_step("Add rook-ceph as storage backend.")
    system_storage_backend_keywords.system_storage_backend_add(backend="ceph-rook", confirmed=True, deployment_model="controller")


def _add_ceph_monitor_host_fs():
    """
    Create ceph-monitors for all controllers nodes
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)

    full_host_list = system_host_list_keywords.get_system_host_list()
    host_controllers = full_host_list.get_controller_names()

    get_logger().log_test_case_step("Create ceph-monitors for the controllers")

    for host_name in host_controllers:
        get_logger().log_info(f"Creating host-fs ceph for host: {host_name}")
        SystemHostFSKeywords(ssh_connection).system_host_fs_add(host_name, "ceph", 20)


def _add_ceph_monitor_osd():
    """
    - Add OSD's for all controllers
    - Installing the rook-ceph application
    - Verify that they are now in the `configured` state.
    - Wait for all Alarms cleared
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_stor_keyword = SystemHostStorageKeywords(ssh_connection)
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    system_app_apply_keywords = SystemApplicationApplyKeywords(ssh_connection)
    alarm_list_keyword = AlarmListKeywords(ssh_connection)

    full_host_list = system_host_list_keywords.get_system_host_list()

    app_name = "rook-ceph"
    app_status_list = ["applied"]

    get_logger().log_test_case_step("Add OSD's for all controllers")
    host_controllers = full_host_list.get_controller_names()

    for host_controller in host_controllers:
        disk_output = SystemHostDiskKeywords(ssh_connection).get_system_host_disk_list(host_controller)
        uuids_output = disk_output.get_all_uuid()
        system_host_stor_keyword.system_host_stor_add(host_controller, uuids_output)
        validate_equals_with_retry(lambda: system_host_stor_keyword.get_system_host_stor_list(host_controller).get_state_osd(), ["configuring-with-app"], "Checking if the osd state changed to configuring-with-app")

    get_logger().log_test_case_step("Installing the rook-ceph application")
    get_logger().log_info("Wait for rook-ceph in applied status")
    SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=1500, polling_sleep_time=10)

    get_logger().log_test_case_step("Verify that they are now in the `configured` state.")

    if all("configured" in system_host_stor_keyword.get_system_host_stor_list(host_controller).get_state_osd() for host_controller in host_controllers):
        get_logger().log_info("All OSDs are in configured state.")
    else:
        get_logger().log_info(f"Reapplying app '{app_name}'...")
        system_app_apply_keywords.system_application_apply(app_name=app_name, timeout=1500, polling_sleep_time=10)

        for host_controller in host_controllers:
            validate_equals_with_retry(lambda: system_host_stor_keyword.get_system_host_stor_list(host_controller).get_state_osd(), ["configured"], "Checking if the osd state changed to configured", timeout=300, polling_sleep_time=10)

    get_logger().log_test_case_step("Wait for all Alarms cleared")
    alarm_list_keyword.wait_for_all_alarms_cleared()


@mark.lab_is_simplex
def test_rook_ceph_installation_model_controller_simplex():
    """
    Test case: rook-ceph installation

    Setup:
        - Check if each host has at least 4 CPUs dedicated to 'platform'
        - Check if there are no active alarms
        - Check if no storage backend is configured
        - Create rook-ceph storage backend

    Test Steps:
        - Create ceph-monitors for all controllers
        - Add OSD's for all controllers
        - Installing the rook-ceph application
        - Verify that they are now in the `configured` state.
        - Wait for all Alarms cleared
    """

    _setup_rook_ceph()
    _add_ceph_monitor_host_fs()
    _add_ceph_monitor_osd()


@mark.lab_is_duplex
def test_rook_ceph_installation_model_controller_duplex():
    """
    Test case: rook-ceph installation

    Setup:
        - Check if each host has at least 4 CPUs dedicated to 'platform'
        - Check if there are no active alarms
        - Check if no storage backend is configured
        - Create rook-ceph storage backend

    Test Steps:
        - Create ceph-monitors for all controllers
        - Add OSD's for all controllers
        - Installing the rook-ceph application
        - Verify that they are now in the `configured` state.
        - Wait for all Alarms cleared
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)

    _setup_rook_ceph()
    _add_ceph_monitor_host_fs()

    get_logger().log_test_case_step("Add floating monitor")
    lock_host = SystemHostListKeywords(ssh_connection).get_standby_controller()
    lock_host_name = lock_host.get_host_name()
    system_host_lock_keywords.lock_host(lock_host_name)

    validate_equals(system_host_lock_keywords.wait_for_host_locked(lock_host_name), True, "Validate if the host is locked")
    get_logger().log_info(f"Creating floating monitor for host: {lock_host_name}")
    SystemControllerFSKeywords(ssh_connection).system_host_controllerfs_add("ceph", 20)
    validate_list_contains_with_retry(lambda: SystemControllerFSShowKeywords(ssh_connection).get_system_controllerfs_show("ceph-float").get_filesystems().get_state().get_status(), expected_values="available", validation_description="checking ceph float state")
    system_host_lock_keywords.unlock_host(lock_host_name)

    _add_ceph_monitor_osd()


@mark.lab_has_compute
def test_rook_ceph_installation_model_controller():
    """
    Test case: rook-ceph installation

    Setup:
        - Check if each host has at least 4 CPUs dedicated to 'platform'
        - Check if there are no active alarms
        - Check if no storage backend is configured
        - Create rook-ceph storage backend

    Test Steps:
        - Create ceph-monitors for all controllers
        - Create ceph-monitors on compute
        - Add OSD's for all controllers
        - Installing the rook-ceph application
        - Verify that they are now in the `configured` state.
        - Wait for all Alarms cleared
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)

    full_host_list = system_host_list_keywords.get_system_host_list()
    host_computes = full_host_list.get_computer_names()

    _setup_rook_ceph()
    _add_ceph_monitor_host_fs()

    get_logger().log_test_case_step("Create ceph-monitors on compute")
    SystemHostFSKeywords(ssh_connection).system_host_fs_add(host_computes[0], "ceph", 20)

    _add_ceph_monitor_osd()

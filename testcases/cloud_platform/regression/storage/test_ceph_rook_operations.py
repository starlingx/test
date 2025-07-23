from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_str_contains
from keywords.ceph.ceph_osd_pool_ls_detail_keywords import CephOsdPoolLsDetailKeywords
from keywords.ceph.ceph_status_keywords import CephStatusKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.host.system_host_fs_keywords import SystemHostFSKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.storage.system_storage_backend_keywords import SystemStorageBackendKeywords


@mark.p2
@mark.lab_rook_ceph
def test_ceph_rook_host_fs_operation():
    """
    Test case: [TC_34893] host-fs cmd operations testing. This TC was migrated from cgcs.

    Test Steps:
        - Make sure ceph-rook is storage backend
        - Verify if file system "image-conversion" or "ceph" is not exist on the active controller
        - Add size 2 G file system into the active controller
        - Verify that the file system added
        - Modify file size to 3G, the modification should be allowed
        - Modify file size to 1G, the modification should be rejected
        - delete file system on the active host
    Args: None
    Raises:
        ValueError: If both file system "image-conversion" or "ceph" are config in system,no fs available for testing
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)

    get_logger().log_test_case_step("\n\nCheck whether rook-ceph is configured as storage backend.\n")

    if not system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("ceph-rook"):
        get_logger().log_test_case_step("\n\nAdd rook-ceph as storage backend.\n")
        system_storage_backend_keywords.system_storage_backend_add(backend="ceph-rook", confirmed=True)

    backend_name = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_backend()
    get_logger().log_info(f"Backend is: {backend_name}")

    get_logger().log_test_case_step(f"\n\nCheck whether 'image-conversion' or 'ceph' file system exist on the {host}.\n")
    system_host_fs_keywords = SystemHostFSKeywords(ssh_connection)
    fs_name = ""
    if not system_host_fs_keywords.get_system_host_fs_list(host_name=host).is_fs_exist(fs_name="image-conversion"):
        fs_name = "image-conversion"
    elif not system_host_fs_keywords.get_system_host_fs_list(host_name=host).is_fs_exist(fs_name="ceph"):
        fs_name = "ceph"
    else:
        raise ValueError("Both 'image-conversion' and 'ceph' were not available for this test.")
    get_logger().log_info(f"{fs_name} is available for test.")

    fs_size = 2
    get_logger().log_test_case_step(f"\n\nAdd {fs_name} as size of {fs_size}GB into file system\n")
    system_host_fs_keywords.system_host_fs_add(hostname=host, fs_name=fs_name, fs_size=fs_size)

    def is_filesystem_exist():
        return system_host_fs_keywords.get_system_host_fs_list(host).is_fs_exist(fs_name)

    validate_equals_with_retry(is_filesystem_exist, True, f"{fs_name} should be added in 2 mins", 120, 5)

    curr_fs_size = system_host_fs_keywords.get_system_host_fs_list(host).get_system_host_fs(fs_name).get_size()
    validate_equals(curr_fs_size, fs_size, f"Tried to set {fs_name} to {fs_size}GB, actually set to {curr_fs_size}GB")

    def is_filesystem_ready():
        return system_host_fs_keywords.get_system_host_fs_list(host).get_system_host_fs(fs_name).get_state()

    validate_equals_with_retry(is_filesystem_ready, "Ready", f"{fs_name} is in Ready Status in 2 mins", 120, 5)

    fs_new_size = 3
    get_logger().log_test_case_step(f"\n\nIncrease {fs_name} size to {fs_new_size}GiB.\n")
    system_host_fs_keywords.system_host_fs_modify(hostname=host, fs_name=fs_name, fs_size=fs_new_size)
    curr_fs_size = system_host_fs_keywords.get_system_host_fs_list(host).get_system_host_fs(fs_name).get_size()
    validate_equals(curr_fs_size, fs_new_size, f"Tried to set {fs_name} to {fs_new_size}GB, actually set to {curr_fs_size}GB")
    validate_equals_with_retry(is_filesystem_ready, "Ready", f"{fs_name} is in Ready Status in 2 mins", 120, 5)

    fs_new_size = 1
    get_logger().log_test_case_step(f"\n\nDecrease {fs_name} to {fs_new_size}GiB, it should be rejected\n")
    msg = system_host_fs_keywords.system_host_fs_modify_with_error(hostname=host, fs_name=fs_name, fs_size=fs_new_size)
    get_logger().log_info(f"Error msg: {msg}.")
    validate_str_contains(msg[0], "should be bigger than", f"host-fs-modify decrease size should be rejected: {msg[0]}")

    get_logger().log_test_case_step(f"\n\nDelete {fs_name} file system on {host}.\n")
    system_host_fs_keywords.system_host_fs_delete(hostname=host, fs_name=fs_name)
    validate_equals_with_retry(is_filesystem_exist, False, f"{fs_name} should be deleted in 2 mins", 120, 5)


@mark.p2
@mark.lab_rook_ceph
def test_ceph_rook_capabilities_testing_open_model(request):
    """
    Test case: [TC_34918] WRCPPV-1015 ceph-rook backend capabilities testing for open model

    Test Steps:
        - Make sure the storage backend is ceph-rook.
        - Get original capabilities value
        - Test "open" model
        - Modify replication between 1:Max OSD number
        - Modify min_replication value
        - check whether "ceph osd pool ls detail" aligned with current replication

    Teardown:
        - Restore storage backend capabilities value to original value
        - check whether "ceph osd pool ls detail" aligned with current replication
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)

    get_logger().log_test_case_step("\n\nCheck whether rook-ceph is configured as storage backend.\n")

    if not system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("ceph-rook"):
        get_logger().log_test_case_step("\n\nAdd rook-ceph as storage backend.\n")
        system_storage_backend_keywords.system_storage_backend_add(backend="ceph-rook", confirmed=True)

    backend_name = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_backend()
    get_logger().log_info(f"Backend is: {backend_name}")

    get_logger().log_test_case_step("\n\nGet original backend capabilities value.\n")
    original_capa_obj = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities()
    original_deployment_model = original_capa_obj.get_deployment_model()
    original_replication = original_capa_obj.get_replication()
    original_min_replication = original_capa_obj.get_min_replication()
    get_logger().log_info(f"\nOriginal Capabilities deployment model is: {original_deployment_model}" f"\nOriginal Capabilities replication value is: {original_replication}" f"\nOriginal Capabilities min_replication value is: {original_min_replication}\n")

    def teardown_restore_original_capabilities():

        get_logger().log_test_case_step("\n\nRestore capabilities values to original if original value is changed .\n")
        curr_capa_obj = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities()
        curr_deployment_model = curr_capa_obj.get_deployment_model()
        curr_replication = curr_capa_obj.get_replication()
        curr_min_replication = curr_capa_obj.get_min_replication()
        get_logger().log_info(f"\nCurrent Capabilities deployment model is: {curr_deployment_model}" f"\nCurrent Capabilities replication value is: {curr_replication}" f"\nCurrent Capabilities min_replication value is: {curr_min_replication}\n" f"\nOriginal Capabilities deployment model is: {original_deployment_model}" f"\nOriginal Capabilities replication value is: {original_replication}" f"\nOriginal Capabilities min_replication value is: {original_min_replication}\n")

        if curr_replication != original_replication or curr_min_replication != original_min_replication:
            get_logger().log_info(f"\n\nModify replication value to {original_replication} and min_replication value to {original_min_replication}'.\n")
            system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", replication=original_replication, min_replication=original_min_replication)

        if curr_deployment_model != original_deployment_model:
            get_logger().log_info(f"\n\nModify deployment model to {original_deployment_model}.\n")
            system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", deployment_model=original_deployment_model)

        curr_capa_obj = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities()
        curr_deployment_model = curr_capa_obj.get_deployment_model()
        curr_replication = curr_capa_obj.get_replication()
        curr_min_replication = curr_capa_obj.get_min_replication()
        get_logger().log_info(f"\nCurrent Capabilities deployment model is: {curr_deployment_model}" f"\nCurrent Capabilities replication value is: {curr_replication}" f"\nCurrent Capabilities min_replication value is: {curr_min_replication}\n")
        validate_equals(curr_deployment_model, original_deployment_model, f"deployment model should be {original_deployment_model}")
        validate_equals(curr_replication, original_replication, f"replication value should be {original_replication}")
        validate_equals(curr_min_replication, original_min_replication, f"min_replication value should be {original_min_replication}")

        get_logger().log_test_case_step("\n\nCheck whether 'ceph osd pool ls detail' aligned with replication.\n")
        ceph_pool_keywords = CephOsdPoolLsDetailKeywords(ssh_connection)
        pool_update = ceph_pool_keywords.wait_for_ceph_osd_pool_replicated_size_update(pool_name=".mgr", expected_replicated_size=original_replication)
        validate_equals(pool_update, True, "Replicated value is updated.")

        pool_update = ceph_pool_keywords.wait_for_ceph_osd_pool_min_size_update(pool_name=".mgr", expected_min_size=original_min_replication)
        validate_equals(pool_update, True, "min_size value is updated.")

    request.addfinalizer(teardown_restore_original_capabilities)

    get_logger().log_test_case_step("\n\nMake sure the deployment model is open.\n")
    curr_deployment_model = original_deployment_model
    if original_deployment_model != "open":
        get_logger().log_test_case_step(f"\n\nModify deployment_model from '{original_deployment_model}' to 'open'.\n")
        system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", deployment_model="open")
        curr_deployment_model = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_deployment_model()
        validate_equals(curr_deployment_model, "open", "Current deployment model should be 'open'.")

    get_logger().log_info(f"\nCurrent Capabilities deployment model is: {curr_deployment_model};")

    get_logger().log_test_case_step("\n\nGet OSD number.\n")
    ceph_status_keywords = CephStatusKeywords(ssh_connection)
    ceph_status_output = ceph_status_keywords.ceph_status()
    osd_number = ceph_status_output.get_ceph_osd_count()
    get_logger().log_info(f"\nOSD number is: {osd_number};")

    # replication value should not be greater than osd number, and should not be zero
    if original_replication < osd_number:
        new_replication_value = osd_number
    elif original_replication == osd_number and original_replication != 1:
        new_replication_value = osd_number - 1
    else:
        raise ValueError(f"System has {osd_number} osd, but replication is {original_replication}, TC should not run.")

    get_logger().log_test_case_step(f"\n\nModify replication from {original_replication} to {new_replication_value}.\n")
    system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", replication=new_replication_value)
    curr_replication = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_replication()
    get_logger().log_info(f"\nCurrent Capabilities replication value is: {curr_replication};")
    validate_equals(curr_replication, new_replication_value, f"replication value should be {new_replication_value}")

    get_logger().log_test_case_step("\n\nCheck whether 'ceph osd pool ls detail' aligned with replication.\n")
    ceph_pool_keywords = CephOsdPoolLsDetailKeywords(ssh_connection)
    pool_update = ceph_pool_keywords.wait_for_ceph_osd_pool_replicated_size_update(pool_name=".mgr", expected_replicated_size=curr_replication)
    validate_equals(pool_update, True, "Replicated value should be updated.")

    get_logger().log_test_case_step("\n\nIt should be rejected if modifying min_replication value great than replication value.\n")
    new_min_replication_value = curr_replication + 1
    msg = system_storage_backend_keywords.system_storage_backend_modify_with_error(backend="ceph-rook", min_replication=new_min_replication_value)
    validate_str_contains(msg, "must be greater than", f"system backend modify should be failed: {msg}")

    curr_min_replication = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_min_replication()

    if curr_min_replication > 1:
        new_min_replication_value = 1
        get_logger().log_test_case_step(f"\n\nModify min_replication from {curr_min_replication} to {new_min_replication_value}.\n")
        system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", min_replication=new_min_replication_value)
        curr_min_replication = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_min_replication()
        get_logger().log_info(f"\nCurrent Capabilities min_replication value is: {curr_min_replication};")
        validate_equals(curr_min_replication, new_min_replication_value, f"min_replication value should be {new_min_replication_value}")

        get_logger().log_test_case_step("\n\nCheck whether 'ceph osd pool ls detail' aligned with min_replication.\n")
        ceph_pool_keywords = CephOsdPoolLsDetailKeywords(ssh_connection)
        pool_update = ceph_pool_keywords.wait_for_ceph_osd_pool_min_size_update(pool_name=".mgr", expected_min_size=curr_min_replication)
        validate_equals(pool_update, True, "Replicated min_size is updated.")


@mark.lab_rook_ceph
def test_lock_unlock_multiple_hosts():
    """
    Lock and unlock multiple nodes on a standard lab

    Test Steps:
        - Make sure ceph-rook is storage backend
        - Lock all hosts (excluding active controller)
        - Unlock all hosts
        - Check ceph-rook health OK
    Args: None
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    system_host_keywords = SystemHostListKeywords(ssh_connection)
    full_host_list = system_host_keywords.get_system_host_with_extra_column(["capabilities"])
    host_names = full_host_list.get_host_names_except_active_controller()

    ceph_status_keywords = CephStatusKeywords(ssh_connection)

    get_logger().log_test_case_step("Checking rook-ceph health before Lock/Unlock nodes.")
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)

    get_logger().log_test_case_step("Locking multiple nodes.")
    SystemHostLockKeywords.lock_multiple_hosts(ssh_connection, host_names)

    get_logger().log_test_case_step("Unlocking all previously locked nodes.")
    SystemHostLockKeywords.unlock_multiple_hosts(ssh_connection, host_names)

    get_logger().log_test_case_step("Checking ceph health after Lock/Unlock nodes.")
    ceph_status_keywords.wait_for_ceph_health_status(expect_health_status=True)


@mark.p2
@mark.lab_rook_ceph
@mark.lab_is_simplex
def test_ceph_rook_backend_deployment_model_operation_sx():
    """
    Test case: ceph-rook backend deployment model testing (SX).

    Test Steps:
        - Make sure ceph-rook is storage backend
        - Make sure the deployment model is "open"
        - Modifying deployment model "open" to "dedicated" should be rejected
        - change deployment model to "controller"
        - Modifying deployment model "controller" to "dedicated" should be rejected
        - Modifying deployment model to open if necessary
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)

    get_logger().log_test_case_step("Check whether rook-ceph is configured as storage backend.")

    if not system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("ceph-rook"):
        get_logger().log_test_case_step("Add rook-ceph as storage backend.")
        system_storage_backend_keywords.system_storage_backend_add(backend="ceph-rook", confirmed=True)

    backend_name = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_backend()
    get_logger().log_info(f"Backend is: {backend_name}")

    get_logger().log_test_case_step("Get original backend deployment model.")
    original_deployment_model = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_deployment_model()
    get_logger().log_info(f"Original Capabilities deployment model is: {original_deployment_model}")
    if original_deployment_model == "controller":
        get_logger().log_test_case_step(f"Modify deployment_model from '{original_deployment_model}' to 'open'.")
        system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", deployment_model="open")
        curr_deployment_model = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_deployment_model()
        validate_equals(curr_deployment_model, "open", "Current deployment model should be open.")

    get_logger().log_test_case_step("Modify deployment_model from 'open' to 'dedicated' should be rejected in SX system.")
    msg = system_storage_backend_keywords.system_storage_backend_modify_with_error(backend="ceph-rook", deployment_model="dedicated")
    validate_str_contains(msg, "OSDs deployed", f"system backend modify should be failed: {msg}")

    get_logger().log_test_case_step("Modify deployment_model from 'open' to 'controller'.")
    system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", deployment_model="controller")
    curr_deployment_model = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_deployment_model()
    validate_equals(curr_deployment_model, "controller", f"Current deployment model should be {curr_deployment_model}.")

    get_logger().log_test_case_step("Modify deployment_model from 'controller' to 'dedicated' should be rejected in SX system.")
    msg = system_storage_backend_keywords.system_storage_backend_modify_with_error(backend="ceph-rook", deployment_model="dedicated")
    validate_str_contains(msg, "not supported", f"system backend modify should be failed: {msg}")

    if original_deployment_model == "open":
        get_logger().log_test_case_step("Modify deployment_model from 'controller' to 'open'.")
        system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", deployment_model="open")
        curr_deployment_model = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_deployment_model()
        validate_equals(curr_deployment_model, "open", "Current deployment model should be 'open'.")


@mark.p2
@mark.lab_rook_ceph
@mark.lab_is_duplex
def test_ceph_rook_backend_deployment_model_operation_dx():
    """
    Test case: ceph-rook backend deployment model testing (DX).

    Test Steps:
        - Make sure ceph-rook is storage backend
        - Make sure the deployment model is "open"
        - Modifying deployment model "open" to "dedicated" should be rejected
        - change deployment model to "controller"
        - check whether rook-ceph app auto re-applied
        - Modifying deployment model "controller" to "dedicated" should be rejected
        - Modifying deployment model to open if necessary
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)

    get_logger().log_test_case_step("Check whether rook-ceph is configured as storage backend.")
    if not system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("ceph-rook"):
        get_logger().log_test_case_step("Add rook-ceph as storage backend.")
        system_storage_backend_keywords.system_storage_backend_add(backend="ceph-rook", confirmed=True)

    backend_name = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_backend()
    get_logger().log_info(f"Backend is: {backend_name}")

    get_logger().log_test_case_step("Get original backend deployment model.")
    original_deployment_model = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_deployment_model()
    get_logger().log_info(f"Original Capabilities deployment model is: {original_deployment_model}")

    if original_deployment_model == "controller":
        get_logger().log_test_case_step(f"Modify deployment_model from '{original_deployment_model}' to 'open'.")
        system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", deployment_model="open")
        curr_deployment_model = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_deployment_model()
        validate_equals(curr_deployment_model, "open", "Current deployment model should be open.")
        get_logger().log_info("Wait for rook-ceph app auto reapplied")
        app_name = "rook-ceph"
        app_status_list = ["applying"]
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=360, polling_sleep_time=5)
        app_status_list = ["applied"]
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=360, polling_sleep_time=10)

    get_logger().log_test_case_step("Modify deployment_model from 'open' to 'dedicated' should be rejected in DX system.")
    msg = system_storage_backend_keywords.system_storage_backend_modify_with_error(backend="ceph-rook", deployment_model="dedicated")
    validate_str_contains(msg, "OSDs deployed", f"system backend modify should be failed: {msg}")

    get_logger().log_test_case_step("Modify deployment_model from 'open' to 'controller'.")
    system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", deployment_model="controller")
    curr_deployment_model = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_deployment_model()
    validate_equals(curr_deployment_model, "controller", f"Current deployment model should be {curr_deployment_model}.")
    get_logger().log_info("Wait for rook-ceph app auto reapplied")
    app_name = "rook-ceph"
    app_status_list = ["applying"]
    SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=360, polling_sleep_time=5)
    app_status_list = ["applied"]
    SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=360, polling_sleep_time=10)

    get_logger().log_test_case_step("Modify deployment_model from 'controller' to 'dedicated' should be rejected in DX system.")
    msg = system_storage_backend_keywords.system_storage_backend_modify_with_error(backend="ceph-rook", deployment_model="dedicated")
    validate_str_contains(msg, "Unable to change", f"system backend modify should be failed: {msg}")

    if original_deployment_model == "open":
        get_logger().log_test_case_step("Modify deployment_model from 'controller' to 'open'.")
        system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", deployment_model="open")
        curr_deployment_model = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_capabilities().get_deployment_model()
        validate_equals(curr_deployment_model, "open", "Current deployment model should be 'open'.")
        get_logger().log_info("Wait for rook-ceph app auto reapplied")
        app_name = "rook-ceph"
        app_status_list = ["applying"]
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=360, polling_sleep_time=5)
        app_status_list = ["applied"]
        SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=360, polling_sleep_time=10)


@mark.p2
@mark.lab_rook_ceph
def test_ceph_rook_backend_services_operation():
    """
    Test case: ceph-rook backend services testing.

    Test Steps:
        - Make sure ceph-rook is storage backend
        - Test service block and ecblock could exist one only
        - Test take off service is not support
        - Add service if possible
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)

    get_logger().log_test_case_step("Check whether rook-ceph is configured as storage backend.")

    if not system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("ceph-rook"):
        get_logger().log_test_case_step("Add rook-ceph as storage backend.")
        system_storage_backend_keywords.system_storage_backend_add(backend="ceph-rook", confirmed=True)

    backend_name = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_backend()
    get_logger().log_info(f"Backend is: {backend_name}")

    get_logger().log_test_case_step("Get current services.")
    curr_services = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_services()
    get_logger().log_info(f"Current Services are {curr_services}")

    get_logger().log_test_case_step("Testing service block and ecblock could only exist one in system.")
    if "ecblock" in curr_services:
        new_services = f"block,{curr_services}"
    elif "block," in curr_services:
        new_services = f"ecblock,{curr_services}"
    else:
        new_services = f"block,ecblock,{curr_services}"

    msg = system_storage_backend_keywords.system_storage_backend_modify_with_error(backend="ceph-rook", services=new_services)
    validate_str_contains(msg, "not supported for the ceph-rook backend in same time", f"system backend modify should be rejected: {msg}")

    get_logger().log_test_case_step("Removing service is not supported.")
    # finding any one of the existing services, and then attempting to remove it
    if "," not in curr_services:
        # there is only one service
        sub_str = curr_services
    elif "object," in curr_services:
        sub_str = "object,"
    elif "block," in curr_services:
        sub_str = "block,"
    elif "ecblock," in curr_services:
        sub_str = "ecblock,"
    elif "filesystem," in curr_services:
        sub_str = "filesystem,"
    else:
        raise ValueError(f"invalid services {curr_services}")
    # remove sub_str
    new_services = curr_services.replace(sub_str, "")
    msg = system_storage_backend_keywords.system_storage_backend_modify_with_error(backend="ceph-rook", services=new_services)
    validate_str_contains(msg, "is not supported", f"system backend modify should be rejected: {msg}")

    if "block" not in curr_services and "ecblock" not in curr_services:
        new_service = "block"
    elif "filesystem" not in curr_services:
        new_service = "filesystem"
    elif "object" not in curr_services:
        new_service = "object"
    else:
        raise ValueError("This system just has no new service available to add for this testing and it is not an issue")

    get_logger().log_info("Make sure rook-ceph app in applied status")
    app_name = "rook-ceph"
    app_status_list = ["applied"]
    SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=360, polling_sleep_time=10)
    get_logger().log_test_case_step(f"Add new service: {new_service}.")
    new_services = f"{new_service},{curr_services}"
    system_storage_backend_keywords.system_storage_backend_modify(backend="ceph-rook", services=new_services)
    get_logger().log_info("Wait for rook-ceph app auto reapply starts")
    app_status_list = ["applying"]
    SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=360, polling_sleep_time=5)
    app_status_list = ["applied"]
    SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=360, polling_sleep_time=10)

    curr_services = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_services()
    get_logger().log_info(f"Current Services are {curr_services}")


@mark.p2
@mark.lab_rook_ceph
def test_ceph_rook_backend_delete_negative_testing():
    """
    Test case: ceph-rook backend delete cmd testing.

    Test Steps:
        - Make sure ceph-rook is storage backend
        - storage-backend-delete cmd negative test
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_storage_backend_keywords = SystemStorageBackendKeywords(ssh_connection)

    get_logger().log_test_case_step("Check whether rook-ceph is configured as storage backend.")

    if not system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("ceph-rook"):
        get_logger().log_test_case_step("Add rook-ceph as storage backend.")
        system_storage_backend_keywords.system_storage_backend_add(backend="ceph-rook", confirmed=True)

    backend_name = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_backend()
    get_logger().log_info(f"Backend is: {backend_name}")

    get_logger().log_test_case_step("backend delete cmd negative testing")
    get_logger().log_info("storage-backend-delete --force should not delete backend when rook-ceph app is applied.")
    msg = system_storage_backend_keywords.system_storage_backend_delete_with_error(backend="ceph-rook")
    validate_str_contains(msg, "Cannot delete", f"storage-backend-delete --force should not delete backend when app is applied: {msg}")

    get_logger().log_info("storage-backend-delete missing argument --force should be not supported.")
    msg = system_storage_backend_keywords.system_storage_backend_delete_without_force(backend="ceph-rook")
    validate_str_contains(msg, "not supported", f"storage-delete missing --force not supported: {msg}")


@mark.p2
@mark.lab_rook_ceph
def test_rook_ceph_applying_host_lock_reject_testing():
    """
    Test case: rook-ceph app applying host-lock reject testing (SX).

    Test Steps:
        - Make sure rook-ceph app in applied status
        - Apply rook-ceph application to make storage_backend task in "applying" status.
        - host-lock should be rejected.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_type = ConfigurationManager.get_lab_config().get_lab_type()

    get_logger().log_test_case_step("Check whether rook-ceph app in applied status")
    app_name = "rook-ceph"
    app_status_list = ["applied"]
    SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=360, polling_sleep_time=10)

    get_logger().log_test_case_step("Re-apply rook-ceph and make the app in 'applying' status.")
    app_status_list = ["applying"]
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name, wait_for_applied=False)
    app_status = SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=60, polling_sleep_time=5)

    get_logger().log_test_case_step(f"Host-lock should be rejected when app in '{app_status}' status.")
    if lab_type == "Simplex":
        lock_host = SystemHostListKeywords(ssh_connection).get_active_controller()
    else:
        lock_host = SystemHostListKeywords(ssh_connection).get_standby_controller()
    lock_host_name = lock_host.get_host_name()
    msg = SystemHostLockKeywords(ssh_connection).lock_host_with_error(lock_host_name)
    validate_str_contains(msg, "Rejected: The application rook-ceph is in transition", f"system host-lock rejected: {msg}")

    # Wait for rook-ceph in applied status
    app_status_list = ["applied"]
    SystemApplicationListKeywords(ssh_connection).validate_app_status_in_list(app_name, app_status_list, timeout=360, polling_sleep_time=10)

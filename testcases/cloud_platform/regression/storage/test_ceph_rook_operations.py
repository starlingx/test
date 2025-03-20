from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_fs_keywords import SystemHostFSKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.storage.system_storage_backend_keywords import SystemStorageBackendKeywords


@mark.p2
@mark.lab_ceph_rook
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

    get_logger().log_info("\n\nCheck whether rook-ceph is configured as storage backend.\n")

    if not system_storage_backend_keywords.get_system_storage_backend_list().is_backend_configured("ceph-rook"):
        get_logger().log_info("\n\nAdd rook-ceph as storage backend.\n")
        system_storage_backend_keywords.system_storage_backend_add(backend="ceph-rook", confirmed=True)

    backend_name = system_storage_backend_keywords.get_system_storage_backend_list().get_system_storage_backend("ceph-rook").get_backend()
    get_logger().log_info(f"Backend is: {backend_name}")

    get_logger().log_info(f"\n\nCheck whether 'image-conversion' or 'ceph' file system exist on the {host}.\n")
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
    get_logger().log_info(f"\n\nAdd {fs_name} as size of {fs_size}GB into file system\n")
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
    get_logger().log_info(f"\n\nIncrease {fs_name} size to {fs_new_size}GiB.\n")
    system_host_fs_keywords.system_host_fs_modify(hostname=host, fs_name=fs_name, fs_size=fs_new_size)
    curr_fs_size = system_host_fs_keywords.get_system_host_fs_list(host).get_system_host_fs(fs_name).get_size()
    validate_equals(curr_fs_size, fs_new_size, f"Tried to set {fs_name} to {fs_new_size}GB, actually set to {curr_fs_size}GB")
    validate_equals_with_retry(is_filesystem_ready, "Ready", f"{fs_name} is in Ready Status in 2 mins", 120, 5)

    fs_new_size = 1
    get_logger().log_info(f"\n\nDecrease {fs_name} to {fs_new_size}GiB, it should be rejected\n")
    msg = system_host_fs_keywords.system_host_fs_modify_with_error(hostname=host, fs_name=fs_name, fs_size=fs_new_size)
    get_logger().log_info(f"Error msg: {msg}.")
    validate_str_contains(msg[0], "should be bigger than", f"host-fs-modify decrease size should be rejected: {msg[0]}")

    get_logger().log_info(f"\n\nDelete {fs_name} file system on {host}\n.")
    system_host_fs_keywords.system_host_fs_delete(hostname=host, fs_name=fs_name)
    validate_equals_with_retry(is_filesystem_exist, False, f"{fs_name} should be deleted in 2 mins", 120, 5)

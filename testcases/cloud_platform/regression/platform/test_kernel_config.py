from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_kernel_keywords import SystemHostKernelKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords

KERNEL_CONFIGS = ["standard", "lowlatency"]
# CONFIG_FILE = 'deployment-config.yaml'


@mark.p0
@mark.lab_is_simplex
def test_modify_kernel_config_using_cli_aio_simplex(request):
    """
    Testcase to verify kernel config can be modified using DM
    Test Steps:
        - connect to active controller
        - get the cuttent kernel type
        - modify the kernel config using CLI
        - Revert back the kernel config changes

    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller()

    # Get the host name of the Active controller
    active_controller_host_name = active_controller.get_host_name()

    running_kernel = SystemHostKernelKeywords(ssh_connection).get_running_kernel("controller-0")
    get_logger().log_info(f"running Kernel on {active_controller_host_name} is {running_kernel}")

    new_kernel = next((config for config in KERNEL_CONFIGS if config not in running_kernel), None)

    get_logger().log_info(f"new Kernel to be configured:{new_kernel}")

    get_logger().log_info(f"lock host {active_controller_host_name} before kernel modification")
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(active_controller_host_name)
    validate_equals(lock_success, True, "Controller locked")
    # Modify the kernel config using DM
    SystemHostKernelKeywords(ssh_connection).modify_kernel_config(active_controller_host_name, new_kernel)

    get_logger().log_info(f"unlock host {active_controller_host_name} for new kernel configuraion")
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(active_controller_host_name)
    validate_equals(unlock_success, True, "Controller unlocked")

    # Verify the kernel config has been updated
    validate_equals(SystemHostKernelKeywords(ssh_connection).get_running_kernel(active_controller_host_name), new_kernel, "Kernel config updation")

    # Revert back the kernel config changes
    # Lock the controller
    get_logger().log_info(f"lock host {active_controller_host_name} before kernel modification")
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(active_controller_host_name)
    validate_equals(lock_success, True, "Controller locked")

    SystemHostKernelKeywords(ssh_connection).modify_kernel_config(active_controller_host_name, running_kernel)

    # unLock the controller
    get_logger().log_info(f"unlock host {active_controller_host_name} for kernel configuraion")
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(active_controller_host_name)
    validate_equals(unlock_success, True, "Controller unlocked")

    # Verify the kernel config has been reverted
    validate_equals(SystemHostKernelKeywords(ssh_connection).get_running_kernel(active_controller_host_name), running_kernel, "Kernel config has not been reverted")


@mark.p0
@mark.lab_has_standby_controller
def test_modify_kernel_config_using_cli_aio_duplex(request):
    """
    Testcase to verify kernel config can be modified using DM
    Test Steps:
        - connect to active controller
        - get the cuttent kernel type of standby controller
        - modify the kernel config using CLI for standby controller
        - Revert back the kernel config changes

    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    standby_controller = SystemHostListKeywords(ssh_connection).get_standby_controller()

    # Get the host name of the Standby controller
    standby_controller_host_name = standby_controller.get_host_name()

    running_kernel = SystemHostKernelKeywords(ssh_connection).get_running_kernel(standby_controller_host_name)
    get_logger().log_info(f"running Kernel on {standby_controller_host_name} is {running_kernel}")

    new_kernel = next((config for config in KERNEL_CONFIGS if config not in running_kernel), None)

    get_logger().log_info(f"new Kernel to be configured:{new_kernel}")

    get_logger().log_info(f"lock host {standby_controller_host_name} before kernel modification")
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(standby_controller_host_name)
    validate_equals(lock_success, True, "Controller locked")
    # Modify the kernel config using DM
    SystemHostKernelKeywords(ssh_connection).modify_kernel_config(standby_controller_host_name, new_kernel)

    get_logger().log_info(f"unlock host {standby_controller_host_name} for new kernel configuraion")
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(standby_controller_host_name)
    validate_equals(unlock_success, True, "Controller unlocked")

    # Verify the kernel config has been updated
    validate_equals(SystemHostKernelKeywords(ssh_connection).get_running_kernel(standby_controller_host_name), new_kernel, "Kernel config updation")

    # Revert back the kernel config changes
    # Lock the controller
    get_logger().log_info(f"lock host {standby_controller_host_name} before kernel modification")
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(standby_controller_host_name)
    validate_equals(lock_success, True, "Controller locked")

    SystemHostKernelKeywords(ssh_connection).modify_kernel_config(standby_controller_host_name, running_kernel)

    # unLock the controller
    get_logger().log_info(f"unlock host {standby_controller_host_name} for kernel configuraion")
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(standby_controller_host_name)
    validate_equals(unlock_success, True, "Controller unlocked")

    # Verify the kernel config has been reverted
    validate_equals(SystemHostKernelKeywords(ssh_connection).get_running_kernel(standby_controller_host_name), running_kernel, "Kernel config has not been reverted")


@mark.p0
@mark.lab_has_compute
def test_modify_kernel_config_using_cli_standard(request):
    """
    Testcase to verify kernel config can be modified using DM
    Test Steps:
        - connect to active controller
        - get the cuttent kernel type of compute node
        - modify the kernel config using CLI for compute node
        - Revert back the kernel config changes

    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    computes = SystemHostListKeywords(ssh_connection).get_computes()
    compute = computes[0]

    # Get the host name of the Standby controller
    compute_host_name = compute.get_host_name()

    running_kernel = SystemHostKernelKeywords(ssh_connection).get_running_kernel(compute_host_name)
    get_logger().log_info(f"running Kernel on {compute_host_name} is {running_kernel}")

    new_kernel = next((config for config in KERNEL_CONFIGS if config not in running_kernel), None)

    get_logger().log_info(f"new Kernel to be configured:{new_kernel}")

    get_logger().log_info(f"lock host {compute_host_name} before kernel modification")
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(compute_host_name)
    validate_equals(lock_success, True, "Controller locked")
    # Modify the kernel config using DM
    SystemHostKernelKeywords(ssh_connection).modify_kernel_config(compute_host_name, new_kernel)

    get_logger().log_info(f"unlock host {compute_host_name} for new kernel configuraion")
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(compute_host_name)
    validate_equals(unlock_success, True, "Controller unlocked")

    # Verify the kernel config has been updated
    validate_equals(SystemHostKernelKeywords(ssh_connection).get_running_kernel(compute_host_name), new_kernel, "Kernel config updation")

    # Revert back the kernel config changes
    # Lock the compute node
    get_logger().log_info(f"lock host {compute_host_name} before kernel modification")
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(compute_host_name)
    validate_equals(lock_success, True, "host locked")

    SystemHostKernelKeywords(ssh_connection).modify_kernel_config(compute_host_name, running_kernel)

    # unLock the host
    get_logger().log_info(f"unlock host {compute_host_name} for kernel configuraion")
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(compute_host_name)
    validate_equals(unlock_success, True, "host unlocked")

    # Verify the kernel config has been reverted
    validate_equals(SystemHostKernelKeywords(ssh_connection).get_running_kernel(compute_host_name), running_kernel, "Kernel config has not been reverted")

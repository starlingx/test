import yaml
from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.networking.sriov_fec.object.sriov_fec_device_config import VRB2
from keywords.cloud_platform.networking.sriov_fec.sriov_fec_operator_keywords import SriovFecOperatorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.sriov_vrb_node_config.kubectl_get_sriov_vrb_node_config_keywords import KubectlGetSriovVrbNodeConfigKeywords
from keywords.server.power_keywords import PowerKeywords


def apply_vrb2_configuration(ssh_connection: SSHConnection, pf_driver: str, vf_driver: str, index: int, base_path: str, host_name: str) -> str:
    """Apply sriov-fec-operator VRB2 configuration and verify it is applied.

    Kept local because VRB2 uses the SriovVrbNodeConfig keyword instead of the
    SriovFecNodeConfig keyword used by the shared helper.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        pf_driver (str): PF driver name.
        vf_driver (str): VF driver name.
        index (int): VRB2 device index.
        base_path (str): Remote directory where the file was created.
        host_name (str): Host name.

    Returns:
        str: Path to the applied accelerator configuration file.
    """
    operator_file = f"{base_path}/sriov-fec-operator-{pf_driver}-{vf_driver}-vrb2-{index}.yaml"

    get_logger().log_info("Apply sriov-fec-operator VRB2 card configuration file")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(operator_file)
    get_logger().log_info("Verify if sriov-fec-operator VRB2 card configuration file was applied")
    KubectlGetSriovVrbNodeConfigKeywords(ssh_connection).wait_for_configured_status(
        host_name,
        expected_status="InProgress",
        timeout=90,
        poll_interval=15,
    )
    KubectlGetSriovVrbNodeConfigKeywords(ssh_connection).wait_for_configured_status(host_name)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace="sriov-fec-system")

    return operator_file


def delete_vrb2_configuration(ssh_connection: SSHConnection, base_path: str, pf_driver: str, vf_driver: str, index: int, host_name: str) -> None:
    """Delete VRB2 card configuration and verify operator pods are running.

    Kept local because VRB2 uses the SriovVrbNodeConfig keyword instead of the
    SriovFecNodeConfig keyword used by the shared helper.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        base_path (str): Remote directory where files are located.
        pf_driver (str): PF driver name.
        vf_driver (str): VF driver name.
        index (int): VRB2 device index.
        host_name (str): Host name.
    """
    get_logger().log_info("Delete VRB2 configuration")
    KubectlFileDeleteKeywords(ssh_connection).delete_resources(f"{base_path}/sriov-fec-operator-{pf_driver}-{vf_driver}-vrb2-{index}.yaml")
    get_logger().log_info("Verify VRB2 card configuration was deleted and operator pods are running")
    KubectlGetSriovVrbNodeConfigKeywords(ssh_connection).wait_for_configured_status(
        host_name,
        expected_status="InProgress",
        timeout=90,
        poll_interval=15,
    )
    KubectlGetSriovVrbNodeConfigKeywords(ssh_connection).wait_for_configured_status(host_name)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace="sriov-fec-system")


def delete_remaining_node_config(ssh_connection: SSHConnection, last_configuration_file: str) -> None:
    """Delete SriovVrbNodeConfig for the node targeted by the configuration file.

    Kept local because VRB2 uses the SriovVrbNodeConfig keyword instead of the
    SriovFecNodeConfig keyword used by the shared helper.

    Extracts the node name from the configuration file's nodeSelector and checks
    if that specific node has active configuration before deleting.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        last_configuration_file (str): Path to the accelerator configuration file to delete.
    """
    get_logger().log_teardown_step("Delete SriovVrbNodeConfig resource from configuration file")

    # Extract node name from the configuration file's parsed nodeSelector
    file_kw = FileKeywords(ssh_connection)
    file_content = file_kw.read_file(last_configuration_file)
    parsed = yaml.safe_load(SriovFecOperatorKeywords._as_text(file_content)) or {}
    node_name = parsed.get("spec", {}).get("nodeSelector", {}).get("kubernetes.io/hostname")

    if not node_name:
        get_logger().log_info(f"Could not extract node name from {last_configuration_file}, skipping deletion")
        return

    get_logger().log_info(f"Configuration file targets node: {node_name}")

    sriov_vrb_kw = KubectlGetSriovVrbNodeConfigKeywords(ssh_connection)
    config = sriov_vrb_kw.get_sriov_vrb_node_configs().get_sriov_vrb_node_config_by_name(node_name)

    if config.get_configured() == "NotRequested":
        get_logger().log_info(f"Skipping {node_name}: status is NotRequested (no configuration loaded)")
        return

    yaml_output = sriov_vrb_kw.get_sriov_vrb_node_config_yaml(node_name)

    if not yaml_output.has_physical_functions():
        get_logger().log_info(f"Skipping {node_name}: no active physicalFunctions configured")
        return

    get_logger().log_info(f"Deleting SriovVrbNodeConfig: {node_name} (status: {config.get_configured()})")
    KubectlFileDeleteKeywords(ssh_connection).delete_resources(last_configuration_file)

    KubectlGetSriovVrbNodeConfigKeywords(ssh_connection).wait_for_configured_status(
        node_name,
        expected_status="InProgress",
        timeout=90,
        poll_interval=15,
    )
    KubectlGetSriovVrbNodeConfigKeywords(ssh_connection).wait_for_configured_status(node_name)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace="sriov-fec-system")


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_vrb2
@mark.lab_has_page_size_1gb
def test_fec_operator_pf_driver_igb_uio_vf_driver_igb_uio_vrb2(request: FixtureRequest) -> None:
    """Verify VRB2 FEC operator with igb_uio pf/vf drivers.

    Install sriov-fec-operator application and configure VRB2
    accelerator cards with pfDriver and vfDriver set to igb_uio
    drivers and run test-bbdev pods successfully against the
    configured devices.

    Preconditions:
        - Lab has VRB2 accelerator devices
        - Lab has SR-IOV capability
        - Lab has 1GB huge page size allocated

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all VRB2 accelerators and verify at least one is enabled
        2. Generate configuration YAML and pod files for each VRB2 device
        3. Generate bbdev script
        4. Upload and apply the sriov-fec-operator application
        5. For each VRB2 device:
            a. Apply VRB2 configuration and run accelerator pod
            b. Run bbdev script inside the pod and verify all tests passed
            c. Delete VRB2 configuration and pod resources

    Teardown:
        - Delete VRB2 accelerator card configuration if necessary and VRB2 pod
        - Delete VRB2 configuration and pod files
        - Remove and delete sriov-fec-operator application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pf_driver = "igb_uio"
    vf_driver = "igb_uio"
    base_path = "/home/sysadmin"
    last_configuration_file = None
    sriov_fec_operator_kw = SriovFecOperatorKeywords(ssh_connection)

    sriov_fec_operator_kw.cleanup_sriov_fec_operator_and_pods()

    def teardown():
        get_logger().log_teardown_step("Delete VRB2 pod resources")
        sriov_fec_operator_kw.delete_fec_pods()

        get_logger().log_teardown_step("Delete VRB2 configuration resources")
        if last_configuration_file:
            delete_remaining_node_config(ssh_connection, last_configuration_file)

        get_logger().log_teardown_step("Delete Generated Files")
        sriov_fec_operator_kw.delete_generated_files(VRB2, base_path)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        sriov_fec_operator_kw.cleanup_sriov_fec_operator()

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all VRB2 accelerators and verify at least one is enabled")
    vrb2_devices = sriov_fec_operator_kw.get_devices_address(VRB2)
    validate_not_equals(len(vrb2_devices), 0, "Enabled VRB2 devices found in the system")

    get_logger().log_test_case_step("Generate card configuration YAML files for each VRB2")
    sriov_fec_operator_kw.generate_configuration_file(VRB2, vrb2_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate pods file YAML files")
    sriov_fec_operator_kw.generate_pod_file(VRB2, vrb2_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate bbdev file script")
    bbdev_sh_name = sriov_fec_operator_kw.generate_bbdev_script(VRB2, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    sriov_fec_operator_kw.upload_install_sriov_fec_operator()

    for index, (host_name, device_address) in enumerate(vrb2_devices):
        get_logger().log_info(f"Processing device {index}: host={host_name}, address={device_address}")
        get_logger().log_test_case_step("Apply sriov-fec-operator VRB2 configuration")
        last_configuration_file = apply_vrb2_configuration(ssh_connection, pf_driver, vf_driver, index, base_path, host_name)
        get_logger().log_test_case_step("Run sriov-fec-operator VRB2 pod and verify if it is running")
        pod_name = sriov_fec_operator_kw.apply_pod(VRB2, pf_driver, vf_driver, index, base_path, host_name)

        get_logger().log_test_case_step("Run bbdev script inside the pod and verify all tests passed.")
        sriov_fec_operator_kw.run_and_verify_bbdev_test(pod_name, bbdev_sh_name, base_path)

        get_logger().log_test_case_step("Delete VRB2 card configuration and pod resources.")
        delete_vrb2_configuration(ssh_connection, base_path, pf_driver, vf_driver, index, host_name)
        sriov_fec_operator_kw.delete_pod(VRB2, base_path, pf_driver, vf_driver, index)


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_vrb2
@mark.lab_has_page_size_1gb
def test_fec_operator_pf_driver_igb_uio_vf_driver_vfio_pci_vrb2(request: FixtureRequest) -> None:
    """Verify VRB2 FEC operator with igb_uio pf and vfio-pci vf drivers.

    Install sriov-fec-operator application and configure VRB2
    accelerator cards with pfDriver is set to igb_uio and vfDriver
    set to vfio-pci and run test-bbdev pods successfully against the
    configured devices.

    Preconditions:
        - Lab has VRB2 accelerator devices
        - Lab has SR-IOV capability
        - Lab has 1GB huge page size allocated

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all VRB2 accelerators and verify at least one is enabled
        2. Generate configuration YAML and pod files for each VRB2 device
        3. Generate bbdev script
        4. Upload and apply the sriov-fec-operator application
        5. For each VRB2 device:
            a. Apply VRB2 configuration and run accelerator pod
            b. Run bbdev script inside the pod and verify all tests passed
            c. Delete VRB2 configuration and pod resources

    Teardown:
        - Delete VRB2 accelerator card configuration if necessary and VRB2 pod
        - Delete VRB2 configuration and pod files
        - Remove and delete sriov-fec-operator application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pf_driver = "igb_uio"
    vf_driver = "vfio-pci"
    base_path = "/home/sysadmin"
    last_configuration_file = None
    sriov_fec_operator_kw = SriovFecOperatorKeywords(ssh_connection)

    sriov_fec_operator_kw.cleanup_sriov_fec_operator_and_pods()

    def teardown():
        get_logger().log_teardown_step("Delete VRB2 pod resources")
        sriov_fec_operator_kw.delete_fec_pods()

        get_logger().log_teardown_step("Delete VRB2 configuration resources")
        if last_configuration_file:
            delete_remaining_node_config(ssh_connection, last_configuration_file)

        get_logger().log_teardown_step("Delete Generated Files")
        sriov_fec_operator_kw.delete_generated_files(VRB2, base_path)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        sriov_fec_operator_kw.cleanup_sriov_fec_operator()

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all VRB2 accelerators and verify at least one is enabled")
    vrb2_devices = sriov_fec_operator_kw.get_devices_address(VRB2)
    validate_not_equals(len(vrb2_devices), 0, "Enabled VRB2 devices found in the system")

    get_logger().log_test_case_step("Generate card configuration YAML files for each VRB2")
    sriov_fec_operator_kw.generate_configuration_file(VRB2, vrb2_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate pods file YAML files")
    sriov_fec_operator_kw.generate_pod_file(VRB2, vrb2_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate bbdev file script")
    bbdev_sh_name = sriov_fec_operator_kw.generate_bbdev_script(VRB2, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    sriov_fec_operator_kw.upload_install_sriov_fec_operator()

    for index, (host_name, device_address) in enumerate(vrb2_devices):
        get_logger().log_info(f"Processing device {index}: host={host_name}, address={device_address}")
        get_logger().log_test_case_step("Apply sriov-fec-operator VRB2 configuration")
        last_configuration_file = apply_vrb2_configuration(ssh_connection, pf_driver, vf_driver, index, base_path, host_name)
        get_logger().log_test_case_step("Run sriov-fec-operator VRB2 pod and verify if it is running")
        pod_name = sriov_fec_operator_kw.apply_pod(VRB2, pf_driver, vf_driver, index, base_path, host_name)

        get_logger().log_test_case_step("Run bbdev script inside the pod and verify all tests passed.")
        sriov_fec_operator_kw.run_and_verify_bbdev_test(pod_name, bbdev_sh_name, base_path)

        get_logger().log_test_case_step("Delete VRB2 card configuration and pod resources.")
        delete_vrb2_configuration(ssh_connection, base_path, pf_driver, vf_driver, index, host_name)
        sriov_fec_operator_kw.delete_pod(VRB2, base_path, pf_driver, vf_driver, index)


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_vrb2
@mark.lab_has_page_size_1gb
def test_fec_operator_pf_driver_vfio_pci_vf_driver_vfio_pci_vrb2(request: FixtureRequest) -> None:
    """Verify VRB2 FEC operator with vfio-pci pf/vf drivers.

    Install sriov-fec-operator application and configure VRB2
    accelerator cards with pfDriver and vfDriver set to vfio-pci
    drivers and run test-bbdev pods successfully against the
    configured devices.

    Preconditions:
        - Lab has VRB2 accelerator devices
        - Lab has SR-IOV capability
        - Lab has 1GB huge page size allocated

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all VRB2 accelerators and verify at least one is enabled
        2. Generate configuration YAML and pod files for each VRB2 device
        3. Generate bbdev script
        4. Upload and apply the sriov-fec-operator application
        5. For each VRB2 device:
            a. Apply VRB2 configuration and run accelerator pod
            b. Run bbdev script inside the pod and verify all tests passed
            c. Delete VRB2 configuration and pod resources

    Teardown:
        - Delete VRB2 accelerator card configuration if necessary and VRB2 pod
        - Delete VRB2 configuration and pod files
        - Remove and delete sriov-fec-operator application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pf_driver = "vfio-pci"
    vf_driver = "vfio-pci"
    base_path = "/home/sysadmin"
    last_configuration_file = None
    sriov_fec_operator_kw = SriovFecOperatorKeywords(ssh_connection)

    sriov_fec_operator_kw.cleanup_sriov_fec_operator_and_pods()

    def teardown():
        get_logger().log_teardown_step("Delete VRB2 pod resources")
        sriov_fec_operator_kw.delete_fec_pods()

        get_logger().log_teardown_step("Delete VRB2 configuration resources")
        if last_configuration_file:
            delete_remaining_node_config(ssh_connection, last_configuration_file)

        get_logger().log_teardown_step("Delete Generated Files")
        sriov_fec_operator_kw.delete_generated_files(VRB2, base_path)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        sriov_fec_operator_kw.cleanup_sriov_fec_operator()

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all VRB2 accelerators and verify at least one is enabled")
    vrb2_devices = sriov_fec_operator_kw.get_devices_address(VRB2)
    validate_not_equals(len(vrb2_devices), 0, "Enabled VRB2 devices found in the system")

    get_logger().log_test_case_step("Generate card configuration YAML files for each VRB2")
    sriov_fec_operator_kw.generate_configuration_file(VRB2, vrb2_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate pods file YAML files")
    sriov_fec_operator_kw.generate_pod_file(VRB2, vrb2_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate bbdev file script")
    bbdev_sh_name = sriov_fec_operator_kw.generate_bbdev_script(VRB2, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    sriov_fec_operator_kw.upload_install_sriov_fec_operator()

    for index, (host_name, device_address) in enumerate(vrb2_devices):
        get_logger().log_info(f"Processing device {index}: host={host_name}, address={device_address}")
        get_logger().log_test_case_step("Apply sriov-fec-operator VRB2 configuration")
        last_configuration_file = apply_vrb2_configuration(ssh_connection, pf_driver, vf_driver, index, base_path, host_name)
        get_logger().log_test_case_step("Run sriov-fec-operator VRB2 pod and verify if it is running")
        pod_name = sriov_fec_operator_kw.apply_pod(VRB2, pf_driver, vf_driver, index, base_path, host_name)

        get_logger().log_test_case_step("Run bbdev script inside the pod and verify all tests passed.")
        sriov_fec_operator_kw.run_and_verify_bbdev_test(pod_name, bbdev_sh_name, base_path)

        get_logger().log_test_case_step("Delete VRB2 card configuration and pod resources.")
        delete_vrb2_configuration(ssh_connection, base_path, pf_driver, vf_driver, index, host_name)
        sriov_fec_operator_kw.delete_pod(VRB2, base_path, pf_driver, vf_driver, index)


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_vrb2
def test_fec_operator_verify_configured_accelerator_vrb2_remains_after_lock_unlock(request: FixtureRequest) -> None:
    """Verify VRB2 FEC operator configuration persists after lock/unlock.

    Install sriov-fec-operator application and configure VRB2
    accelerator cards with pfDriver and vfDriver set to igb_uio
    drivers and lock and unlock the host with VRB2 configured
    device and check if the configuration is preserved after
    lock and unlock

    Preconditions:
        - Lab has VRB2 accelerator devices
        - Lab has SR-IOV capability

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all VRB2 accelerators and verify at least one is enabled
        2. Generate configuration YAML file for VRB2 accelerator device
        3. Upload and apply the sriov-fec-operator application
        4. Apply VRB2 configuration
        5. Verify the card configuration
        6. Lock and unlock the node with VRB2 configured
        7. Verify if configuration done previously is kept after lock and unlock

    Teardown:
        - Delete VRB2 accelerator card configuration if necessary
        - Delete VRB2 accelerator card configuration files
        - Remove and delete sriov-fec-operator application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pf_driver = "igb_uio"
    vf_driver = "igb_uio"
    base_path = "/home/sysadmin"
    last_configuration_file = None
    sriov_fec_operator_kw = SriovFecOperatorKeywords(ssh_connection)

    sriov_fec_operator_kw.cleanup_sriov_fec_operator_and_pods()

    def teardown():
        get_logger().log_teardown_step("Delete VRB2 configuration resources")
        if last_configuration_file:
            delete_remaining_node_config(ssh_connection, last_configuration_file)

        get_logger().log_teardown_step("Delete Generated Files")
        sriov_fec_operator_kw.delete_generated_files(VRB2, base_path, False)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        sriov_fec_operator_kw.cleanup_sriov_fec_operator()

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all VRB2 accelerators and verify at least one is enabled")
    vrb2_devices = sriov_fec_operator_kw.get_devices_address(VRB2)
    validate_not_equals(len(vrb2_devices), 0, "Enabled VRB2 devices found in the system")

    get_logger().log_test_case_step("Select a single VRB2 accelerator device, preferring one not on the active controller")
    ssh_connection, selected_device = sriov_fec_operator_kw.select_device_preferring_non_active_controller(vrb2_devices, "VRB2")
    vrb2_devices = [selected_device]

    get_logger().log_test_case_step("Generate igb_uio configuration YAML files for VRB2 device")
    sriov_fec_operator_kw.generate_configuration_file(VRB2, vrb2_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    sriov_fec_operator_kw.upload_install_sriov_fec_operator()

    get_logger().log_test_case_step("Apply sriov-fec-operator VRB2 configuration and verify the card configuration")
    last_configuration_file = apply_vrb2_configuration(ssh_connection, pf_driver, vf_driver, 0, base_path, selected_device[0])

    get_logger().log_test_case_step("Save the sriovvrbnodeconfig YAML before lock")
    sriov_vrb_kw = KubectlGetSriovVrbNodeConfigKeywords(ssh_connection)
    config_before_lock = sriov_vrb_kw.get_sriov_vrb_node_config_yaml(selected_device[0])
    get_logger().log_info(f"Configuration before lock:\n{config_before_lock}")

    get_logger().log_test_case_step("Lock and unlock the node with VRB2 configured")
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    host_locked = host_lock_keywords.lock_host(selected_device[0])
    validate_equals(host_locked, True, f"Host locked {selected_device[0]}")
    host_unlocked = host_lock_keywords.unlock_host(selected_device[0])
    validate_equals(host_unlocked, True, f"Host unlocked {selected_device[0]}")

    get_logger().log_test_case_step("Wait for sriovvrbnodeconfig to be configured after unlock")
    sriov_vrb_kw.wait_for_configured_status(selected_device[0])

    get_logger().log_test_case_step("Verify if configuration done previously is kept after lock and unlock")
    config_after_unlock = sriov_vrb_kw.get_sriov_vrb_node_config_yaml(selected_device[0])
    get_logger().log_info(f"Configuration after unlock:\n{config_after_unlock}")

    validate_equals(config_before_lock.get_spec(), config_after_unlock.get_spec(), "VRB2 configuration remains the same after lock and unlock")

    get_logger().log_test_case_step("Delete VRB2 card configuration.")
    delete_vrb2_configuration(ssh_connection, base_path, pf_driver, vf_driver, 0, selected_device[0])


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_vrb2
@mark.lab_is_duplex
def test_fec_operator_verify_configured_accelerator_vrb2_remains_after_power_off_power_on(request: FixtureRequest) -> None:
    """Verify VRB2 FEC operator configuration persists after power off/on.

    Install sriov-fec-operator application and configure VRB2
    accelerator cards with pfDriver and vfDriver set to igb_uio
    drivers and power off and power on the host with VRB2 configured
    device and check if the configuration is preserved after
    power off and power on

    Preconditions:
        - Lab has hosts that support power off/power on capabilities
        - Lab has VRB2 accelerator devices
        - Lab has SR-IOV capability

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all VRB2 accelerators and verify at least one is enabled
        2. Generate configuration YAML file for VRB2 accelerator device
        3. Upload and apply the sriov-fec-operator application
        4. Apply VRB2 configuration
        5. Verify the VRB2 card configuration
        6. Power off and power on the host with VRB2 configured
        7. Verify if configuration done previously is kept after power off and power on

    Teardown:
        - Delete VRB2 accelerator card configuration if necessary
        - Delete VRB2 accelerator card configuration files
        - Remove and delete sriov-fec-operator application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pf_driver = "igb_uio"
    vf_driver = "igb_uio"
    base_path = "/home/sysadmin"
    last_configuration_file = None
    sriov_fec_operator_kw = SriovFecOperatorKeywords(ssh_connection)

    sriov_fec_operator_kw.cleanup_sriov_fec_operator_and_pods()

    def teardown():
        get_logger().log_teardown_step("Delete VRB2 configuration resources")
        if last_configuration_file:
            delete_remaining_node_config(ssh_connection, last_configuration_file)

        get_logger().log_teardown_step("Delete Generated Files")
        sriov_fec_operator_kw.delete_generated_files(VRB2, base_path, False)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        sriov_fec_operator_kw.cleanup_sriov_fec_operator()

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all VRB2 accelerators and verify at least one is enabled")
    vrb2_devices = sriov_fec_operator_kw.get_devices_address(VRB2)
    validate_not_equals(len(vrb2_devices), 0, "Enabled VRB2 devices found in the system")

    get_logger().log_test_case_step("Select a single VRB2 accelerator device, preferring one not on the active controller")
    ssh_connection, selected_device = sriov_fec_operator_kw.select_device_preferring_non_active_controller(vrb2_devices, "VRB2")
    vrb2_devices = [selected_device]

    get_logger().log_test_case_step("Generate igb_uio configuration YAML files for VRB2 device")
    sriov_fec_operator_kw.generate_configuration_file(VRB2, vrb2_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    sriov_fec_operator_kw.upload_install_sriov_fec_operator()

    get_logger().log_test_case_step("Apply sriov-fec-operator VRB2 configuration and verify the card configuration")
    last_configuration_file = apply_vrb2_configuration(ssh_connection, pf_driver, vf_driver, 0, base_path, selected_device[0])

    get_logger().log_test_case_step("Save the sriovvrbnodeconfig YAML before power off")
    sriov_vrb_kw = KubectlGetSriovVrbNodeConfigKeywords(ssh_connection)
    config_before_power_off = sriov_vrb_kw.get_sriov_vrb_node_config_yaml(selected_device[0])
    get_logger().log_info(f"Configuration before power off:\n{config_before_power_off}")

    get_logger().log_test_case_step("Power off and power on the node with VRB2 configured")
    power_kw = PowerKeywords(ssh_connection)
    validate_equals(power_kw.power_off(selected_device[0]), True, f"Host {selected_device[0]} powered off")
    validate_equals(power_kw.power_on(selected_device[0]), True, f"Host {selected_device[0]} powered on and recovered")

    get_logger().log_test_case_step("Wait for sriovvrbnodeconfig to be configured after power on")
    sriov_vrb_kw.wait_for_configured_status(selected_device[0])

    get_logger().log_test_case_step("Verify if configuration done previously is kept after power off and power on")
    config_after_power_on = sriov_vrb_kw.get_sriov_vrb_node_config_yaml(selected_device[0])
    get_logger().log_info(f"Configuration after power on:\n{config_after_power_on}")

    validate_equals(config_before_power_off.get_spec(), config_after_power_on.get_spec(), "VRB2 configuration remains the same after power off and power on")

    get_logger().log_test_case_step("Delete VRB2 card configuration.")
    delete_vrb2_configuration(ssh_connection, base_path, pf_driver, vf_driver, 0, selected_device[0])

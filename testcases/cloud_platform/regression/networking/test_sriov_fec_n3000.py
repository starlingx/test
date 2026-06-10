from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.networking.sriov_fec.object.sriov_fec_device_config import N3000
from keywords.cloud_platform.networking.sriov_fec.sriov_fec_operator_keywords import SriovFecOperatorKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.k8s.sriov_fec_node_config.kubectl_get_sriov_fec_node_config_keywords import KubectlGetSriovFecNodeConfigKeywords
from keywords.server.power_keywords import PowerKeywords


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_n3000
@mark.lab_has_page_size_1gb
def test_fec_operator_pf_driver_igb_uio_vf_driver_igb_uio_n3000(request: FixtureRequest) -> None:
    """Verify N3000 FEC operator with igb_uio pf/vf drivers.

    Install sriov-fec-operator application and configure N3000
    accelerator cards with pfDriver and vfDriver set to igb_uio
    drivers and run test-bbdev pods successfully against the
    configured devices.

    Preconditions:
        - Lab has N3000 accelerator devices
        - Lab has SR-IOV capability
        - Lab has 1GB huge page size allocated

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all N3000 accelerators and verify at least one is enabled
        2. Generate configuration YAML and pod files for each N3000 device
        3. Generate bbdev script
        4. Upload and apply the sriov-fec-operator application
        5. For each N3000 device:
            a. Apply N3000 configuration and run accelerator pod
            b. Run bbdev script inside the pod and verify all tests passed
            c. Delete N3000 configuration and pod resources

    Teardown:
        - Delete N3000 accelerator card configuration if necessary and N3000 pod
        - Delete N3000 configuration and pod files
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
        get_logger().log_teardown_step("Delete N3000 pod resources")
        sriov_fec_operator_kw.delete_fec_pods()

        get_logger().log_teardown_step("Delete N3000 configuration resources")
        if last_configuration_file:
            sriov_fec_operator_kw.delete_remaining_node_config(last_configuration_file)

        get_logger().log_teardown_step("Delete Generated Files")
        sriov_fec_operator_kw.delete_generated_files(N3000, base_path)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        sriov_fec_operator_kw.cleanup_sriov_fec_operator()

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all N3000 accelerators and verify at least one is enabled")
    n3000_devices = sriov_fec_operator_kw.get_devices_address(N3000)
    validate_not_equals(len(n3000_devices), 0, "Enabled N3000 devices found in the system")

    get_logger().log_test_case_step("Generate card configuration YAML files for each N3000")
    sriov_fec_operator_kw.generate_configuration_file(N3000, n3000_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate pods file YAML files")
    sriov_fec_operator_kw.generate_pod_file(N3000, n3000_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate bbdev file script")
    bbdev_sh_name = sriov_fec_operator_kw.generate_bbdev_script(N3000, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    sriov_fec_operator_kw.upload_install_sriov_fec_operator()

    for index, (host_name, device_address) in enumerate(n3000_devices):
        get_logger().log_info(f"Processing device {index}: host={host_name}, address={device_address}")
        get_logger().log_test_case_step("Apply sriov-fec-operator N3000 configuration")
        last_configuration_file = sriov_fec_operator_kw.apply_configuration(N3000, pf_driver, vf_driver, index, base_path, host_name)
        get_logger().log_test_case_step("Run sriov-fec-operator N3000 pod and verify if it is running")
        pod_name = sriov_fec_operator_kw.apply_pod(N3000, pf_driver, vf_driver, index, base_path, host_name)

        get_logger().log_test_case_step("Run bbdev script inside the pod and verify all tests passed.")
        sriov_fec_operator_kw.run_and_verify_bbdev_test(pod_name, bbdev_sh_name, base_path)

        get_logger().log_test_case_step("Delete N3000 card configuration and pod resources.")
        sriov_fec_operator_kw.delete_configuration(N3000, base_path, pf_driver, vf_driver, index, host_name)
        sriov_fec_operator_kw.delete_pod(N3000, base_path, pf_driver, vf_driver, index)


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_n3000
@mark.lab_has_page_size_1gb
def test_fec_operator_pf_driver_igb_uio_vf_driver_vfio_pci_n3000(request: FixtureRequest) -> None:
    """Verify N3000 FEC operator with igb_uio pf and vfio-pci vf drivers.

    Install sriov-fec-operator application and configure N3000
    accelerator cards with pfDriver is set to igb_uio and vfDriver
    set to vfio-pci and run test-bbdev pods successfully against the
    configured devices.

    Preconditions:
        - Lab has N3000 accelerator devices
        - Lab has SR-IOV capability
        - Lab has 1GB huge page size allocated

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all N3000 accelerators and verify at least one is enabled
        2. Generate configuration YAML and pod files for each N3000 device
        3. Generate bbdev script
        4. Upload and apply the sriov-fec-operator application
        5. For each N3000 device:
            a. Apply N3000 configuration and run accelerator pod
            b. Run bbdev script inside the pod and verify all tests passed
            c. Delete N3000 configuration and pod resources

    Teardown:
        - Delete N3000 accelerator card configuration if necessary and N3000 pod
        - Delete N3000 configuration and pod files
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
        get_logger().log_teardown_step("Delete N3000 pod resources")
        sriov_fec_operator_kw.delete_fec_pods()

        get_logger().log_teardown_step("Delete N3000 configuration resources")
        if last_configuration_file:
            sriov_fec_operator_kw.delete_remaining_node_config(last_configuration_file)

        get_logger().log_teardown_step("Delete Generated Files")
        sriov_fec_operator_kw.delete_generated_files(N3000, base_path)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        sriov_fec_operator_kw.cleanup_sriov_fec_operator()

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all N3000 accelerators and verify at least one is enabled")
    n3000_devices = sriov_fec_operator_kw.get_devices_address(N3000)
    validate_not_equals(len(n3000_devices), 0, "Enabled N3000 devices found in the system")

    get_logger().log_test_case_step("Generate card configuration YAML files for each N3000")
    sriov_fec_operator_kw.generate_configuration_file(N3000, n3000_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate pods file YAML files")
    sriov_fec_operator_kw.generate_pod_file(N3000, n3000_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate bbdev file script")
    bbdev_sh_name = sriov_fec_operator_kw.generate_bbdev_script(N3000, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    sriov_fec_operator_kw.upload_install_sriov_fec_operator()

    for index, (host_name, device_address) in enumerate(n3000_devices):
        get_logger().log_info(f"Processing device {index}: host={host_name}, address={device_address}")
        get_logger().log_test_case_step("Apply sriov-fec-operator N3000 configuration")
        last_configuration_file = sriov_fec_operator_kw.apply_configuration(N3000, pf_driver, vf_driver, index, base_path, host_name)
        get_logger().log_test_case_step("Run sriov-fec-operator N3000 pod and verify if it is running")
        pod_name = sriov_fec_operator_kw.apply_pod(N3000, pf_driver, vf_driver, index, base_path, host_name)

        get_logger().log_test_case_step("Run bbdev script inside the pod and verify all tests passed.")
        sriov_fec_operator_kw.run_and_verify_bbdev_test(pod_name, bbdev_sh_name, base_path)

        get_logger().log_test_case_step("Delete N3000 card configuration and pod resources.")
        sriov_fec_operator_kw.delete_configuration(N3000, base_path, pf_driver, vf_driver, index, host_name)
        sriov_fec_operator_kw.delete_pod(N3000, base_path, pf_driver, vf_driver, index)


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_n3000
@mark.lab_has_page_size_1gb
def test_fec_operator_pf_driver_vfio_pci_vf_driver_vfio_pci_n3000(request: FixtureRequest) -> None:
    """Verify N3000 FEC operator with vfio-pci pf/vf drivers.

    Install sriov-fec-operator application and configure N3000
    accelerator cards with pfDriver and vfDriver set to vfio-pci
    drivers and run test-bbdev pods successfully against the
    configured devices.

    Preconditions:
        - Lab has N3000 accelerator devices
        - Lab has SR-IOV capability
        - Lab has 1GB huge page size allocated

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all N3000 accelerators and verify at least one is enabled
        2. Generate configuration YAML and pod files for each N3000 device
        3. Generate bbdev script
        4. Upload and apply the sriov-fec-operator application
        5. For each N3000 device:
            a. Apply N3000 configuration and run accelerator pod
            b. Run bbdev script inside the pod and verify all tests passed
            c. Delete N3000 configuration and pod resources

    Teardown:
        - Delete N3000 accelerator card configuration if necessary and N3000 pod
        - Delete N3000 configuration and pod files
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
        get_logger().log_teardown_step("Delete N3000 pod resources")
        sriov_fec_operator_kw.delete_fec_pods()

        get_logger().log_teardown_step("Delete N3000 configuration resources")
        if last_configuration_file:
            sriov_fec_operator_kw.delete_remaining_node_config(last_configuration_file)

        get_logger().log_teardown_step("Delete Generated Files")
        sriov_fec_operator_kw.delete_generated_files(N3000, base_path)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        sriov_fec_operator_kw.cleanup_sriov_fec_operator()

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all N3000 accelerators and verify at least one is enabled")
    n3000_devices = sriov_fec_operator_kw.get_devices_address(N3000)
    validate_not_equals(len(n3000_devices), 0, "Enabled N3000 devices found in the system")

    get_logger().log_test_case_step("Generate card configuration YAML files for each N3000")
    sriov_fec_operator_kw.generate_configuration_file(N3000, n3000_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate pods file YAML files")
    sriov_fec_operator_kw.generate_pod_file(N3000, n3000_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate bbdev file script")
    bbdev_sh_name = sriov_fec_operator_kw.generate_bbdev_script(N3000, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    sriov_fec_operator_kw.upload_install_sriov_fec_operator()

    for index, (host_name, device_address) in enumerate(n3000_devices):
        get_logger().log_info(f"Processing device {index}: host={host_name}, address={device_address}")
        get_logger().log_test_case_step("Apply sriov-fec-operator N3000 configuration")
        last_configuration_file = sriov_fec_operator_kw.apply_configuration(N3000, pf_driver, vf_driver, index, base_path, host_name)
        get_logger().log_test_case_step("Run sriov-fec-operator N3000 pod and verify if it is running")
        pod_name = sriov_fec_operator_kw.apply_pod(N3000, pf_driver, vf_driver, index, base_path, host_name)

        get_logger().log_test_case_step("Run bbdev script inside the pod and verify all tests passed.")
        sriov_fec_operator_kw.run_and_verify_bbdev_test(pod_name, bbdev_sh_name, base_path)

        get_logger().log_test_case_step("Delete N3000 card configuration and pod resources.")
        sriov_fec_operator_kw.delete_configuration(N3000, base_path, pf_driver, vf_driver, index, host_name)
        sriov_fec_operator_kw.delete_pod(N3000, base_path, pf_driver, vf_driver, index)


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_n3000
def test_fec_operator_verify_configured_accelerator_n3000_remains_after_lock_unlock(request: FixtureRequest) -> None:
    """Verify N3000 FEC operator configuration persists after lock/unlock.

    Install sriov-fec-operator application and configure N3000
    accelerator cards with pfDriver and vfDriver set to igb_uio
    drivers and lock and unlock the host with N3000 configured
    device and check if the configuration is preserved after
    lock and unlock

    Preconditions:
        - Lab has N3000 accelerator devices
        - Lab has SR-IOV capability

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all N3000 accelerators and verify at least one is enabled
        2. Generate configuration YAML file for N3000 accelerator device
        3. Upload and apply the sriov-fec-operator application
        4. Apply N3000 configuration
        5. Verify the card configuration
        6. Lock and unlock the node with N3000 configured
        7. Verify if configuration done previously is kept after lock and unlock

    Teardown:
        - Delete N3000 accelerator card configuration if necessary
        - Delete N3000 accelerator card configuration files
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
        get_logger().log_teardown_step("Delete N3000 configuration resources")
        if last_configuration_file:
            sriov_fec_operator_kw.delete_remaining_node_config(last_configuration_file)

        get_logger().log_teardown_step("Delete Generated Files")
        sriov_fec_operator_kw.delete_generated_files(N3000, base_path, False)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        sriov_fec_operator_kw.cleanup_sriov_fec_operator()

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all N3000 accelerators and verify at least one is enabled")
    n3000_devices = sriov_fec_operator_kw.get_devices_address(N3000)
    validate_not_equals(len(n3000_devices), 0, "Enabled N3000 devices found in the system")

    get_logger().log_test_case_step("Select a single N3000 accelerator device, preferring one not on the active controller")
    ssh_connection, selected_device = sriov_fec_operator_kw.select_device_preferring_non_active_controller(n3000_devices, "N3000")
    n3000_devices = [selected_device]

    get_logger().log_test_case_step("Generate igb_uio configuration YAML files for N3000 device")
    sriov_fec_operator_kw.generate_configuration_file(N3000, n3000_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    sriov_fec_operator_kw.upload_install_sriov_fec_operator()

    get_logger().log_test_case_step("Apply sriov-fec-operator N3000 configuration and verify the card configuration")
    last_configuration_file = sriov_fec_operator_kw.apply_configuration(N3000, pf_driver, vf_driver, 0, base_path, selected_device[0])

    get_logger().log_test_case_step("Save the sriovfecnodeconfig YAML before lock")
    sriov_fec_node_config_kw = KubectlGetSriovFecNodeConfigKeywords(ssh_connection)
    config_before_lock = sriov_fec_node_config_kw.get_sriov_fec_node_config_yaml(selected_device[0])
    get_logger().log_info(f"Configuration before lock:\n{config_before_lock}")

    get_logger().log_test_case_step("Lock and unlock the node with N3000 configured")
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    host_locked = host_lock_keywords.lock_host(selected_device[0])
    validate_equals(host_locked, True, f"Host locked {selected_device[0]}")
    host_unlocked = host_lock_keywords.unlock_host(selected_device[0])
    validate_equals(host_unlocked, True, f"Host unlocked {selected_device[0]}")

    get_logger().log_test_case_step("Wait for sriovfecnodeconfig to be configured after unlock")
    sriov_fec_node_config_kw.wait_for_configured_status(selected_device[0])

    get_logger().log_test_case_step("Verify if configuration done previously is kept after lock and unlock")
    config_after_unlock = sriov_fec_node_config_kw.get_sriov_fec_node_config_yaml(selected_device[0])
    get_logger().log_info(f"Configuration after unlock:\n{config_after_unlock}")

    validate_equals(config_before_lock.get_spec(), config_after_unlock.get_spec(), "N3000 configuration remains the same after lock and unlock")

    get_logger().log_test_case_step("Delete N3000 card configuration.")
    sriov_fec_operator_kw.delete_configuration(N3000, base_path, pf_driver, vf_driver, 0, selected_device[0])


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_n3000
@mark.lab_is_duplex
def test_fec_operator_verify_configured_accelerator_n3000_remains_after_power_off_power_on(request: FixtureRequest) -> None:
    """Verify N3000 FEC operator configuration persists after power off/on.

    Install sriov-fec-operator application and configure N3000
    accelerator cards with pfDriver and vfDriver set to igb_uio
    drivers and power off and power on the host with N3000 configured
    device and check if the configuration is preserved after
    power off and power on

    Preconditions:
        - Lab has hosts that support power off/power on capabilities
        - Lab has N3000 accelerator devices
        - Lab has SR-IOV capability

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all N3000 accelerators and verify at least one is enabled
        2. Generate configuration YAML file for N3000 accelerator device
        3. Upload and apply the sriov-fec-operator application
        4. Apply N3000 configuration
        5. Verify the N3000 card configuration
        6. Power off and power on the host with N3000 configured
        7. Verify if configuration done previously is kept after power off and power on

    Teardown:
        - Delete N3000 accelerator card configuration if necessary
        - Delete N3000 accelerator card configuration files
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
        get_logger().log_teardown_step("Delete N3000 configuration resources")
        if last_configuration_file:
            sriov_fec_operator_kw.delete_remaining_node_config(last_configuration_file)

        get_logger().log_teardown_step("Delete Generated Files")
        sriov_fec_operator_kw.delete_generated_files(N3000, base_path, False)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        sriov_fec_operator_kw.cleanup_sriov_fec_operator()

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all N3000 accelerators and verify at least one is enabled")
    n3000_devices = sriov_fec_operator_kw.get_devices_address(N3000)
    validate_not_equals(len(n3000_devices), 0, "Enabled N3000 devices found in the system")

    get_logger().log_test_case_step("Select a single N3000 accelerator device, preferring one not on the active controller")
    ssh_connection, selected_device = sriov_fec_operator_kw.select_device_preferring_non_active_controller(n3000_devices, "N3000")
    n3000_devices = [selected_device]

    get_logger().log_test_case_step("Generate igb_uio configuration YAML files for N3000 device")
    sriov_fec_operator_kw.generate_configuration_file(N3000, n3000_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    sriov_fec_operator_kw.upload_install_sriov_fec_operator()

    get_logger().log_test_case_step("Apply sriov-fec-operator N3000 configuration and verify the card configuration")
    last_configuration_file = sriov_fec_operator_kw.apply_configuration(N3000, pf_driver, vf_driver, 0, base_path, selected_device[0])

    get_logger().log_test_case_step("Save the sriovfecnodeconfig YAML before power off")
    sriov_fec_node_config_kw = KubectlGetSriovFecNodeConfigKeywords(ssh_connection)
    config_before_power_off = sriov_fec_node_config_kw.get_sriov_fec_node_config_yaml(selected_device[0])
    get_logger().log_info(f"Configuration before power off:\n{config_before_power_off}")

    get_logger().log_test_case_step("Power off and power on the node with N3000 configured")
    power_kw = PowerKeywords(ssh_connection)
    validate_equals(power_kw.power_off(selected_device[0]), True, f"Host {selected_device[0]} powered off")
    validate_equals(power_kw.power_on(selected_device[0]), True, f"Host {selected_device[0]} powered on and recovered")

    get_logger().log_test_case_step("Wait for sriovfecnodeconfig to be configured after power on")
    sriov_fec_node_config_kw.wait_for_configured_status(selected_device[0])

    get_logger().log_test_case_step("Verify if configuration done previously is kept after power off and power on")
    config_after_power_on = sriov_fec_node_config_kw.get_sriov_fec_node_config_yaml(selected_device[0])
    get_logger().log_info(f"Configuration after power on:\n{config_after_power_on}")

    validate_equals(config_before_power_off.get_spec(), config_after_power_on.get_spec(), "N3000 configuration remains the same after power off and power on")

    get_logger().log_test_case_step("Delete N3000 card configuration.")
    sriov_fec_operator_kw.delete_configuration(N3000, base_path, pf_driver, vf_driver, 0, selected_device[0])

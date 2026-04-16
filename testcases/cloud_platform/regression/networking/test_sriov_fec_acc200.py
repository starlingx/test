from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_device_keywords import SystemHostDeviceKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_copy_to_pod_keywords import KubectlCopyToPodKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.sriov_fec_node_config.kubectl_get_sriov_fec_node_config_keywords import KubectlGetSriovFecNodeConfigKeywords

ACC200_DEVICE_ID = "57c0"
VF_DEVICE_ID = "57c1"
VF_VENDOR_ID = "8086"


def get_acc200_devices_address(ssh_connection: SSHConnection) -> list[tuple[str, str]]:
    """Get ACC200 devices address for all hosts in the system.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        list[tuple[str, str]]: Tuples of hostname and ACC200 device address.
    """
    system_host_list_output = SystemHostListKeywords(ssh_connection).get_system_host_list()
    acc200_devices = []
    for host_name in system_host_list_output.get_host_names():
        device_output = SystemHostDeviceKeywords(ssh_connection).get_system_host_device_list(host_name)
        for device in device_output.get_device_address_by_device_id(ACC200_DEVICE_ID):
            acc200_devices.append((host_name, device))

    for host_name, address in acc200_devices:
        get_logger().log_info(f"Host: {host_name}, Address: {address}")

    return acc200_devices


def generate_acc200_configuration_file(ssh_connection: SSHConnection, acc200_devices: list[tuple[str, str]], pf_driver: str, vf_driver: str, base_path: str) -> None:
    """Generate ACC200 configuration file and pod YAML file from template.

    Args:
        ssh_connection (SSHConnection): SSH connection to the target host.
        acc200_devices (list[tuple[str, str]]): Tuples of hostname and ACC200 device address.
        pf_driver (str): PF driver name.
        vf_driver (str): VF driver name.
        base_path (str): Remote directory where files will be saved.
    """
    yaml_kw = YamlKeywords(ssh_connection)
    operator_config_files = []
    pod_config_files = []
    for index, (host_name, device_adress) in enumerate(acc200_devices):
        template_path = get_stx_resource_path("resources/cloud_platform/sriov-fec-operator/sriov-fec-operator-acc200.yaml.j2")
        replacement_dict = {
            "name": f"acc200-{index}",
            "hostName": host_name,
            "pfDriver": pf_driver,
            "vfDriver": vf_driver,
            "pciAddress": device_adress,
        }
        remote_file = yaml_kw.generate_yaml_file_from_template(template_path, replacement_dict, f"sriov-fec-operator-{pf_driver}-{vf_driver}-acc200-{index}.yaml", base_path, preserve_order=True)
        operator_config_files.append(remote_file)
        get_logger().log_info(f"Generated operator config: {remote_file}")

        template_path = get_stx_resource_path("resources/cloud_platform/sriov-fec-operator/sriov-pod-acc200.yaml.j2")
        replacement_dict = {
            "podName": f"acc200-{index}",
        }
        remote_file = yaml_kw.generate_yaml_file_from_template(template_path, replacement_dict, f"sriov-pod-k8s-manifest-{pf_driver}-{vf_driver}-acc200-{index}.yaml", base_path, preserve_order=True)
        pod_config_files.append(remote_file)
        get_logger().log_info(f"Generated pod config: {remote_file}")


def generate_bbdev_script(ssh_connection: SSHConnection, pf_driver: str, vf_driver: str, base_path: str) -> str:
    """Generate a bbdev test script from template with driver configuration.

    Args:
        ssh_connection (SSHConnection): SSH connection to the target host.
        pf_driver (str): PF driver name.
        vf_driver (str): VF driver name.
        base_path (str): Remote directory where the file will be saved.

    Returns:
        str: Generated bbdev script file name.
    """
    file_kw = FileKeywords(ssh_connection)
    template_path = get_stx_resource_path("resources/cloud_platform/sriov-fec-operator/bbdev.sh")
    replacement_dict = {
        "vf_vendor_id": VF_VENDOR_ID,
        "vf_device_id": VF_DEVICE_ID,
        "pfDriver": pf_driver,
        "vfDriver": vf_driver,
    }
    bbdev_sh_name = f"bbdev_{pf_driver}_{vf_driver}.sh"
    bbdev_script_file = file_kw.generate_file_from_template(template_path, replacement_dict, bbdev_sh_name, base_path)
    get_logger().log_info(f"Generated bbdev script: {bbdev_script_file}")
    return bbdev_sh_name


def upload_install_sriov_fec_operator(ssh_connection: SSHConnection) -> None:
    """Upload, apply sriov-fec-operator, and wait for its pods to be running.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    sriov_fec_name = app_config.get_sriov_fec_operator_app_name()
    sriov_fec_file_path = f"{base_path}{sriov_fec_name}*.tgz"

    get_logger().log_info(f"Uploading and applying {sriov_fec_name}")
    sriov_fec_app_output = SystemApplicationUploadKeywords(ssh_connection).system_application_upload_and_apply_app(sriov_fec_name, sriov_fec_file_path)
    sriov_fec_app_object = sriov_fec_app_output.get_system_application_object()
    validate_equals(sriov_fec_app_object.get_name(), sriov_fec_name, f"{sriov_fec_name} name validation")
    validate_equals(sriov_fec_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{sriov_fec_name} application status validation")
    get_logger().log_info("Waiting for sriov-fec-operator pods to be running")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace="sriov-fec-system")


def apply_acc200_configuration_and_pod(ssh_connection: SSHConnection, pf_driver: str, vf_driver: str, index: int, base_path: str, host_name: str) -> str:
    """Apply sriov-fec-operator ACC200 configuration and run accelerator pod and verify if pod is running.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        pf_driver (str): PF driver name.
        vf_driver (str): VF driver name.
        index (int): ACC200 device index.
        base_path (str): Remote directory where the file was created.
        host_name (str): Host name.

    Returns:
        str: Name of the created pod.
    """

    operator_file = f"{base_path}/sriov-fec-operator-{pf_driver}-{vf_driver}-acc200-{index}.yaml"
    pod_file = f"{base_path}/sriov-pod-k8s-manifest-{pf_driver}-{vf_driver}-acc200-{index}.yaml"

    get_logger().log_info("Apply sriov-fec-operator ACC200 card configuration file")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(operator_file)
    get_logger().log_info("Verify if sriov-fec-operator ACC200 card configuration file was applied and pod is running")
    KubectlGetSriovFecNodeConfigKeywords(ssh_connection).wait_for_configured_status(
        host_name,
        expected_status="InProgress",
        timeout=90,
        poll_interval=15,
    )
    KubectlGetSriovFecNodeConfigKeywords(ssh_connection).wait_for_configured_status(host_name)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace="sriov-fec-system")
    get_logger().log_info("Run ACC200 pod for accelerator card")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(pod_file, namespace="default")
    get_pods_kw = KubectlGetPodsKeywords(ssh_connection)
    get_logger().log_info("Verify ACC200 pod is running")
    pod_name = get_pods_kw.get_pods(namespace="default").get_unique_pod_matching_prefix(starts_with="acc200")
    pod_status = get_pods_kw.wait_for_pod_status(pod_name, "Running", "default")
    validate_equals(pod_status, True, "ACC200 pod status is running")

    return pod_name


def run_and_verify_bbdev_test(ssh_connection: SSHConnection, pod_name: str, bbdev_sh_name: str, base_path: str) -> None:
    """Run bbdev script inside the pod and verify all tests passed.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        pod_name (str): Name of the pod to execute the script in.
        bbdev_sh_name (str): Name of the bbdev script file.
        base_path (str): Remote directory where the file was created.
    """
    get_logger().log_info("Copy bbdev script inside the pod")
    KubectlCopyToPodKeywords(ssh_connection).copy_to_pod(local_filename=f"{base_path}/{bbdev_sh_name}", namespace="default", pod_name=pod_name, dest_filename=".")

    get_logger().log_info("Run bbdev script inside the pod")
    bbdev_output = KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(pod_name, f"bash {bbdev_sh_name}", options="-n default")
    bbdev_output_str = "".join(bbdev_output) if isinstance(bbdev_output, list) else bbdev_output

    get_logger().log_info("Verify bbdev test executed and all tests passed")
    validate_str_contains(bbdev_output_str, "Test Suite Summary", "bbdev test suite was executed")
    validate_str_contains(bbdev_output_str, "Tests Failed :       0", "bbdev tests have no failures")


def delete_acc200_configuration_and_pod(ssh_connection: SSHConnection, base_path: str, pf_driver: str, vf_driver: str, index: int, host_name: str) -> None:
    """Delete ACC200 operator configuration and pod resource files.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        base_path (str): Remote directory where files are located.
        pf_driver (str): PF driver name.
        vf_driver (str): VF driver name.
        index (int): ACC200 device index.
        host_name (str): Host Name
    """
    get_logger().log_info("Delete ACC200 configuration")
    kubectl_delete_kw = KubectlFileDeleteKeywords(ssh_connection)
    kubectl_delete_kw.delete_resources(f"{base_path}/sriov-fec-operator-{pf_driver}-{vf_driver}-acc200-{index}.yaml")
    get_logger().log_info("Verify if sriov-fec-operator ACC200 card configuration file was applied and pod is running")
    KubectlGetSriovFecNodeConfigKeywords(ssh_connection).wait_for_configured_status(
        host_name,
        expected_status="InProgress",
        timeout=90,
        poll_interval=15,
    )
    KubectlGetSriovFecNodeConfigKeywords(ssh_connection).wait_for_configured_status(host_name)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(expected_status="Running", namespace="sriov-fec-system")
    get_logger().log_info("Delete ACC200 pod")
    kubectl_delete_kw.delete_resources(f"{base_path}/sriov-pod-k8s-manifest-{pf_driver}-{vf_driver}-acc200-{index}.yaml")


def cleanup_sriov_fec_operator(ssh_connection: SSHConnection) -> None:
    """Remove sriov-fec-operator application if previously installed or uploaded.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    app_config = ConfigurationManager.get_app_config()
    sriov_fec_name = app_config.get_sriov_fec_operator_app_name()

    get_logger().log_setup_step("Verify if sriov-fec-operator is previously installed or uploaded")
    sriov_fec_applied = SystemApplicationApplyKeywords(ssh_connection).is_applied_or_failed(sriov_fec_name)

    if sriov_fec_applied:
        get_logger().log_setup_step("Remove and delete sriov-fec-operator application")
        sriov_fec_app_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove_and_delete_app(sriov_fec_name)
        validate_equals(sriov_fec_app_output, f"Application {sriov_fec_name} deleted.\n", "SRIOV FEC deletion validation")
        KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_be_deleted(namespace="sriov-fec-system")
        return

    sriov_fec_uploaded = SystemApplicationUploadKeywords(ssh_connection).is_already_uploaded(sriov_fec_name)
    if sriov_fec_uploaded:
        get_logger().log_setup_step("Delete sriov-fec-operator application")
        system_application_delete_input = SystemApplicationDeleteInput()
        system_application_delete_input.set_app_name(sriov_fec_name)
        system_application_delete_input.set_force_deletion(False)
        sriov_fec_app_output = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(system_application_delete_input)
        validate_equals(sriov_fec_app_output, f"Application {sriov_fec_name} deleted.\n", "Application deletion message validation")
        return

    get_logger().log_info("sriov-fec-operator is not installed")


def delete_fec_pods(ssh_connection: SSHConnection) -> None:
    """Delete all FEC pods matching known prefixes.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    get_logger().log_setup_step("Delete FEC pods")
    pod_prefixes = ["vrb2", "dualvrb2", "acc100", "dualacc100", "acc200", "n3000"]
    get_pods_kw = KubectlGetPodsKeywords(ssh_connection)
    delete_pods_kw = KubectlDeletePodsKeywords(ssh_connection)

    for prefix in pod_prefixes:
        pods = get_pods_kw.get_pods(namespace="default").get_pods_start_with(starts_with=prefix)
        for pod in pods:
            delete_pods_kw.delete_pod(pod.get_name())
            get_logger().log_info(f"Deleted pod: {pod.get_name()}")


def _cleanup_sriov_fec_operator_and_pods(ssh_connection: SSHConnection):
    """Clean up delete pods and sriov-fec-operator.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Delete FEC pods
    delete_fec_pods(ssh_connection)

    # Verify the Sriov FEC operator app is not present in the system
    cleanup_sriov_fec_operator(ssh_connection)


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_acc200
@mark.lab_has_page_size_1gb
def test_fec_operator_pf_driver_igb_uio_vf_drive_igb_uio_acc200(request: FixtureRequest):
    """Verify ACC200 FEC operator with igb_uio pf/vf drivers.

    Install sriov-fec-operator application and configure ACC200
    accelerator cards with pfDriver and vfDriver set to igb_uio
    drivers and run test-bbdev pods successfully against the
    configured devices.

    Preconditions:
        - Lab has ACC200 accelerator devices
        - Lab has SR-IOV capability
        - Lab has 1GB page size enabled

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all ACC200 accelerators and verify at least one is enabled
        2. Generate configuration YAML and pod files for each ACC200 device
        3. Generate bbdev script
        4. Upload and apply the sriov-fec-operator application
        5. For each ACC200 device:
            a. Apply ACC200 configuration and run accelerator pod
            b. Run bbdev script inside the pod and verify all tests passed
            c. Delete ACC200 configuration and pod resources

    Teardown:
        - Delete ACC200 pod and configuration resources
        - Remove and delete sriov-fec-operator application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pf_driver = "igb_uio"
    vf_driver = "igb_uio"
    base_path = "/home/sysadmin"

    _cleanup_sriov_fec_operator_and_pods(ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Delete ACC200 pod and configuration resources")
        delete_fec_pods(ssh_connection)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        cleanup_sriov_fec_operator(ssh_connection)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all ACC200 accelerators and verify at least one is enabled")
    acc200_devices = get_acc200_devices_address(ssh_connection)
    validate_not_equals(len(acc200_devices), 0, "Enabled ACC200 devices found in the system")

    get_logger().log_test_case_step("Generate igb_uio configuration YAML files for each ACC200 device and pod files")
    generate_acc200_configuration_file(ssh_connection, acc200_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate bbdev file script")
    bbdev_sh_name = generate_bbdev_script(ssh_connection, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    upload_install_sriov_fec_operator(ssh_connection)

    for index, (host_name, device_address) in enumerate(acc200_devices):
        get_logger().log_info(f"Processing device {index}: host={host_name}, address={device_address}")
        get_logger().log_test_case_step("Apply sriov-fec-operator ACC200 configuration and run accelerator pod and verify if pod is running")
        pod_name = apply_acc200_configuration_and_pod(ssh_connection, pf_driver, vf_driver, index, base_path, host_name)

        get_logger().log_test_case_step("Run bbdev script inside the pod and verify all tests passed.")
        run_and_verify_bbdev_test(ssh_connection, pod_name, bbdev_sh_name, base_path)

        get_logger().log_test_case_step("Delete ACC200 configuration and pod resources.")
        delete_acc200_configuration_and_pod(ssh_connection, base_path, pf_driver, vf_driver, index, host_name)


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_acc200
@mark.lab_has_page_size_1gb
def test_fec_operator_pf_driver_igb_uio_vf_drive_vfio_pci_acc200(request: FixtureRequest):
    """Verify ACC200 FEC operator with igb_uio pf/vf drivers.

    Install sriov-fec-operator application and configure ACC200
    accelerator cards with pfDriver is set to igb_uio and vfDriver
    set to vfio-pci and run test-bbdev pods successfully against the
    configured devices.

    Preconditions:
        - Lab has ACC200 accelerator devices
        - Lab has SR-IOV capability
        - Lab has 1GB page size enabled

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all ACC200 accelerators and verify at least one is enabled
        2. Generate configuration YAML and pod files for each ACC200 device
        3. Generate bbdev script
        4. Upload and apply the sriov-fec-operator application
        5. For each ACC200 device:
            a. Apply ACC200 configuration and run accelerator pod
            b. Run bbdev script inside the pod and verify all tests passed
            c. Delete ACC200 configuration and pod resources

    Teardown:
        - Delete ACC200 pod and configuration resources
        - Remove and delete sriov-fec-operator application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pf_driver = "igb_uio"
    vf_driver = "vfio-pci"
    base_path = "/home/sysadmin"

    _cleanup_sriov_fec_operator_and_pods(ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Delete ACC200 pod and configuration resources")
        delete_fec_pods(ssh_connection)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        cleanup_sriov_fec_operator(ssh_connection)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all ACC200 accelerators and verify at least one is enabled")
    acc200_devices = get_acc200_devices_address(ssh_connection)
    validate_not_equals(len(acc200_devices), 0, "Enabled ACC200 devices found in the system")

    get_logger().log_test_case_step("Generate igb_uio configuration YAML files for each ACC200 device and pod files")
    generate_acc200_configuration_file(ssh_connection, acc200_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate bbdev file script")
    bbdev_sh_name = generate_bbdev_script(ssh_connection, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    upload_install_sriov_fec_operator(ssh_connection)

    for index, (host_name, device_address) in enumerate(acc200_devices):
        get_logger().log_info(f"Processing device {index}: host={host_name}, address={device_address}")
        get_logger().log_test_case_step("Apply sriov-fec-operator ACC200 configuration and run accelerator pod and verify if pod is running")
        pod_name = apply_acc200_configuration_and_pod(ssh_connection, pf_driver, vf_driver, index, base_path, host_name)

        get_logger().log_test_case_step("Run bbdev script inside the pod and verify all tests passed.")
        run_and_verify_bbdev_test(ssh_connection, pod_name, bbdev_sh_name, base_path)

        get_logger().log_test_case_step("Delete ACC200 configuration and pod resources.")
        delete_acc200_configuration_and_pod(ssh_connection, base_path, pf_driver, vf_driver, index, host_name)


@mark.p1
@mark.lab_has_sriov
@mark.lab_has_acc200
@mark.lab_has_page_size_1gb
def test_fec_operator_pf_driver_vfio_pci_vf_drive_vfio_pci_acc200(request: FixtureRequest):
    """Verify ACC200 FEC operator with igb_uio pf/vf drivers.

    Install sriov-fec-operator application and configure ACC200
    accelerator cards with pfDriver and vfDriver set to vfio-pci
    drivers and run test-bbdev pods successfully against the
    configured devices.

    Preconditions:
        - Lab has ACC200 accelerator devices
        - Lab has SR-IOV capability
        - Lab has 1GB page size enabled

    Setup:
        - Clean up any previously installed sriov-fec-operator application
        - Establish SSH connection to active controller

    Test Steps:
        1. Get all ACC200 accelerators and verify at least one is enabled
        2. Generate configuration YAML and pod files for each ACC200 device
        3. Generate bbdev script
        4. Upload and apply the sriov-fec-operator application
        5. For each ACC200 device:
            a. Apply ACC200 configuration and run accelerator pod
            b. Run bbdev script inside the pod and verify all tests passed
            c. Delete ACC200 configuration and pod resources

    Teardown:
        - Delete ACC200 pod and configuration resources
        - Remove and delete sriov-fec-operator application
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pf_driver = "vfio-pci"
    vf_driver = "vfio-pci"
    base_path = "/home/sysadmin"

    _cleanup_sriov_fec_operator_and_pods(ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Delete ACC200 pod and configuration resources")
        delete_fec_pods(ssh_connection)

        get_logger().log_teardown_step("Remove and delete sriov-fec-operator application")
        cleanup_sriov_fec_operator(ssh_connection)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Get all ACC200 accelerators and verify at least one is enabled")
    acc200_devices = get_acc200_devices_address(ssh_connection)
    validate_not_equals(len(acc200_devices), 0, "Enabled ACC200 devices found in the system")

    get_logger().log_test_case_step("Generate igb_uio configuration YAML files for each ACC200 device and pod files")
    generate_acc200_configuration_file(ssh_connection, acc200_devices, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Generate bbdev file script")
    bbdev_sh_name = generate_bbdev_script(ssh_connection, pf_driver, vf_driver, base_path)

    get_logger().log_test_case_step("Upload and apply the sriov-fec-operator configuration")
    upload_install_sriov_fec_operator(ssh_connection)

    for index, (host_name, device_address) in enumerate(acc200_devices):
        get_logger().log_info(f"Processing device {index}: host={host_name}, address={device_address}")
        get_logger().log_test_case_step("Apply sriov-fec-operator ACC200 configuration and run accelerator pod and verify if pod is running")
        pod_name = apply_acc200_configuration_and_pod(ssh_connection, pf_driver, vf_driver, index, base_path, host_name)

        get_logger().log_test_case_step("Run bbdev script inside the pod and verify all tests passed.")
        run_and_verify_bbdev_test(ssh_connection, pod_name, bbdev_sh_name, base_path)

        get_logger().log_test_case_step("Delete ACC200 configuration and pod resources.")
        delete_acc200_configuration_and_pod(ssh_connection, base_path, pf_driver, vf_driver, index, host_name)

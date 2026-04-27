from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_none
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.virtctl.virtctl_keywords import VirtctlKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.crd.kubectl_wait_crd_keywords import KubectlWaitCrdKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.helm.kubectl_get_helm_keywords import KubectlGetHelmKeywords
from keywords.k8s.patch.kubectl_apply_patch_keywords import KubectlApplyPatchKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_wait_pod_keywords import KubectlWaitPodKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_delete_secret_keywords import KubectlDeleteSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.k8s.vm.kubectl_delete_vm_keywords import KubectlDeleteVmKeywords
from keywords.k8s.vm.kubectl_get_vm_keywords import KubectlGetVmKeywords
from keywords.k8s.vm.kubectl_get_vmi_keywords import KubectlGetVmiKeywords
from keywords.linux.ln.ln_keywords import LnKeywords
from keywords.linux.ls.ls_keywords import LsKeywords
from keywords.linux.which.which_keywords import WhichKeywords

APP_NAME = "kubevirt-app"
KUBEVIRT_VM_DIR = "/home/sysadmin/kubevirt"
KUBEVIRT_REGISTRY_SECRET = "default-registry-key"
KUBEVIRT_NAMESPACE = "kubevirt"
CDI_NAMESPACE = "cdi"
CHART_PATH = "/usr/local/share/applications/helm/kubevirt-app-[0-9]*"
CHART_NAME = "kube-system-kubevirt-app"
KUBE_SYSTEM_NAMESPACE = "kube-system"

# Expected pod name patterns
KUBEVIRT_EXPECTED_PODS = ["virt-api", "virt-operator", "kubevirt-daemonset"]
CDI_EXPECTED_PODS = ["cdi-apiserver", "cdi-deployment", "cdi-operator", "cdi-uploadproxy"]

# For virtctl setup
PATH_VARIABLE = "/home/sysadmin/bin"
VIRTCTL_PATH = "/var/opt/kubevirt/virtctl"


def setup_virtctl_on_controller(ssh_connection: SSHConnection) -> bool:
    """
    Setup virtctl on a single controller.

    Args:
        ssh_connection (SSHConnection): SSH connection to controller.

    Returns:
        bool: True if virtctl setup successfully, False otherwise.
    """
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.create_directory(PATH_VARIABLE)

    get_logger().log_info("Finding virtctl executable path")
    ls_keywords = LsKeywords(ssh_connection)
    actual_virtctl_path = ls_keywords.get_first_matching_file(VIRTCTL_PATH)

    get_logger().log_info(f"Creating symbolic link to virtctl at {PATH_VARIABLE}/virtctl")
    ln_keywords = LnKeywords(ssh_connection)
    ln_keywords.create_symbolic_link_to_a_file(actual_virtctl_path, f"{PATH_VARIABLE}/virtctl")
    ssh_connection.close()


def setup_virtctl(ssh_connection: SSHConnection) -> None:
    """
    Setup virtctl client executable to be accessible from sysadmin's PATH.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    system_host_list = SystemHostListKeywords(ssh_connection)
    controllers = system_host_list.get_controllers()

    # Create symbolic link to virtctl on all controllers
    for controller in controllers:
        controller_name = controller.get_host_name()
        get_logger().log_info(f"Setting up virtctl on {controller_name}")
        controller_ssh = LabConnectionKeywords().get_ssh_for_hostname(controller_name)
        setup_virtctl_on_controller(controller_ssh)
        ssh_connection.close()

    get_logger().log_info("Validating virtctl is set up properly")
    which_keywords = WhichKeywords(ssh_connection)
    which_keywords.which_process("virtctl")


def remove_virtctl(ssh_connection: SSHConnection) -> None:
    """
    Remove virtctl client executable from sysadmin's PATH.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Removing virtctl from all controllers")
    system_host_list = SystemHostListKeywords(ssh_connection)
    controllers = system_host_list.get_controllers()

    for controller in controllers:
        controller_name = controller.get_host_name()
        get_logger().log_info(f"Removing virtctl from {controller_name}")
        controller_ssh = LabConnectionKeywords().get_ssh_for_hostname(controller_name)
        file_keywords = FileKeywords(controller_ssh)
        file_keywords.delete_file(f"{PATH_VARIABLE}/virtctl")
        file_keywords.delete_directory(PATH_VARIABLE)


def setup_kubevirt_environment(ssh_connection: SSHConnection) -> None:
    """
    Setup kubevirt application.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info(f"Uploading {APP_NAME} application")
    ls_keywords = LsKeywords(ssh_connection)
    actual_chart = ls_keywords.get_first_matching_file(CHART_PATH)
    upload_input = SystemApplicationUploadInput()
    upload_input.set_tar_file_path(actual_chart)
    upload_input.set_app_name(APP_NAME)
    system_app_upload = SystemApplicationUploadKeywords(ssh_connection)
    system_app_upload.system_application_upload(upload_input)

    get_logger().log_info(f"Applying {APP_NAME} application")
    system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
    system_app_apply.system_application_apply(APP_NAME)

    # Verify all kubevirt and cdi pods are running
    get_logger().log_info("Verifying kubevirt pods are running")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=CDI_EXPECTED_PODS, namespace=CDI_NAMESPACE, timeout=30)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KUBEVIRT_EXPECTED_PODS, namespace=KUBEVIRT_NAMESPACE, timeout=30)

    # Wait for kubevirt to be fully ready (virt-api pods ready + KubeVirt CR available)
    get_logger().log_info("Waiting for kubevirt to be fully ready")
    kubectl_wait = KubectlWaitPodKeywords(ssh_connection)
    kubectl_wait.wait_for_pods_ready(label="kubevirt.io=virt-api", namespace=KUBEVIRT_NAMESPACE, timeout=120)
    KubectlWaitCrdKeywords(ssh_connection).wait_for_condition(resource="kv", resource_name="kubevirt", condition="Available", namespace=KUBEVIRT_NAMESPACE, timeout=120)

    # setting up virtctl
    get_logger().log_info("Setting up virtctl on all controllers")
    setup_virtctl(ssh_connection)


def verify_kubevirt_helmchart_removed(ssh_connection: SSHConnection) -> None:
    """Verify that kubevirt entry is removed from HelmChart list.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Verifying kubevirt HelmChart is removed")
    kubectl_helmchart = KubectlGetHelmKeywords(ssh_connection)
    chart = kubectl_helmchart.get_helmchart_by_name(CHART_NAME, KUBE_SYSTEM_NAMESPACE)
    validate_none(chart, "kubevirt HelmChart should be removed")


def cleanup_kubevirt_environment(ssh_connection: SSHConnection) -> None:
    """
    Clean up kubevirt test resources.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Cleaning up kubevirt test resources")

    system_app_list = SystemApplicationListKeywords(ssh_connection)
    if system_app_list.is_app_present(APP_NAME):
        get_logger().log_info(f"Removing {APP_NAME} application")
        system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
        if system_app_apply.is_applied_or_failed(APP_NAME):
            remove_input = SystemApplicationRemoveInput()
            remove_input.set_app_name(APP_NAME)
            system_app_remove = SystemApplicationRemoveKeywords(ssh_connection)
            system_app_remove.system_application_remove(remove_input)

        delete_input = SystemApplicationDeleteInput()
        delete_input.set_app_name(APP_NAME)
        delete_input.set_force_deletion(True)
        system_app_delete = SystemApplicationDeleteKeywords(ssh_connection)
        system_app_delete.get_system_application_delete(delete_input)
        # remove virtctl
        remove_virtctl(ssh_connection)


def setup_registry_secret(ssh_connection: SSHConnection, request: FixtureRequest, namespace: str = "default") -> None:
    """Create a docker-registry secret and patch the default service account for image pulls.

    Reads the local registry credentials from the docker configuration and creates
    a Kubernetes secret in the given namespace. Then patches the default service account
    to use that secret for image pulls. Registers a finalizer to clean up the secret
    on teardown.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        request (FixtureRequest): Pytest request object for registering teardown.
        namespace (str): Namespace to create the secret in. Defaults to 'default'.
    """
    local_registry = ConfigurationManager.get_docker_config().get_local_registry()
    secret_names = KubectlGetSecretsKeywords(ssh_connection).get_secret_names(namespace=namespace)

    if KUBEVIRT_REGISTRY_SECRET not in secret_names:
        get_logger().log_info(f"Creating registry secret {KUBEVIRT_REGISTRY_SECRET} in namespace {namespace}")
        KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(
            registry=local_registry,
            secret_name=KUBEVIRT_REGISTRY_SECRET,
            namespace=namespace,
        )

        def teardown_secret():
            get_logger().log_teardown_step(f"Deleting registry secret {KUBEVIRT_REGISTRY_SECRET}")
            KubectlDeleteSecretsKeywords(ssh_connection).cleanup_secret(KUBEVIRT_REGISTRY_SECRET, namespace)

        request.addfinalizer(teardown_secret)
    else:
        get_logger().log_info(f"Registry secret {KUBEVIRT_REGISTRY_SECRET} already exists in namespace {namespace}")

    get_logger().log_info(f"Patching default service account with imagePullSecrets in {namespace}")
    args_sa = '{"imagePullSecrets":[{"name":"' + KUBEVIRT_REGISTRY_SECRET + '"}]}'
    KubectlApplyPatchKeywords(ssh_connection).apply_patch_saccount(
        "default",
        namespace,
        args_sa,
    )


@mark.p1
def test_kubevirt_upload_apply_delete(request: FixtureRequest):
    """
    Test kubevirt application upload, apply and delete.

    Test Steps:
        - Cleanup kubevirt application
        - Upload and Apply kubevirt application
        - Reapply the application
        - Verify pods are running
        - Reboot the controller
        - Verify application is in applied state
        - Verify pods are running
        - Remove and delete the application
        - Verify kubevirt HelmChart is removed
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Cleanup kubevirt application")
    cleanup_kubevirt_environment(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Removing kubevirt application if not already removed")
        cleanup_kubevirt_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_setup_step("Setting up kubevirt environment")
    setup_kubevirt_environment(ssh_connection)

    get_logger().log_test_case_step(f"Reapplying {APP_NAME} application")
    system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
    system_app_apply.system_application_apply(APP_NAME)

    get_logger().log_test_case_step("Verifying kubevirt pods are running after reapply")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=CDI_EXPECTED_PODS, namespace=CDI_NAMESPACE, timeout=120)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KUBEVIRT_EXPECTED_PODS, namespace=KUBEVIRT_NAMESPACE, timeout=120)

    system_host_list = SystemHostListKeywords(ssh_connection)
    active_controller = system_host_list.get_active_controller().get_host_name()

    get_logger().log_test_case_step(f"Rebooting controller {active_controller}")
    pre_uptime = system_host_list.get_uptime(active_controller)
    ssh_connection.send_as_sudo("reboot -f")
    system_host_reboot = SystemHostRebootKeywords(ssh_connection)
    reboot_success = system_host_reboot.wait_for_force_reboot(active_controller, pre_uptime)
    validate_equals(reboot_success, True, "Controller should reboot successfully")

    get_logger().log_test_case_step(f"Verifying {APP_NAME} is in applied state after reboot")
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    system_app_list.validate_app_status(APP_NAME, "applied", timeout=30)

    get_logger().log_test_case_step("Verifying kubevirt pods are running after reboot")
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=CDI_EXPECTED_PODS, namespace=CDI_NAMESPACE, timeout=120)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KUBEVIRT_EXPECTED_PODS, namespace=KUBEVIRT_NAMESPACE, timeout=120)

    get_logger().log_test_case_step("Removing kubevirt application")
    cleanup_kubevirt_environment(ssh_connection)

    get_logger().log_test_case_step("Verifying kubevirt HelmChart is removed")
    verify_kubevirt_helmchart_removed(ssh_connection)


@mark.p2
@mark.lab_has_standby_controller
def test_launch_vm_after_lock_unlock_multinode(request: FixtureRequest):
    """
    Test launching VM and verify it works after lock/unlock of standby.

    Test Steps:
        - Setup kubevirt environment
        - Get standby controller name
        - Create VM YAML with nodeSelector for standby
        - Deploy VM on standby controller
        - Verify VM and VMI are running on standby
        - Login to VM via virtctl console
        - Lock standby controller
        - Verify VM is stopped after lock
        - Unlock standby controller
        - Verify VM and VMI are still running after unlock
        - Login to VM via virtctl console after unlock
    """
    vm_name = "vm-cirros"
    vm_yaml_template = "cirros-vm-containerdisk-nodeselector.yaml.j2"
    remote_yaml_path = f"{KUBEVIRT_VM_DIR}/vm-cirros-standby.yaml"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Cleanup kubevirt environment")
    cleanup_kubevirt_environment(ssh_connection)

    kubectl_vm = KubectlGetVmKeywords(ssh_connection)
    kubectl_vmi = KubectlGetVmiKeywords(ssh_connection)
    system_host_lock = SystemHostLockKeywords(ssh_connection)
    system_host_list = SystemHostListKeywords(ssh_connection)

    get_logger().log_setup_step("Getting standby controller")
    standby_name = system_host_list.get_standby_controller().get_host_name()
    get_logger().log_info(f"Standby controller is {standby_name}")

    def cleanup():
        get_logger().log_teardown_step(f"Deleting VM {vm_name}")
        KubectlDeleteVmKeywords(ssh_connection).delete_vm(vm_name, ignore_not_found=True)

        get_logger().log_teardown_step("Cleaning up remote VM directory")
        FileKeywords(ssh_connection).delete_directory(KUBEVIRT_VM_DIR)

        get_logger().log_teardown_step(f"Unlocking {standby_name} if locked")
        if system_host_lock.is_host_locked(standby_name):
            system_host_lock.unlock_host(standby_name)

        get_logger().log_teardown_step("Cleaning up kubevirt environment")
        cleanup_kubevirt_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_setup_step("Setting up kubevirt environment")
    setup_kubevirt_environment(ssh_connection)

    get_logger().log_test_case_step(f"Creating VM YAML with nodeSelector for {standby_name}")
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.create_directory(KUBEVIRT_VM_DIR)
    YamlKeywords(ssh_connection).generate_yaml_file_from_template(
        get_stx_resource_path(f"resources/cloud_platform/containers/kubevirt/{vm_yaml_template}"),
        {"node_name": standby_name},
        "vm-cirros-standby.yaml",
        KUBEVIRT_VM_DIR,
    )

    get_logger().log_test_case_step(f"Deploying VM {vm_name} on {standby_name}")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(remote_yaml_path)

    get_logger().log_test_case_step(f"Verifying VM and VMI {vm_name} are running on {standby_name}")
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=120)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=120)
    vm_host = kubectl_vmi.get_vmi_node(vm_name)
    validate_equals(vm_host, standby_name, f"VM should be running on {standby_name}")

    get_logger().log_test_case_step(f"Logging into VM {vm_name} via virtctl console")
    VirtctlKeywords(ssh_connection).login_to_vm(vm_name, "cirros", "gocubsgo")

    get_logger().log_test_case_step(f"Locking standby controller {standby_name}")
    system_host_lock.lock_host(standby_name)

    get_logger().log_test_case_step(f"Verifying VM {vm_name} is stopped after lock")
    kubectl_vm.wait_for_vm_status(vm_name, "ErrorUnschedulable", timeout=240)

    get_logger().log_test_case_step(f"Unlocking standby controller {standby_name}")
    system_host_lock.unlock_host(standby_name)

    get_logger().log_test_case_step(f"Verifying VM and VMI {vm_name} are still running after unlock")
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=60)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=60)

    get_logger().log_test_case_step(f"Logging into VM {vm_name} via virtctl console after unlock")
    VirtctlKeywords(ssh_connection).login_to_vm(vm_name, "cirros", "gocubsgo")


@mark.p2
@mark.lab_has_min_2_compute
def test_launch_vm_after_lock_unlock_compute(request: FixtureRequest):
    """
    Test launching VM on compute and verify it works after lock/unlock.

    Test Steps:
        - Setup kubevirt environment
        - Create registry secret and patch default service account for image pulls
        - Get compute hostnames and generate VM YAML with node affinity
        - Deploy VM with nodeAffinity targeting compute nodes
        - Verify VM and VMI are running on a compute node
        - Login to VM via virtctl console
        - Lock the compute node hosting the VM
        - Verify VM migrates to another compute and is still running
        - Unlock the compute node
        - Verify VM and VMI are still running after unlock
        - Login to VM via virtctl console after unlock
    """
    vm_name = "vm-cirros-1"
    vm_yaml_resource = "resources/cloud_platform/containers/kubevirt/cirros-vm-containerdisk-compute.yaml"
    vm_namespace = "default"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Cleanup kubevirt environment")
    cleanup_kubevirt_environment(ssh_connection)

    kubectl_vm = KubectlGetVmKeywords(ssh_connection)
    kubectl_vmi = KubectlGetVmiKeywords(ssh_connection)
    system_host_lock = SystemHostLockKeywords(ssh_connection)

    locked_compute = None

    def cleanup():
        get_logger().log_teardown_step(f"Deleting VM {vm_name}")
        KubectlDeleteVmKeywords(ssh_connection).delete_vm(vm_name, ignore_not_found=True)

        get_logger().log_teardown_step("Cleaning up remote VM directory")
        FileKeywords(ssh_connection).delete_directory(KUBEVIRT_VM_DIR)

        if locked_compute and system_host_lock.is_host_locked(locked_compute):
            get_logger().log_teardown_step(f"Unlocking {locked_compute}")
            system_host_lock.unlock_host(locked_compute)

        get_logger().log_teardown_step("Cleaning up kubevirt environment")
        cleanup_kubevirt_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_setup_step("Setting up kubevirt environment")
    setup_kubevirt_environment(ssh_connection)

    get_logger().log_setup_step("Creating registry secret for image pulls")
    setup_registry_secret(ssh_connection, request, vm_namespace)

    get_logger().log_test_case_step("Getting compute hostnames for node affinity")
    computes = SystemHostListKeywords(ssh_connection).get_computes()
    compute_names = [compute.get_host_name() for compute in computes]
    get_logger().log_info(f"Compute hostnames for VM affinity: {compute_names}")

    get_logger().log_test_case_step("Generating VM YAML from template and uploading to remote host")
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.create_directory(KUBEVIRT_VM_DIR)
    yaml_keywords = YamlKeywords(ssh_connection)
    remote_yaml_path = yaml_keywords.generate_yaml_file_from_template(
        template_file=get_stx_resource_path(vm_yaml_resource),
        replacement_dictionary={"compute_hostnames": compute_names},
        target_file_name="cirros-vm-containerdisk-compute.yaml",
        target_remote_location=KUBEVIRT_VM_DIR,
    )

    get_logger().log_test_case_step(f"Deploying VM {vm_name}")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(remote_yaml_path)

    get_logger().log_test_case_step(f"Verifying VM and VMI {vm_name} are running on a compute node")
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=120)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=120)
    initial_node = kubectl_vmi.get_vmi_node(vm_name)
    get_logger().log_info(f"VM {vm_name} is running on {initial_node}")

    get_logger().log_test_case_step(f"Logging into VM {vm_name} via virtctl console")
    VirtctlKeywords(ssh_connection).login_to_vm(vm_name, "cirros", "gocubsgo")

    get_logger().log_test_case_step(f"Locking compute node {initial_node}")
    locked_compute = initial_node
    system_host_lock.lock_host(initial_node)

    get_logger().log_test_case_step(f"Verifying VM {vm_name} migrated away from {initial_node}")
    new_node = kubectl_vmi.wait_for_vmi_node_change(vm_name, initial_node, timeout=240)
    get_logger().log_info(f"VM migrated to {new_node}")

    get_logger().log_test_case_step(f"Verifying VM and VMI {vm_name} are still running after migration")
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=120)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=120)

    get_logger().log_test_case_step(f"Unlocking compute node {initial_node}")
    system_host_lock.unlock_host(initial_node)
    locked_compute = None

    get_logger().log_test_case_step(f"Verifying VM and VMI {vm_name} are still running after unlock")
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=60)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=60)

    get_logger().log_test_case_step(f"Verifying VM {vm_name} console is accessible after unlock")
    VirtctlKeywords(ssh_connection).verify_vm_console_accessible(vm_name)


@mark.p2
@mark.lab_is_simplex
def test_launch_vm_after_lock_unlock(request: FixtureRequest):
    """
    Test launching VM and verify it recovers after lock/unlock of the node.

    This test targets simplex systems where there is only one node.
    Locking the node causes the VM to become unschedulable, and unlocking
    allows it to recover.

    Test Steps:
        - Setup kubevirt environment
        - Create registry secret for image pulls
        - Deploy VM on the active controller with nodeSelector
        - Verify VM and VMI are running on the node
        - Login to VM via virtctl console
        - Lock the node
        - Verify VM becomes ErrorUnschedulable after lock
        - Unlock the node
        - Verify kubevirt application is in applied state after unlock
        - Verify kubevirt pods are running after unlock
        - Verify VM and VMI recover to Running state after unlock
        - Verify VM console is accessible after unlock
    """
    vm_name = "vm-cirros"
    vm_yaml_template = "cirros-vm-containerdisk-nodeselector.yaml.j2"
    remote_yaml_path = f"{KUBEVIRT_VM_DIR}/vm-cirros-node.yaml"
    vm_namespace = "default"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Cleanup kubevirt environment")
    cleanup_kubevirt_environment(ssh_connection)

    target_node = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    get_logger().log_info(f"Target node is {target_node}")

    system_host_lock = SystemHostLockKeywords(ssh_connection)
    kubectl_vm = KubectlGetVmKeywords(ssh_connection)
    kubectl_vmi = KubectlGetVmiKeywords(ssh_connection)

    def cleanup():
        new_ssh = LabConnectionKeywords().get_active_controller_ssh()

        get_logger().log_teardown_step(f"Unlocking {target_node} if locked")
        lock_kw = SystemHostLockKeywords(new_ssh)
        if lock_kw.is_host_locked(target_node):
            lock_kw.unlock_host(target_node)

        get_logger().log_teardown_step(f"Deleting VM {vm_name}")
        KubectlDeleteVmKeywords(new_ssh).delete_vm(vm_name, ignore_not_found=True)

        get_logger().log_teardown_step("Cleaning up remote VM directory")
        FileKeywords(new_ssh).delete_directory(KUBEVIRT_VM_DIR)

        get_logger().log_teardown_step("Cleaning up kubevirt environment")
        cleanup_kubevirt_environment(new_ssh)

    request.addfinalizer(cleanup)

    get_logger().log_setup_step("Setting up kubevirt environment")
    setup_kubevirt_environment(ssh_connection)

    get_logger().log_setup_step("Creating registry secret for image pulls")
    setup_registry_secret(ssh_connection, request, vm_namespace)

    get_logger().log_test_case_step(f"Creating VM YAML with nodeSelector for {target_node}")
    FileKeywords(ssh_connection).create_directory(KUBEVIRT_VM_DIR)
    YamlKeywords(ssh_connection).generate_yaml_file_from_template(
        get_stx_resource_path(f"resources/cloud_platform/containers/kubevirt/{vm_yaml_template}"),
        {"node_name": target_node},
        "vm-cirros-node.yaml",
        KUBEVIRT_VM_DIR,
    )

    get_logger().log_test_case_step(f"Deploying VM {vm_name} on {target_node}")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(remote_yaml_path)

    get_logger().log_test_case_step(f"Verifying VM and VMI {vm_name} are running on {target_node}")
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=120)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=120)
    vm_host = kubectl_vmi.get_vmi_node(vm_name)
    validate_equals(vm_host, target_node, f"VM should be running on {target_node}")

    get_logger().log_test_case_step(f"Logging into VM {vm_name} via virtctl console")
    VirtctlKeywords(ssh_connection).login_to_vm(vm_name, "cirros", "gocubsgo")

    get_logger().log_test_case_step(f"Locking node {target_node}")
    system_host_lock.lock_host(target_node)

    get_logger().log_test_case_step(f"Verifying VM {vm_name} is ErrorUnschedulable after lock")
    kubectl_vm.wait_for_vm_status(vm_name, "ErrorUnschedulable", timeout=240)

    get_logger().log_test_case_step(f"Unlocking node {target_node}")
    system_host_lock.unlock_host(target_node)

    get_logger().log_test_case_step(f"Verifying {APP_NAME} is in applied state after unlock")
    SystemApplicationListKeywords(ssh_connection).validate_app_status(APP_NAME, "applied", timeout=60)

    get_logger().log_test_case_step("Verifying kubevirt pods are running after unlock")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=CDI_EXPECTED_PODS, namespace=CDI_NAMESPACE, timeout=120)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KUBEVIRT_EXPECTED_PODS, namespace=KUBEVIRT_NAMESPACE, timeout=120)

    get_logger().log_test_case_step(f"Verifying VM and VMI {vm_name} recover to Running state after unlock")
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=300)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=120)

    get_logger().log_test_case_step(f"Verifying VM {vm_name} console is accessible after unlock")
    VirtctlKeywords(ssh_connection).verify_vm_console_accessible(vm_name)


@mark.p2
@mark.lab_has_standby_controller
def test_verify_vm_after_swact(request: FixtureRequest):
    """
    Test launching VM on active controller and verify it works after swact.

    Args:
        request (FixtureRequest): Pytest fixture request for teardown registration.

    Test Steps:
        - Setup kubevirt environment
        - Create registry secret for image pulls
        - Deploy VM with nodeSelector for active controller
        - Verify VM is running on active controller
        - Perform swact
        - Reconnect SSH to new active controller
        - Verify kubevirt application is in applied state after swact
        - Verify kubevirt pods are running after swact
        - Verify VM continues running after swact
    """
    vm_name = "vm-cirros"
    vm_yaml_template = "cirros-vm-containerdisk-nodeselector.yaml.j2"
    remote_yaml_path = f"{KUBEVIRT_VM_DIR}/vm-cirros-active.yaml"
    vm_namespace = "default"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Cleanup kubevirt environment")
    cleanup_kubevirt_environment(ssh_connection)

    get_logger().log_setup_step("Getting active controller")
    active_name = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    get_logger().log_info(f"Active controller is {active_name}")

    def cleanup():
        new_ssh = LabConnectionKeywords().get_active_controller_ssh()

        get_logger().log_teardown_step(f"Deleting VM {vm_name}")
        KubectlDeleteVmKeywords(new_ssh).delete_vm(vm_name, ignore_not_found=True)

        get_logger().log_teardown_step("Cleaning up remote VM directory")
        FileKeywords(new_ssh).delete_directory(KUBEVIRT_VM_DIR)

        get_logger().log_teardown_step("Cleaning up kubevirt environment")
        cleanup_kubevirt_environment(new_ssh)

        get_logger().log_teardown_step(f"Swacting back to original active controller {active_name}")
        current_active = SystemHostListKeywords(new_ssh).get_active_controller().get_host_name()
        if current_active != active_name:
            SystemHostSwactKeywords(new_ssh).host_swact()

    request.addfinalizer(cleanup)

    get_logger().log_setup_step("Setting up kubevirt environment")
    setup_kubevirt_environment(ssh_connection)

    get_logger().log_setup_step("Creating registry secret for image pulls")
    setup_registry_secret(ssh_connection, request, vm_namespace)

    get_logger().log_test_case_step(f"Creating VM YAML with nodeSelector for {active_name}")
    FileKeywords(ssh_connection).create_directory(KUBEVIRT_VM_DIR)
    YamlKeywords(ssh_connection).generate_yaml_file_from_template(
        get_stx_resource_path(f"resources/cloud_platform/containers/kubevirt/{vm_yaml_template}"),
        {"node_name": active_name},
        "vm-cirros-active.yaml",
        KUBEVIRT_VM_DIR,
    )

    get_logger().log_test_case_step(f"Deploying VM {vm_name} on active controller {active_name}")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(remote_yaml_path)

    get_logger().log_test_case_step(f"Verifying VM {vm_name} is running on {active_name}")
    kubectl_vm = KubectlGetVmKeywords(ssh_connection)
    kubectl_vmi = KubectlGetVmiKeywords(ssh_connection)
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=120)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=120)
    vm_host = kubectl_vmi.get_vmi_node(vm_name)
    validate_equals(vm_host, active_name, f"VM should be running on {active_name}")

    get_logger().log_test_case_step("Performing swact")
    SystemHostSwactKeywords(ssh_connection).host_swact()

    get_logger().log_test_case_step("Reconnecting to new active controller after swact")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kubectl_vm = KubectlGetVmKeywords(ssh_connection)
    kubectl_vmi = KubectlGetVmiKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Verifying {APP_NAME} is in applied state after swact")
    SystemApplicationListKeywords(ssh_connection).validate_app_status(APP_NAME, "applied", timeout=30)

    get_logger().log_test_case_step("Verifying kubevirt pods are running after swact")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=CDI_EXPECTED_PODS, namespace=CDI_NAMESPACE, timeout=120)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KUBEVIRT_EXPECTED_PODS, namespace=KUBEVIRT_NAMESPACE, timeout=120)

    get_logger().log_test_case_step(f"Verifying VM {vm_name} is running after swact")
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=240)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=120)

    get_logger().log_test_case_step(f"Verifying VM {vm_name} is still on original node {active_name}")
    vm_node_after_swact = kubectl_vmi.get_vmi_node(vm_name)
    get_logger().log_info(f"VM {vm_name} is running on {vm_node_after_swact}")
    validate_equals(vm_node_after_swact, active_name, f"VM should remain on {active_name} after swact")


@mark.p2
@mark.lab_has_min_2_compute
def test_launch_vm_after_reboot_compute(request: FixtureRequest):
    """
    Test launching VM on compute and verify it works after compute reboot.

    Args:
        request (FixtureRequest): Pytest fixture request for teardown registration.

    Test Steps:
        - Setup kubevirt environment
        - Create registry secret for image pulls
        - Get compute hostnames and generate VM YAML with node affinity
        - Deploy VM with nodeAffinity targeting compute nodes
        - Verify VM and VMI are running on a compute node
        - Login to VM via virtctl console
        - Force reboot the compute node hosting the VM
        - Verify VM migrates to another compute
        - Verify VM and VMI are running after migration
        - Wait for rebooted compute to come back online
        - Verify kubevirt application is in applied state after reboot
        - Verify kubevirt pods are running after reboot
        - Verify VM console is accessible after reboot
    """
    vm_name = "vm-cirros-1"
    vm_yaml_resource = "resources/cloud_platform/containers/kubevirt/cirros-vm-containerdisk-compute.yaml"
    vm_namespace = "default"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Cleanup kubevirt environment")
    cleanup_kubevirt_environment(ssh_connection)

    kubectl_vm = KubectlGetVmKeywords(ssh_connection)
    kubectl_vmi = KubectlGetVmiKeywords(ssh_connection)
    system_host_list = SystemHostListKeywords(ssh_connection)
    system_host_lock = SystemHostLockKeywords(ssh_connection)

    rebooted_compute = None

    def cleanup():
        if rebooted_compute and not system_host_lock.is_host_unlocked(rebooted_compute):
            get_logger().log_teardown_step(f"Waiting for {rebooted_compute} to come back online")
            system_host_lock.wait_for_host_unlocked(rebooted_compute)

        get_logger().log_teardown_step(f"Deleting VM {vm_name}")
        KubectlDeleteVmKeywords(ssh_connection).delete_vm(vm_name, ignore_not_found=True)

        get_logger().log_teardown_step("Cleaning up remote VM directory")
        FileKeywords(ssh_connection).delete_directory(KUBEVIRT_VM_DIR)

        get_logger().log_teardown_step("Cleaning up kubevirt environment")
        cleanup_kubevirt_environment(ssh_connection)

    request.addfinalizer(cleanup)

    get_logger().log_setup_step("Setting up kubevirt environment")
    setup_kubevirt_environment(ssh_connection)

    get_logger().log_setup_step("Creating registry secret for image pulls")
    setup_registry_secret(ssh_connection, request, vm_namespace)

    get_logger().log_test_case_step("Getting compute hostnames for node affinity")
    computes = system_host_list.get_computes()
    compute_names = [compute.get_host_name() for compute in computes]
    get_logger().log_info(f"Compute hostnames for VM affinity: {compute_names}")

    get_logger().log_test_case_step("Generating VM YAML from template and uploading to remote host")
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.create_directory(KUBEVIRT_VM_DIR)
    yaml_keywords = YamlKeywords(ssh_connection)
    remote_yaml_path = yaml_keywords.generate_yaml_file_from_template(
        template_file=get_stx_resource_path(vm_yaml_resource),
        replacement_dictionary={"compute_hostnames": compute_names},
        target_file_name="cirros-vm-containerdisk-compute.yaml",
        target_remote_location=KUBEVIRT_VM_DIR,
    )

    get_logger().log_test_case_step(f"Deploying VM {vm_name}")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(remote_yaml_path)

    get_logger().log_test_case_step(f"Verifying VM and VMI {vm_name} are running on a compute node")
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=120)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=120)
    initial_node = kubectl_vmi.get_vmi_node(vm_name)
    get_logger().log_info(f"VM {vm_name} is running on {initial_node}")

    get_logger().log_test_case_step(f"Logging into VM {vm_name} via virtctl console")
    VirtctlKeywords(ssh_connection).login_to_vm(vm_name, "cirros", "gocubsgo")

    get_logger().log_test_case_step(f"Rebooting compute node {initial_node}")
    rebooted_compute = initial_node
    compute_ssh = LabConnectionKeywords().get_ssh_for_hostname(initial_node)
    pre_uptime = system_host_list.get_uptime(initial_node)
    SystemHostRebootKeywords(compute_ssh).host_force_reboot()

    get_logger().log_test_case_step(f"Verifying VM {vm_name} migrated away from {initial_node}")
    new_node = kubectl_vmi.wait_for_vmi_node_change(vm_name, initial_node, timeout=240)
    get_logger().log_info(f"VM {vm_name} migrated to {new_node}")

    get_logger().log_test_case_step(f"Verifying VM and VMI {vm_name} are running after migration")
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=120)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=120)

    get_logger().log_test_case_step(f"Waiting for compute {initial_node} to complete reboot")
    reboot_success = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(initial_node, pre_uptime)
    validate_equals(reboot_success, True, f"{initial_node} should reboot successfully")

    get_logger().log_test_case_step(f"Verifying {APP_NAME} is in applied state after reboot")
    SystemApplicationListKeywords(ssh_connection).validate_app_status(APP_NAME, "applied", timeout=30)

    get_logger().log_test_case_step("Verifying kubevirt pods are running after reboot")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=CDI_EXPECTED_PODS, namespace=CDI_NAMESPACE, timeout=120)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KUBEVIRT_EXPECTED_PODS, namespace=KUBEVIRT_NAMESPACE, timeout=120)

    get_logger().log_test_case_step(f"Verifying VM {vm_name} console is accessible after reboot")
    VirtctlKeywords(ssh_connection).verify_vm_console_accessible(vm_name)


@mark.p2
def test_launch_vm_after_reboot(request: FixtureRequest):
    """
    Test launching VM and verify it recovers after rebooting the node.

    Test Steps:
        - Setup kubevirt environment
        - Create registry secret for image pulls
        - Deploy VM on the active controller
        - Verify VM and VMI are running
        - Login to VM via virtctl console
        - Force reboot the node hosting the VM
        - Wait for node to come back online
        - Verify kubevirt application is in applied state after reboot
        - Verify kubevirt pods are running after reboot
        - Verify VM recovers and reaches Running state
        - Verify VM console is accessible after reboot
    """
    vm_name = "vm-cirros"
    vm_yaml_template = "cirros-vm-containerdisk-nodeselector.yaml.j2"
    remote_yaml_path = f"{KUBEVIRT_VM_DIR}/vm-cirros-node.yaml"
    vm_namespace = "default"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Cleanup kubevirt environment")
    cleanup_kubevirt_environment(ssh_connection)

    target_node = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()
    get_logger().log_info(f"Target node is {target_node}")

    def cleanup():
        get_logger().log_teardown_step(f"Deleting VM {vm_name}")
        new_ssh = LabConnectionKeywords().get_active_controller_ssh()
        KubectlDeleteVmKeywords(new_ssh).delete_vm(vm_name, ignore_not_found=True)

        get_logger().log_teardown_step("Cleaning up remote VM directory")
        FileKeywords(new_ssh).delete_directory(KUBEVIRT_VM_DIR)

        get_logger().log_teardown_step("Cleaning up kubevirt environment")
        cleanup_kubevirt_environment(new_ssh)

    request.addfinalizer(cleanup)

    get_logger().log_setup_step("Setting up kubevirt environment")
    setup_kubevirt_environment(ssh_connection)

    get_logger().log_setup_step("Creating registry secret for image pulls")
    setup_registry_secret(ssh_connection, request, vm_namespace)

    get_logger().log_test_case_step(f"Creating VM YAML with nodeSelector for {target_node}")
    FileKeywords(ssh_connection).create_directory(KUBEVIRT_VM_DIR)
    YamlKeywords(ssh_connection).generate_yaml_file_from_template(
        get_stx_resource_path(f"resources/cloud_platform/containers/kubevirt/{vm_yaml_template}"),
        {"node_name": target_node},
        "vm-cirros-node.yaml",
        KUBEVIRT_VM_DIR,
    )

    get_logger().log_test_case_step(f"Deploying VM {vm_name} on {target_node}")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(remote_yaml_path)

    get_logger().log_test_case_step(f"Verifying VM and VMI {vm_name} are running")
    kubectl_vm = KubectlGetVmKeywords(ssh_connection)
    kubectl_vmi = KubectlGetVmiKeywords(ssh_connection)
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=120)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=120)
    vm_host = kubectl_vmi.get_vmi_node(vm_name)
    validate_equals(vm_host, target_node, f"VM should be running on {target_node}")

    get_logger().log_test_case_step(f"Logging into VM {vm_name} via virtctl console")
    VirtctlKeywords(ssh_connection).login_to_vm(vm_name, "cirros", "gocubsgo")

    get_logger().log_test_case_step(f"Rebooting node {target_node}")
    pre_uptime = SystemHostListKeywords(ssh_connection).get_uptime(target_node)
    SystemHostRebootKeywords(ssh_connection).host_force_reboot()

    get_logger().log_test_case_step(f"Waiting for {target_node} to come back online after reboot")
    reboot_success = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(target_node, pre_uptime)
    validate_equals(reboot_success, True, f"{target_node} should reboot successfully")

    get_logger().log_test_case_step(f"Verifying {APP_NAME} is in applied state after reboot")
    SystemApplicationListKeywords(ssh_connection).validate_app_status(APP_NAME, "applied", timeout=60)

    get_logger().log_test_case_step("Verifying kubevirt pods are running after reboot")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=CDI_EXPECTED_PODS, namespace=CDI_NAMESPACE, timeout=120)
    kubectl_pods.wait_for_pods_to_reach_status(expected_status="Running", pod_names=KUBEVIRT_EXPECTED_PODS, namespace=KUBEVIRT_NAMESPACE, timeout=120)

    get_logger().log_test_case_step(f"Verifying VM {vm_name} recovers and reaches Running state after reboot")
    kubectl_vm.wait_for_vm_status(vm_name, "Running", timeout=300)
    kubectl_vmi.wait_for_vmi_status(vm_name, "Running", timeout=120)

    get_logger().log_test_case_step(f"Verifying VM {vm_name} console is accessible after reboot")
    VirtctlKeywords(ssh_connection).login_to_vm(vm_name, "cirros", "gocubsgo")

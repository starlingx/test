import time

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.helm.helm_keywords import HelmKeywords
from keywords.cloud_platform.networking.sriov.get_sriov_config_keywords import GetSriovConfigKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.datanetwork.system_datanetwork_add_keywords import SystemDatanetworkAddKeywords
from keywords.cloud_platform.system.datanetwork.system_datanetwork_delete_keywords import SystemDatanetworkDeleteKeywords
from keywords.cloud_platform.system.datanetwork.system_datanetwork_list_keywords import SystemDatanetworkListKeywords
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_if_keywords import SystemHostInterfaceKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.interface.system_interface_datanetwork_keywords import SystemInterfaceDatanetworkKeywords
from keywords.docker.images.docker_images_keywords import DockerImagesKeywords
from keywords.docker.images.docker_load_image_keywords import DockerLoadImageKeywords
from keywords.docker.images.docker_remove_images_keywords import DockerRemoveImagesKeywords
from keywords.docker.login.docker_login_keywords import DockerLoginKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.cat.cat_cpu_manager_state_keywords import CatCpuManagerStateKeywords
from keywords.k8s.cat.cat_cpuset_keywords import CatCpuSetKeywords
from keywords.k8s.daemonsets.kubectl_delete_daemonset_apps_keywords import KubectlDeleteDaemonsetAppsKeywords
from keywords.k8s.daemonsets.kubectl_get_daemonsets_keywords import KubectlGetDaemonsetsKeywords
from keywords.k8s.deployments.kubectl_delete_deployments_keywords import KubectlDeleteDeploymentsKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.network_definition.kubectl_delete_network_definition_keywords import KubectlDeleteNetworkDefinitionKeywords
from keywords.k8s.node.kubectl_describe_node_keywords import KubectlDescribeNodeKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_copy_to_pod_keywords import KubectlCopyToPodKeywords
from keywords.k8s.pods.kubectl_create_pods_keywords import KubectlCreatePodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.validation.kubectl_get_pods_validation_keywords import KubectlPodValidationKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.service.kubectl_delete_service_keywords import KubectlDeleteServiceKeywords
from keywords.linux.dpkg.dpkg_status import DpkgStatusKeywords
from keywords.linux.ip.ip_keywords import IPKeywords
from keywords.linux.ip.object.ip_link_show_output import IPLinkShowOutput
from keywords.linux.process_status.process_status_args_keywords import ProcessStatusArgsKeywords
from keywords.server.power_keywords import PowerKeywords
from pytest import mark


@mark.p0
@mark.lab_is_simplex
def test_push_docker_image_to_local_registry_simplex(request):
    """
    Test push a docker image to local docker registry

    Test Steps:
      - Copy busybox.tar file to controller
      - Load image to host
      - tag image for local registry
      - Push image to local registry
      - Assert image appears using docker images command

    Cleanup
      - Remove docker image

    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    local_registry = ConfigurationManager.get_docker_config().get_registry('local_registry')

    FileKeywords(ssh_connection).upload_file(get_stx_resource_path("resources/images/busybox.tar"), "/home/sysadmin/busybox.tar", overwrite=False)
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, 'local-secret')
    docker_load_image_keywords = DockerLoadImageKeywords(ssh_connection)
    docker_load_image_keywords.load_docker_image_to_host('busybox.tar')
    docker_load_image_keywords.tag_docker_image_for_registry('busybox', 'busybox', local_registry)
    docker_load_image_keywords.push_docker_image_to_registry('busybox', local_registry)

    def remove_docker_image():
        """
        Finalizer to remove docker image
        Returns:

        """
        DockerRemoveImagesKeywords(ssh_connection).remove_docker_image('busybox')

    request.addfinalizer(remove_docker_image)

    # remove cached images
    docker_image_keywords = DockerImagesKeywords(ssh_connection)
    docker_image_keywords.remove_image('registry.local:9001/busybox')
    docker_image_keywords.remove_image('busybox')

    # pull image
    docker_image_keywords.pull_image('registry.local:9001/busybox')

    images = DockerImagesKeywords(ssh_connection).list_images()
    assert 'registry.local:9001/busybox' in list(map(lambda image: image.get_repository(), images))


@mark.p0
@mark.lab_has_standby_controller
def test_push_docker_image_to_local_registry_standby(request):
    """
    Test push a docker image to local docker registry

    Test Steps:
      - Copy busybox.tar file to controller
      - Load image to host
      - tag image for local registry
      - Push image to local registry
      - Assert image appears on active controller using docker images command
      - Assert image appears on standby controller

    Cleanup
      - Remove docker image

    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    local_registry = ConfigurationManager.get_docker_config().get_registry('local_registry')

    FileKeywords(ssh_connection).upload_file(get_stx_resource_path("resources/images/busybox.tar"), "/home/sysadmin/busybox.tar", overwrite=False)
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, 'local-secret')
    docker_load_image_keywords = DockerLoadImageKeywords(ssh_connection)
    docker_load_image_keywords.load_docker_image_to_host('busybox.tar')
    docker_load_image_keywords.tag_docker_image_for_registry('busybox', 'busybox', local_registry)
    docker_load_image_keywords.push_docker_image_to_registry('busybox', local_registry)

    def remove_docker_image():
        """
        Finalizer to remove docker image
        Returns:

        """
        DockerRemoveImagesKeywords(ssh_connection).remove_docker_image('busybox')

    request.addfinalizer(remove_docker_image)

    # remove cached images from active controller
    docker_image_keywords = DockerImagesKeywords(ssh_connection)
    docker_image_keywords.remove_image('registry.local:9001/busybox')
    docker_image_keywords.remove_image('busybox')

    # pull image
    docker_image_keywords.pull_image('registry.local:9001/busybox')

    # check images on active controller
    images = docker_image_keywords.list_images()
    assert 'registry.local:9001/busybox' in list(map(lambda image: image.get_repository(), images))

    # check on standby controller
    standby_ssh_connection = LabConnectionKeywords().get_standby_controller_ssh()

    # docker login on standby controller
    DockerLoginKeywords(standby_ssh_connection).login(local_registry.get_user_name(), local_registry.get_password(), local_registry.get_registry_url())

    # remove cached images from standby controller
    docker_image_keywords = DockerImagesKeywords(standby_ssh_connection)
    docker_image_keywords.remove_image('registry.local:9001/busybox')
    docker_image_keywords.remove_image('busybox')

    # pull image
    docker_image_keywords.pull_image('registry.local:9001/busybox')

    # check images on active controller
    images = docker_image_keywords.list_images()
    assert 'registry.local:9001/busybox' in list(map(lambda image: image.get_repository(), images))


@mark.p0
@mark.lab_is_simplex
def test_host_operations_with_custom_kubectl_app_simplex(request):
    """
    Tests that custom app is created and comes back to running when lock/unlock happens

    Test Steps:
        - deploy image to local registry
        - deploy pods and ensure running
        - lock/unlock host
        - assert pods are running after unlock
        - cleanup pods


    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    deploy_images_to_local_registry(ssh_connection)
    deploy_pods(request, ssh_connection)

    # lock/unlock controller
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host("controller-0")
    assert lock_success, "Controller was not locked successfully."
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host("controller-0")
    assert unlock_success, "Controller was not unlocked successfully."

    assert wait_for_pods_status_running, "Consumer pods did not reach running status in expected time after lock/unlock"


@mark.p0
@mark.lab_has_standby_controller
def test_host_operations_with_custom_kubectl_app_standby(request):
    """
    Tests that custom app is created and comes back to running when lock/unlock happens

    Test Steps:
        - deploy image to local registry
        - deploy pods and ensure running
        - swatch hosts
        - assert pods are running after swact
        - cleanup pods


    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    deploy_images_to_local_registry(ssh_connection)
    deploy_pods(request, ssh_connection)

    swact_success = SystemHostSwactKeywords(ssh_connection).host_swact()
    assert swact_success, 'Host swact completed successfully'

    # if swact was successful, swact again at the end
    def swact_controller():
        SystemHostSwactKeywords(ssh_connection).host_swact()

    request.addfinalizer(swact_controller)

    assert wait_for_pods_status_running, "Consumer pods did not reach running status in expected time after swact"


@mark.p0
@mark.lab_is_simplex
def test_upload_charts_via_helm_upload_simplex():
    """
    Test upload helm charts via helm-upload cmd directly.

    Test Steps:
        - Delete file from /var/www/pages/helm_charts/starlingx
        - Upload helm charts via 'helm-upload <tar_file>'
        - Verify the charts appear at /var/www/pages/helm_charts/starlingx

    """
    helm_chart_location = "/var/www/pages/helm_charts/starlingx"
    helm_file = "hello-kitty-min-k8s-version.tgz"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Delete file tar file if it exists
    file_keywords = FileKeywords(ssh_connection)
    if file_keywords.file_exists(f"{helm_chart_location}/{helm_file}"):
        file_keywords.delete_file(f"{helm_chart_location}/{helm_file}")

    # upload file to lab
    file_keywords.upload_file(get_stx_resource_path(f"resources/cloud_platform/containers/{helm_file}"), f"/home/sysadmin/{helm_file}", overwrite=True)

    # run helm-upload command
    HelmKeywords(ssh_connection).helm_upload('starlingx', f'/home/sysadmin/{helm_file}')

    assert file_keywords.file_exists(f"{helm_chart_location}/{helm_file}")


@mark.p0
@mark.lab_has_standby_controller
def test_upload_charts_via_helm_upload_standby_controller(request):
    """
    Test upload helm charts via helm-upload cmd directly.

    Test Steps:
        - Delete file from /var/www/pages/helm_charts/starlingx
        - Upload helm charts via 'helm-upload <tar_file>'
        - Verify the charts appear at /var/www/pages/helm_charts/starlingx
        - swact to standby controller
        - Validate that charts appear at /var/www/pages/helm-charts/starlingx

    """
    helm_chart_location = "/var/www/pages/helm_charts/starlingx"
    helm_file = "hello-kitty-min-k8s-version.tgz"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Delete file tar file if it exists
    file_keywords = FileKeywords(ssh_connection)
    if file_keywords.file_exists(f"{helm_chart_location}/{helm_file}"):
        file_keywords.delete_file(f"{helm_chart_location}/{helm_file}")

    # upload file to lab
    file_keywords.upload_file(get_stx_resource_path(f"resources/cloud_platform/containers/{helm_file}"), f"/home/sysadmin/{helm_file}", overwrite=True)

    # run helm-upload command
    HelmKeywords(ssh_connection).helm_upload('starlingx', f'/home/sysadmin/{helm_file}')

    assert file_keywords.file_exists(f"{helm_chart_location}/{helm_file}")

    swact_success = SystemHostSwactKeywords(ssh_connection).host_swact()
    assert swact_success, "Swact was not completed successfully"

    # add teardown
    def swact_back():
        SystemHostSwactKeywords(ssh_connection).host_swact()

    request.addfinalizer(swact_back)

    # assert file is on the standby controller
    assert file_keywords.file_exists(f"{helm_chart_location}/{helm_file}")


@mark.p0
def test_system_core_dumps():
    """
    Test to validate no core dump files found

    Test Steps:
        - Validate no files found in /var/lib/systemd/coredump directory
    Returns:

    """
    core_dump_dir = '/var/lib/systemd/coredump/'

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    files = FileKeywords(ssh_connection).get_files_in_dir(core_dump_dir)

    assert not files, "Core dump files were found"  # check the files is empty, assert will print out filenames if they exist


@mark.p0
def test_system_crash_reports():
    """
    Test to validate no crash reports found

    Test Steps:
        - Validate no files found in /var/crash directory
        - Validate no files found in the /var/logs/crash directory
    Returns:

    """
    crash_report_dir = '/var/crash'
    crash_log_dir = '/var/log/crash'

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    files = FileKeywords(ssh_connection).get_files_in_dir(crash_report_dir)
    assert not files, "Crash report files were found"  # check that files is empty, assert will print out filenames if they exist

    files = FileKeywords(ssh_connection).get_files_in_dir(crash_log_dir)
    assert not files, "Crash log files were found"  # check that files is empty, assert will print out filenames if they exist


@mark.p0
@mark.lab_has_standby_controller
def test_force_reboot_host_active_controller(request):
    """
    Ungraceful reboot host of active controller

    Test Steps:
        - Power off and power on active host
        - Validate that the hosts will swact
        - Validate that the host recovers

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pre_active_host = SystemHostListKeywords(ssh_connection).get_active_controller()
    pre_standby_host = SystemHostListKeywords(ssh_connection).get_standby_controller()

    power_keywords = PowerKeywords(ssh_connection)
    assert power_keywords.power_off(pre_active_host.get_host_name()), 'host was not powered off'

    # swact the hosts at the end of the test
    request.addfinalizer(SystemHostSwactKeywords(ssh_connection).host_swact)

    # Power on method checks host status and alarms
    assert power_keywords.power_on(pre_active_host.get_host_name()), 'host did not come back online in time'

    post_active_host = SystemHostListKeywords(ssh_connection).get_active_controller()
    post_standby_host = SystemHostListKeywords(ssh_connection).get_standby_controller()

    assert pre_active_host.get_host_name() == post_standby_host.get_host_name(), 'Active host did not swact to standby'
    assert pre_standby_host.get_host_name() == post_active_host.get_host_name(), 'Standby host did not swact to active'


@mark.p0
@mark.lab_has_standby_controller
def test_force_reboot_active_host_swact_timeout(request):
    """
    Ungraceful reboot host of active controller

    Test Steps:
        - Power off active host
        - Validate that the standby controller will become active before the MAX Timeout

    """
    MAX_SWACT_TIME = 100

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pre_active_host = SystemHostListKeywords(ssh_connection).get_active_controller()
    pre_standby_host = SystemHostListKeywords(ssh_connection).get_standby_controller()

    power_keywords = PowerKeywords(ssh_connection)
    assert power_keywords.power_off(pre_active_host.get_host_name()), 'host was not powered off'
    start_time = time.time()

    # swact the hosts at the end of the test
    request.addfinalizer(SystemHostSwactKeywords(ssh_connection).host_swact)
    # power on host at the end of the test
    request.addfinalizer(lambda: power_keywords.power_on(pre_active_host.get_host_name()))

    timeout = time.time() + MAX_SWACT_TIME
    refresh_time = 5

    while time.time() < timeout:
        try:
            active_controller = SystemHostListKeywords(ssh_connection).get_active_controller()
            if active_controller.get_host_name() == pre_standby_host.get_host_name():
                break
        except Exception:
            get_logger().log_info(f"Found an exception when running system host list command. " f"Trying again after {refresh_time} seconds")

        time.sleep(refresh_time)
    end_time = time.time()

    assert end_time - start_time < MAX_SWACT_TIME, 'swact time was greater then the max timeout'


@mark.p0
@mark.lab_has_standby_controller
def test_force_reboot_host_standby_controller():
    """
    Ungraceful reboot host of standby controller

    Test Steps:
        - Power off and power on standby host
        - Validate that the host recovers

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    standby_host = SystemHostListKeywords(ssh_connection).get_standby_controller()

    power_keywords = PowerKeywords(ssh_connection)
    assert power_keywords.power_off(standby_host.get_host_name()), 'host was not powered off'

    # Power on method checks host status and alarms
    assert power_keywords.power_on(standby_host.get_host_name()), 'host did not come back online in time'


@mark.p0
@mark.lab_has_worker
def test_force_reboot_host_worker():
    """
    Ungraceful reboot host of compute

    Test Steps:
        - Power off and power on compute
        - Validate that the host recovers

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    computes = SystemHostListKeywords(ssh_connection).get_compute()

    assert len(computes) > 0, 'no computes were found on the system'

    compute = computes[0]  # we just need one compute so take the first one

    power_keywords = PowerKeywords(ssh_connection)
    assert power_keywords.power_off(compute.get_host_name()), 'host was not powered off'

    # Power on method checks host status and alarms
    assert power_keywords.power_on(compute.get_host_name()), 'host did not come back online in time'


@mark.p0
@mark.lab_has_storage
def test_force_reboot_host_storage():
    """
    Ungraceful reboot host of storage node

    Test Steps:
        - Power off and power on storage
        - Validate that the host recovers

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    storages = SystemHostListKeywords(ssh_connection).get_storages()

    assert len(storages) > 0, 'no storages were found on the system'

    storage = storages[0]  # we just need one compute so take the first one

    power_keywords = PowerKeywords(ssh_connection)
    assert power_keywords.power_off(storage.get_host_name()), 'host was not powered off'

    # Power on method checks host status and alarms
    assert power_keywords.power_on(storage.get_host_name()), 'host did not come back online in time'


def deploy_images_to_local_registry(ssh_connection: SSHConnection):
    """
    Deploys images to the local registry for testcases in this suite
    Args:
        ssh_connection (): the ssh connection

    Returns:

    """
    local_registry = ConfigurationManager.get_docker_config().get_registry('local_registry')

    docker_load_image_keywords = DockerLoadImageKeywords(ssh_connection)
    FileKeywords(ssh_connection).upload_file(get_stx_resource_path("resources/images/resource-consumer.tar"), "/home/sysadmin/resource-consumer.tar", overwrite=False)
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, 'local-secret')
    docker_load_image_keywords.load_docker_image_to_host('resource-consumer.tar')
    docker_load_image_keywords.tag_docker_image_for_registry('gcr.io/kubernetes-e2e-test-images/resource-consumer:1.4', 'resource-consumer', local_registry)
    docker_load_image_keywords.push_docker_image_to_registry('resource-consumer', local_registry)


def deploy_pods(request, ssh_connection: SSHConnection):
    """
    Deploys pods needed by some suites in this suite
    Args:
        request (): request needed for adding teardown
        ssh_connection (): the ssh connection

    Returns:

    """

    # Create teardown to remove pods
    def remove_deployments_and_pods():
        """
        Finalizer to remove deployments and pods
        Returns:

        """
        rc = KubectlDeleteDeploymentsKeywords(ssh_connection).cleanup_deployment('resource-consumer')
        rc += KubectlDeleteServiceKeywords(ssh_connection).cleanup_service('resource-consumer')
        rc += KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace('resource-consumer')

        assert rc == 0

    request.addfinalizer(remove_deployments_and_pods)

    FileKeywords(ssh_connection).upload_file(get_stx_resource_path('resources/cloud_platform/sanity/pods/consumer_app.yaml'), '/home/sysadmin/consumer_app.yaml')
    kubectl_create_pods_keyword = KubectlCreatePodsKeywords(ssh_connection)
    kubectl_create_pods_keyword.create_from_yaml('/home/sysadmin/consumer_app.yaml')

    assert wait_for_pods_status_running(ssh_connection), "Consumer pods did not reach running status in expected time"


def wait_for_pods_status_running(ssh_connection: SSHConnection) -> bool:
    """
    Gets the name of the pods and waits for them to be running
    Args:
        ssh_connection (): the ssh connection

    Returns: True if they are running, False otherwise

    """
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()

    consumer_pods = pods.get_pods_start_with('resource-consumer')
    assert len(consumer_pods) == 2, "Incorrect number of consumer_pods were created"
    consumer_pod1_name = consumer_pods[0].get_name()
    consumer_pod2_name = consumer_pods[1].get_name()

    # wait for all pods to be running
    kubectl_get_pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    consumer_pod1_running = kubectl_get_pods_keywords.wait_for_pod_status(consumer_pod1_name, 'Running')
    consumer_pod2_running = kubectl_get_pods_keywords.wait_for_pod_status(consumer_pod2_name, 'Running')

    return consumer_pod1_running and consumer_pod2_running


@mark.p0
@mark.lab_has_processor_min_2
def test_isolated_2processors_2big_pods_best_effort_simplex(request):
    """
    This test case will validate the isolated CPU capability of the system when using 2-processors by creating 2 big pods
    on the system with kube-cpu-mgr-policy=static and kube-topology-mgr-policy=best-effort.

        Test Steps:
        - Lock the Controller
        - Use 'system host-cpu-modify' to set all CPUs to be application-isolated, except for necessary platform/application cores.
        - Set the label values of 'kube-cpu-mgr-policy=static' and 'kube-topology-mgr-policy=best-effort'
        - Unlock the Controller to apply the configuration change
        - Validate that the isolcpu plugin is enabled
        - Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs
        - Validate that the labels are set correctly in the host-labels-list
        - Ensure that the kube-system pods recover from the configuration change
        - Check cpu-manager-policy from state file on active controller
        - Create Pod0 to fill the isolated cpus on one processor
        - Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs now that pod0 is using isolated CPUs
        - Validate that the CPUs used by pod0 are all on the same processor.
        - Create Pod 1 to fill the isolated cpus on the second processor
        - Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs now that pod0 and pod1 is using all the isolated CPUs
        - Validate that the CPUs used by pod1 are all on the same processor.

        Teardown:
        - Delete the Pods
        - Revert the isolated cpus / labels configuration
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller_name = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    host_cpu_output = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(active_controller_name)
    assert host_cpu_output.get_processor_count() == 2, f"This test case requires 2 processors. Observed: {host_cpu_output.get_processor_count()} processor(s)"

    # Gather the current state of CPU distribution
    total_cpus_processor_0 = host_cpu_output.get_number_of_physical_cores(processor_id=0)
    total_cpus_processor_1 = host_cpu_output.get_number_of_physical_cores(processor_id=1)
    get_logger().log_info(f"There are {total_cpus_processor_0} cores on processor 0 and {total_cpus_processor_1} on processor 1.")

    # Target state of CPU distribution for the Test
    target_application_isolated_cpus_processor_0 = total_cpus_processor_0 - 2  # Leave 2 Physical Cores for Platform
    target_application_isolated_cpus_processor_1 = total_cpus_processor_1 - 2  # Leave 2 Physical Cores for Applications
    target_isolated_cpu_physical_cores = target_application_isolated_cpus_processor_0 + target_application_isolated_cpus_processor_1
    assert target_application_isolated_cpus_processor_0 > 1, "There are at least 3 Physical Cores on processor 0"
    assert target_application_isolated_cpus_processor_1 > 1, "There are at least 3 Physical Cores on processor 1"

    # Lock Controller-0 to configure CPUs.
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(active_controller_name)
    assert lock_success, "Controller was not locked successfully."

    get_logger().log_info("Modify the CPUs to have 2 Platform cores on the first processor and 2 Application cores on the second processor.")
    get_logger().log_info("The rest of the cores will be set to Application-Isolated.")

    # Revert CPU configuration to default.
    system_host_cpu_keywords = SystemHostCPUKeywords(ssh_connection)
    system_host_cpu_keywords.system_host_cpu_modify(active_controller_name, "application-isolated", num_cores_on_processor_0=0, num_cores_on_processor_1=0)
    system_host_cpu_keywords.system_host_cpu_modify(active_controller_name, "vswitch", num_cores_on_processor_0=0, num_cores_on_processor_1=0)
    system_host_cpu_keywords.system_host_cpu_modify(active_controller_name, "shared", num_cores_on_processor_0=0, num_cores_on_processor_1=0)
    system_host_cpu_keywords.system_host_cpu_modify(active_controller_name, "platform", num_cores_on_processor_0=2, num_cores_on_processor_1=0)

    # Set the Isolated CPUs count to fill all the application cores.
    system_host_cpu_keywords.system_host_cpu_modify(
        active_controller_name, "application-isolated", num_cores_on_processor_0=target_application_isolated_cpus_processor_0, num_cores_on_processor_1=target_application_isolated_cpus_processor_1
    )

    # Add the kube-cpu-mgr-policy/kube-topology-mgr-policy labels
    get_logger().log_info("Set the label values of 'kube-cpu-mgr-policy=static' and 'kube-topology-mgr-policy=best-effort'.")
    system_host_label_keywords = SystemHostLabelKeywords(ssh_connection)
    system_host_label_keywords.system_host_label_remove(active_controller_name, "kube-cpu-mgr-policy kube-topology-mgr-policy")
    system_host_label_keywords.system_host_label_assign(active_controller_name, "kube-cpu-mgr-policy=static kube-topology-mgr-policy=best-effort")

    # Unlock
    get_logger().log_info("Unlock the controller to apply the new configuration.")
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(active_controller_name)
    assert unlock_success, "Controller was not unlocked successfully."

    # Cleanup the configuration change after the test case.
    request.addfinalizer(revert_isolcpu_configuration)

    # Validate that the isolcpu plugin is enabled
    isolcpus_plugin_status_output = DpkgStatusKeywords(ssh_connection).get_dpkg_status_application("isolcpus-device-plugin")
    isolcpus_plugin_status = isolcpus_plugin_status_output.get_status_object().get_status()
    assert isolcpus_plugin_status == "install ok installed", "isolcpus-device-plugin should be 'install ok installed'."
    get_logger().log_info("isolcpus-device-plugin is installed successfully")

    # Validate that the system host-cpu-list shows the correct amount of isolated cpus
    host_cpu_output_for_validation = system_host_cpu_keywords.get_system_host_cpu_list(active_controller_name)
    isolated_physical_cores = host_cpu_output_for_validation.get_number_of_physical_cores(assigned_function='Application-isolated')
    assert (
        isolated_physical_cores == target_isolated_cpu_physical_cores
    ), f"Expecting {target_isolated_cpu_physical_cores} isolcpus physical cores in active controller, Observed: {isolated_physical_cores}"
    get_logger().log_info("Validated that the system host-cpu-list shows the correct amount of isolated cpus")

    # Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs
    expected_total_isolcpus = host_cpu_output_for_validation.get_number_of_logical_cores(assigned_function='Application-isolated')
    active_controller_node_description = KubectlDescribeNodeKeywords(ssh_connection).describe_node(active_controller_name).get_node_description()
    kubectl_allocatable_isolcpus = active_controller_node_description.get_allocatable().get_windriver_isolcpus()
    assert kubectl_allocatable_isolcpus == expected_total_isolcpus, f"Expecting {expected_total_isolcpus} isolcpus logical cores in active controller. Observed: {kubectl_allocatable_isolcpus}"
    kubectl_allocated_isolcpus = active_controller_node_description.get_allocated_resources().get_windriver_isolcpus()
    kubectl_allocated_isolcpus_requests = kubectl_allocated_isolcpus.get_requests()
    kubectl_allocated_isolcpus_limits = kubectl_allocated_isolcpus.get_limits()
    assert kubectl_allocated_isolcpus_requests == '0', f"Expecting 0 allocated isolcpus requests in active controller. Observed: {kubectl_allocated_isolcpus_requests}"
    assert kubectl_allocated_isolcpus_limits == '0', f"Expecting 0 allocated isolcpus limits in active controller. Observed: {kubectl_allocated_isolcpus_limits}"
    get_logger().log_info("Validated that amount of allocatable / allocated CPUs from 'kubectl describe node'.")

    # Validate that the labels are set correctly in the host-labels-list
    host_label_list_output = SystemHostLabelKeywords(ssh_connection).get_system_host_label_list(active_controller_name)
    cpu_mgr_policy = host_label_list_output.get_label_value("kube-cpu-mgr-policy")
    assert cpu_mgr_policy == "static", f"The value associated with kube-cllpu-mgr-policy is {cpu_mgr_policy}, we expected 'static'."
    topology_mgr_policy = host_label_list_output.get_label_value("kube-topology-mgr-policy")
    assert topology_mgr_policy == "best-effort", f"The value associated with kube-topology-mgr-policy is {topology_mgr_policy}, we expected 'best-effort'."
    get_logger().log_info("Validated that amount of allocatable / allocated CPUs from 'kubectl describe node'.")

    # Check and wait for kube-system pods status on active controller
    KubectlPodValidationKeywords(ssh_connection).validate_kube_system_pods_status()

    # Check cpu-manager-policy from state file on active controller
    cpu_manager_state_from_file = CatCpuManagerStateKeywords(ssh_connection).get_cpu_manager_state().get_cpu_manager_state_object()
    assert cpu_manager_state_from_file.get_policy_name() == "static", f"/var/lib/kubelet/cpu_manager_state should have policyName='static', Observed: {cpu_manager_state_from_file}"

    kubelet_arguments = ProcessStatusArgsKeywords(ssh_connection).get_process_arguments_as_string("kubelet")
    assert "--cpu-manager-policy=static" in kubelet_arguments, "--cpu-manager-policy=static should be in the command line arguments."
    assert "--topology-manager-policy=best-effort" in kubelet_arguments, "--topology-manager-policy=best-effort should be in the command line arguments."
    get_logger().log_info("Validated the cpu-manager-policy and topology-manager-policy from the kubelet command line.")

    # Upload Docker image to local registry
    local_registry = ConfigurationManager.get_docker_config().get_registry('local_registry')
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, 'local-secret')

    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path("resources/images/pv-test.tar"), "/home/sysadmin/pv-test.tar", overwrite=False)
    docker_load_image_keywords = DockerLoadImageKeywords(ssh_connection)
    docker_load_image_keywords.load_docker_image_to_host('pv-test.tar')
    docker_load_image_keywords.tag_docker_image_for_registry('registry.local:9001/pv-test', 'pv-test', local_registry)
    docker_load_image_keywords.push_docker_image_to_registry('pv-test', local_registry)
    get_logger().log_info("Uploaded 'pv-test' docker image to the local registry.")

    # Create Pod 0 to fill the isolcpus on one processor
    pod0_name = "test-isolated-2p-2-big-pod-best-effort-ht-aio-pod0"
    isolcpus_on_processor_0 = host_cpu_output_for_validation.get_number_of_logical_cores(processor_id=0, assigned_function='Application-isolated')
    template_file = get_stx_resource_path("resources/cloud_platform/nightly_regression/isolated_cpu_tools.yaml")
    replacement_dictionary = {"pod_name": pod0_name, "number_of_isolcpus": isolcpus_on_processor_0, "host_name": active_controller_name}
    pod0_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, "isolated_cpu_tools.yaml", "/home/sysadmin")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(pod0_yaml)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod0_name, "Running")
    get_logger().log_info("Pod0 created to use all the isolated CPUs on one of the processor.")

    def cleanup_pod0():
        get_logger().log_info(f"Cleaning up {pod0_name}")
        return KubectlDeletePodsKeywords(ssh_connection).delete_pod(pod0_name)

    request.addfinalizer(cleanup_pod0)

    # Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs now that pod0 is using isolated CPUs
    active_controller_node_description = KubectlDescribeNodeKeywords(ssh_connection).describe_node(active_controller_name).get_node_description()
    kubectl_allocatable_isolcpus = active_controller_node_description.get_allocatable().get_windriver_isolcpus()
    assert kubectl_allocatable_isolcpus == expected_total_isolcpus, f"Expecting {expected_total_isolcpus} isolcpus logical cores in active controller. Observed: {kubectl_allocatable_isolcpus}"
    kubectl_allocated_isolcpus = active_controller_node_description.get_allocated_resources().get_windriver_isolcpus()
    kubectl_allocated_isolcpus_requests = kubectl_allocated_isolcpus.get_requests()
    kubectl_allocated_isolcpus_limits = kubectl_allocated_isolcpus.get_limits()
    assert kubectl_allocated_isolcpus_requests == str(
        isolcpus_on_processor_0
    ), f"Expecting {isolcpus_on_processor_0} allocated isolcpus requests in active controller. Observed: {kubectl_allocated_isolcpus_requests}"
    assert kubectl_allocated_isolcpus_limits == str(
        isolcpus_on_processor_0
    ), f"Expecting {isolcpus_on_processor_0} allocated isolcpus limits in active controller. Observed: {kubectl_allocated_isolcpus_limits}"
    get_logger().log_info("Validated the allocated/allocatable CPUs now that pod0 is running.")

    # Validate that the CPUs used by the pod are all on the same processor.
    cpuset_of_pod = CatCpuSetKeywords(ssh_connection).get_cpuset_from_pod(pod0_name)
    cpu_manager_state_from_file = CatCpuManagerStateKeywords(ssh_connection).get_cpu_manager_state().get_cpu_manager_state_object()
    cpus_assigned_to_pod = cpu_manager_state_from_file.get_entry_pod_cpus(cpuset_of_pod, pod0_name)
    processors_hosting_those_cpus = set()
    for core in cpus_assigned_to_pod:
        system_host_cpu = host_cpu_output_for_validation.get_system_host_cpu_from_log_core(core)
        processor_hosting_cpu = system_host_cpu.get_processor()
        processors_hosting_those_cpus.add(processor_hosting_cpu)
    assert len(processors_hosting_those_cpus) == 1, "The CPUs hosting pod0 are on different processors."
    get_logger().log_info("Validated that all the CPUs used for pod0 are on the same processor.")

    # Create Pod 1 to fill the isolcpus on the second processor
    pod1_name = "test-isolated-2p-2-big-pod-best-effort-ht-aio-pod1"
    isolcpus_on_processor_1 = host_cpu_output_for_validation.get_number_of_logical_cores(processor_id=1, assigned_function='Application-isolated')
    template_file = get_stx_resource_path("resources/cloud_platform/nightly_regression/isolated_cpu_tools.yaml")
    replacement_dictionary = {"pod_name": pod1_name, "number_of_isolcpus": isolcpus_on_processor_1, "host_name": active_controller_name}
    pod1_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, "isolated_cpu_tools.yaml", "/home/sysadmin")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(pod1_yaml)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod1_name, "Running")
    get_logger().log_info("Pod1 created to use all the isolated CPUs on one of the processor.")

    def cleanup_pod1():
        get_logger().log_info(f"Cleaning up {pod1_name}")
        return KubectlDeletePodsKeywords(ssh_connection).delete_pod(pod1_name)

    request.addfinalizer(cleanup_pod1)

    # Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs now that pod0 and pod1 is using all the isolated CPUs
    active_controller_node_description = KubectlDescribeNodeKeywords(ssh_connection).describe_node(active_controller_name).get_node_description()
    kubectl_allocatable_isolcpus = active_controller_node_description.get_allocatable().get_windriver_isolcpus()
    assert kubectl_allocatable_isolcpus == expected_total_isolcpus, f"Expecting {expected_total_isolcpus} isolcpus logical cores in active controller. Observed: {kubectl_allocatable_isolcpus}"
    kubectl_allocated_isolcpus = active_controller_node_description.get_allocated_resources().get_windriver_isolcpus()
    kubectl_allocated_isolcpus_requests = kubectl_allocated_isolcpus.get_requests()
    kubectl_allocated_isolcpus_limits = kubectl_allocated_isolcpus.get_limits()
    total_expected_allocated_isolcpus = isolcpus_on_processor_0 + isolcpus_on_processor_1
    assert kubectl_allocated_isolcpus_requests == str(
        total_expected_allocated_isolcpus
    ), f"Expecting {total_expected_allocated_isolcpus} allocated isolcpus requests in active controller. Observed: {kubectl_allocated_isolcpus_requests}"
    assert kubectl_allocated_isolcpus_limits == str(
        total_expected_allocated_isolcpus
    ), f"Expecting {total_expected_allocated_isolcpus} allocated isolcpus limits in active controller. Observed: {kubectl_allocated_isolcpus_limits}"
    get_logger().log_info("Validated the allocated/allocatable CPUs now that pod0 is running.")

    # Validate that the CPUs used by the pod are all on the same processor.
    cpuset_of_pod = CatCpuSetKeywords(ssh_connection).get_cpuset_from_pod(pod1_name)
    cpu_manager_state_from_file = CatCpuManagerStateKeywords(ssh_connection).get_cpu_manager_state().get_cpu_manager_state_object()
    cpus_assigned_to_pod = cpu_manager_state_from_file.get_entry_pod_cpus(cpuset_of_pod, pod1_name)
    processors_hosting_those_cpus = set()
    for core in cpus_assigned_to_pod:
        system_host_cpu = host_cpu_output_for_validation.get_system_host_cpu_from_log_core(core)
        processor_hosting_cpu = system_host_cpu.get_processor()
        processors_hosting_those_cpus.add(processor_hosting_cpu)
    assert len(processors_hosting_those_cpus) == 1, "The CPUs hosting pod1 are on different processors."
    get_logger().log_info("Validated that all the CPUs used for pod1 are on the same processor.")


def revert_isolcpu_configuration():
    """
    This function will revert the configuration made by the iso_cpu test case.
    - Lock the active controller
    - Sets all cores to 2-Platform and the rest to Application.
    - Remove the 'conf_cpu-mgr-policy' and 'conf_topo_mgr_policy' labels

    Returns: None

    """

    get_logger().log_info("Revert the CPU and Label configurations.")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller_name = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    # Lock Controller-0 to configure CPUs.
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(active_controller_name)
    assert lock_success, "Controller was not locked successfully."

    # Revert CPU configuration to default.
    system_host_cpu_keywords = SystemHostCPUKeywords(ssh_connection)
    system_host_cpu_keywords.system_host_cpu_modify(active_controller_name, "application-isolated", num_cores_on_processor_0=0, num_cores_on_processor_1=0)

    # Remove the kube-cpu-mgr-policy/kube-topology-mgr-policy labels
    SystemHostLabelKeywords(ssh_connection).system_host_label_remove(active_controller_name, "kube-cpu-mgr-policy kube-topology-mgr-policy")

    # Unlock
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(active_controller_name)
    assert unlock_success, "Controller was not unlocked successfully."


@mark.p1
@mark.lab_has_standby_controller
@mark.lab_has_processor_min_2
def test_isolated_2processors_2big_pods_best_effort_standby_controller(request):
    """
    This test case will validate the isolated CPU capability of the system when using 2-processors by creating 2 big pods
    on the system's standby-controller with kube-cpu-mgr-policy=static and kube-topology-mgr-policy=best-effort.

        Test Steps:
        - Lock the Controller
        - Use 'system host-cpu-modify' to set all CPUs to be application-isolated, except for necessary platform/application cores.
        - Set the label values of 'kube-cpu-mgr-policy=static' and 'kube-topology-mgr-policy=best-effort'
        - Unlock the Controller to apply the configuration change
        - Validate that the isolcpu plugin is enabled
        - Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs
        - Validate that the labels are set correctly in the host-labels-list
        - Ensure that the kube-system pods recover from the configuration change
        - Check cpu-manager-policy from state file on active controller
        - Create Pod0 to fill the isolated cpus on one processor
        - Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs now that pod0 is using isolated CPUs
        - Validate that the CPUs used by pod0 are all on the same processor.
        - Create Pod 1 to fill the isolated cpus on the second processor
        - Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs now that pod0 and pod1 is using all the isolated CPUs
        - Validate that the CPUs used by pod1 are all on the same processor.

        Teardown:
        - Delete the Pods
        - Revert the isolated cpus / labels configuration
    """

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    system_host_output = SystemHostListKeywords(ssh_connection)
    standby_controller_name = system_host_output.get_standby_controller().get_host_name()

    host_cpu_output = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(standby_controller_name)
    assert host_cpu_output.get_processor_count() == 2, f"This test case requires 2 processors on the standby-controller. Observed: {host_cpu_output.get_processor_count()} processor(s)"

    # Gather the current state of CPU distribution
    total_cpus_processor_0 = host_cpu_output.get_number_of_physical_cores(processor_id=0)
    total_cpus_processor_1 = host_cpu_output.get_number_of_physical_cores(processor_id=1)
    get_logger().log_info(f"There are {total_cpus_processor_0} cores on processor 0 and {total_cpus_processor_1} on processor 1.")

    # Target state of CPU distribution for the Test
    target_application_isolated_cpus_processor_0 = total_cpus_processor_0 - 2  # Leave 2 Physical Cores for Platform
    target_application_isolated_cpus_processor_1 = total_cpus_processor_1 - 2  # Leave 2 Physical Cores for Applications
    target_isolated_cpu_physical_cores = target_application_isolated_cpus_processor_0 + target_application_isolated_cpus_processor_1
    assert target_application_isolated_cpus_processor_0 > 1, "There are at least 3 Physical Cores on processor 0"
    assert target_application_isolated_cpus_processor_1 > 1, "There are at least 3 Physical Cores on processor 1"

    # Lock Controller-0 to configure CPUs.
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(standby_controller_name)
    assert lock_success, "Standby-Controller was not locked successfully."

    get_logger().log_info("Modify the CPUs to have 2 Platform cores on the first processor and 2 Application cores on the second processor.")
    get_logger().log_info("The rest of the cores will be set to Application-Isolated.")

    # Revert CPU configuration to default.
    system_host_cpu_keywords = SystemHostCPUKeywords(ssh_connection)
    system_host_cpu_keywords.system_host_cpu_modify(standby_controller_name, "application-isolated", num_cores_on_processor_0=0, num_cores_on_processor_1=0)
    system_host_cpu_keywords.system_host_cpu_modify(standby_controller_name, "vswitch", num_cores_on_processor_0=0, num_cores_on_processor_1=0)
    system_host_cpu_keywords.system_host_cpu_modify(standby_controller_name, "shared", num_cores_on_processor_0=0, num_cores_on_processor_1=0)
    system_host_cpu_keywords.system_host_cpu_modify(standby_controller_name, "platform", num_cores_on_processor_0=2, num_cores_on_processor_1=0)

    # Set the Isolated CPUs count to fill all the application cores.
    system_host_cpu_keywords.system_host_cpu_modify(
        standby_controller_name, "application-isolated", num_cores_on_processor_0=target_application_isolated_cpus_processor_0, num_cores_on_processor_1=target_application_isolated_cpus_processor_1
    )

    # Add the kube-cpu-mgr-policy/kube-topology-mgr-policy labels
    get_logger().log_info("Set the label values of 'kube-cpu-mgr-policy=static' and 'kube-topology-mgr-policy=best-effort'.")
    system_host_label_keywords = SystemHostLabelKeywords(ssh_connection)
    system_host_label_keywords.system_host_label_remove(standby_controller_name, "kube-cpu-mgr-policy kube-topology-mgr-policy")
    system_host_label_keywords.system_host_label_assign(standby_controller_name, "kube-cpu-mgr-policy=static kube-topology-mgr-policy=best-effort")

    # Unlock
    get_logger().log_info("Unlock the controller to apply the new configuration.")
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(standby_controller_name)
    assert unlock_success, "Standby-Controller was not unlocked successfully."

    # Cleanup the configuration change after the test case.
    request.addfinalizer(revert_standby_controller_isolcpu_configuration)

    # Validate that the isolcpu plugin is enabled
    isolcpus_plugin_status_output = DpkgStatusKeywords(ssh_connection).get_dpkg_status_application("isolcpus-device-plugin")
    isolcpus_plugin_status = isolcpus_plugin_status_output.get_status_object().get_status()
    assert isolcpus_plugin_status == "install ok installed", "isolcpus-device-plugin should be 'install ok installed'."
    get_logger().log_info("isolcpus-device-plugin is installed successfully")

    # Validate that the system host-cpu-list shows the correct amount of isolated cpus
    host_cpu_output_for_validation = system_host_cpu_keywords.get_system_host_cpu_list(standby_controller_name)
    isolated_physical_cores = host_cpu_output_for_validation.get_number_of_physical_cores(assigned_function='Application-isolated')
    assert (
        isolated_physical_cores == target_isolated_cpu_physical_cores
    ), f"Expecting {target_isolated_cpu_physical_cores} isolcpus physical cores in standby controller, Observed: {isolated_physical_cores}"
    get_logger().log_info("Validated that the system host-cpu-list shows the correct amount of isolated cpus")

    # Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs
    expected_total_isolcpus = host_cpu_output_for_validation.get_number_of_logical_cores(assigned_function='Application-isolated')
    standby_controller_node_description = KubectlDescribeNodeKeywords(ssh_connection).describe_node(standby_controller_name).get_node_description()
    kubectl_allocatable_isolcpus = standby_controller_node_description.get_allocatable().get_windriver_isolcpus()
    assert kubectl_allocatable_isolcpus == expected_total_isolcpus, f"Expecting {expected_total_isolcpus} isolcpus logical cores in standby controller. Observed: {kubectl_allocatable_isolcpus}"
    kubectl_allocated_isolcpus = standby_controller_node_description.get_allocated_resources().get_windriver_isolcpus()
    kubectl_allocated_isolcpus_requests = kubectl_allocated_isolcpus.get_requests()
    kubectl_allocated_isolcpus_limits = kubectl_allocated_isolcpus.get_limits()
    assert kubectl_allocated_isolcpus_requests == '0', f"Expecting 0 allocated isolcpus requests in standby controller. Observed: {kubectl_allocated_isolcpus_requests}"
    assert kubectl_allocated_isolcpus_limits == '0', f"Expecting 0 allocated isolcpus limits in standby controller. Observed: {kubectl_allocated_isolcpus_limits}"
    get_logger().log_info("Validated that amount of allocatable / allocated CPUs from 'kubectl describe node'.")

    # Validate that the labels are set correctly in the host-labels-list
    host_label_list_output = SystemHostLabelKeywords(ssh_connection).get_system_host_label_list(standby_controller_name)
    cpu_mgr_policy = host_label_list_output.get_label_value("kube-cpu-mgr-policy")
    assert cpu_mgr_policy == "static", f"The value associated with kube-cllpu-mgr-policy is {cpu_mgr_policy}, we expected 'static'."
    topology_mgr_policy = host_label_list_output.get_label_value("kube-topology-mgr-policy")
    assert topology_mgr_policy == "best-effort", f"The value associated with kube-topology-mgr-policy is {topology_mgr_policy}, we expected 'best-effort'."
    get_logger().log_info("Validated that amount of allocatable / allocated CPUs from 'kubectl describe node'.")

    # Check and wait for kube-system pods status on active controller
    standby_controller_ssh = LabConnectionKeywords().get_standby_controller_ssh()
    KubectlPodValidationKeywords(standby_controller_ssh).validate_kube_system_pods_status()

    # Check cpu-manager-policy from state file on active controller
    cpu_manager_state_from_file = CatCpuManagerStateKeywords(standby_controller_ssh).get_cpu_manager_state().get_cpu_manager_state_object()
    assert cpu_manager_state_from_file.get_policy_name() == "static", f"/var/lib/kubelet/cpu_manager_state should have policyName='static', Observed: {cpu_manager_state_from_file}"

    kubelet_arguments = ProcessStatusArgsKeywords(standby_controller_ssh).get_process_arguments_as_string("kubelet")
    assert "--cpu-manager-policy=static" in kubelet_arguments, "--cpu-manager-policy=static should be in the command line arguments."
    assert "--topology-manager-policy=best-effort" in kubelet_arguments, "--topology-manager-policy=best-effort should be in the command line arguments."
    get_logger().log_info("Validated the cpu-manager-policy and topology-manager-policy from the kubelet command line.")

    # Upload Docker image to local registry
    local_registry = ConfigurationManager.get_docker_config().get_registry('local_registry')
    KubectlCreateSecretsKeywords(standby_controller_ssh).create_secret_for_registry(local_registry, 'local-secret')

    file_keywords = FileKeywords(standby_controller_ssh)
    file_keywords.upload_file(get_stx_resource_path("resources/images/pv-test.tar"), "/home/sysadmin/pv-test.tar", overwrite=False)
    docker_load_image_keywords = DockerLoadImageKeywords(standby_controller_ssh)
    docker_load_image_keywords.load_docker_image_to_host('pv-test.tar')
    docker_load_image_keywords.tag_docker_image_for_registry('registry.local:9001/pv-test', 'pv-test', local_registry)
    docker_load_image_keywords.push_docker_image_to_registry('pv-test', local_registry)
    get_logger().log_info("Uploaded 'pv-test' docker image to the local registry.")

    # Create Pod 0 to fill the isolcpus on one processor
    pod0_name = "test-isolated-2p-2-big-pod-best-effort-ht-aio-pod0"
    isolcpus_on_processor_0 = host_cpu_output_for_validation.get_number_of_logical_cores(processor_id=0, assigned_function='Application-isolated')
    template_file = get_stx_resource_path("resources/cloud_platform/nightly_regression/isolated_cpu_tools.yaml")
    replacement_dictionary = {"pod_name": pod0_name, "number_of_isolcpus": isolcpus_on_processor_0, "host_name": standby_controller_name}
    pod0_yaml = YamlKeywords(standby_controller_ssh).generate_yaml_file_from_template(template_file, replacement_dictionary, "isolated_cpu_tools.yaml", "/home/sysadmin")
    KubectlApplyPodsKeywords(standby_controller_ssh).apply_from_yaml(pod0_yaml)
    KubectlGetPodsKeywords(standby_controller_ssh).wait_for_pod_status(pod0_name, "Running")
    get_logger().log_info("Pod0 created to use all the isolated CPUs on one of the processor.")

    def cleanup_pod0():
        get_logger().log_info(f"Cleaning up {pod0_name}")
        return KubectlDeletePodsKeywords(standby_controller_ssh).delete_pod(pod0_name)

    request.addfinalizer(cleanup_pod0)

    # Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs now that pod0 is using isolated CPUs
    standby_controller_node_description = KubectlDescribeNodeKeywords(standby_controller_ssh).describe_node(standby_controller_name).get_node_description()
    kubectl_allocatable_isolcpus = standby_controller_node_description.get_allocatable().get_windriver_isolcpus()
    assert kubectl_allocatable_isolcpus == expected_total_isolcpus, f"Expecting {expected_total_isolcpus} isolcpus logical cores in active controller. Observed: {kubectl_allocatable_isolcpus}"
    kubectl_allocated_isolcpus = standby_controller_node_description.get_allocated_resources().get_windriver_isolcpus()
    kubectl_allocated_isolcpus_requests = kubectl_allocated_isolcpus.get_requests()
    kubectl_allocated_isolcpus_limits = kubectl_allocated_isolcpus.get_limits()
    assert kubectl_allocated_isolcpus_requests == str(
        isolcpus_on_processor_0
    ), f"Expecting {isolcpus_on_processor_0} allocated isolcpus requests in standby controller. Observed: {kubectl_allocated_isolcpus_requests}"
    assert kubectl_allocated_isolcpus_limits == str(
        isolcpus_on_processor_0
    ), f"Expecting {isolcpus_on_processor_0} allocated isolcpus limits in standby controller. Observed: {kubectl_allocated_isolcpus_limits}"
    get_logger().log_info("Validated the allocated/allocatable CPUs now that pod0 is running.")

    # Validate that the CPUs used by the pod are all on the same processor.
    cpuset_of_pod = CatCpuSetKeywords(standby_controller_ssh).get_cpuset_from_pod(pod0_name)
    cpu_manager_state_from_file = CatCpuManagerStateKeywords(standby_controller_ssh).get_cpu_manager_state().get_cpu_manager_state_object()
    cpus_assigned_to_pod = cpu_manager_state_from_file.get_entry_pod_cpus(cpuset_of_pod, pod0_name)
    processors_hosting_those_cpus = set()
    for core in cpus_assigned_to_pod:
        system_host_cpu = host_cpu_output_for_validation.get_system_host_cpu_from_log_core(core)
        processor_hosting_cpu = system_host_cpu.get_processor()
        processors_hosting_those_cpus.add(processor_hosting_cpu)
    assert len(processors_hosting_those_cpus) == 1, "The CPUs hosting pod0 are on different processors."
    get_logger().log_info("Validated that all the CPUs used for pod0 are on the same processor.")

    # Create Pod 1 to fill the isolcpus on the second processor
    pod1_name = "test-isolated-2p-2-big-pod-best-effort-ht-aio-pod1"
    isolcpus_on_processor_1 = host_cpu_output_for_validation.get_number_of_logical_cores(processor_id=1, assigned_function='Application-isolated')
    template_file = get_stx_resource_path("resources/cloud_platform/nightly_regression/isolated_cpu_tools.yaml")
    replacement_dictionary = {"pod_name": pod1_name, "number_of_isolcpus": isolcpus_on_processor_1, "host_name": standby_controller_name}
    pod1_yaml = YamlKeywords(standby_controller_ssh).generate_yaml_file_from_template(template_file, replacement_dictionary, "isolated_cpu_tools.yaml", "/home/sysadmin")
    KubectlApplyPodsKeywords(standby_controller_ssh).apply_from_yaml(pod1_yaml)
    KubectlGetPodsKeywords(standby_controller_ssh).wait_for_pod_status(pod1_name, "Running")
    get_logger().log_info("Pod1 created to use all the isolated CPUs on one of the processor.")

    def cleanup_pod1():
        get_logger().log_info(f"Cleaning up {pod1_name}")
        return KubectlDeletePodsKeywords(standby_controller_ssh).delete_pod(pod1_name)

    request.addfinalizer(cleanup_pod1)

    # Validate that K8s knows that there is the correct amount of allocatable / allocated CPUs now that pod0 and pod1 is using all the isolated CPUs
    standby_controller_node_description = KubectlDescribeNodeKeywords(standby_controller_ssh).describe_node(standby_controller_name).get_node_description()
    kubectl_allocatable_isolcpus = standby_controller_node_description.get_allocatable().get_windriver_isolcpus()
    assert kubectl_allocatable_isolcpus == expected_total_isolcpus, f"Expecting {expected_total_isolcpus} isolcpus logical cores in active controller. Observed: {kubectl_allocatable_isolcpus}"
    kubectl_allocated_isolcpus = standby_controller_node_description.get_allocated_resources().get_windriver_isolcpus()
    kubectl_allocated_isolcpus_requests = kubectl_allocated_isolcpus.get_requests()
    kubectl_allocated_isolcpus_limits = kubectl_allocated_isolcpus.get_limits()
    total_expected_allocated_isolcpus = isolcpus_on_processor_0 + isolcpus_on_processor_1
    assert kubectl_allocated_isolcpus_requests == str(
        total_expected_allocated_isolcpus
    ), f"Expecting {total_expected_allocated_isolcpus} allocated isolcpus requests in standby controller. Observed: {kubectl_allocated_isolcpus_requests}"
    assert kubectl_allocated_isolcpus_limits == str(
        total_expected_allocated_isolcpus
    ), f"Expecting {total_expected_allocated_isolcpus} allocated isolcpus limits in standby controller. Observed: {kubectl_allocated_isolcpus_limits}"
    get_logger().log_info("Validated the allocated/allocatable CPUs now that pod0 is running.")

    # Validate that the CPUs used by the pod are all on the same processor.
    cpuset_of_pod = CatCpuSetKeywords(standby_controller_ssh).get_cpuset_from_pod(pod1_name)
    cpu_manager_state_from_file = CatCpuManagerStateKeywords(standby_controller_ssh).get_cpu_manager_state().get_cpu_manager_state_object()
    cpus_assigned_to_pod = cpu_manager_state_from_file.get_entry_pod_cpus(cpuset_of_pod, pod1_name)
    processors_hosting_those_cpus = set()
    for core in cpus_assigned_to_pod:
        system_host_cpu = host_cpu_output_for_validation.get_system_host_cpu_from_log_core(core)
        processor_hosting_cpu = system_host_cpu.get_processor()
        processors_hosting_those_cpus.add(processor_hosting_cpu)
    assert len(processors_hosting_those_cpus) == 1, "The CPUs hosting pod1 are on different processors."
    get_logger().log_info("Validated that all the CPUs used for pod1 are on the same processor.")


def revert_standby_controller_isolcpu_configuration():
    """
    This function will revert the configuration made by the iso_cpu test case.
    - Lock the standby controller
    - Sets all cores to 2-Platform and the rest to Application.
    - Remove the 'conf_cpu-mgr-policy' and 'conf_topo_mgr_policy' labels

    Returns: None

    """

    get_logger().log_info("Revert the CPU and Label configurations.")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    standby_controller_name = SystemHostListKeywords(ssh_connection).get_standby_controller().get_host_name()

    # Lock Controller-0 to configure CPUs.
    lock_success = SystemHostLockKeywords(ssh_connection).lock_host(standby_controller_name)
    assert lock_success, "Standby-Controller was not locked successfully."

    # Revert CPU configuration to default.
    system_host_cpu_keywords = SystemHostCPUKeywords(ssh_connection)
    system_host_cpu_keywords.system_host_cpu_modify(standby_controller_name, "application-isolated", num_cores_on_processor_0=0, num_cores_on_processor_1=0)

    # Remove the kube-cpu-mgr-policy/kube-topology-mgr-policy labels
    SystemHostLabelKeywords(ssh_connection).system_host_label_remove(standby_controller_name, "kube-cpu-mgr-policy kube-topology-mgr-policy")

    # Unlock
    unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(standby_controller_name)
    assert unlock_success, "Controller was not unlocked successfully."


@mark.p0
@mark.lab_has_sriov
def test_sriovdp_netdev_single_pod_1vf_lock(request):
    """
    Test creation of a pod with netdevice SR-IOV interfaces
    Args:

    Test Steps:
        - Create a network attachment definition for the SR-IOV VFs
        - Create a pod with SR-IOV netdevice NICs
        - Verify if pod is in Running State
        - Verify if DaemonSet has expected values
        - Lock/unlock host
        - Verify if pod is in Running State
        - Verify if DaemonSet has expected values
        - Delete the pods
        - Delete the network attachment definition

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Get a worker node from the lab
    lab_config = ConfigurationManager.get_lab_config()
    computes = []
    for node in lab_config.get_nodes():
        if 'lab_has_worker' in node.get_node_capabilities():
            computes.append(node)

    assert len(computes) > 0, 'we do not have any worker nodes for this test'
    worker_to_use = computes[0]  # pick the first one

    # Deploy required images
    sriov_deploy_images_to_local_registry(ssh_connection)

    # Deploy required pods
    sriov_deploy_pods(request, 'netdef_test-sriovdp.yaml', 'calicoctl-ippool-sriov-pool-group0-data1-vf1.yaml', ssh_connection)

    # Deploy daemon set pod
    deploy_daemonset_pod(request, 'daemon_set_daemonset.yaml', ssh_connection)

    # check the daemonset values
    daemonset = KubectlGetDaemonsetsKeywords(ssh_connection).get_daemonsets().get_daemonset('daemonset-sriovdp-netdev-single-pod')

    assert daemonset, 'no daemonset was found'
    assert daemonset.get_name() == 'daemonset-sriovdp-netdev-single-pod', 'daesomeset name was incorrect'
    assert daemonset.get_desired() == 1, 'daemonset desired value was not 1'
    assert daemonset.get_ready() == 1, 'daemonset ready value was not 1'
    assert daemonset.get_available() == 1, 'daemonset available value was not 1'
    assert daemonset.get_node_selector() == "kubernetes.io/hostname=controller-0", 'daemonset node selector is wroing'

    # validate that the sriov interface net1 is 'UP'
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()
    daemonset_pod = pods.get_pods_start_with('daemonset-sriovdp-netdev-single-pod')[0]  # should only be one

    output = KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(daemonset_pod.get_name(), 'ip link show net1')
    interface = IPLinkShowOutput(output).get_interface()

    assert interface.state == 'UP', 'interface state was not UP'

    # lock and unlock host and ensure pods come back online and interface is up
    assert SystemHostLockKeywords(ssh_connection).lock_host(worker_to_use.get_name()), f'failed to lock host {worker_to_use.get_name()}'
    assert SystemHostLockKeywords(ssh_connection).unlock_host(worker_to_use.get_name()), f'failed to unlock host {worker_to_use.get_name()}'

    # check calicoctl pod is running
    assert KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status('calicoctl', 'Running', namespace='kube-system'), 'calicoctl did not start in time'

    # check that the daemonset pod is running
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()
    daemonset_pod = pods.get_pods_start_with('daemonset-sriovdp-netdev-single-pod')[0]  # should only be one

    assert KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        daemonset_pod.get_name(),
        'Running',
    ), 'daemonset pod did not start in time'

    output = KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(daemonset_pod.get_name(), 'ip link show net1')
    interface = IPLinkShowOutput(output).get_interface()

    assert interface.state == 'UP', 'interface state was not UP'


@mark.p0
@mark.lab_has_sriov
@mark.lab_is_ipv4
def test_sriovdp_netdev_single_pod_1vf_lock_ipv4(request):
    """
    Test creation of a pod with netdevice SR-IOV interfaces
    Args:

    Test Steps:
        - Create a network attachment definition for the SR-IOV VFs
        - Create a pod with SR-IOV netdevice NICs
        - Verify if DaemonSet has expected values
        - Lock/unlock host
        - Verify if DaemonSet has expected values
        - Delete the pods
        - Delete the network attachment definition

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Get a worker node from the lab
    lab_config = ConfigurationManager.get_lab_config()
    computes = []
    for node in lab_config.get_nodes():
        if 'lab_has_worker' in node.get_node_capabilities():
            computes.append(node)

    assert len(computes) > 0, 'we do not have any worker nodes for this test'
    worker_to_use = computes[0]  # pick the first one

    # Deploy required images
    sriov_deploy_images_to_local_registry(ssh_connection)

    # Deploy required pods
    sriov_deploy_pods_ipv4(request, ssh_connection)

    # Deploy daemon set pod
    deploy_daemonset_pod(request, 'daemon_set_daemonset_ipv4.yaml', ssh_connection)

    # check the daemonset values
    daemonset = KubectlGetDaemonsetsKeywords(ssh_connection).get_daemonsets().get_daemonset('daemonset-sriovdp-netdev-single-pod')

    assert daemonset, 'no daemonset was found'
    assert daemonset.get_name() == 'daemonset-sriovdp-netdev-single-pod', 'daesomeset name was incorrect'
    assert daemonset.get_desired() == 1, 'daemonset desired value was not 1'
    assert daemonset.get_ready() == 1, 'daemonset ready value was not 1'
    assert daemonset.get_available() == 1, 'daemonset available value was not 1'
    assert daemonset.get_node_selector() == "kubernetes.io/hostname=controller-0", 'daemonset node selector is wrong'

    # validate that the sriov interface net1 is 'UP'
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()
    daemonset_pod = pods.get_pods_start_with('daemonset-sriovdp-netdev-single-pod')[0]  # should only be one

    output = KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(daemonset_pod.get_name(), 'ip link show net1')
    interface = IPLinkShowOutput(output).get_interface()

    assert interface.state == 'UP', 'interface state was not UP'

    # lock and unlock host and ensure pods come back online and interface is up
    assert SystemHostLockKeywords(ssh_connection).lock_host(worker_to_use.get_name()), f'failed to lock host {worker_to_use.get_name()}'
    assert SystemHostLockKeywords(ssh_connection).unlock_host(worker_to_use.get_name()), f'failed to unlock host {worker_to_use.get_name()}'

    # check that the daemonset pod is running
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()
    daemonset_pod = pods.get_pods_start_with('daemonset-sriovdp-netdev-single-pod')[0]  # should only be one

    assert KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        daemonset_pod.get_name(),
        'Running',
    ), 'daemonset pod did not start in time'

    output = KubectlExecInPodsKeywords(ssh_connection).run_pod_exec_cmd(daemonset_pod.get_name(), 'ip link show net1')
    interface = IPLinkShowOutput(output).get_interface()

    assert interface.state == 'UP', 'interface state was not UP'


@mark.p0
@mark.lab_has_sriov
def test_sriovdp_mixed_add_pod_vf_interface(request):
    """
    Test the creation of a VF interface via 'system' commands

    Test Steps:
        - Lock the host.
        - Create a VF interface with specified virtual functions (`vfs`).
        - Create a datanetwork dedicated to the VF interface.
        - Assign the VF interface to the newly created datanetwork.
        - Unlock the host.
        - Validate the vfs for the original datanetwork and the test data network

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    sriov_configs = GetSriovConfigKeywords(ssh_connection).get_sriov_configs_for_host(active_controller)
    assert len(sriov_configs) > 0, 'sriov was not found on the system'

    # get a config that has type of vf
    configs = list(filter(lambda config: config.get_system_host_interface_object().get_iftype() == 'vf', sriov_configs))
    assert len(configs) > 0, 'no sriov with type vf was found'

    # take the first one
    sriov_config = configs[0]

    # get the datanetwork and interface name from the sriov config
    datanetwork = sriov_config.get_datanetworks().get_datanetwork_name()
    interface_name = sriov_config.get_system_host_interface_object().get_ifname()

    # This call does not need a node name, so passing '' instead
    node_description_object = KubectlDescribeNodeKeywords(ssh_connection).describe_node('').get_node_description()
    # Get the initial num of vfs to validate against later
    initial_vfs_for_datanetwork = node_description_object.get_allocatable().get_datanetwork_allocatable(datanetwork)

    # System needs to be locked for these changes
    SystemHostLockKeywords(ssh_connection).lock_host(active_controller)

    # Add the interface called sriov
    SystemHostInterfaceKeywords(ssh_connection).system_host_interface_add(active_controller, 'sriov', 'vf', interface_name, vf_driver='vfio', ifclass='pci-sriov', num_vfs=1)

    # Add the new test datanetwork call 'sriov-test-datanetwork'
    SystemDatanetworkAddKeywords(ssh_connection).datanetwork_add('sriov-test-datanetwork', 'vlan')

    # create teardown method to remove the added interface and network
    def remove_datanetwork_and_interface():
        system_host_lock_keywords = SystemHostLockKeywords(ssh_connection)
        # test was failing while host was locked, check before attempting to lock
        if system_host_lock_keywords.is_host_unlocked(active_controller):
            system_host_lock_keywords.lock_host(active_controller)
        SystemHostInterfaceKeywords(ssh_connection).cleanup_interface(active_controller, 'sriov')
        data_network = SystemDatanetworkListKeywords(ssh_connection).system_datanetwork_list().get_system_datanetwork('sriov-test-datanetwork')
        SystemDatanetworkDeleteKeywords(ssh_connection).cleanup_datanetwork(data_network.get_uuid())
        system_host_lock_keywords.unlock_host(active_controller)

    request.addfinalizer(remove_datanetwork_and_interface)

    # assign the new interface sriov to the new sriov-test-datanetwork
    SystemInterfaceDatanetworkKeywords(ssh_connection).interface_datanetwork_assign(active_controller, 'sriov', 'sriov-test-datanetwork')

    # Unlock the host to see the changes
    SystemHostLockKeywords(ssh_connection).unlock_host(active_controller)

    # This call does not need a node name, so passing '' instead
    node_description_object = KubectlDescribeNodeKeywords(ssh_connection).describe_node('').get_node_description()
    post_vfs = node_description_object.get_allocatable().get_datanetwork_allocatable(datanetwork)
    test_sriov_vfs = node_description_object.get_allocatable().get_datanetwork_allocatable('sriov-test-datanetwork')

    # Check that the orig datanetwork has 1 less vf's and the test datanetwork has 1
    assert post_vfs == initial_vfs_for_datanetwork - 1, 'wrong number of vfs for datanetwork, should be 1 less then original'
    assert test_sriov_vfs == 1, ' wrong number of vfs for the test datanetwork'


@mark.p0
@mark.lab_has_sriov
@mark.lab_is_ipv6
def test_sriovdp_netdev_connectivity_ipv6(request):
    """
    Test connectivity between SR-IOV interfaces in a pod

    Test Steps:
        - Create a network attachment definition for the SR-IOV VFs
        - Create 2 pods on the same host
        - Send ICMP traffic from each pod to the other pod over
              the SR-IOV interface(s)
        - Delete the pods
        - Delete the network attachment definition

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pod1_name = 'test-sriovdp-netdev-connectivity-ipv6-0'
    pod2_name = 'test-sriovdp-netdev-connectivity-ipv6-1'

    # Deploy required images
    sriov_deploy_images_to_local_registry(ssh_connection)

    # Deploy required pods
    sriov_deploy_pods(request, 'netdef_test-sriovdp.yaml', 'calicoctl-ippool-sriov-pool-group0-data1-vf1.yaml', ssh_connection)

    deploy_sriovdp_netdev_pods_ipv6(request, ssh_connection)

    # validate that the sriov interface net1 is 'UP'
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()
    pod_1 = pods.get_pods_start_with(pod1_name)[0]  # should only be one
    pod_2 = pods.get_pods_start_with(pod2_name)[0]  # should only be one

    kubeclt_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    output = kubeclt_exec_in_pods.run_pod_exec_cmd(pod_1.get_name(), 'ip link show net1')
    interface = IPLinkShowOutput(output).get_interface()

    assert interface.state == 'UP', 'interface state was not UP for pod#1'

    output = kubeclt_exec_in_pods.run_pod_exec_cmd(pod_2.get_name(), 'ip link show net1')
    interface = IPLinkShowOutput(output).get_interface()

    assert interface.state == 'UP', 'interface state was not UP for pod#2'

    # add routes to both pods
    IPKeywords(ssh_connection).add_route_in_pod(pod1_name, 'net1')
    IPKeywords(ssh_connection).add_route_in_pod(pod2_name, 'net1')

    pod_1_ip = IPKeywords(ssh_connection).get_ip_address_from_pod(pod1_name, 'net1')
    pod_2_ip = IPKeywords(ssh_connection).get_ip_address_from_pod(pod2_name, 'net1')

    # validate that pod1 can ping server pod2
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod1_name, f"ping6 -c 3 {pod_2_ip}")
    assert ssh_connection.get_return_code() == 0

    # validate that pod 2 can ping pod1
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod2_name, f"ping6 -c 3 {pod_1_ip}")
    assert ssh_connection.get_return_code() == 0


@mark.p0
@mark.lab_has_sriov
@mark.lab_is_ipv4
def test_sriovdp_netdev_connectivity_ipv4(request):
    """
    Test connectivity between SR-IOV interfaces in a pod

    Test Steps:
        - Create a network attachment definition for the SR-IOV VFs
        - Create 2 pods on the same host
        - Send ICMP traffic from each pod to the other pod over
              the SR-IOV interface(s)
        - Delete the pods
        - Delete the network attachment definition

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    pod1_name = 'test-sriovdp-netdev-connectivity-ipv4-0'
    pod2_name = 'test-sriovdp-netdev-connectivity-ipv4-1'

    # Deploy required images
    sriov_deploy_images_to_local_registry(ssh_connection)

    # Deploy required pods
    sriov_deploy_pods(request, 'netdef_test-sriovdp_ipv4_with_pools.yaml', 'calicoctl-ippool-sriov-pool-group0-data0-vf1.yaml', ssh_connection)

    deploy_sriovdp_netdev_pods_ipv4(request, ssh_connection)

    # validate that the sriov interface net1 is 'UP'
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()
    pod_1 = pods.get_pods_start_with(pod1_name)[0]  # should only be one
    pod_2 = pods.get_pods_start_with(pod2_name)[0]  # should only be one

    kubeclt_exec_in_pods = KubectlExecInPodsKeywords(ssh_connection)
    output = kubeclt_exec_in_pods.run_pod_exec_cmd(pod_1.get_name(), 'ip link show net1')
    interface = IPLinkShowOutput(output).get_interface()

    assert interface.state == 'UP', 'interface state was not UP for pod#1'

    output = kubeclt_exec_in_pods.run_pod_exec_cmd(pod_2.get_name(), 'ip link show net1')
    interface = IPLinkShowOutput(output).get_interface()

    assert interface.state == 'UP', 'interface state was not UP for pod#2'

    # add routes to both pods
    IPKeywords(ssh_connection).add_route_in_pod(pod1_name, 'net1')
    IPKeywords(ssh_connection).add_route_in_pod(pod2_name, 'net1')

    pod_1_ip = IPKeywords(ssh_connection).get_ip_address_from_pod(pod1_name, 'net1')
    pod_2_ip = IPKeywords(ssh_connection).get_ip_address_from_pod(pod2_name, 'net1')

    # validate that pod1 can ping server pod2
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod1_name, f"ping -c 3 {pod_2_ip}")
    assert ssh_connection.get_return_code() == 0

    # validate that pod 2 can ping pod1
    kubeclt_exec_in_pods.run_pod_exec_cmd(pod2_name, f"ping -c 3 {pod_1_ip}")
    assert ssh_connection.get_return_code() == 0


def sriov_deploy_images_to_local_registry(ssh_connection: SSHConnection):
    """
    Deploys images to the local registry for sriov testcases in this suite
    Args:
        ssh_connection (): the ssh connection

    Returns:

    """
    local_registry = ConfigurationManager.get_docker_config().get_registry('local_registry')
    file_keywords = FileKeywords(ssh_connection)

    file_keywords.upload_file(get_stx_resource_path("resources/images/pv-test.tar"), "/home/sysadmin/pv-test.tar", overwrite=False)
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, 'local-secret')
    docker_load_image_keywords = DockerLoadImageKeywords(ssh_connection)
    docker_load_image_keywords.load_docker_image_to_host('pv-test.tar')
    docker_load_image_keywords.tag_docker_image_for_registry('registry.local:9001/pv-test', 'pv-test', local_registry)
    docker_load_image_keywords.push_docker_image_to_registry('pv-test', local_registry)

    file_keywords.upload_file(get_stx_resource_path("resources/images/calico-ctl.tar"), "/home/sysadmin/calico-ctl.tar", overwrite=False)
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, 'local-secret')
    docker_load_image_keywords.load_docker_image_to_host('calico-ctl.tar')
    docker_load_image_keywords.tag_docker_image_for_registry('registry.local:9001/calico-ctl', 'calico-ctl', local_registry)
    docker_load_image_keywords.push_docker_image_to_registry('calico-ctl', local_registry)


def sriov_deploy_pods(request, net_def_yaml: str, calicoctl_pod_yaml: str, ssh_connection: SSHConnection):
    """
    Deploys pods needed by the sriov testcases
    Args:
        request (): request needed for adding teardown
        net_def_yaml (): the network definition yaml
        calicoctl_pod_yaml (): the calicoctl pod yaml
        ssh_connection (): the ssh connection

    Returns:

    """

    # Create teardown to cleanup
    def remove_pods_and_network_definitions():
        """
        Finalizer to remove pods, daemonsets and network definitions
        Returns:

        """
        rc = KubectlDeletePodsKeywords(ssh_connection).cleanup_pod('calicoctl', namespace='kube-system')
        rc += KubectlDeleteNetworkDefinitionKeywords(ssh_connection).cleanup_network_definition("netdev-sriov")
        assert rc == 0

    request.addfinalizer(remove_pods_and_network_definitions)

    # copy required files to system
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path('resources/cloud_platform/nightly_regression/calicoctl_sa.yaml'), '/home/sysadmin/calicoctl_sa.yaml')
    file_keywords.upload_file(get_stx_resource_path('resources/cloud_platform/nightly_regression/calicoctl_cr.yaml'), '/home/sysadmin/calicoctl_cr.yaml')
    file_keywords.upload_file(get_stx_resource_path('resources/cloud_platform/nightly_regression/calicoctl_crb.yaml'), '/home/sysadmin/calicoctl_crb.yaml')
    file_keywords.upload_file(get_stx_resource_path('resources/cloud_platform/nightly_regression/calicoctl_pod.yaml'), '/home/sysadmin/calicoctl_pod.yaml')
    file_keywords.upload_file(get_stx_resource_path(f'resources/cloud_platform/nightly_regression/{net_def_yaml}'), f'/home/sysadmin/{net_def_yaml}')
    file_keywords.upload_file(get_stx_resource_path(f'resources/cloud_platform/nightly_regression/{calicoctl_pod_yaml}'), f'/home/sysadmin/{calicoctl_pod_yaml}')

    # apply config files
    kubectl_apply_pods_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_apply_pods_keywords.apply_from_yaml('/home/sysadmin/calicoctl_sa.yaml')
    kubectl_apply_pods_keywords.apply_from_yaml('/home/sysadmin/calicoctl_cr.yaml')
    kubectl_apply_pods_keywords.apply_from_yaml('/home/sysadmin/calicoctl_crb.yaml')

    # apply yaml and check pod is rumnning
    kubectl_apply_pods_keywords.apply_from_yaml('/home/sysadmin/calicoctl_pod.yaml')
    assert KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status('calicoctl', 'Running', namespace='kube-system'), 'calicoctl did not start in time'

    kubectl_apply_pods_keywords.apply_from_yaml(f'/home/sysadmin/{net_def_yaml}')

    # copy yaml to calicoctl pod
    KubectlCopyToPodKeywords(ssh_connection).copy_to_pod(f'/home/sysadmin/{calicoctl_pod_yaml}', 'kube-system', 'calicoctl', f'/tmp/{calicoctl_pod_yaml}')
    # apply yaml in calicoclt pod
    KubectlExecInPodsKeywords(ssh_connection).exec_calicoctl_apply('calicoctl', 'kube-system', f'/tmp/{calicoctl_pod_yaml}')


def sriov_deploy_pods_ipv4(request, ssh_connection: SSHConnection):
    """
    Deploys pods needed by the sriov testcases
    Args:
        request (): request needed for adding teardown
        ssh_connection (): the ssh connection

    Returns:

    """

    # Create teardown to cleanup
    def remove_pods_and_network_definitions():
        """
        Finalizer to remove pods, daemonsets and network definitions
        Returns:

        """
        rc = KubectlDeleteNetworkDefinitionKeywords(ssh_connection).cleanup_network_definition("netdev-sriov")
        assert rc == 0

    request.addfinalizer(remove_pods_and_network_definitions)

    # copy required files to system
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path('resources/cloud_platform/nightly_regression/netdef_test-sriovdp_ipv4.yaml'), '/home/sysadmin/netdef_test-sriovdp_ipv4.yaml')

    # apply config files
    kubectl_apply_pods_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_apply_pods_keywords.apply_from_yaml('/home/sysadmin/netdef_test-sriovdp_ipv4.yaml')


def deploy_daemonset_pod(request, daemonset_pod_yaml: str, ssh_connection: SSHConnection):
    """
    Uploads and deploys the daemonset pod
    Args:
        request (): the request
        daemon_set_pod_yaml: the yaml file to apply
        ssh_connection (): the ssh connection

    Returns:

    """
    FileKeywords(ssh_connection).upload_file(get_stx_resource_path(f'resources/cloud_platform/nightly_regression/{daemonset_pod_yaml}'), f'/home/sysadmin/{daemonset_pod_yaml}')

    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(f'/home/sysadmin/{daemonset_pod_yaml}')

    # Create teardown to cleanup
    def remove_daemonset_pod():
        """
        Finalizer to remove pods, daemonsets and network definitions
        Returns:

        """
        rc = KubectlDeleteDaemonsetAppsKeywords(ssh_connection).cleanup_daemonset_apps('daemonset-sriovdp-netdev-single-pod')
        assert rc == 0

    request.addfinalizer(remove_daemonset_pod)

    # check that the daemonset pod is running
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()
    pod = pods.get_pods_start_with('daemonset-sriovdp-netdev-single-pod')

    assert len(pod) == 1, 'wrong number of pods'
    assert KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod[0].get_name(),
        'Running',
    ), 'daemonset pod did not start in time'


def deploy_sriovdp_netdev_pods_ipv6(request, ssh_connection: SSHConnection):
    """
    Uploads and deploys the sriovdp netdev pods
    Args:
        request (): the request
        ssh_connection (): the ssh connection

    Returns:

    """
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(
        get_stx_resource_path('resources/cloud_platform/nightly_regression/pod-test-sriovdp-netdev-connectivity-ipv6-0.yaml'), '/home/sysadmin/pod-test-sriovdp-netdev-connectivity-ipv6-0.yaml'
    )
    file_keywords.upload_file(
        get_stx_resource_path('resources/cloud_platform/nightly_regression/pod-test-sriovdp-netdev-connectivity-ipv6-1.yaml'), '/home/sysadmin/pod-test-sriovdp-netdev-connectivity-ipv6-1.yaml'
    )

    kubectl_apply_pods_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_apply_pods_keywords.apply_from_yaml('/home/sysadmin/pod-test-sriovdp-netdev-connectivity-ipv6-0.yaml')
    kubectl_apply_pods_keywords.apply_from_yaml('/home/sysadmin/pod-test-sriovdp-netdev-connectivity-ipv6-1.yaml')

    # Create teardown to cleanup
    def remove_pods():
        """
        Finalizer to remove pods, daemonsets and network definitions
        Returns:

        """
        rc = KubectlDeletePodsKeywords(ssh_connection).cleanup_pod('test-sriovdp-netdev-connectivity-ipv6-0')
        rc += KubectlDeletePodsKeywords(ssh_connection).cleanup_pod('test-sriovdp-netdev-connectivity-ipv6-1')
        assert rc == 0

    request.addfinalizer(remove_pods)

    # check that the daemonset pod is running
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()
    pod_1 = pods.get_pods_start_with('test-sriovdp-netdev-connectivity-ipv6-0')
    pod_2 = pods.get_pods_start_with('test-sriovdp-netdev-connectivity-ipv6-1')

    assert len(pod_1) == 1, 'wrong number of pods'
    assert KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod_1[0].get_name(),
        'Running',
    ), 'pod1 did not start in time'

    assert len(pod_2) == 1, 'wrong number of pods'
    assert KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod_2[0].get_name(),
        'Running',
    ), 'pod2 did not start in time'


def deploy_sriovdp_netdev_pods_ipv4(request, ssh_connection: SSHConnection):
    """
    Uploads and deploys the sriovdp netdev pods
    Args:
        request (): the request
        ssh_connection (): the ssh connection

    Returns:

    """
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(
        get_stx_resource_path('resources/cloud_platform/nightly_regression/pod-test-sriovdp-netdev-connectivity-ipv4-0.yaml'), '/home/sysadmin/pod-test-sriovdp-netdev-connectivity-ipv4-0.yaml'
    )
    file_keywords.upload_file(
        get_stx_resource_path('resources/cloud_platform/nightly_regression/pod-test-sriovdp-netdev-connectivity-ipv4-1.yaml'), '/home/sysadmin/pod-test-sriovdp-netdev-connectivity-ipv4-1.yaml'
    )

    kubectl_apply_pods_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_apply_pods_keywords.apply_from_yaml('/home/sysadmin/pod-test-sriovdp-netdev-connectivity-ipv4-0.yaml')
    kubectl_apply_pods_keywords.apply_from_yaml('/home/sysadmin/pod-test-sriovdp-netdev-connectivity-ipv4-1.yaml')

    # Create teardown to cleanup
    def remove_pods():
        """
        Finalizer to remove pods, daemonsets and network definitions
        Returns:

        """
        rc = KubectlDeletePodsKeywords(ssh_connection).cleanup_pod('test-sriovdp-netdev-connectivity-ipv4-0')
        rc += KubectlDeletePodsKeywords(ssh_connection).cleanup_pod('test-sriovdp-netdev-connectivity-ipv4-1')
        assert rc == 0

    request.addfinalizer(remove_pods)

    # check that the daemonset pod is running
    pods = KubectlGetPodsKeywords(ssh_connection).get_pods()
    pod_1 = pods.get_pods_start_with('test-sriovdp-netdev-connectivity-ipv4-0')
    pod_2 = pods.get_pods_start_with('test-sriovdp-netdev-connectivity-ipv4-1')

    assert len(pod_1) == 1, 'wrong number of pods'
    assert KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod_1[0].get_name(),
        'Running',
    ), 'pod1 did not start in time'

    assert len(pod_2) == 1, 'wrong number of pods'
    assert KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(
        pod_2[0].get_name(),
        'Running',
    ), 'pod2 did not start in time'

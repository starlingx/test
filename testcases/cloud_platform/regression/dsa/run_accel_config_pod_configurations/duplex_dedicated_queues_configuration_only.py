from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_chart_attribute_modify_keywords import SystemHelmChartAttributeModifyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords
from keywords.docker.login.docker_login_keywords import DockerLoginKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.node.kubectl_nodes_keywords import KubectlNodesKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.lsmod.lsmod_keywords import LsmodKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.k8s.pods.kubectl_logs_keywords import KubectlLogsKeywords


@mark.p0
@mark.lab_has_dsa
@mark.lab_is_duplex
def test_dsa_accel_config_pod_dedicated_queues_only_duplex(request):
    """Test case to install and validate Intel DSA plugin with dedicated queues only on duplex lab.

    **Requirements**
    - Lab hardware must support DSA.
    - Lab must be configured as duplex.
    - Access to registry.local:9001 for pushing required images.

    **Test Steps**
    1. Check if DSA-related kernel modules are loaded (idxd, idxd_bus).
    2. Upload and apply Node Feature Discovery (NFD).
    3. Upload Intel Device Plugins application (IDP) and enable the DSA Helm chart.
    4. Configure DSA with dedicated queues using helm override.
    5. Apply IDP and verify the chart is enabled.
    6. Verify DSA queues configuration (dedicated queues only on both nodes).
    7. Create default-registry-key secret in default namespace.
    8. Ensure stx-debian-tools-dev:stx.10.0-v1.0.0 is available on registry.
    9. Upload and apply the DSA accel-config test pod YAML for dedicated queues.
    10. Wait for the pod to reach Completed status and validate logs success markers.
    """
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    nfd_app_name = app_config.get_node_feature_discovery_app_name()
    nfd_tar_glob = f"{base_path}{nfd_app_name}*.tgz"
    intel_plugins_app_name = app_config.get_intel_device_plugins_app_name()
    idp_tar_glob = f"{base_path}{intel_plugins_app_name}*.tgz"
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    app_list_kw = SystemApplicationListKeywords(ssh_connection)
    apply_kw = SystemApplicationApplyKeywords(ssh_connection)
    remove_kw = SystemApplicationRemoveKeywords(ssh_connection)
    upload_kw = SystemApplicationUploadKeywords(ssh_connection)

    # Teardown: delete test pod, then remove Intel Device Plugins and NFD
    def cleanup_dsa_test():
        get_logger().log_teardown_step("Delete test pod dsa-accel-config-demo")
        KubectlDeletePodsKeywords(ssh_connection).cleanup_pod("dsa-accel-config-demo", namespace="default")

        app_list_kw = SystemApplicationListKeywords(ssh_connection)
        remove_kw = SystemApplicationRemoveKeywords(ssh_connection)

        for app_name in (intel_plugins_app_name, nfd_app_name):
            get_logger().log_teardown_step(f"Cleaning up {app_name}")
            remove_kw.cleanup_app_if_present(app_name)
            validate_equals(
                app_list_kw.is_app_present(app_name),
                False,
                f"{app_name} removal in teardown",
            )

    request.addfinalizer(cleanup_dsa_test)

    # Pre Test applications check and cleanup:
    for app_name in (intel_plugins_app_name, nfd_app_name):
        remove_kw.cleanup_app_if_present(app_name)

    # 1) Kernel modules check
    get_logger().log_test_case_step("Check if DSA-related kernel modules are loaded (idxd, idxd_bus)")
    lsmod_keywords = LsmodKeywords(ssh_connection)
    module_list = ("idxd", "idxd_bus")
    lsmod_out = lsmod_keywords.get_lsmod_output()
    lsmod_result = lsmod_out.check_modules_loaded(module_list)
    validate_equals(all(lsmod_result.values()), True, "All required kernel modules are loaded")

    # 2) DSA plugin installed and resources working
    get_logger().log_test_case_step("Ensure DSA plugin is installed and resources are healthy")

    # Upload and apply NFD
    get_logger().log_info(f"Uploading and applying {nfd_app_name}...")
    nfd_upload_apply_out = upload_kw.system_application_upload_and_apply_app(nfd_app_name, nfd_tar_glob)
    nfd_obj = nfd_upload_apply_out.get_system_application_object()
    validate_equals(nfd_obj.get_name(), nfd_app_name, "NFD name validation")
    validate_equals(apply_kw.is_already_applied(nfd_app_name), True, "NFD application status is applied")

    # Upload IDPO
    get_logger().log_info(f"Uploading {intel_plugins_app_name}...")
    idp_upload_input = SystemApplicationUploadInput()
    idp_upload_input.set_app_name(intel_plugins_app_name)
    idp_upload_input.set_tar_file_path(idp_tar_glob)
    upload_kw.system_application_upload(idp_upload_input)

    helm_attr_kw = SystemHelmChartAttributeModifyKeywords(ssh_connection)
    modify_output = helm_attr_kw.helm_chart_attribute_modify_enabled(
        app_name=intel_plugins_app_name,
        namespace=intel_plugins_app_name,
        chart_name="intel-device-plugins-dsa",
        enabled_value="true",
    )
    enabled_attr = modify_output.get_helm_chart_attribute_modify().get_attributes().get("enabled", False)
    validate_equals(enabled_attr, True, "DSA Helm chart enabled")

    apply_kw_idp = SystemApplicationApplyKeywords(ssh_connection)
    idp_apply_out = apply_kw_idp.system_application_apply(intel_plugins_app_name)
    validate_not_equals(idp_apply_out.get_system_application_object(), None, "IDP application apply validation")

    helm_override_kw = SystemHelmOverrideKeywords(ssh_connection)

    file_kw = FileKeywords(ssh_connection)
    repo_override_path = "resources/cloud_platform/accel_config_pods/dsa-override-dedicated.yaml"
    remote_override_path = "/home/sysadmin/dsa-override-dedicated.yaml"
    file_kw.upload_file(repo_override_path, remote_override_path)

    # 3) Check DSA queues configuration before override
    get_logger().log_test_case_step("Check DSA queues configuration before override")
    nodes_kw = KubectlNodesKeywords(ssh_connection)
    nodes_json = nodes_kw.get_nodes_allocatable_resources()

    for node in nodes_json.get_node_objects():
        get_logger().log_info(f"Node {node.get_name()} allocatable resources before override: {node.get_allocatable()}")

    # 4) Apply dedicated-only override and re-apply IDP
    get_logger().log_test_case_step("Apply dedicated-only override and re-apply IDP")
    helm_override_kw.update_helm_override(
        "/home/sysadmin/dsa-override-dedicated.yaml",
        intel_plugins_app_name,
        "intel-device-plugins-dsa",
        intel_plugins_app_name,
    )
    get_logger().log_info("helm-override-update executed successfully.")

    apply_kw_dedicated = SystemApplicationApplyKeywords(ssh_connection)
    apply_kw_dedicated.system_application_apply(intel_plugins_app_name)
    app_list_kw.get_system_application_list()

    nodes_json_after = KubectlNodesKeywords(ssh_connection).get_nodes_allocatable_resources()
    for node_after in nodes_json_after.get_node_objects():
        get_logger().log_info(f"Node {node_after.get_name()} allocatable resources after override: {node_after.get_allocatable()}")

    shared_total = nodes_json_after.count_resource_total("dsa.intel.com/wq-user-shared")
    validate_equals(shared_total, 0, "Only dedicated queues remain after override on both nodes")

    dedicated_total = nodes_json_after.count_resource_total("dsa.intel.com/wq-user-dedicated")
    validate_not_equals(dedicated_total, 0, "Dedicated queues available on both nodes")

    # 5) Create default-registry-key secret in default (copy from kube-system)
    get_logger().log_test_case_step("Create default-registry-key secret in default (copy from kube-system)")
    secret_kw = KubectlCreateSecretsKeywords(ssh_connection)
    secret_kw.copy_secret_between_namespaces("default-registry-key", "kube-system", "default")
    get_secrets_kw = KubectlGetSecretsKeywords(ssh_connection)
    validate_equals(
        "default-registry-key" in get_secrets_kw.get_secret_names(namespace="default"),
        True,
        "default-registry-key present in default namespace"
    )

    # 6) Ensure stx-debian-tools-dev:stx.10.0-v1.0.0 is available on registry
    get_logger().log_test_case_step("Ensure stx-debian-tools-dev:stx.10.0-v1.0.0 is available on registry.local:9001")

    image_name = "starlingx/stx-debian-tools-dev"
    image_tag = "stx.10.0-v1.0.0"
    manifest_name = "stx-sanity"

    local_registry = ConfigurationManager.get_docker_config().get_local_registry()
    DockerLoginKeywords(ssh_connection).login(local_registry.get_user_name(), local_registry.get_password(), local_registry.get_registry_url())

    docker_sync_keywords = DockerSyncImagesKeywords(ssh_connection)
    docker_sync_keywords.sync_image_from_manifest(image_name, image_tag, manifest_name)

    # 7) Upload dsa-pod-dedicated.yaml and apply it
    get_logger().log_test_case_step("Upload dsa-pod-dedicated.yaml and apply it")
    repo_pod_yaml = "resources/cloud_platform/accel_config_pods/dsa-pod-dedicated.yaml"
    remote_pod_yaml = "/home/sysadmin/dsa-pod-dedicated.yaml"
    FileKeywords(ssh_connection).upload_file(repo_pod_yaml, remote_pod_yaml)

    apply_pod_kw = KubectlApplyPodsKeywords(ssh_connection)
    apply_pod_kw.apply_from_yaml(remote_pod_yaml, namespace="default")

    # 8) Wait up to 40 seconds for pod to reach Completed status
    get_logger().log_info("Waiting up to 40s for pod to reach Completed...")
    test_pod_name = "dsa-accel-config-demo"
    test_namespace = "default"
    pods_kw = KubectlGetPodsKeywords(ssh_connection)

    validate_equals(
        pods_kw.wait_for_pod_status(test_pod_name, "Completed", test_namespace, timeout=40),
        True,
        "Pod must reach Completed within 40s",
    )

    # 9) Validate accel-config pod logs
    get_logger().log_test_case_step("Validate accel-config pod logs")
    logs_kw = KubectlLogsKeywords(ssh_connection)
    logs_text = logs_kw.get_logs("dsa-accel-config-demo", namespace="default", tail=200)
    for marker in ["All Tags Validated", "compsts: 1"]:
        validate_equals(marker in logs_text, True, f"Log contains success marker: {marker}")

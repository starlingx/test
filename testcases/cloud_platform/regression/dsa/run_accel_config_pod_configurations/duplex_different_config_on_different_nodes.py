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
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords
from keywords.docker.login.docker_login_keywords import DockerLoginKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.node.kubectl_nodes_keywords import KubectlNodesKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_logs_keywords import KubectlLogsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.linux.lsmod.lsmod_keywords import LsmodKeywords


@mark.p0
@mark.lab_has_dsa
@mark.lab_is_duplex
def test_dsa_accel_config_pod_different_config_on_different_nodes_duplex(request):
    """Test case to validate Intel DSA plugin default configuration with different configs on different nodes.

    **Requirements**
    - Lab hardware must support DSA.
    - Lab must be configured as duplex.
    - Access to registry.local:9001 for pushing required images.

    **Test Steps**
    1. Check if DSA-related kernel modules are loaded (idxd, idxd_bus).
    2. Upload and apply Node Feature Discovery (NFD).
    3. Upload Intel Device Plugins application (IDP) and enable the DSA Helm chart.
    4. Apply IDP and verify default configuration (controller-0: shared, controller-1: dedicated).
    5. Create default-registry-key secret in default namespace.
    6. Ensure stx-debian-tools-dev:stx.10.0-v1.0.0 is available on registry.
    7. Test shared queues pod (should run on controller-0).
    8. Test dedicated queues pod (should run on controller-1).
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
    KubectlDeletePodsKeywords(ssh_connection).cleanup_pod("dsa-accel-config-demo", namespace="default")

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

    # Upload and apply IDP
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

    pre_show = helm_override_kw.get_system_helm_override_show(intel_plugins_app_name, "intel-device-plugins-dsa", intel_plugins_app_name)
    get_logger().log_info("Current helm-override-show (pre-update) user_overrides:\n" + str(pre_show.get_helm_override_show().get_user_overrides()))

    kubectl_pods_kw = KubectlGetPodsKeywords(ssh_connection)
    kubectl_pods_kw.get_pods(namespace="intel-device-plugins-operator")

    file_kw = FileKeywords(ssh_connection)
    custom_config_yaml = "resources/cloud_platform/accel_config_pods/dsa-override-different-config-on-different-nodes.yaml"
    remote_config_yaml = "/home/sysadmin/dsa-different-config.yaml"
    file_kw.upload_file(custom_config_yaml, remote_config_yaml)

    # 3) Check DSA queues configuration before override
    get_logger().log_test_case_step("Check DSA queues configuration before override")
    nodes_kw = KubectlNodesKeywords(ssh_connection)
    nodes_json = nodes_kw.get_nodes_allocatable_resources()

    for node in nodes_json.get_node_objects():
        get_logger().log_info(f"Node {node.get_name()} allocatable resources before override: {node.get_allocatable()}")

    # 4) Apply different-config override and re-apply IDP
    get_logger().log_test_case_step("Apply different-config override and re-apply IDP")
    helm_override_kw.update_helm_override(
        remote_config_yaml,
        intel_plugins_app_name,
        "intel-device-plugins-dsa",
        intel_plugins_app_name,
    )
    get_logger().log_info("helm-override-update executed successfully.")

    post_show = helm_override_kw.get_system_helm_override_show(intel_plugins_app_name, "intel-device-plugins-dsa", intel_plugins_app_name)
    get_logger().log_info("helm-override-show (post-update) user_overrides:\n" + str(post_show.get_helm_override_show().get_user_overrides()))

    apply_kw_shared = SystemApplicationApplyKeywords(ssh_connection)
    apply_kw_shared.system_application_apply(intel_plugins_app_name)
    app_list_kw.get_system_application_list()
    kubectl_pods_kw.get_pods(namespace="intel-device-plugins-operator")

    nodes_json_after = KubectlNodesKeywords(ssh_connection).get_nodes_allocatable_resources()
    for node in nodes_json_after.get_node_objects():
        get_logger().log_info(f"Node {node.get_name()} allocatable resources after override: {node.get_allocatable()}")

    # 5) Verify DSA queues configuration (different config on different nodes)
    get_logger().log_test_case_step("Verify DSA queues configuration (different config on different nodes)")

    get_logger().log_info("=== DSA Queue Distribution (After Override) ===")

    host_list_kw = SystemHostListKeywords(ssh_connection)
    controllers = host_list_kw.get_controllers()
    validate_equals(len(controllers), 2, "Duplex system should have exactly 2 controllers")

    controller_configs = {}
    for controller in controllers:
        hostname = controller.get_host_name()
        controller_configs[hostname] = {"shared": 0, "dedicated": 0}

    for node in nodes_json_after.get_node_objects():
        node_name = node.get_name()
        if node_name in controller_configs:
            controller_configs[node_name]["shared"] = int(node.get_allocatable().get("dsa.intel.com/wq-user-shared", "0"))
            controller_configs[node_name]["dedicated"] = int(node.get_allocatable().get("dsa.intel.com/wq-user-dedicated", "0"))
            get_logger().log_info(f"{node_name}: shared={controller_configs[node_name]['shared']}, dedicated={controller_configs[node_name]['dedicated']}")

    controller_names = list(controller_configs.keys())
    controller_1 = controller_names[0]
    controller_2 = controller_names[1]

    config_1 = (controller_configs[controller_1]["shared"], controller_configs[controller_1]["dedicated"])
    config_2 = (controller_configs[controller_2]["shared"], controller_configs[controller_2]["dedicated"])
    validate_not_equals(config_1, config_2, "Controllers should have different DSA queue configurations")

    # Validate each controller has DSA queues and only one type
    for controller_name, config in controller_configs.items():
        shared_count = config["shared"]
        dedicated_count = config["dedicated"]
        validate_not_equals((shared_count, dedicated_count), (0, 0), f"{controller_name} should have DSA queues configured")

        has_both = shared_count > 0 and dedicated_count > 0
        validate_equals(has_both, False, f"{controller_name} should have either shared OR dedicated queues, not both")

    # 6) Create default-registry-key secret in default (copy from kube-system)
    get_logger().log_test_case_step("Create default-registry-key secret in default (copy from kube-system)")
    secret_kw = KubectlCreateSecretsKeywords(ssh_connection)
    secret_kw.copy_secret_between_namespaces("default-registry-key", "kube-system", "default")
    get_secrets_kw = KubectlGetSecretsKeywords(ssh_connection)
    validate_equals("default-registry-key" in get_secrets_kw.get_secret_names(namespace="default"), True, "default-registry-key present in default namespace")

    # 7) Ensure stx-debian-tools-dev:stx.10.0-v1.0.0 is available on registry
    get_logger().log_test_case_step("Ensure stx-debian-tools-dev:stx.10.0-v1.0.0 is available on registry.local:9001")

    image_name = "starlingx/stx-debian-tools-dev"
    image_tag = "stx.10.0-v1.0.0"
    manifest_name = "stx-sanity"

    local_registry = ConfigurationManager.get_docker_config().get_local_registry()
    DockerLoginKeywords(ssh_connection).login(local_registry.get_user_name(), local_registry.get_password(), local_registry.get_registry_url())

    docker_sync_keywords = DockerSyncImagesKeywords(ssh_connection)
    docker_sync_keywords.sync_image_from_manifest(image_name, image_tag, manifest_name)

    # 8) Test shared queues with dsa-pod-shared.yaml
    get_logger().log_test_case_step("Test shared queues with dsa-pod-shared.yaml")

    repo_pod_shared = "resources/cloud_platform/accel_config_pods/dsa-pod-shared.yaml"
    remote_pod_shared = "/home/sysadmin/dsa-pod-shared.yaml"
    FileKeywords(ssh_connection).upload_file(repo_pod_shared, remote_pod_shared)

    apply_pod_kw = KubectlApplyPodsKeywords(ssh_connection)
    apply_pod_kw.apply_from_yaml(remote_pod_shared, namespace="default")

    # Wait for shared pod to complete
    get_logger().log_info("Waiting up to 40s for shared pod to reach Completed...")
    test_pod_name = "dsa-accel-config-demo"
    test_namespace = "default"
    pods_kw = KubectlGetPodsKeywords(ssh_connection)

    validate_equals(
        pods_kw.wait_for_pod_status(test_pod_name, "Completed", test_namespace, timeout=40),
        True,
        "Shared pod must reach Completed within 40s",
    )

    # Validate shared pod logs
    get_logger().log_test_case_step("Validate shared pod logs")
    logs_kw = KubectlLogsKeywords(ssh_connection)
    logs_text = logs_kw.get_logs("dsa-accel-config-demo", namespace="default", tail=200)
    for marker in ["All Tags Validated", "compsts: 1"]:
        validate_equals(marker in logs_text, True, f"Shared pod log contains success marker: {marker}")

    # Delete shared pod
    get_logger().log_info("Deleting shared pod before testing dedicated pod")
    KubectlDeletePodsKeywords(ssh_connection).cleanup_pod("dsa-accel-config-demo", namespace="default")

    # 9) Test dedicated queues with dsa-pod-dedicated.yaml
    get_logger().log_test_case_step("Test dedicated queues with dsa-pod-dedicated.yaml")

    # Upload and test dedicated pod
    repo_pod_dedicated = "resources/cloud_platform/accel_config_pods/dsa-pod-dedicated.yaml"
    remote_pod_dedicated = "/home/sysadmin/dsa-pod-dedicated.yaml"
    FileKeywords(ssh_connection).upload_file(repo_pod_dedicated, remote_pod_dedicated)

    apply_pod_kw.apply_from_yaml(remote_pod_dedicated, namespace="default")

    # Wait for dedicated pod to complete
    get_logger().log_info("Waiting up to 40s for dedicated pod to reach Completed...")
    validate_equals(
        pods_kw.wait_for_pod_status(test_pod_name, "Completed", test_namespace, timeout=40),
        True,
        "Dedicated pod must reach Completed within 40s",
    )

    # Validate dedicated pod logs
    get_logger().log_test_case_step("Validate dedicated pod logs")
    logs_text = logs_kw.get_logs("dsa-accel-config-demo", namespace="default", tail=200)
    for marker in ["All Tags Validated", "compsts: 1"]:
        validate_equals(marker in logs_text, True, f"Dedicated pod log contains success marker: {marker}")

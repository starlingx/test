from pytest import FixtureRequest, mark

from starlingx.config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from starlingx.config.configuration_manager import ConfigurationManager
from starlingx.framework.logging.automation_logger import get_logger
from starlingx.framework.resources.resource_finder import get_stx_resource_path
from starlingx.framework.ssh.ssh_connection import SSHConnection
from starlingx.framework.validation.validation import validate_equals
from starlingx.keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from starlingx.keywords.docker.images.docker_load_image_keywords import DockerLoadImageKeywords
from starlingx.keywords.files.file_keywords import FileKeywords
from starlingx.keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from starlingx.keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from starlingx.keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from starlingx.keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from starlingx.keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords


@mark.p0
def test_policy_labels_on_platform_namespaces():
    """
    Verify that cert-manager, armada, kube-system, deployment namespaces contains the
    privileged policy labels
    Steps:
        - Get the platform namespaces with the privileged policy labels
        - Assert the expected namespace is ["cert-manager", "kube-system",
            "deployment", "flux-helm"]
    """

    label = "pod-security.kubernetes.io/audit=privileged,pod-security.kubernetes.io/audit-version=latest," "pod-security.kubernetes.io/enforce=privileged,pod-security.kubernetes.io/enforce-version=latest," "pod-security.kubernetes.io/warn=privileged,pod-security.kubernetes.io/warn-version=latest "
    active_ssh = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_info("Get the privileged namespace list based on release")
    expected_ns = ["cert-manager", "deployment", "flux-helm", "kube-system"]
    get_logger().log_info("Get the platform namespaces with labels")
    actual_ns = KubectlGetNamespacesKeywords(active_ssh).get_namespaces_by_label(label=label).get_namespaces()
    actual_ns_names = [ns.get_name() for ns in actual_ns]
    validate_equals(actual_ns_names, expected_ns, "Verifying that the retrieved namespaces match the expected values.")


def deploy_policy_ns(request: FixtureRequest, ssh_connection: SSHConnection) -> None:
    """
    Function to deploy the privileged-ns, baseline-ns and restricted-ns namespaces
    in setup and delete the namespaces in teardown

    Args:
        request (FixtureRequest): request needed for adding teardown
        ssh_connection (SSHConnection): the ssh connection
    Returns:
        None:  This function does not return a value.
    """

    # Transfer the pod yaml file to the active controller
    # Defines pod definition file name, source (local) and destination (remote) file paths.
    psa_file_name = "psa_ns.yaml"

    config_file_locations = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(config_file_locations)
    local_path = get_stx_resource_path(f"resources/cloud_platform/nightly_regression/{psa_file_name}")
    remote_path = f"/home/{ConfigurationManager.get_lab_config().get_admin_credentials().get_user_name()}/{psa_file_name}"
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path(local_path), remote_path, overwrite=False)

    get_logger().log_info(f"Creating resource from file {remote_path}")
    kubectl_apply_pods_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_apply_pods_keywords.apply_from_yaml(yaml_file=remote_path)

    def teardown():
        KubectlFileDeleteKeywords(ssh_connection).delete_resources(remote_path)

    request.addfinalizer(teardown)


def deploy_docker_image_to_local_registry(ssh_connection: SSHConnection, secret_namespace: str) -> None:
    """
    Deploy images to the local registry
    Args:
        ssh_connection (SSHConnection): the ssh connection
        secret_namespace (str): the namespace
    Returns:
        None:  This function does not return a value.

    """
    local_registry = ConfigurationManager.get_docker_config().get_registry("local_registry")

    get_logger().log_info(f"Deploy docker images to local registry to {local_registry}")
    FileKeywords(ssh_connection).upload_file(get_stx_resource_path("resources/images/pause.tar"), "/home/sysadmin/pause.tar")
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(local_registry, "local-secret", secret_namespace)
    docker_load_image_keywords = DockerLoadImageKeywords(ssh_connection)
    docker_load_image_keywords.load_docker_image_to_host("pause.tar")
    docker_load_image_keywords.tag_docker_image_for_registry("k8s.gcr.io/pause:latest", "pause", local_registry)
    docker_load_image_keywords.push_docker_image_to_registry("pause", local_registry)


@mark.p1
def test_deny_pod_in_baseline_ns(request: FixtureRequest):
    """
    Test to verify that baseline-ns rejects the pod with "privileged: true"

    Args:
        request (FixtureRequest): request needed for adding teardown
    Steps:
        - Deploy the privileged-ns, baseline-ns and restricted-ns namespaces
        - Upload the psa pod yaml to the lab
        - Deploy images to the local registry for this testcase
        - Deploy the pod with "privileged: true" and expect it to reject
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    psa_baseline_pod_deny_file_name = "psa-baseline-pod-deny.yaml"
    namespace = "baseline-ns"

    # Deploy the privileged-ns, baseline-ns and restricted-ns namespaces
    deploy_policy_ns(request, ssh_connection)

    # Upload the psa pod yaml to the lab
    local_path = get_stx_resource_path(f"resources/cloud_platform/nightly_regression/{psa_baseline_pod_deny_file_name}")
    config_file_locations = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(config_file_locations)
    remote_path = f"/home/{ConfigurationManager.get_lab_config().get_admin_credentials().get_user_name()}/{psa_baseline_pod_deny_file_name}"

    get_logger().log_info(f"Upload yaml on local {local_path} to {remote_path} on active controller")
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path(local_path), remote_path, overwrite=True)

    # Deploy images to the local registry for this testcase
    deploy_docker_image_to_local_registry(ssh_connection, namespace)

    # Deploy the pod with "privileged: true" and expect it to reject
    get_logger().log_info(f"Deploy {remote_path} with 'privileged: true' on active controller and expect it to reject")
    kubectl_apply_pods_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_apply_pods_keywords.fail_apply_from_yaml(remote_path)


@mark.p1
def test_allow_pod_in_baseline_ns(request: FixtureRequest):
    """
    Test to verify that baseline-ns accepts the pod with "privileged: false"
    Args:
        request (FixtureRequest): request needed for adding teardown
    Steps:
        - Deploy the privileged-ns, baseline-ns and restricted-ns namespaces
        - Upload the psa pod yaml to the lab
        - Deploy images to the local registry for this testcase
        - Deploy the pod with "privileged: false" and expect it to accept
    Raises:
        AssertionError: If the pod does not reach 'running' status within the
                        specified timeout, an AssertionError will be raised
                        with a descriptive error message.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    psa_baseline_pod_deny_file_name = "psa-baseline-pod-allow.yaml"
    namespace = "baseline-ns"

    # Deploy the privileged-ns, baseline-ns and restricted-ns namespaces
    deploy_policy_ns(request, ssh_connection)

    # Upload the psa pod yaml to the lab
    local_path = get_stx_resource_path(f"resources/cloud_platform/nightly_regression/{psa_baseline_pod_deny_file_name}")
    config_file_locations = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(config_file_locations)
    remote_path = f"/home/{ConfigurationManager.get_lab_config().get_admin_credentials().get_user_name()}/{psa_baseline_pod_deny_file_name}"

    get_logger().log_info(f"Upload yaml on local {local_path} to {remote_path} on active controller")

    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path(local_path), remote_path, overwrite=True)

    # Deploy images to the local registry for this testcase
    deploy_docker_image_to_local_registry(ssh_connection, namespace)

    # Deploy the pod with "privileged: false" and expect it to accept
    get_logger().log_info(f"Deploy {remote_path}  with 'privileged: false' on active controller and expect it to accept")
    kubectl_apply_pods_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_apply_pods_keywords.apply_from_yaml(remote_path)

    get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
    pod_obj = get_pod_obj.get_pods(namespace).get_pods()
    pod_name = [pod.get_name() for pod in pod_obj][0]
    pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
    validate_equals(pod_status, True, "Veryfing that the baseline-ns namespace accepts the pod with the 'privileged: false' configuration.")


@mark.p1
def test_deny_pod_in_restricted_ns(request: FixtureRequest):
    """
    Test to verify that restricted-ns rejects the pod with restricted values
    Args:
        request (FixtureRequest): request needed for adding teardown

    Steps:
        - Deploy the privileged-ns, baseline-ns and restricted-ns namespaces
        - Upload the psa pod yaml to the lab
        - Deploy images to the local registry for this testcase
        - Deploy the pod with restricted values and expect it to reject in restricted-ns
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    psa_restricted_pod_deny_file_name = "psa-restricted-pod-deny.yaml"
    namespace = "restricted-ns"

    # Deploy the privileged-ns, baseline-ns and restricted-ns namespaces
    deploy_policy_ns(request, ssh_connection)

    # Upload the psa pod yaml to the lab
    local_path = get_stx_resource_path(f"resources/cloud_platform/nightly_regression/{psa_restricted_pod_deny_file_name}")
    config_file_locations = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(config_file_locations)
    remote_path = f"/home/{ConfigurationManager.get_lab_config().get_admin_credentials().get_user_name()}/{psa_restricted_pod_deny_file_name}"

    get_logger().log_info(f"Upload yaml on local {local_path} to {remote_path} on active controller")
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path(local_path), remote_path, overwrite=True)

    # Deploy images to the local registry for this testcase
    deploy_docker_image_to_local_registry(ssh_connection, namespace)

    # Deploy the pod with restricted values and expect it to reject in restricted-ns
    get_logger().log_info(f"Deploy {remote_path} with restricted values and expect it to reject in restricted-ns")
    kubectl_apply_pods_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_apply_pods_keywords.fail_apply_from_yaml(remote_path)


@mark.p1
def test_allow_pod_in_restricted_ns(request: FixtureRequest):
    """
    Test to verify that restricted-ns accepts the pod
    Args:
        request (FixtureRequest): request needed for adding teardown
    Steps:
        - Deploy the privileged-ns, baseline-ns and restricted-ns namespaces
        - Upload the psa pod yaml to the lab
        - Deploy images to the local registry for this testcase
        - Deploy the pod and expect it to accept in restricted-ns
    Raises:
        AssertionError: If the pod does not reach 'running' status within the
                        specified timeout, an AssertionError will be raised
                        with a descriptive error message.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    psa_restricted_pod_allow_file_name = "psa-restricted-pod-allow.yaml"
    namespace = "restricted-ns"

    # Deploy the privileged-ns, baseline-ns and restricted-ns namespaces
    deploy_policy_ns(request, ssh_connection)

    # Upload the psa pod yaml to the lab
    local_path = get_stx_resource_path(f"resources/cloud_platform/nightly_regression/{psa_restricted_pod_allow_file_name}")
    config_file_locations = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(config_file_locations)
    remote_path = f"/home/{ConfigurationManager.get_lab_config().get_admin_credentials().get_user_name()}/{psa_restricted_pod_allow_file_name}"

    get_logger().log_info(f"Upload yaml on local {local_path} to {remote_path} on active controller")

    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path(local_path), remote_path, overwrite=True)

    # Deploy images to the local registry for this testcase
    deploy_docker_image_to_local_registry(ssh_connection, namespace)

    # Deploy the pod and expect it to accept in restricted-ns
    get_logger().log_info(f"Deploy {remote_path} in restricted-ns on active controller and expect it to accept")
    kubectl_apply_pods_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_apply_pods_keywords.apply_from_yaml(remote_path)

    get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
    pod_obj = get_pod_obj.get_pods(namespace).get_pods()
    pod_name = [pod.get_name() for pod in pod_obj][0]
    pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
    validate_equals(pod_status, True, "Veryfing that the restricted-ns namespace accepts the pod.")


@mark.p1
def test_allow_any_in_privileged_ns(request: FixtureRequest):
    """
    Test to verify that privileged-ns accepts any pod
    Args:
        request (FixtureRequest): request needed for adding teardown
    Steps:
        - Deploy the privileged-ns, baseline-ns and restricted-ns namespaces
        - Upload the psa pod yaml to the lab
        - Deploy images to the local registry for this testcase
        - Deploy the pods in privileged-ns and expect it to accept
    Raises:
        AssertionError: If the pod does not reach 'running' status within the
                        specified timeout, an AssertionError will be raised
                        with a descriptive error message.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    psa_privileged_pod_allow_file_name = "psa-privileged-allow-any.yaml"
    namespace = "privileged-ns"

    # Deploy the privileged-ns, baseline-ns and restricted-ns namespaces
    deploy_policy_ns(request, ssh_connection)

    # Upload the psa pod yaml to the lab
    local_path = get_stx_resource_path(f"resources/cloud_platform/nightly_regression/{psa_privileged_pod_allow_file_name}")
    config_file_locations = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(config_file_locations)
    remote_path = f"/home/{ConfigurationManager.get_lab_config().get_admin_credentials().get_user_name()}/{psa_privileged_pod_allow_file_name}"

    get_logger().log_info(f"Upload yaml on local {local_path} to {remote_path} on active controller")

    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path(local_path), remote_path, overwrite=True)

    # Deploy images to the local registry for this testcase
    deploy_docker_image_to_local_registry(ssh_connection, namespace)

    # Deploy the pods in privileged-ns and expect it to accept
    get_logger().log_info(f"Deploy {remote_path} in privileged-ns on active controller and expect it to accept")
    kubectl_apply_pods_keywords = KubectlApplyPodsKeywords(ssh_connection)
    kubectl_apply_pods_keywords.apply_from_yaml(remote_path)

    get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
    pod_obj = get_pod_obj.get_pods(namespace).get_pods()
    pod_name = [pod.get_name() for pod in pod_obj][0]
    pod_status = get_pod_obj.wait_for_pod_status(pod_name, "Running", namespace)
    validate_equals(pod_status, True, "Veryfing that the privileged-ns namespace accepts the pod.")

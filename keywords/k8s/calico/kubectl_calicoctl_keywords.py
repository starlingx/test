"""Keywords for calicoctl commands run from a one-shot pod."""

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.calico.object.calicoctl_ippool_output import CalicoctlIppoolOutput
from keywords.k8s.calico.object.calicoctl_workload_endpoints_output import CalicoctlWorkloadEndpointsOutput
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_logs_keywords import KubectlLogsKeywords
from keywords.k8s.pods.kubectl_run_pod_keywords import KubectlRunPodKeywords

CALICOCTL_POD_NAME = "calicoctl"
CALICOCTL_NAMESPACE = "kube-system"
CALICOCTL_SERVICE_ACCOUNT = "calicoctl"
REGISTRY_LOCAL_SECRET = "registry-local-secret"
# The calicoctl ServiceAccount, ClusterRole and ClusterRoleBinding shared with the sanity tests.
CALICOCTL_RBAC_RESOURCE_DIR = "resources/cloud_platform/nightly_regression"
CALICOCTL_RBAC_RESOURCES = ["calicoctl_sa.yaml", "calicoctl_cr.yaml", "calicoctl_crb.yaml"]
REMOTE_RESOURCE_DIR = "/tmp"
CALICOCTL_RUN_TIMEOUT_SECONDS = 120


class KubectlCalicoctlKeywords(K8sBaseKeyword):
    """Keywords for calicoctl commands run from a one-shot pod in kube-system.

    The calicoctl image must match the installed Calico release; callers pass the image
    they synced to the local registry.
    """

    def is_calicoctl_rbac_present(self) -> bool:
        """Check whether the calicoctl ClusterRoleBinding already exists.

        Returns:
            bool: True if the ClusterRoleBinding exists, False otherwise.
        """
        output = self.ssh_connection.send(self.k8s_config.export(f"kubectl get clusterrolebinding {CALICOCTL_SERVICE_ACCOUNT} --ignore-not-found -o name"))
        self.validate_success_return_code(self.ssh_connection)
        return "".join(output).strip() != ""

    def setup_calicoctl_rbac(self) -> bool:
        """Create the calicoctl ServiceAccount, ClusterRole and ClusterRoleBinding when they are missing.

        These resources are shared with other tests, so existing ones are reused as they are.

        Returns:
            bool: True if this call created the resources, False if they already existed.
        """
        if self.is_calicoctl_rbac_present():
            get_logger().log_info("The calicoctl ServiceAccount, ClusterRole and ClusterRoleBinding already exist; reusing them")
            return False
        get_logger().log_info("Creating the calicoctl ServiceAccount, ClusterRole and ClusterRoleBinding")
        file_keywords = FileKeywords(self.ssh_connection)
        apply_keywords = KubectlFileApplyKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())
        for resource_file in CALICOCTL_RBAC_RESOURCES:
            remote_path = f"{REMOTE_RESOURCE_DIR}/{resource_file}"
            file_keywords.upload_file(get_stx_resource_path(f"{CALICOCTL_RBAC_RESOURCE_DIR}/{resource_file}"), remote_path, overwrite=True)
            apply_keywords.apply_resource_from_yaml(remote_path)
        return True

    def teardown_calicoctl(self, delete_rbac: bool) -> None:
        """Delete any leftover calicoctl pod and, when the test created them, the calicoctl RBAC resources.

        Args:
            delete_rbac (bool): Whether to delete the RBAC resources; pass the value returned by setup_calicoctl_rbac.
        """
        get_logger().log_info("Deleting the calicoctl pod")
        KubectlDeletePodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).cleanup_pod(CALICOCTL_POD_NAME, namespace=CALICOCTL_NAMESPACE)
        if not delete_rbac:
            return
        get_logger().log_info("Deleting the calicoctl RBAC resources created by the test")
        delete_keywords = KubectlDeleteResourceKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())
        delete_keywords.delete_resource("clusterrolebinding", CALICOCTL_SERVICE_ACCOUNT)
        delete_keywords.delete_resource("clusterrole", CALICOCTL_SERVICE_ACCOUNT)
        delete_keywords.delete_resource("serviceaccount", CALICOCTL_SERVICE_ACCOUNT, namespace=CALICOCTL_NAMESPACE)

    def run_calicoctl(self, calicoctl_image: str, args: list[str]) -> str:
        """Run a calicoctl command from a one-shot pod and return its output.

        The pod is created, waited on until it finishes, its logs are read and it is
        deleted before the result is checked, so a failed command leaves no pod behind
        and its output is part of the failure message.

        Example:
            run_calicoctl(image, ["get", "ippool", "-o", "yaml"])

        Args:
            calicoctl_image (str): The calicoctl image in the local registry.
            args (list[str]): The calicoctl arguments; each element is passed as one argument.

        Returns:
            str: The calicoctl output.
        """
        delete_pods_keywords = KubectlDeletePodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())
        get_pods_keywords = KubectlGetPodsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())
        delete_pods_keywords.cleanup_pod(CALICOCTL_POD_NAME, namespace=CALICOCTL_NAMESPACE)

        get_logger().log_info(f"Running calicoctl {' '.join(args)}")
        overrides = {"spec": {"serviceAccountName": CALICOCTL_SERVICE_ACCOUNT, "hostNetwork": True, "imagePullSecrets": [{"name": REGISTRY_LOCAL_SECRET}]}}
        KubectlRunPodKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).run_pod(CALICOCTL_POD_NAME, calicoctl_image, namespace=CALICOCTL_NAMESPACE, overrides=overrides, args=[*args, "--allow-version-mismatch"])

        # A finished pod shows Completed (exit code 0) or Error in the 'kubectl get pods' STATUS column.
        get_pods_keywords.wait_for_pods_to_reach_status(["Completed", "Error"], pod_names=[CALICOCTL_POD_NAME], namespace=CALICOCTL_NAMESPACE, timeout=CALICOCTL_RUN_TIMEOUT_SECONDS)
        pod_status = get_pods_keywords.get_pods(namespace=CALICOCTL_NAMESPACE).get_pod(CALICOCTL_POD_NAME).get_status()
        output = KubectlLogsKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_logs(CALICOCTL_POD_NAME, namespace=CALICOCTL_NAMESPACE)
        delete_pods_keywords.cleanup_pod(CALICOCTL_POD_NAME, namespace=CALICOCTL_NAMESPACE)

        validate_equals(pod_status, "Completed", f"calicoctl {' '.join(args)} succeeds; output: {output}")
        return output

    def get_ippools(self, calicoctl_image: str) -> CalicoctlIppoolOutput:
        """Get the Calico IP pools with calicoctl.

        Args:
            calicoctl_image (str): The calicoctl image in the local registry.

        Returns:
            CalicoctlIppoolOutput: The parsed IP pools.
        """
        return CalicoctlIppoolOutput(self.run_calicoctl(calicoctl_image, ["get", "ippool", "-o", "yaml"]))

    def get_workload_endpoints(self, calicoctl_image: str) -> CalicoctlWorkloadEndpointsOutput:
        """Get the workload endpoints with calicoctl.

        Args:
            calicoctl_image (str): The calicoctl image in the local registry.

        Returns:
            CalicoctlWorkloadEndpointsOutput: The parsed workload endpoints.
        """
        return CalicoctlWorkloadEndpointsOutput(self.run_calicoctl(calicoctl_image, ["get", "workloadendpoints"]))

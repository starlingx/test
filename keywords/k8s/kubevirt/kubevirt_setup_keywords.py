"""Keyword for setting up KubeVirt as a test precondition.

Ensures the kubevirt-app is applied and a test VM instance is Running so tests
that need a running VMI can guarantee that precondition in one call, without
depending on test order or the lab being pre-provisioned.
"""

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.vm.kubectl_get_vm_keywords import KubectlGetVmKeywords
from keywords.k8s.vm.kubectl_get_vmi_keywords import KubectlGetVmiKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

KUBEVIRT_APP_NAME = "kubevirt-app"
KUBEVIRT_CHART_PATH = "/usr/local/share/applications/helm/kubevirt-app-[0-9]*"
KUBEVIRT_VM_NAME = "ubuntu-vm"
KUBEVIRT_VM_YAML_RESOURCE = "resources/cloud_platform/containers/kubevirt/vm-ubuntu2404.yaml"
KUBEVIRT_REMOTE_VM_DIR = "/home/sysadmin/kubevirt"
KUBEVIRT_REMOTE_VM_YAML = f"{KUBEVIRT_REMOTE_VM_DIR}/vm-ubuntu2404.yaml"
KUBEVIRT_VM_READY_TIMEOUT_SECONDS = 300
KUBEVIRT_APPLY_RETRY_TIMEOUT_SECONDS = 300


class KubevirtSetupKeywords(BaseKeyword):
    """Keyword for ensuring KubeVirt is applied and a test VM is Running."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize the keyword.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def ensure_kubevirt_ready(self) -> None:
        """Ensure KubeVirt is applied and a test VM instance is Running. Idempotent.

        Applies the kubevirt-app (no-op if already applied), then deploys the test
        VM and waits for its VMI to reach Running. If the VM is already Running this
        returns immediately, so it is safe to call at the start of every test that
        needs a running VMI without depending on test order or the lab being
        pre-provisioned.
        """
        apply_keywords = SystemApplicationApplyKeywords(self.ssh_connection)
        if apply_keywords.is_already_applied(KUBEVIRT_APP_NAME):
            get_logger().log_info(f"Application '{KUBEVIRT_APP_NAME}' already applied - skipping upload and apply")
        elif SystemApplicationListKeywords(self.ssh_connection).get_system_application_list().is_in_application_list(KUBEVIRT_APP_NAME):
            # If the app is already uploaded but not applied (e.g. uploaded or apply-failed),
            # so re-uploading would be rejected - just apply the existing upload.
            get_logger().log_info(f"Application '{KUBEVIRT_APP_NAME}' already uploaded - applying")
            apply_keywords.system_application_apply(KUBEVIRT_APP_NAME)
        else:
            get_logger().log_info(f"Uploading and applying application '{KUBEVIRT_APP_NAME}'")
            actual_chart = LsKeywords(self.ssh_connection).get_first_matching_file(KUBEVIRT_CHART_PATH)
            SystemApplicationUploadKeywords(self.ssh_connection).system_application_upload_and_apply_app(KUBEVIRT_APP_NAME, actual_chart)

        vmi_keywords = KubectlGetVmiKeywords(self.ssh_connection)
        if vmi_keywords.is_vmi_present(KUBEVIRT_VM_NAME):
            vmi_status = vmi_keywords.get_vmi_status(KUBEVIRT_VM_NAME)
        else:
            vmi_status = ""

        if vmi_status == "Running":
            get_logger().log_info(f"KubeVirt VM '{KUBEVIRT_VM_NAME}' already Running - skipping deploy")
            return

        get_logger().log_info(f"Deploying KubeVirt VM '{KUBEVIRT_VM_NAME}'")
        file_keywords = FileKeywords(self.ssh_connection)
        file_keywords.create_directory(KUBEVIRT_REMOTE_VM_DIR)
        file_keywords.upload_file(get_stx_resource_path(KUBEVIRT_VM_YAML_RESOURCE), KUBEVIRT_REMOTE_VM_YAML)
        # The KubeVirt virt-api admission webhook may not be reachable immediately
        # after the app is applied, so retry the apply until it succeeds.
        KubectlFileApplyKeywords(self.ssh_connection).apply_resource_from_yaml_with_retry(KUBEVIRT_REMOTE_VM_YAML, timeout=KUBEVIRT_APPLY_RETRY_TIMEOUT_SECONDS)

        get_logger().log_info(f"Waiting for KubeVirt VM '{KUBEVIRT_VM_NAME}' to be Running")
        KubectlGetVmKeywords(self.ssh_connection).wait_for_vm_status(KUBEVIRT_VM_NAME, "Running", timeout=KUBEVIRT_VM_READY_TIMEOUT_SECONDS)
        vmi_keywords.wait_for_vmi_status(KUBEVIRT_VM_NAME, "Running", timeout=KUBEVIRT_VM_READY_TIMEOUT_SECONDS)

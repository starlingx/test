"""System Test Setup Keywords.

Provides reusable methods for setting up PVC pods and SRIOV FEC
accelerator configurations for system testing.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_not_none
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_device_keywords import SystemHostDeviceKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


SRIOV_FEC_NAMESPACE = "sriov-fec-system"
SRIOV_FEC_APP_NAME = "sriov-fec-operator"
SRIOV_FEC_TARBALL_PATH = "/usr/local/share/applications/helm"

PVC_YAML_CONTENT = """apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: busybox-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: busybox-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: busybox
  template:
    metadata:
      labels:
        app: busybox
    spec:
      containers:
        - name: busybox
          image: busybox:latest
          command: ["sh", "-c", "sleep 3600"]
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: busybox-pvc
"""

SRIOV_FEC_ACC100_YAML_TEMPLATE = """apiVersion: sriovfec.intel.com/v2
kind: SriovFecClusterConfig
metadata:
  name: config
  namespace: sriov-fec-system
spec:
  priority: 1
  nodeSelector:
    kubernetes.io/hostname: {hostname}
  acceleratorSelector:
    pciAddress: {pci_address}
  physicalFunction:
    pfDriver: "vfio-pci"
    vfDriver: "vfio-pci"
    vfAmount: 8
    bbDevConfig:
      acc100:
        pfMode: false
        numVfBundles: 8
        maxQueueSize: 1024
        uplink4G:
          numQueueGroups: 0
          numAqsPerGroups: 16
          aqDepthLog2: 4
        downlink4G:
          numQueueGroups: 0
          numAqsPerGroups: 16
          aqDepthLog2: 4
        uplink5G:
          numQueueGroups: 4
          numAqsPerGroups: 16
          aqDepthLog2: 4
        downlink5G:
          numQueueGroups: 4
          numAqsPerGroups: 16
          aqDepthLog2: 4
  drainSkip: true
"""

SRIOV_FEC_ACC200_YAML_TEMPLATE = """apiVersion: sriovfec.intel.com/v2
kind: SriovFecClusterConfig
metadata:
  name: config
  namespace: sriov-fec-system
spec:
  priority: 1
  nodeSelector:
    kubernetes.io/hostname: {hostname}
  acceleratorSelector:
    pciAddress: {pci_address}
  physicalFunction:
    pfDriver: "vfio-pci"
    vfDriver: "vfio-pci"
    vfAmount: 16
    bbDevConfig:
      acc200:
        pfMode: false
        numVfBundles: 16
        maxQueueSize: 1024
        uplink4G:
          numQueueGroups: 0
          numAqsPerGroups: 16
          aqDepthLog2: 4
        downlink4G:
          numQueueGroups: 0
          numAqsPerGroups: 16
          aqDepthLog2: 4
        uplink5G:
          numQueueGroups: 4
          numAqsPerGroups: 16
          aqDepthLog2: 4
        downlink5G:
          numQueueGroups: 4
          numAqsPerGroups: 16
          aqDepthLog2: 4
        qfft:
          numQueueGroups: 4
          numAqsPerGroups: 16
          aqDepthLog2: 4
  drainSkip: true
"""

SRIOV_FEC_VRB2_YAML_TEMPLATE = """apiVersion: sriovvrb.intel.com/v1
kind: SriovVrbClusterConfig
metadata:
  name: config
  namespace: sriov-fec-system
spec:
  priority: 1
  nodeSelector:
    kubernetes.io/hostname: {hostname}
  acceleratorSelector:
    pciAddress: {pci_address}
  physicalFunction:
    pfDriver: "vfio-pci"
    vfDriver: "vfio-pci"
    vfAmount: 4
    bbDevConfig:
      vrb2:
        pfMode: false
        numVfBundles: 4
        maxQueueSize: 1024
        uplink4G:
          numQueueGroups: 0
          numAqsPerGroups: 16
          aqDepthLog2: 4
        downlink4G:
          numQueueGroups: 0
          numAqsPerGroups: 16
          aqDepthLog2: 4
        uplink5G:
          numQueueGroups: 4
          numAqsPerGroups: 16
          aqDepthLog2: 4
        downlink5G:
          numQueueGroups: 4
          numAqsPerGroups: 16
          aqDepthLog2: 4
        qfft:
          numQueueGroups: 4
          numAqsPerGroups: 16
          aqDepthLog2: 4
        qmld:
          numQueueGroups: 4
          numAqsPerGroups: 64
          aqDepthLog2: 4
  drainSkip: true
"""

SRIOV_FEC_N3000_YAML_TEMPLATE = """apiVersion: sriovfec.intel.com/v2
kind: SriovFecClusterConfig
metadata:
  name: config
  namespace: sriov-fec-system
spec:
  priority: 1
  nodeSelector:
    kubernetes.io/hostname: {hostname}
  acceleratorSelector:
    pciAddress: {pci_address}
  physicalFunction:
    pfDriver: "vfio-pci"
    vfDriver: "vfio-pci"
    vfAmount: 2
    bbDevConfig:
      n3000:
        networkType: "FPGA_5GNR"
        pfMode: false
        downlink:
          bandwidth: 3
          loadBalance: 128
          queues:
            vf0: 16
            vf1: 16
            vf2: 0
            vf3: 0
            vf4: 0
            vf5: 0
            vf6: 0
            vf7: 0
        uplink:
          bandwidth: 3
          loadBalance: 128
          queues:
            vf0: 16
            vf1: 16
            vf2: 0
            vf3: 0
            vf4: 0
            vf5: 0
            vf6: 0
            vf7: 0
  drainSkip: true
"""

SRIOV_FEC_CONFIG_TEMPLATES = {
    "acc100": SRIOV_FEC_ACC100_YAML_TEMPLATE,
    "acc200": SRIOV_FEC_ACC200_YAML_TEMPLATE,
    "vrb2": SRIOV_FEC_VRB2_YAML_TEMPLATE,
    "n3000": SRIOV_FEC_N3000_YAML_TEMPLATE,
}


class SetupSystemTestKeywords:
    """Keywords for setting up system test prerequisites (PVC pods, SRIOV FEC).

    Args:
        ssh_connection: SSH connection to the active controller.
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection
        self.file_keywords = FileKeywords(ssh_connection)
        self.kubectl_apply = KubectlFileApplyKeywords(ssh_connection)
        self.kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
        self.app_apply = SystemApplicationApplyKeywords(ssh_connection)
        self.app_list = SystemApplicationListKeywords(ssh_connection)

    def __str__(self) -> str:
        return "SetupSystemTestKeywords"

    def setup_pvc_pod(self, remote_path: str, yaml_filename: str = "busybox.yaml") -> None:
        """Create, apply, and verify the PVC pod deployment.

        Args:
            remote_path: Remote directory path for YAML files.
            yaml_filename: Filename for the busybox YAML.
        """
        get_logger().log_info("Creating PVC pod YAML file")
        self.file_keywords.create_file_with_heredoc(
            f"{remote_path}/{yaml_filename}", PVC_YAML_CONTENT
        )

        get_logger().log_info("Applying PVC pod YAML")
        self.kubectl_apply.apply_resource_from_yaml(f"{remote_path}/{yaml_filename}")

        get_logger().log_info("Waiting for busybox pod to be running")
        self.kubectl_pods.wait_for_pods_to_reach_status(
            expected_status=["Running"],
            pod_names=["busybox-deployment"],
            timeout=300
        )
        get_logger().log_info("PVC pod deployed and running")

    def setup_accelerator_card(self, remote_path: str, yaml_filename: str = "sriov-fec-cluster-config.yaml") -> None:
        """Identify network accelerator and set up SRIOV FEC operator and configuration.

        Args:
            remote_path: Remote directory path for YAML files.
            yaml_filename: Filename for the SRIOV FEC config YAML.
        """
        controller_hostname = SystemHostListKeywords(
            self.ssh_connection
        ).get_active_controller().get_host_name()
        get_logger().log_info(f"Active controller: {controller_hostname}")

        get_logger().log_info("Identifying network accelerator card")
        accelerator_type = self._identify_accelerator(controller_hostname)
        validate_not_none(
            accelerator_type,
            "No supported network accelerator found on the controller"
        )
        get_logger().log_info(f"Found {accelerator_type} accelerator")

        get_logger().log_info("Uploading and applying SRIOV FEC operator")
        self._upload_and_apply_sriov_operator()

        get_logger().log_info("Getting PCI address for SRIOV FEC configuration")
        pci_address = self._get_pci_address(controller_hostname)
        validate_not_none(
            pci_address,
            f"Could not retrieve PCI address on {controller_hostname}"
        )

        get_logger().log_info(f"Applying SRIOV FEC config for {accelerator_type}")
        self._apply_sriov_config(
            accelerator_type, controller_hostname, pci_address, remote_path, yaml_filename
        )

        get_logger().log_info("SRIOV FEC configuration applied successfully")

    def _identify_accelerator(self, hostname: str) -> str:
        """Identify the network accelerator card type.

        Args:
            hostname: The hostname to check.

        Returns:
            str: The accelerator type (n3000, acc100, acc200, vrb2) or None.
        """
        device_output = SystemHostDeviceKeywords(
            self.ssh_connection
        ).get_system_host_device_list(hostname)

        if device_output.has_host_vrb2():
            return "vrb2"
        if device_output.has_host_acc200():
            return "acc200"
        if device_output.has_host_acc100():
            return "acc100"
        if device_output.has_host_n3000():
            return "n3000"

        return None

    def _upload_and_apply_sriov_operator(self) -> None:
        """Upload and apply the SRIOV FEC operator application. Removes first if already present."""
        if self.app_list.is_app_present(SRIOV_FEC_APP_NAME):
            get_logger().log_info(f"{SRIOV_FEC_APP_NAME} already present, removing before re-apply")
            SystemApplicationRemoveKeywords(self.ssh_connection).cleanup_app_if_present(
                SRIOV_FEC_APP_NAME, force_removal=True, force_deletion=True, timeout_in_seconds=600
            )

        find_cmd = f"ls -t {SRIOV_FEC_TARBALL_PATH}/sriov-fec-operator*.tgz 2>/dev/null | head -1"
        output = self.ssh_connection.send(find_cmd)
        tarball_path = output[0].strip() if isinstance(output, list) and output else ""
        validate_not_none(
            tarball_path if tarball_path else None,
            f"SRIOV FEC operator tarball not found in {SRIOV_FEC_TARBALL_PATH}"
        )

        get_logger().log_info(f"SRIOV FEC operator tarball: {tarball_path}")

        upload_input = SystemApplicationUploadInput()
        upload_input.set_app_name(SRIOV_FEC_APP_NAME)
        upload_input.set_tar_file_path(tarball_path)
        SystemApplicationUploadKeywords(self.ssh_connection).system_application_upload(upload_input)

        self.app_apply.system_application_apply(SRIOV_FEC_APP_NAME, timeout=600)

        self.app_list.validate_app_status(SRIOV_FEC_APP_NAME, "applied", timeout=60)

        get_logger().log_info("SRIOV FEC operator pods verification")
        self.kubectl_pods.wait_for_pods_to_reach_status(
            expected_status=["Running", "Completed"],
            namespace=SRIOV_FEC_NAMESPACE,
            timeout=300
        )

    def _get_pci_address(self, hostname: str) -> str:
        """Get the PCI address of the SRIOV FEC accelerator device.

        Args:
            hostname: The hostname to query.

        Returns:
            str: The PCI address of the FEC accelerator device, or None.
        """
        cmd = (
            f"kubectl get sriovfecnodeconfigs.sriovfec.intel.com -n {SRIOV_FEC_NAMESPACE} "
            f"{hostname} -o jsonpath='{{.status.inventory.sriovAccelerators[0].pciAddress}}'"
        )
        output = self.ssh_connection.send(export_k8s_config(cmd))
        pci_address = output[0].strip() if isinstance(output, list) and output else None

        if not pci_address:
            cmd_vrb = (
                f"kubectl get sriovvrbnodeconfigs.sriovvrb.intel.com -n {SRIOV_FEC_NAMESPACE} "
                f"{hostname} -o jsonpath='{{.status.inventory.sriovAccelerators[0].pciAddress}}'"
            )
            output = self.ssh_connection.send(export_k8s_config(cmd_vrb))
            pci_address = output[0].strip() if isinstance(output, list) and output else None

        get_logger().log_info(f"Discovered PCI address: {pci_address} on {hostname}")
        return pci_address

    def _apply_sriov_config(
        self, accelerator_type: str, hostname: str, pci_address: str,
        remote_path: str, yaml_filename: str
    ) -> None:
        """Generate and apply the SRIOV FEC cluster configuration.

        Args:
            accelerator_type: Type of accelerator (acc100, acc200, vrb2, n3000).
            hostname: Controller hostname.
            pci_address: PCI address of the accelerator.
            remote_path: Remote directory for YAML files.
            yaml_filename: Filename for the config YAML.
        """
        config_template = SRIOV_FEC_CONFIG_TEMPLATES.get(accelerator_type)
        validate_not_none(
            config_template, f"Unsupported accelerator type: {accelerator_type}"
        )

        config_content = config_template.format(
            hostname=hostname, pci_address=pci_address
        )

        self.file_keywords.create_file_with_heredoc(
            f"{remote_path}/{yaml_filename}", config_content
        )

        self.kubectl_apply.apply_resource_from_yaml(f"{remote_path}/{yaml_filename}")
        get_logger().log_info(f"SRIOV FEC cluster config applied for {accelerator_type}")

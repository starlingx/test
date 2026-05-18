from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_not_none
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.host.system_host_device_keywords import SystemHostDeviceKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config


NAMESPACE = "sriov-fec-system"


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
    pfDriver: "igb_uio"
    vfDriver: "igb_uio"
    vfAmount: 16
    bbDevConfig:
      acc100:
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
        flrTimeout: 610
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
    "n3000": SRIOV_FEC_N3000_YAML_TEMPLATE,
}


def identify_network_accelerator(ssh_connection, hostname):
    """
    Identify the network accelerator card type by checking device and vendor IDs.
    
    Args:
        ssh_connection: SSH connection to the active controller
        hostname: The hostname to check
        
    Returns:
        str: The accelerator type (n3000, acc100, acc200) or None if not found
    """
    get_logger().log_info(f"Identifying network accelerator on {hostname}")

    system_host_device_keywords = SystemHostDeviceKeywords(ssh_connection)
    device_output = system_host_device_keywords.get_system_host_device_list(hostname)

    if device_output.has_host_acc100():
        get_logger().log_info("Identified acc100 accelerator")
        return "acc100"
    if device_output.has_host_acc200():
        get_logger().log_info("Identified acc200 accelerator")
        return "acc200"
    if device_output.has_host_n3000():
        get_logger().log_info("Identified n3000 accelerator")
        return "n3000"

    get_logger().log_info("No known network accelerator found")
    return None


def get_pci_address(ssh_connection, hostname):
    """
    Get the PCI address of the SRIOV FEC accelerator device.
    
    Args:
        ssh_connection: SSH connection to the active controller
        hostname: The hostname to query
        
    Returns:
        str: The PCI address of the FEC accelerator device
    """
    cmd = f"kubectl get sriovfecnodeconfigs.sriovfec.intel.com -n {NAMESPACE} {hostname} -o jsonpath='{{.status.inventory.sriovAccelerators[0].pciAddress}}'"
    output = ssh_connection.send(export_k8s_config(cmd))
    pci_address = output[0].strip() if output else None
    get_logger().log_info(f"Discovered PCI address: {pci_address} on {hostname}")
    return pci_address


def setup_pvc_pod(ssh_connection, file_keywords, kubectl_file_apply_keywords, kubectl_get_pods_keywords, remote_path, busybox_yaml):
    """
    Create, apply, and verify the PVC pod deployment.

    Args:
        ssh_connection: SSH connection to the active controller
        file_keywords: FileKeywords instance
        kubectl_file_apply_keywords: KubectlFileApplyKeywords instance
        kubectl_get_pods_keywords: KubectlGetPodsKeywords instance
        remote_path: Remote path for YAML files
        busybox_yaml: Filename for the busybox YAML
    """
    get_logger().log_info("Creating PVC pod YAML file")
    file_keywords.create_file_with_echo(
        f"{remote_path}/{busybox_yaml}",
        PVC_YAML_CONTENT
    )

    get_logger().log_info("Applying PVC pod YAML")
    kubectl_file_apply_keywords.apply_resource_from_yaml(f"{remote_path}/{busybox_yaml}")

    get_logger().log_info("Waiting for busybox pod to be running")
    kubectl_get_pods_keywords.wait_for_pods_to_reach_status(
        expected_status="Running",
        pod_names=["busybox-deployment"],
        timeout=300
    )


def setup_accelerator_card(ssh_connection, controller_hostname, file_keywords, kubectl_file_apply_keywords,
                           kubectl_get_pods_keywords, system_application_apply_keywords,
                           remote_path, sriov_fec_config_yaml):
    """
    Identify network accelerator and set up SRIOV FEC operator and configuration.

    Args:
        ssh_connection: SSH connection to the active controller
        controller_hostname: Hostname of the controller
        file_keywords: FileKeywords instance
        kubectl_file_apply_keywords: KubectlFileApplyKeywords instance
        kubectl_get_pods_keywords: KubectlGetPodsKeywords instance
        system_application_apply_keywords: SystemApplicationApplyKeywords instance
        remote_path: Remote path for YAML files
        sriov_fec_config_yaml: Filename for the SRIOV FEC config YAML
    """
    get_logger().log_info("Identifying network accelerator card")
    accelerator_type = identify_network_accelerator(ssh_connection, controller_hostname)
    validate_not_none(accelerator_type, "No supported network accelerator found on the controller")

    get_logger().log_info(f"Found {accelerator_type} accelerator, proceeding with SRIOV FEC setup")

    get_logger().log_info("Uploading SRIOV FEC operator")
    upload_input = SystemApplicationUploadInput()
    upload_input.set_app_name("sriov-fec-operator")
    upload_input.set_tar_file_path("/usr/local/share/applications/helm/sriov-fec-operator*.tgz")
    upload_input.set_force(True)
    SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input)

    get_logger().log_info("Applying SRIOV FEC operator")
    system_application_apply_keywords.system_application_apply("sriov-fec-operator", timeout=600)

    get_logger().log_info("Verifying SRIOV FEC operator pods are running")
    kubectl_get_pods_keywords.wait_for_pods_to_reach_status(
        expected_status="Running",
        namespace=NAMESPACE,
        timeout=300
    )

    get_logger().log_info("Getting PCI address for SRIOV FEC configuration")
    pci_address = get_pci_address(ssh_connection, controller_hostname)
    validate_not_none(pci_address, f"Could not retrieve PCI address for SRIOV FEC configuration on {controller_hostname}")

    get_logger().log_info(f"Creating SRIOV FEC configuration for {accelerator_type}")
    sriov_config_template = SRIOV_FEC_CONFIG_TEMPLATES.get(accelerator_type)
    validate_not_none(sriov_config_template, f"Unsupported accelerator type: {accelerator_type}")
    sriov_config_content = sriov_config_template.format(hostname=controller_hostname, pci_address=pci_address)

    file_keywords.create_file_with_echo(
        f"{remote_path}/{sriov_fec_config_yaml}",
        sriov_config_content
    )

    get_logger().log_info("Applying SRIOV FEC cluster configuration")
    kubectl_file_apply_keywords.apply_resource_from_yaml(
        f"{remote_path}/{sriov_fec_config_yaml}"
    )

    get_logger().log_info("Verifying SRIOV FEC configuration is applied")
    verify_cmd = f"kubectl get sriovfecnodeconfigs.sriovfec.intel.com -n {NAMESPACE} {controller_hostname} -o yaml"
    output = ssh_connection.send(verify_cmd)
    get_logger().log_info(f"SRIOV FEC node config: {output}")

    get_logger().log_info("SRIOV FEC configuration applied successfully")

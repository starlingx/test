class SriovFecDeviceConfig:
    """Device-specific configuration for a SR-IOV FEC accelerator card.

    Captures the device IDs, VF IDs, template file names and resource name
    prefix for a single accelerator card type so the same keywords can be
    reused for every supported card.
    """

    def __init__(self, name: str, prefix: str, device_id: str, vf_device_id: str, vf_vendor_id: str, operator_template: str, pod_template: str):
        """Constructor.

        Args:
            name (str): Short device name used for logging (e.g., 'ACC100').
            prefix (str): Resource name prefix used in file names and pod names (e.g., 'acc100').
            device_id (str): PCI device ID of the physical accelerator.
            vf_device_id (str): PCI device ID of the virtual function.
            vf_vendor_id (str): PCI vendor ID of the virtual function.
            operator_template (str): Relative path to the operator config YAML template.
            pod_template (str): Relative path to the pod YAML template.
        """
        self.name = name
        self.prefix = prefix
        self.device_id = device_id
        self.vf_device_id = vf_device_id
        self.vf_vendor_id = vf_vendor_id
        self.operator_template = operator_template
        self.pod_template = pod_template

    def get_name(self) -> str:
        """Getter for the short device name.

        Returns:
            str: Short device name used for logging (e.g., 'ACC100').
        """
        return self.name

    def get_prefix(self) -> str:
        """Getter for the resource name prefix.

        Returns:
            str: Resource name prefix used in file names and pod names (e.g., 'acc100').
        """
        return self.prefix

    def get_device_id(self) -> str:
        """Getter for the physical accelerator PCI device ID.

        Returns:
            str: PCI device ID of the physical accelerator.
        """
        return self.device_id

    def get_vf_device_id(self) -> str:
        """Getter for the virtual function PCI device ID.

        Returns:
            str: PCI device ID of the virtual function.
        """
        return self.vf_device_id

    def get_vf_vendor_id(self) -> str:
        """Getter for the virtual function PCI vendor ID.

        Returns:
            str: PCI vendor ID of the virtual function.
        """
        return self.vf_vendor_id

    def get_operator_template(self) -> str:
        """Getter for the operator config YAML template path.

        Returns:
            str: Relative path to the operator config YAML template.
        """
        return self.operator_template

    def get_pod_template(self) -> str:
        """Getter for the pod YAML template path.

        Returns:
            str: Relative path to the pod YAML template.
        """
        return self.pod_template


# Prefixes of all FEC accelerator pods, used when cleaning up leftover pods.
FEC_POD_PREFIXES = ["vrb2", "acc100", "acc200", "n3000"]


# Pre-built device configurations for each supported accelerator card.
ACC100 = SriovFecDeviceConfig(
    name="ACC100",
    prefix="acc100",
    device_id="0d5c",
    vf_device_id="0d5d",
    vf_vendor_id="8086",
    operator_template="resources/cloud_platform/sriov-fec-operator/sriov-fec-operator-acc100.yaml.j2",
    pod_template="resources/cloud_platform/sriov-fec-operator/sriov-pod-acc100.yaml.j2",
)

ACC200 = SriovFecDeviceConfig(
    name="ACC200",
    prefix="acc200",
    device_id="57c0",
    vf_device_id="57c1",
    vf_vendor_id="8086",
    operator_template="resources/cloud_platform/sriov-fec-operator/sriov-fec-operator-acc200.yaml.j2",
    pod_template="resources/cloud_platform/sriov-fec-operator/sriov-pod-acc200.yaml.j2",
)

N3000 = SriovFecDeviceConfig(
    name="N3000",
    prefix="n3000",
    device_id="0d8f",
    vf_device_id="0d90",
    vf_vendor_id="8086",
    operator_template="resources/cloud_platform/sriov-fec-operator/sriov-fec-operator-n3000.yaml.j2",
    pod_template="resources/cloud_platform/sriov-fec-operator/sriov-pod-n3000.yaml.j2",
)

VRB2 = SriovFecDeviceConfig(
    name="VRB2",
    prefix="vrb2",
    device_id="57c2",
    vf_device_id="57c3",
    vf_vendor_id="8086",
    operator_template="resources/cloud_platform/sriov-fec-operator/sriov-fec-operator-vrb2.yaml.j2",
    pod_template="resources/cloud_platform/sriov-fec-operator/sriov-pod-vrb2.yaml.j2",
)

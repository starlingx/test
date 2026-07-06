import json
from typing import List, Optional, Union

from framework.logging.automation_logger import get_logger
from keywords.k8s.sriov_fec_node_config.object.kubectl_sriov_fec_node_config_detail_object import KubectlSriovFecNodeConfigDetailObject
from keywords.k8s.sriov_fec_node_config.object.sriov_fec_accelerator_object import SriovFecAcceleratorObject
from keywords.k8s.sriov_fec_node_config.object.sriov_fec_physical_function_object import SriovFecPhysicalFunctionObject
from keywords.k8s.sriov_fec_node_config.object.sriov_fec_virtual_function_object import SriovFecVirtualFunctionObject

VFIO_PCI_DRIVER = "vfio-pci"


class KubectlGetSriovFecNodeConfigDetailOutput:
    """Class for parsing 'kubectl get sriovfecnodeconfigs.sriovfec.intel.com -o json' output."""

    def __init__(self, kubectl_get_sriov_fec_node_config_output: Union[str, List[str]]) -> None:
        """Constructor.

        Args:
            kubectl_get_sriov_fec_node_config_output (Union[str, List[str]]): Raw JSON output from the kubectl get -o json command.
        """
        self.sriov_fec_node_config_details: List[KubectlSriovFecNodeConfigDetailObject] = []
        self._parse(kubectl_get_sriov_fec_node_config_output)

    def _parse(self, raw_output: Union[str, List[str]]) -> None:
        """Parse the raw JSON output into detail objects.

        Args:
            raw_output (Union[str, List[str]]): Raw JSON string or list of output lines.
        """
        raw = raw_output if isinstance(raw_output, str) else "".join(raw_output)

        json_start = raw.find("{")
        json_end = raw.rfind("}")
        if json_start == -1 or json_end == -1 or json_end < json_start:
            get_logger().log_warning("No JSON found in sriovfecnodeconfigs output")
            return

        json_str = raw[json_start : json_end + 1]
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exception:
            get_logger().log_warning(f"Failed to parse sriovfecnodeconfigs JSON: {exception}")
            return

        items = data.get("items", []) if "items" in data else [data]
        for item in items:
            self.sriov_fec_node_config_details.append(self._build_detail_object_from_dict(item))

    def _build_detail_object_from_dict(self, item: dict) -> KubectlSriovFecNodeConfigDetailObject:
        """Build a single detail object from a parsed JSON dict.

        Args:
            item (dict): The dict representing one SriovFecNodeConfig resource.

        Returns:
            KubectlSriovFecNodeConfigDetailObject: The populated detail object.
        """
        metadata = item.get("metadata", {})
        spec = item.get("spec", {})
        status = item.get("status", {})

        detail = KubectlSriovFecNodeConfigDetailObject()
        detail.set_name(metadata.get("name"))
        detail.set_namespace(metadata.get("namespace"))

        detail.set_physical_functions(self._build_physical_functions(spec.get("physicalFunctions", [])))
        detail.set_accelerators(self._build_accelerators(status.get("inventory", {}).get("sriovAccelerators", [])))

        configured_condition = self._find_configured_condition(status.get("conditions", []))
        if configured_condition is not None:
            detail.set_configured_reason(configured_condition.get("reason"))
            detail.set_configured_status(configured_condition.get("status"))
            detail.set_configured_message(configured_condition.get("message"))

        return detail

    def _build_physical_functions(self, physical_functions: List[dict]) -> List[SriovFecPhysicalFunctionObject]:
        """Build physical function objects from the spec list.

        Args:
            physical_functions (List[dict]): The 'spec.physicalFunctions' list.

        Returns:
            List[SriovFecPhysicalFunctionObject]: The populated physical function objects.
        """
        result: List[SriovFecPhysicalFunctionObject] = []
        for physical_function in physical_functions:
            physical_function_object = SriovFecPhysicalFunctionObject()
            physical_function_object.set_pci_address(physical_function.get("pciAddress"))
            physical_function_object.set_pf_driver(physical_function.get("pfDriver"))
            physical_function_object.set_vf_driver(physical_function.get("vfDriver"))
            physical_function_object.set_vf_amount(physical_function.get("vfAmount"))
            result.append(physical_function_object)
        return result

    def _build_accelerators(self, accelerators: List[dict]) -> List[SriovFecAcceleratorObject]:
        """Build accelerator objects from the status inventory list.

        Args:
            accelerators (List[dict]): The 'status.inventory.sriovAccelerators' list.

        Returns:
            List[SriovFecAcceleratorObject]: The populated accelerator objects.
        """
        result: List[SriovFecAcceleratorObject] = []
        for accelerator in accelerators:
            accelerator_object = SriovFecAcceleratorObject()
            accelerator_object.set_pci_address(accelerator.get("pciAddress"))
            accelerator_object.set_device_id(accelerator.get("deviceID"))
            accelerator_object.set_vendor_id(accelerator.get("vendorID"))
            accelerator_object.set_driver(accelerator.get("driver"))
            accelerator_object.set_max_virtual_functions(accelerator.get("maxVirtualFunctions"))
            accelerator_object.set_virtual_functions(self._build_virtual_functions(accelerator.get("virtualFunctions", [])))
            result.append(accelerator_object)
        return result

    def _build_virtual_functions(self, virtual_functions: List[dict]) -> List[SriovFecVirtualFunctionObject]:
        """Build virtual function objects from an accelerator's list.

        Args:
            virtual_functions (List[dict]): The 'virtualFunctions' list of an accelerator.

        Returns:
            List[SriovFecVirtualFunctionObject]: The populated virtual function objects.
        """
        result: List[SriovFecVirtualFunctionObject] = []
        for virtual_function in virtual_functions:
            virtual_function_object = SriovFecVirtualFunctionObject()
            virtual_function_object.set_pci_address(virtual_function.get("pciAddress"))
            virtual_function_object.set_device_id(virtual_function.get("deviceID"))
            virtual_function_object.set_driver(virtual_function.get("driver"))
            result.append(virtual_function_object)
        return result

    def _find_configured_condition(self, conditions: List[dict]) -> Optional[dict]:
        """Find the 'Configured' status condition.

        Args:
            conditions (List[dict]): The 'status.conditions' list.

        Returns:
            Optional[dict]: The condition dict with type 'Configured', or None if absent.
        """
        for condition in conditions:
            if condition.get("type") == "Configured":
                return condition
        return None

    def get_sriov_fec_node_config_details(self) -> List[KubectlSriovFecNodeConfigDetailObject]:
        """Return the list of all parsed SriovFecNodeConfig detail objects.

        Returns:
            List[KubectlSriovFecNodeConfigDetailObject]: All parsed detail objects.
        """
        return self.sriov_fec_node_config_details

    def get_sriov_fec_node_config_detail_by_name(self, name: str) -> KubectlSriovFecNodeConfigDetailObject:
        """Return the SriovFecNodeConfig detail with the specified name.

        Args:
            name (str): The name of the SriovFecNodeConfig to retrieve.

        Returns:
            KubectlSriovFecNodeConfigDetailObject: The matching detail object.

        Raises:
            ValueError: If no SriovFecNodeConfig with the specified name is found.
        """
        for detail in self.sriov_fec_node_config_details:
            if detail.get_name() == name:
                return detail
        raise ValueError(f"SriovFecNodeConfig '{name}' not found")

    def is_vfio_mode(self, name: str, device_id: Optional[str] = None) -> bool:
        """Check whether a SriovFecNodeConfig is configured in VFIO mode.

        VFIO mode requires the 'vfio-pci' driver everywhere for the scope checked:
        the configured pfDriver and vfDriver in the spec, the driver bound to the
        physical function in the status inventory, and the driver bound to each of
        its virtual functions.

        Both pfDriver and vfDriver are checked because they are configured
        independently. A physical function bound to 'vfio-pci' whose virtual
        functions use another driver is not VFIO mode.

        When device_id is provided, only the accelerator with that device ID and its
        matching physical function (by PCI address) are checked. When device_id is
        None, every physical function and every accelerator must be in VFIO mode.

        Args:
            name (str): The name of the SriovFecNodeConfig to check.
            device_id (Optional[str]): If provided, restrict the check to the accelerator with this device ID.

        Returns:
            bool: True if the config is in VFIO mode for the given scope, False otherwise.

        Raises:
            ValueError: If no SriovFecNodeConfig with the specified name is found, or
                if device_id is provided but no matching accelerator exists.
        """
        detail = self.get_sriov_fec_node_config_detail_by_name(name)

        if device_id is not None:
            accelerator = detail.get_accelerator_by_device_id(device_id)
            if not self._is_accelerator_in_vfio_mode(accelerator):
                return False
            if not detail.has_physical_function_by_pci_address(accelerator.get_pci_address()):
                return False
            return self._is_physical_function_in_vfio_mode(detail.get_physical_function_by_pci_address(accelerator.get_pci_address()))

        physical_functions = detail.get_physical_functions()
        accelerators = detail.get_accelerators()
        if not physical_functions or not accelerators:
            return False

        physical_functions_in_vfio = all(self._is_physical_function_in_vfio_mode(physical_function) for physical_function in physical_functions)
        accelerators_in_vfio = all(self._is_accelerator_in_vfio_mode(accelerator) for accelerator in accelerators)
        return physical_functions_in_vfio and accelerators_in_vfio

    def _is_physical_function_in_vfio_mode(self, physical_function: SriovFecPhysicalFunctionObject) -> bool:
        """Check whether a configured physical function requests the VFIO driver.

        Args:
            physical_function (SriovFecPhysicalFunctionObject): The physical function from the spec.

        Returns:
            bool: True if both pfDriver and vfDriver are 'vfio-pci'.
        """
        return physical_function.get_pf_driver() == VFIO_PCI_DRIVER and physical_function.get_vf_driver() == VFIO_PCI_DRIVER

    def _is_accelerator_in_vfio_mode(self, accelerator: SriovFecAcceleratorObject) -> bool:
        """Check whether an accelerator and its virtual functions are bound to the VFIO driver.

        Args:
            accelerator (SriovFecAcceleratorObject): The accelerator from the status inventory.

        Returns:
            bool: True if the accelerator and all of its virtual functions are bound to 'vfio-pci'.
        """
        if accelerator.get_driver() != VFIO_PCI_DRIVER:
            return False
        return all(virtual_function.get_driver() == VFIO_PCI_DRIVER for virtual_function in accelerator.get_virtual_functions())

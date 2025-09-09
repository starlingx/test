from framework.redfish.objects.boot import Boot
from framework.redfish.objects.computer_system_reset import ComputerSystemReset
from framework.redfish.objects.memory_summary import MemorySummary
from framework.redfish.objects.processor_summary import ProcessorSummary
from framework.redfish.objects.status import Status
from framework.redfish.objects.trusted_modules import TrustedModule


class SystemInfo:
    """Represents system information from Redfish API."""

    def __init__(self, data: dict):
        """Initialize SysInfo object.

        Args:
            data (dict): Dictionary containing system data.

        Raises:
            ValueError: If data is None or empty.
        """
        if not data:
            raise ValueError("System data cannot be None or empty")

        # Simple attributes
        self.power_state = data.get("PowerState", "")
        self.manufacturer = data.get("Manufacturer", "")
        self.model = data.get("Model", "")
        self.serial_number = data.get("SerialNumber", "")
        self.bios_version = data.get("BiosVersion", "")
        self.asset_tag = data.get("AssetTag", "")
        self.host_name = data.get("HostName", "")
        self.indicator_led = data.get("IndicatorLED", "")
        self.last_reset_time = data.get("LastResetTime", "")
        self.location_indicator_active = data.get("LocationIndicatorActive", "")
        self.name = data.get("Name", "")
        self.part_number = data.get("PartNumber", "")
        self.sku = data.get("SKU", "")
        self.system_type = data.get("SystemType", "")
        self.uuid = data.get("UUID", "")
        self.description = data.get("Description", "")
        self.id = data.get("Id", "")

        # Complex objects
        self.status = self.generate_status(data)
        self.boot = self.generate_boot(data)
        self.memory_summary = self.generate_memory_summary(data)
        self.computer_system_reset = self.generate_computer_system_reset(data)
        self.processor_summary = self.generate_processor_summary(data)
        self.trusted_modules = self.generate_trusted_modules(data)

        # Lists
        self.pcie_devices = data.get("PCIeDevices", [])
        self.pcie_functions = data.get("PCIeFunctions", [])

    def get_power_state(self) -> str:
        """Get power state.

        Returns:
            str: Power state value.
        """
        return self.power_state

    def set_power_state(self, power_state: str) -> None:
        """Set power state.

        Args:
            power_state (str): Power state value.
        """
        self.power_state = power_state

    def get_manufacturer(self) -> str:
        """Get manufacturer.

        Returns:
            str: Manufacturer name.
        """
        return self.manufacturer

    def set_manufacturer(self, manufacturer: str) -> None:
        """Set manufacturer.

        Args:
            manufacturer (str): Manufacturer name.
        """
        self.manufacturer = manufacturer

    def get_model(self) -> str:
        """Get model.

        Returns:
            str: Model name.
        """
        return self.model

    def set_model(self, model: str) -> None:
        """Set model.

        Args:
            model (str): Model name.
        """
        self.model = model

    def get_serial_number(self) -> str:
        """Get serial number.

        Returns:
            str: Serial number.
        """
        return self.serial_number

    def set_serial_number(self, serial_number: str) -> None:
        """Set serial number.

        Args:
            serial_number (str): Serial number.
        """
        self.serial_number = serial_number

    def get_bios_version(self) -> str:
        """Get BIOS version.

        Returns:
            str: BIOS version.
        """
        return self.bios_version

    def set_bios_version(self, bios_version: str) -> None:
        """Set BIOS version.

        Args:
            bios_version (str): BIOS version.
        """
        self.bios_version = bios_version

    def get_status(self) -> Status:
        """Get system status.

        Returns:
            Status: System status object.
        """
        return self.status

    def set_status(self, status: Status) -> None:
        """Set system status.

        Args:
            status (Status): System status object.
        """
        self.status = status

    def get_boot(self) -> Boot:
        """Get boot configuration.

        Returns:
            Boot: Boot configuration object.
        """
        return self.boot

    def set_boot(self, boot: Boot) -> None:
        """Set boot configuration.

        Args:
            boot (Boot): Boot configuration object.
        """
        self.boot = boot

    def get_memory_summary(self) -> MemorySummary:
        """Get memory summary.

        Returns:
            MemorySummary: Memory summary object.
        """
        return self.memory_summary

    def set_memory_summary(self, memory_summary: MemorySummary) -> None:
        """Set memory summary.

        Args:
            memory_summary (MemorySummary): Memory summary object.
        """
        self.memory_summary = memory_summary

    def get_asset_tag(self) -> str:
        """Get asset tag.

        Returns:
            str: Asset tag.
        """
        return self.asset_tag

    def set_asset_tag(self, asset_tag: str) -> None:
        """Set asset tag.

        Args:
            asset_tag (str): Asset tag.
        """
        self.asset_tag = asset_tag

    def get_host_name(self) -> str:
        """Get host name.

        Returns:
            str: Host name.
        """
        return self.host_name

    def set_host_name(self, asset_tag: str) -> None:
        """Set host name.

        Args:
            asset_tag (str): Host name.
        """
        self.asset_tag = asset_tag

    def get_indicator_led(self) -> str:
        """Get indicator LED status.

        Returns:
            str: Indicator LED status.
        """
        return self.asset_tag

    def set_indicator_led(self, asset_tag: str) -> None:
        """Set indicator LED status.

        Args:
            asset_tag (str): Indicator LED status.
        """
        self.indicator_led = asset_tag

    def get_last_reset_time(self) -> str:
        """Get last reset time.

        Returns:
            str: Last reset time.
        """
        return self.last_reset_time

    def set_last_reset_time(self, last_reset_time: str) -> None:
        """Set last reset time.

        Args:
            last_reset_time (str): Last reset time.
        """
        self.last_reset_time = last_reset_time

    def get_location_indicator_active(self) -> bool:
        """Get location indicator active status.

        Returns:
            bool: Location indicator active status.
        """
        return self.location_indicator_active

    def set_location_indicator_active(self, location_indicator_active: bool) -> None:
        """Set location indicator active status.

        Args:
            location_indicator_active (bool): Location indicator active status.
        """
        self.location_indicator_active = location_indicator_active

    def get_name(self) -> str:
        """Get system name.

        Returns:
            str: System name.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Set system name.

        Args:
            name (str): System name.
        """
        self.name = name

    def get_part_number(self) -> str:
        """Get part number.

        Returns:
            str: Part number.
        """
        return self.part_number

    def set_part_number(self, part_number: str) -> None:
        """Set part number.

        Args:
            part_number (str): Part number.
        """
        self.part_number = part_number

    def get_sku(self) -> str:
        """Get SKU.

        Returns:
            str: SKU.
        """
        return self.sku

    def set_sku(self, sku: str) -> None:
        """Set SKU.

        Args:
            sku (str): SKU.
        """
        self.sku = sku

    def get_system_type(self) -> str:
        """Get system type.

        Returns:
            str: System type.
        """
        return self.system_type

    def set_system_type(self, system_type: str) -> None:
        """Set system type.

        Args:
            system_type (str): System type.
        """
        self.system_type = system_type

    def get_uuid(self) -> str:
        """Get UUID.

        Returns:
            str: UUID.
        """
        return self.uuid

    def set_uuid(self, uuid: str) -> None:
        """Set UUID.

        Args:
            uuid (str): UUID.
        """
        self.uuid = uuid

    def get_description(self) -> str:
        """Get description.

        Returns:
            str: Description.
        """
        return self.description

    def set_description(self, description: str) -> None:
        """Set description.

        Args:
            description (str): Description.
        """
        self.description = description

    def get_id(self) -> str:
        """Get ID.

        Returns:
            str: System ID.
        """
        return self.id

    def set_id(self, id: str) -> None:
        """Set ID.

        Args:
            id (str): System ID.
        """
        self.id = id

    def get_computer_system_reset(self) -> ComputerSystemReset:
        """Get computer_system_reset.

        Returns:
            ComputerSystemReset: ComputerSystemReset object.
        """
        return self.computer_system_reset

    def set_computer_system_reset(self, computer_system_reset: ComputerSystemReset) -> None:
        """Set computer_system_reset.

        Args:
            computer_system_reset (ComputerSystemReset): ComputerSystemReset object.
        """
        self.computer_system_reset = computer_system_reset

    def get_processor_summary(self) -> ProcessorSummary:
        """Get processor summary.

        Returns:
            ProcessorSummary: Processor summary object.
        """
        return self.processor_summary

    def set_processor_summary(self, processor_summary: ProcessorSummary) -> None:
        """Set processor summary.

        Args:
            processor_summary (ProcessorSummary): Processor summary object.
        """
        self.processor_summary = processor_summary

    def get_trusted_modules(self) -> list[TrustedModule]:
        """Get trusted modules.

        Returns:
            list[TrustedModule]: List of trusted module objects.
        """
        return self.trusted_modules

    def set_trusted_modules(self, trusted_modules: list[TrustedModule]) -> None:
        """Set trusted modules.

        Args:
            trusted_modules (list[TrustedModule]): List of trusted module objects.
        """
        self.trusted_modules = trusted_modules

    def get_pcie_devices(self) -> list:
        """Get PCIe devices.

        Returns:
            list: List of PCIe device references.
        """
        return self.pcie_devices

    def set_pcie_devices(self, pcie_devices: list) -> None:
        """Set PCIe devices.

        Args:
            pcie_devices (list): List of PCIe device references.
        """
        self.pcie_devices = pcie_devices

    def get_pcie_functions(self) -> list:
        """Get PCIe functions.

        Returns:
            list: List of PCIe function references.
        """
        return self.pcie_functions

    def set_pcie_functions(self, pcie_functions: list) -> None:
        """Set PCIe functions.

        Args:
            pcie_functions (list): List of PCIe function references.
        """
        self.pcie_functions = pcie_functions

    def generate_status(self, data: dict) -> Status:
        """
        Generates the status from the dict

        Args:
            data (dict): data to get status from

        Returns:
            Status: Status object.
        """
        status_data = data.get("Status", {})
        return Status(health=status_data.get("Health", ""), health_rollup=status_data.get("HealthRollup", ""), state=status_data.get("State", "")) if status_data else None

    def generate_boot(self, data: dict) -> Boot:
        """
        Generates the boot from the dict

        Args:
            data (dict): data to get the boot from

        Returns:
            Boot: Boot object.

        """
        boot_data = data.get("Boot", {})
        return Boot(boot_source_override_enabled=boot_data.get("BootSourceOverrideEnabled", ""), boot_source_override_target=boot_data.get("BootSourceOverrideTarget", ""), boot_order=boot_data.get("BootOrder", [])) if boot_data else None

    def generate_memory_summary(self, data: dict) -> MemorySummary | None:
        """
        Generates the memory summary

        Args:
            data (dict): the data to get the memory summary from

        Returns:
            MemorySummary | None: the memory summary

        """
        mem_data = data.get("MemorySummary", {})
        if mem_data:
            mem_status_data = mem_data.get("Status", {})
            mem_status = Status(health=mem_status_data.get("Health", ""), health_rollup=mem_status_data.get("HealthRollup", ""), state=mem_status_data.get("State", "")) if mem_status_data else None
            return MemorySummary(total_system_memory_gib=mem_data.get("TotalSystemMemoryGiB", 0), memory_mirroring=mem_data.get("MemoryMirroring", ""), status=mem_status)
        else:
            return None

    def generate_computer_system_reset(self, data: dict) -> ComputerSystemReset | None:
        """
        Generates the computer system reset

        Args:
           data (dict): data to get the computer system reset from

        Returns:
            ComputerSystemReset | None: the computer system reset

        """
        actions_data = data.get("Actions", {})
        if actions_data:
            reset_data = actions_data.get("#ComputerSystem.Reset", {})
            return ComputerSystemReset(reset_type_allowable_values=reset_data.get("ResetType@Redfish.AllowableValues"), target=reset_data.get("target")) if reset_data else None
        else:
            return None

    def generate_processor_summary(self, data: dict) -> ProcessorSummary | None:
        """
        Generates the processor summary

        Args:
            data (dict): data to get the processor summary from

        Returns:
            ProcessorSummary | None: the processor summary

        """
        proc_data = data.get("ProcessorSummary", {})
        if proc_data:
            proc_status_data = proc_data.get("Status", {})
            proc_status = Status(health=proc_status_data.get("Health", ""), health_rollup=proc_status_data.get("HealthRollup", ""), state=proc_status_data.get("State", "")) if proc_status_data else None
            return ProcessorSummary(core_count=proc_data.get("CoreCount", 0), count=proc_data.get("Count", 0), logical_processor_count=proc_data.get("LogicalProcessorCount", 0), model=proc_data.get("Model", ""), threading_enabled=proc_data.get("ThreadingEnabled", False), status=proc_status)
        else:
            return None

    def generate_trusted_modules(self, data: dict) -> list[TrustedModule]:
        """
        Generates the trusted modules

        Args:
            data (dict): data to get the trusted modules from

        Returns:
            list[TrustedModule]: the trusted modules

        """
        trusted_modules_list = []
        for tm_data in data.get("TrustedModules", []):
            tm_status_data = tm_data.get("Status", {})
            tm_status = Status("", "", tm_status_data.get("State", "")) if tm_status_data else None
            trusted_module = TrustedModule(firmware_version=tm_data.get("FirmwareVersion", ""), interface_type=tm_data.get("InterfaceType", ""), status=tm_status)
            trusted_modules_list.append(trusted_module)
        return trusted_modules_list

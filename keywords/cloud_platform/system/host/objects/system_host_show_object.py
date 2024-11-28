from keywords.cloud_platform.system.host.objects.host_capabilities_object import HostCapabilities


class SystemHostShowObject:
    """
    This class represents a Host Show as an object.
    This is typically a line in the system host-show output vertical table.
    """

    def __init__(self):
        self.action = None
        self.administrative = None
        self.apparmor = None
        self.availability = None
        self.bm_ip = None
        self.bm_type = None
        self.bm_username = None
        self.boot_device = None
        self.capabilities = None
        self.clock_synchronization = None
        self.config_applied = None
        self.config_status = None
        self.config_target = None
        self.console = None
        self.created_at = None
        self.cstates_available = None
        self.device_image_update = None
        self.hostname = None
        self.hw_settle = -1
        self.id = -1
        self.install_output = None
        self.install_state = None
        self.install_state_info = None
        self.inv_state = None
        self.invprovision = None
        self.iscsi_initiator_name = None
        self.location = None
        self.max_cpu_mhz_allowed = None
        self.max_cpu_mhz_configured = None
        self.mgmt_mac = None
        self.min_cpu_mhz_allowed = None
        self.nvme_host_id = None
        self.nvme_host_nqn = None
        self.operational = None
        self.personality = None
        self.reboot_needed = False
        self.reserved = False
        self.rootfs_device = None
        self.serialid = None
        self.software_load = None
        self.subfunction_avail = None
        self.subfunction_oper = None
        self.subfunctions = []
        self.sw_version = None
        self.task = None
        self.tboot = None
        self.ttys_dcd = False
        self.updated_at = None
        self.uptime = 0
        self.uuid = None
        self.vim_progress_status = None

    def set_action(self, action: str):
        """
        Setter for the action being executed in this host.
        """
        self.action = action

    def get_action(self) -> str:
        """
        Getter for this action being executed in this host.
        """
        return self.action

    def set_administrative(self, administrative: str):
        """
        Setter for the administrative status of the host.
        """
        self.administrative = administrative

    def get_administrative(self) -> str:
        """
        Getter for the administrative status of the host.
        """
        return self.administrative

    def set_apparmor(self, apparmor: str):
        """
        Setter for the AppArmor status of the host.
        """
        self.apparmor = apparmor

    def get_apparmor(self) -> str:
        """
        Getter for the AppArmor status of the host.
        """
        return self.apparmor

    def set_availability(self, availability: str):
        """
        Setter for the availability status of the host.
        """
        self.availability = availability

    def get_availability(self) -> str:
        """
        Getter for the availability status of the host.
        """
        return self.availability

    def set_bm_ip(self, bm_ip: str):
        """
        Setter for the BM (Baseboard Management) IP address.
        """
        self.bm_ip = bm_ip

    def get_bm_ip(self) -> str:
        """
        Getter for the BM (Baseboard Management) IP address.
        """
        return self.bm_ip

    def set_bm_type(self, bm_type: str):
        """
        Setter for the BM (Baseboard Management) type.
        """
        self.bm_type = bm_type

    def get_bm_type(self) -> str:
        """
        Getter for the BM (Baseboard Management) type.
        """
        return self.bm_type

    def set_bm_username(self, bm_username: str):
        """
        Setter for the BM (Baseboard Management) username.
        """
        self.bm_username = bm_username

    def get_bm_username(self) -> str:
        """
        Getter for the BM (Baseboard Management) username.
        """
        return self.bm_username

    def set_boot_device(self, boot_device: str):
        """
        Setter for the boot device path.
        """
        self.boot_device = boot_device

    def get_boot_device(self) -> str:
        """
        Getter for the boot device path.
        """
        return self.boot_device

    def set_capabilities(self, capabilities: HostCapabilities):
        """
        Setter for the capabilities of the host.
        """
        self.capabilities = capabilities

    def get_capabilities(self) -> HostCapabilities:
        """
        Getter for the capabilities of the host.
        """
        return self.capabilities

    def set_clock_synchronization(self, clock_synchronization: str):
        """
        Setter for the clock synchronization method.
        """
        self.clock_synchronization = clock_synchronization

    def get_clock_synchronization(self) -> str:
        """
        Getter for the clock synchronization method.
        """
        return self.clock_synchronization

    def set_config_applied(self, config_applied: str):
        """
        Setter for the configuration applied to the host.
        """
        self.config_applied = config_applied

    def get_config_applied(self) -> str:
        """
        Getter for the configuration applied to the host.
        """
        return self.config_applied

    def set_config_status(self, config_status: str):
        """
        Setter for the configuration status of the host.
        """
        self.config_status = config_status

    def get_config_status(self) -> str:
        """
        Getter for the configuration status of the host.
        """
        return self.config_status

    def set_config_target(self, config_target: str):
        """
        Setter for the target configuration of the host.
        Usually the same as config_applied when the configuration is successfully applied.
        """
        self.config_target = config_target

    def get_config_target(self) -> str:
        """
        Getter for the target configuration of the host.
        Usually the same as config_applied when the configuration is successfully applied.
        """
        return self.config_target

    def set_console(self, console: str):
        """
        Setter for the configuration of serial console used to access the host, such as 'ttyS0,115200'.
        """
        self.console = console

    def get_console(self) -> str:
        """
        Getter for the configuration of serial console used to access the host, such as 'ttyS0,115200'.
        """
        return self.console

    def set_created_at(self, created_at: str):
        """
        Setter for the creation timestamp of the host.
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for the creation timestamp of the host.
        """
        return self.created_at

    def set_cstates_available(self, cstates_available: str):
        """
        Setter for the available CPU energy economy states, such as C1, C1E, C6, POLL.
        """
        self.cstates_available = cstates_available

    def get_cstates_available(self) -> str:
        """
        Getter for the available CPU energy economy states, such as C1, C1E, C6, POLL.
        """
        return self.cstates_available

    def set_device_image_update(self, device_image_update: str):
        """
        Setter for the device image update status.
        """
        self.device_image_update = device_image_update

    def get_device_image_update(self) -> str:
        """
        Getter for the device image update status.
        """
        return self.device_image_update

    def set_hostname(self, hostname: str):
        """
        Setter for the hostname of the host.
        """
        self.hostname = hostname

    def get_hostname(self) -> str:
        """
        Getter for the hostname of the host.
        """
        return self.hostname

    def set_hw_settle(self, hw_settle: int):
        """
        Setter for the hardware settle time.
        """
        self.hw_settle = hw_settle

    def get_hw_settle(self) -> int:
        """
        Getter for the hardware settle time.
        """
        return self.hw_settle

    def set_id(self, id: int):
        """
        Setter for the ID of the host.
        """
        self.id = id

    def get_id(self) -> int:
        """
        Getter for the ID of the host.
        """
        return self.id

    def set_install_output(self, install_output: str):
        """
        Setter for the output method used during installation.
        'Graphical' indicates an installation with a graphical interface.
        """
        self.install_output = install_output

    def get_install_output(self) -> str:
        """
        Getter for the output method used during installation.
        'Graphical' indicates an installation with a graphical interface.
        """
        return self.install_output

    def set_install_state(self, install_state: str):
        """
        Setter for the current state of the host installation.
        'None' suggests that there is no installation in progress
        """
        self.install_state = install_state

    def get_install_state(self) -> str:
        """
        Getter for the current state of the host installation.
        'None' suggests that there is no installation in progress
        """
        return self.install_state

    def set_install_state_info(self, install_state_info: str):
        """
        Setter for additional installation state information.
        """
        self.install_state_info = install_state_info

    def get_install_state_info(self) -> str:
        """
        Getter for additional installation state information.
        """
        return self.install_state_info

    def set_inv_state(self, inv_state: str):
        """
        Setter for the inventory state of the host.
        """
        self.inv_state = inv_state

    def get_inv_state(self) -> str:
        """
        Getter for the inventory state of the host.
        """
        return self.inv_state

    def set_invprovision(self, invprovision: str):
        """
        Setter for the inventory provision status.
        """
        self.invprovision = invprovision

    def get_invprovision(self) -> str:
        """
        Getter for the inventory provision status.
        """
        return self.invprovision

    def set_iscsi_initiator_name(self, iscsi_initiator_name: str):
        """
        Setter for the iSCSI initiator name.
        """
        self.iscsi_initiator_name = iscsi_initiator_name

    def get_iscsi_initiator_name(self) -> str:
        """
        Getter for the iSCSI initiator name.
        """
        return self.iscsi_initiator_name

    def set_location(self, location: str):
        """
        Setter for the location of the host.
        """
        self.location = location

    def get_location(self) -> str:
        """
        Getter for the location of the host.
        """
        return self.location

    def set_max_cpu_mhz_allowed(self, max_cpu_mhz_allowed: str):
        """
        Setter for the maximum CPU MHz allowed.
        """
        self.max_cpu_mhz_allowed = max_cpu_mhz_allowed

    def get_max_cpu_mhz_allowed(self) -> str:
        """
        Getter for the maximum CPU MHz allowed.
        """
        return self.max_cpu_mhz_allowed

    def set_max_cpu_mhz_configured(self, max_cpu_mhz_configured: str):
        """
        Setter for the maximum CPU MHz configured.
        """
        self.max_cpu_mhz_configured = max_cpu_mhz_configured

    def get_max_cpu_mhz_configured(self) -> str:
        """
        Getter for the maximum CPU MHz configured.
        """
        return self.max_cpu_mhz_configured

    def set_mgmt_mac(self, mgmt_mac: str):
        """
        Setter for the management MAC address.
        """
        self.mgmt_mac = mgmt_mac

    def get_mgmt_mac(self) -> str:
        """
        Getter for the management MAC address.
        """
        return self.mgmt_mac

    def set_min_cpu_mhz_allowed(self, min_cpu_mhz_allowed: str):
        """
        Setter for the minimum CPU MHz allowed.
        """
        self.min_cpu_mhz_allowed = min_cpu_mhz_allowed

    def get_min_cpu_mhz_allowed(self) -> str:
        """
        Getter for the minimum CPU MHz allowed.
        """
        return self.min_cpu_mhz_allowed

    def set_nvme_host_id(self, nvme_host_id: str):
        """
        Setter for the NVMe host ID.
        """
        self.nvme_host_id = nvme_host_id

    def get_nvme_host_id(self) -> str:
        """
        Getter for the NVMe host ID.
        """
        return self.nvme_host_id

    def set_nvme_host_nqn(self, nvme_host_nqn: str):
        """
        Setter for the NVMe host NVMe Qualified Name (NQN).
        """
        self.nvme_host_nqn = nvme_host_nqn

    def get_nvme_host_nqn(self) -> str:
        """
        Getter for the NVMe host NVMe Qualified Name (NQN).
        """
        return self.nvme_host_nqn

    def set_operational(self, operational: str):
        """
        Setter for the operational status of the host.
        """
        self.operational = operational

    def get_operational(self) -> str:
        """
        Getter for the operational status of the host.
        """
        return self.operational

    def set_personality(self, personality: str):
        """
        Setter for the personality of the host.
        """
        self.personality = personality

    def get_personality(self) -> str:
        """
        Getter for the personality of the host.
        """
        return self.personality

    def set_reboot_needed(self, reboot_needed: bool):
        """
        Setter for the reboot needed flag.
        """
        self.reboot_needed = reboot_needed

    def get_reboot_needed(self) -> bool:
        """
        Getter for the reboot needed flag.
        """
        return self.reboot_needed

    def set_reserved(self, reserved: bool):
        """
        Getter for the host reserved for special operation or maintenance flag.
        """
        self.reserved = reserved

    def get_reserved(self) -> bool:
        """
        Getter for the host reserved for special operation or maintenance flag.
        """
        return self.reserved

    def set_rootfs_device(self, rootfs_device: str):
        """
        Setter for the root filesystem device path.
        """
        self.rootfs_device = rootfs_device

    def get_rootfs_device(self) -> str:
        """
        Getter for the root filesystem device path.
        """
        return self.rootfs_device

    def set_serialid(self, serialid: str):
        """
        Setter for the serial ID of the host.
        """
        self.serialid = serialid

    def get_serialid(self) -> str:
        """
        Getter for the serial ID of the host.
        """
        return self.serialid

    def set_software_load(self, software_load: str):
        """
        Setter for the software load version.
        """
        self.software_load = software_load

    def get_software_load(self) -> str:
        """
        Getter for the software load version.
        """
        return self.software_load

    def set_subfunction_avail(self, subfunction_avail: str):
        """
        Setter for the availability of subfunctions.
        """
        self.subfunction_avail = subfunction_avail

    def get_subfunction_avail(self) -> str:
        """
        Getter for the availability of subfunctions.
        """
        return self.subfunction_avail

    def set_subfunction_oper(self, subfunction_oper: str):
        """
        Setter for the operational status of subfunctions.
        """
        self.subfunction_oper = subfunction_oper

    def get_subfunction_oper(self) -> str:
        """
        Getter for the operational status of subfunctions.
        """
        return self.subfunction_oper

    def set_subfunctions(self, subfunctions: list[str]):
        """
        Setter for the list of subfunctions.
        """
        self.subfunctions = subfunctions

    def get_subfunctions(self) -> list[str]:
        """
        Getter for the list of subfunctions.
        """
        return self.subfunctions

    def set_sw_version(self, sw_version: str):
        """
        Setter for the software version.
        """
        self.sw_version = sw_version

    def get_sw_version(self) -> str:
        """
        Getter for the software version.
        """
        return self.sw_version

    def set_task(self, task: str):
        """
        Setter for the task associated with the host.
        """
        self.task = task

    def get_task(self) -> str:
        """
        Getter for the task associated with the host.
        """
        return self.task

    def set_tboot(self, tboot: str):
        """
        Setter for the Trusted Boot (tboot) information.
        """
        self.tboot = tboot

    def get_tboot(self) -> str:
        """
        Getter for the Trusted Boot (tboot) information.
        """
        return self.tboot

    def set_ttys_dcd(self, ttys_dcd: bool):
        """
        Setter for the ttys_dcd status.
        DCD pin configuration for TTY terminals. 'False' indicates that it is not enabled.
        """
        self.ttys_dcd = ttys_dcd

    def get_ttys_dcd(self) -> bool:
        """
        Getter for the ttys_dcd status.
        DCD pin configuration for TTY terminals. 'False' indicates that it is not enabled.
        """
        return self.ttys_dcd

    def set_updated_at(self, updated_at: str):
        """
        Setter for the last updated timestamp of the host.
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for the last updated timestamp of the host.
        """
        return self.updated_at

    def set_uptime(self, uptime: int):
        """
        Setter for the uptime of the host.
        """
        self.uptime = uptime

    def get_uptime(self) -> int:
        """
        Getter for the uptime of the host.
        """
        return self.uptime

    def set_uuid(self, uuid: str):
        """
        Setter for the UUID of the host.
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for the UUID of the host.
        """
        return self.uuid

    def set_vim_progress_status(self, vim_progress_status: str):
        """
        Setter for the VIM (Virtual Infrastructure Manager) progress status.
        """
        self.vim_progress_status = vim_progress_status

    def get_vim_progress_status(self) -> str:
        """
        Getter for the VIM (Virtual Infrastructure Manager) progress status.
        """
        return self.vim_progress_status

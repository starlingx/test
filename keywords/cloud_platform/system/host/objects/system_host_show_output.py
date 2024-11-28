import json5
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.system.host.objects.host_capabilities_object import HostCapabilities
from keywords.cloud_platform.system.host.objects.system_host_show_object import SystemHostShowObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser
from keywords.python.type_converter import TypeConverter


class SystemHostShowOutput:
    """
    This class parses the output of 'system host-show' command into an object of type SystemHostShowObject.
    """

    def __init__(self, system_host_show_output):
        """
        Constructor

        Args:
            system_host_show_output: output of 'system host-show' command as a list of strings.
        """

        if isinstance(system_host_show_output, RestResponse):  # came from REST and is already in dict form
            json_object = system_host_show_output.get_json_content()
            if 'ihosts' in json_object:
                hosts = json_object['ihosts']
            else:
                hosts = [json_object]
        else: # this came from a system command and must be parsed 
            system_vertical_table_parser = SystemVerticalTableParser(system_host_show_output)
            output_values = system_vertical_table_parser.get_output_values_dict()
            output_values = system_host_show_output
            hosts = [output_values]
        
        self.system_host_show_objects: list[SystemHostShowObject] = []
        for host in hosts:
            system_host_show_object = SystemHostShowObject()

            if 'action' in host:
                system_host_show_object.set_action(host['action'])

            if 'administrative' in host:
                system_host_show_object.set_administrative(host['administrative'])

            if 'apparmor' in host:
                system_host_show_object.set_apparmor(host['apparmor'])

            if 'availability' in host:
                system_host_show_object.set_availability(host['availability'])

            if 'bm_ip' in host:
                system_host_show_object.set_bm_ip(host['bm_ip'])

            if 'bm_type' in host:
                system_host_show_object.set_bm_type(host['bm_type'])

            if 'bm_username' in host:
                system_host_show_object.set_bm_username(host['bm_username'])

            if 'boot_device' in host:
                system_host_show_object.set_boot_device(host['boot_device'])

            if 'capabilities' in host:
                capabilities_dict = host['capabilities']
                # if this from system, we need to parse the string to a dict
                if not isinstance(system_host_show_output, RestResponse):
                    capabilities_dict = json5.loads(host['capabilities'])

                capabilities = HostCapabilities()
                if 'is_max_cpu_configurable' in capabilities_dict:
                    capabilities.set_is_max_cpu_configurable(capabilities_dict['is_max_cpu_configurable'])
                if 'mgmt_ipsec' in capabilities_dict:
                    capabilities.set_mgmt_ipsec(capabilities_dict['mgmt_ipsec'])
                if 'stor_function' in capabilities_dict:
                    capabilities.set_stor_function(capabilities_dict['stor_function'])
                if 'Personality' in capabilities_dict:
                    capabilities.set_personality(capabilities_dict['Personality'])
                    system_host_show_object.set_capabilities(capabilities)

            if 'clock_synchronization' in host:
                system_host_show_object.set_clock_synchronization(host['clock_synchronization'])

            if 'config_applied' in host:
                system_host_show_object.set_config_applied(host['config_applied'])

            if 'config_status' in host:
                system_host_show_object.set_config_status(host['config_status'])

            if 'config_target' in host:
                system_host_show_object.set_config_target(host['config_target'])

            if 'console' in host:
                system_host_show_object.set_console(host['console'])

            if 'created_at' in host:
                system_host_show_object.set_created_at(host['created_at'])

            if 'cstates_available' in host:
                system_host_show_object.set_cstates_available(host['cstates_available'])

            if 'device_image_update' in host:
                system_host_show_object.set_device_image_update(host['device_image_update'])

            if 'hostname' in host:
                system_host_show_object.set_hostname(host['hostname'])

            if 'hw_settle' in host:
                system_host_show_object.set_hw_settle(int(host['hw_settle']))

            if 'id' in host:
                system_host_show_object.set_id(int(host['id']))

            if 'install_output' in host:
                system_host_show_object.set_install_output(host['install_output'])

            if 'install_state' in host:
                system_host_show_object.set_install_state(host['install_state'])

            if 'install_state_info' in host:
                system_host_show_object.set_install_state_info(host['install_state_info'])

            if 'inv_state' in host:
                system_host_show_object.set_inv_state(host['inv_state'])

            if 'invprovision' in host:
                system_host_show_object.set_invprovision(host['invprovision'])

            if 'iscsi_initiator_name' in host:
                system_host_show_object.set_iscsi_initiator_name(host['iscsi_initiator_name'])

            if 'location' in host:
                system_host_show_object.set_location(host['location'])

            if 'max_cpu_mhz_allowed' in host:
                system_host_show_object.set_max_cpu_mhz_allowed(host['max_cpu_mhz_allowed'])

            if 'max_cpu_mhz_configured' in host:
                system_host_show_object.set_max_cpu_mhz_configured(host['max_cpu_mhz_configured'])

            if 'mgmt_mac' in host:
                system_host_show_object.set_mgmt_mac(host['mgmt_mac'])

            if 'min_cpu_mhz_allowed' in host:
                system_host_show_object.set_min_cpu_mhz_allowed(host['min_cpu_mhz_allowed'])

            if 'nvme_host_id' in host:
                system_host_show_object.set_nvme_host_id(host['nvme_host_id'])

            if 'nvme_host_nqn' in host:
                system_host_show_object.set_nvme_host_nqn(host['nvme_host_nqn'])

            if 'operational' in host:
                system_host_show_object.set_operational(host['operational'])

            if 'personality' in host:
                system_host_show_object.set_personality(host['personality'])

            if 'reboot_needed' in host:
                value = host['reboot_needed'] if isinstance(host['reboot_needed'], bool) else TypeConverter.str_to_bool(host['reboot_needed'])
                system_host_show_object.set_reboot_needed(value)

            if 'reserved' in host:
                value = host['reserved'] if isinstance(host['reserved'], bool) else TypeConverter.str_to_bool(host['reserved'])
                system_host_show_object.set_reserved(value)

            if 'rootfs_device' in host:
                system_host_show_object.set_rootfs_device(host['rootfs_device'])

            if 'serialid' in host:
                system_host_show_object.set_serialid(host['serialid'])

            if 'software_load' in host:
                system_host_show_object.set_software_load(host['software_load'])

            if 'subfunction_avail' in host:
                system_host_show_object.set_subfunction_avail(host['subfunction_avail'])

            if 'subfunction_oper' in host:
                system_host_show_object.set_subfunction_oper(host['subfunction_oper'])

            if 'subfunctions' in host:
                system_host_show_object.set_subfunctions(TypeConverter.parse_string_to_list(host['subfunctions']))

            if 'sw_version' in host:
                system_host_show_object.set_sw_version(host['sw_version'])

            if 'task' in host:
                system_host_show_object.set_task(host['task'])

            if 'tboot' in host:
                system_host_show_object.set_tboot(host['tboot'])

            if 'ttys_dcd' in host:
                value = host['ttys_dcd'] if isinstance(host['ttys_dcd'], bool) else TypeConverter.str_to_bool(host['ttys_dcd'])
                system_host_show_object.set_ttys_dcd(value)

            if 'updated_at' in host:
                system_host_show_object.set_updated_at(host['updated_at'])

            if 'uptime' in host:
                system_host_show_object.set_uptime(host['uptime'])

            if 'uuid' in host:
                system_host_show_object.set_uuid(host['uuid'])

            if 'vim_progress_status' in host:
                system_host_show_object.set_vim_progress_status(host['vim_progress_status'])
            self.system_host_show_objects.append(system_host_show_object)

    def _get_host_value(self, hostname: str=None):
        
        if hostname:
            hosts = list(filter(lambda system_show_object: system_show_object.get_hostname() == hostname, self.system_host_show_objects))
            if hosts:
                # can never be two
                return hosts[0]
            else:
                raise KeywordException(f"No host was found with the name: {hostname}")
        else:
            if len(self.system_host_show_objects) != 1:
                raise KeywordException("There was not exactly 1 host")
            else:
                # return the first one
                return self.system_host_show_objects[0] 


    def has_host_bmc_ipmi(self, hostname: str=None) -> bool:
        """
        This function will return True if bm_type of this host is 'ipmi'.

        Returns: True if bm_type of this host is 'ipmi', False otherwise.

        """
        system_host_show_object = self._get_host_value(hostname)
        return system_host_show_object.get_bm_type() == "ipmi"

    def has_host_bmc_redfish(self, hostname: str=None) -> bool:
        """
        This function will return True if bm_type of this host is 'redfish', False otherwise.

        Returns: True if bm_type of this host is 'redfish'.

        """
        system_host_show_object = self._get_host_value(hostname)
        return system_host_show_object.get_bm_type() == "redfish"

    def has_host_bmc_dynamic(self, hostname: str=None) -> bool:
        """
        This function will return True if bm_type of this host is 'dynamic', False otherwise.

        Returns: True if bm_type of this host is 'dynamic'.

        """
        system_host_show_object = self._get_host_value(hostname)
        return system_host_show_object.get_bm_type() == "dynamic"
    
    def get_host_id(self, hostname: str=None)-> int:
        """
        Gets the host id
        
        Args:
            hostname (): the name of the host

        Returns: the host id

        """
        system_host_show_object = self._get_host_value(hostname)
        return system_host_show_object.get_id()

    def get_system_host_show_object(self, hostname: str=None) -> SystemHostShowObject:
        """
        Gets the system host show object

        Args:
            hostname (): the name of the host

        Returns: the system host show object

        """
        return self._get_host_value(hostname)
    
    def get_all_system_host_show_objects(self) -> list[SystemHostShowObject]:
        """
        Gets all system host show objects

        Returns: list of system host show objects

        """
        return self.system_host_show_objects

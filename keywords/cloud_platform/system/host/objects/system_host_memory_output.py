from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.system.host.objects.system_host_memory_object import SystemHostMemoryObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostMemoryOutput:
    """
    This class parses the output of 'system host-memory-list' commands into a list of SystemHostMemoryObject
    """

    def __init__(self, system_host_memory_output):
        """
        Constructor

        Args:
            system_host_memory_output: String output of 'system host-memory-list' command
        """

        self.system_host_memory_list: list[SystemHostMemoryObject] = []

        if isinstance(system_host_memory_output, RestResponse):  # came from REST and is already in dict form
            json_object = system_host_memory_output.get_json_content()
            if 'imemorys' in json_object:
                memory = json_object['imemorys']
            else:
                memory = [json_object]
        else:
            system_table_parser = SystemTableParser(system_host_memory_output)
            memory = system_table_parser.get_output_values_list()

        for value in memory:

            system_host_memory_object = SystemHostMemoryObject()

            if 'processor' in value:
                system_host_memory_object.set_processor(int(value['processor']))
            elif 'numa_node' in value:
                system_host_memory_object.set_processor(int(value['numa_node']))

            if 'mem_total(MiB)' in value:
                system_host_memory_object.set_mem_total(int(value['mem_total(MiB)']))
            elif 'memtotal_mib' in value:  # value in REST
                system_host_memory_object.set_mem_total(int(value['memtotal_mib']))

            if 'mem_platform(MiB)' in value:
                if value['mem_platform(MiB)'] != "None":
                    system_host_memory_object.set_mem_platform(int(value['mem_platform(MiB)']))
            elif 'platform_reserved_mib' in value:  # value in REST
                if value['platform_reserved_mib'] != "None":
                    system_host_memory_object.set_mem_platform(int(value['platform_reserved_mib']))

            if 'mem_avail(MiB)' in value:
                system_host_memory_object.set_mem_avail(int(value['mem_avail(MiB)']))
            elif 'memavail_mib' in value:  # value in REST
                system_host_memory_object.set_mem_avail(int(value['memavail_mib']))

            if 'hugepages(hp)_configured' in value:
                system_host_memory_object.set_is_hugepages_configured(bool(value['hugepages(hp)_configured']))
            elif 'hugepages_configured' in value:  # value in REST
                system_host_memory_object.set_is_hugepages_configured(bool(value['hugepages_configured']))

            if 'vs_hp_size(MiB)' in value:
                if value['vs_hp_size(MiB)'] != 'None':
                    system_host_memory_object.set_vs_hp_size(int(value['vs_hp_size(MiB)']))
            elif 'vswitch_hugepages_size_mib' in value:
                if value['vswitch_hugepages_size_mib'] and value['vswitch_hugepages_size_mib'] != 'None':
                    system_host_memory_object.set_vs_hp_size(int(value['vswitch_hugepages_size_mib']))

            if 'vs_hp_total' in value:
                if value['vs_hp_total'] != 'None':
                    system_host_memory_object.set_vs_hp_total(int(value['vs_hp_total']))
            elif 'vswitch_hugepages_nr' in value:
                if value['vswitch_hugepages_nr'] and value['vswitch_hugepages_nr'] != 'None':
                    system_host_memory_object.set_vs_hp_total(int(value['vswitch_hugepages_nr']))

            if 'vs_hp_avail' in value:
                if value['vs_hp_avail'] != 'None':
                    system_host_memory_object.set_vs_hp_avail(int(value['vs_hp_avail']))
            elif 'vswitch_hugepages_avail' in value:
                if value['vswitch_hugepages_avail'] and value['vswitch_hugepages_avail'] != 'None':
                    system_host_memory_object.set_vs_hp_avail(int(value['vswitch_hugepages_avail']))

            if 'vs_hp_reqd' in value:
                if value['vs_hp_reqd'] != 'None':
                    system_host_memory_object.set_vs_hp_reqd(value['vs_hp_reqd'])
            elif 'vswitch_hugepages_reqd' in value:
                if value['vswitch_hugepages_reqd'] and value['vswitch_hugepages_reqd'] != 'None':
                    system_host_memory_object.set_vs_hp_reqd(value['vswitch_hugepages_reqd'])


            if 'app_total_4K' in value:
                if value['app_total_4K'] != 'None':
                    system_host_memory_object.set_app_total_4K(int(value['app_total_4K']))
            elif 'vm_hugepages_nr_4K' in value:
                if value['vm_hugepages_nr_4K'] and value['vm_hugepages_nr_4K'] != 'None':
                    system_host_memory_object.set_app_total_4K(int(value['vm_hugepages_nr_4K']))

            if 'app_hp_as_percentage' in value:
                system_host_memory_object.set_is_app_hp_as_percentage(bool(value['app_hp_as_percentage']))
            elif 'vm_pending_as_percentage' in value:
                system_host_memory_object.set_is_app_hp_as_percentage(bool(value['vm_pending_as_percentage']))

            if 'app_hp_total_2M' in value:
                if value['app_hp_total_2M'] != 'None':
                    system_host_memory_object.set_app_hp_total_2M(int(value['app_hp_total_2M']))
            elif 'vm_hugepages_nr_2M' in value:
                if value['vm_hugepages_nr_2M'] and value['vm_hugepages_nr_2M'] != 'None':
                    system_host_memory_object.set_app_hp_total_2M(int(value['vm_hugepages_nr_2M']))

            if 'app_hp_avail_2M' in value:
                if value['app_hp_avail_2M'] != 'None':
                    system_host_memory_object.set_app_hp_avail_2M(int(value['app_hp_avail_2M']))
            elif 'vm_hugepages_avail_2M' in value:
                if value['vm_hugepages_avail_2M'] and value['vm_hugepages_avail_2M'] != 'None':
                    system_host_memory_object.set_app_hp_avail_2M(int(value['vm_hugepages_avail_2M']))                

            if 'app_hp_pending_2M' in value:
                system_host_memory_object.set_app_hp_pending_2M(value['app_hp_pending_2M'])
            if 'vm_hugepages_nr_2M_pending' in value:
                system_host_memory_object.set_app_hp_pending_2M(value['vm_hugepages_nr_2M_pending'])

            if 'app_hp_total_1G' in value:
                if value['app_hp_total_1G'] != 'None':
                    system_host_memory_object.set_app_hp_total_1G(int(value['app_hp_total_1G']))
            elif 'vm_hugepages_nr_1G' in value:
                if value['vm_hugepages_nr_1G'] and value['vm_hugepages_nr_1G'] != 'None':
                    system_host_memory_object.set_app_hp_total_1G(int(value['vm_hugepages_nr_1G']))


            if 'app_hp_avail_1G' in value:
                if value['app_hp_avail_1G'] != 'None':
                    system_host_memory_object.set_app_hp_avail_1G(int(value['app_hp_avail_1G']))
            elif 'vm_hugepages_avail_1G' in value:
                if value['vm_hugepages_avail_1G'] and value['vm_hugepages_avail_1G'] != 'None':
                    system_host_memory_object.set_app_hp_avail_1G(int(value['vm_hugepages_avail_1G']))

            if 'app_hp_pending_1G' in value:
                system_host_memory_object.set_app_hp_pending_1G(value['app_hp_pending_1G'])
            elif 'vm_hugepages_nr_1G_pending' in value:
                system_host_memory_object.set_app_hp_pending_1G(value['vm_hugepages_nr_1G_pending'])

            if 'app_hp_use_1G' in value:
                system_host_memory_object.set_app_hp_use_1G(bool(value['app_hp_use_1G']))
            elif 'vm_hugepages_use_1G' in value:
                system_host_memory_object.set_app_hp_use_1G(bool(value['vm_hugepages_use_1G']))

            self.system_host_memory_list.append(system_host_memory_object)

    def has_page_size_1gb(self) -> bool:
        """
        This function will look for a processor in the list of processors that has memory HugePage enabled and HugePage
        size of 1 GB.

        Returns: True if this host has at least one processor with memory HugePage enabled and HugePage size of 1 GB.

        """

        return any(item.get_is_hugepages_configured() and item.get_vs_hp_size() == 1024 for item in self.system_host_memory_list)

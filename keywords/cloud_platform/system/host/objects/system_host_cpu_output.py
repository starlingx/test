from typing import List

from framework.exceptions.keyword_exception import KeywordException
from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.system.host.objects.system_host_cpu_object import SystemHostCPUObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostCPUOutput:
    """
    This class parses the output of 'system host-cpu-list' commands into a list of SystemHostCPUObject
    """

    def __init__(self, system_host_cpu_output):
        """
        Constructor

        Args:
            system_host_cpu_output: String output of 'system host-cpu-list' command
        """
        if isinstance(system_host_cpu_output, RestResponse):  # came from REST and is already in dict form
            json_object = system_host_cpu_output.get_json_content()
            if 'icpus' in json_object:
                cpus = json_object['icpus']
            else:
                cpus = [json_object]
        else: # this came from a system command and must be parsed 
        
            system_table_parser = SystemTableParser(system_host_cpu_output)
            cpus = system_table_parser.get_output_values_list()

        self.system_host_cpus: list[SystemHostCPUObject] = []

        for value in cpus:

            if 'uuid' not in value:
                raise KeywordException(f"The output line {value} was not valid because it is missing an 'uuid'.")

            system_host_cpu_object = SystemHostCPUObject(value['uuid'])

            if 'log_core' in value:
                system_host_cpu_object.set_log_core(int(value['log_core']))
            elif 'cpu' in value:  # value in Rest field
                system_host_cpu_object.set_log_core(int(value['cpu']))
            
            if 'processor' in value:
                system_host_cpu_object.set_processor(int(value['processor']))
            elif 'numa_node' in value:  # value in Rest field
                system_host_cpu_object.set_processor(int(value['numa_node']))

            if 'phy_core' in value:
                system_host_cpu_object.set_phy_core(int(value['phy_core']))
            if 'core' in value:  # value in Rest field
                system_host_cpu_object.set_phy_core(int(value['core']))

            if 'thread' in value:
                system_host_cpu_object.set_thread(int(value['thread']))

            if 'processor_model' in value:
                system_host_cpu_object.set_processor_model(value['processor_model'])
            elif 'cpu_model' in value:  # value in Rest field
                system_host_cpu_object.set_processor_model(value['cpu_model'])

            if 'assigned_function' in value:
                system_host_cpu_object.set_assigned_function(value['assigned_function'])
            elif 'allocated_function' in value:  # value in Rest field
                system_host_cpu_object.set_assigned_function(value['allocated_function'])

            self.system_host_cpus.append(system_host_cpu_object)

    def get_system_host_cpu_objects(self, processor_id: int = -1, assigned_function: str = None) -> List[SystemHostCPUObject]:
        """
        This function will return the list of SystemHostCPU objects associated with the specified processor_id (if specified)
        and matching the assigned_function (if specified).
        Args:
            processor_id (int): The ID (e.g. 0)  of the processor of interest. (-1 means any processor)
            assigned_function (optional): If we want to limit the CPUs returned to specific functions.

        Returns: List of SystemHostCPU objects matching the parameters.

        """

        target_system_host_cpu_objects = []
        for system_host_cpu in self.system_host_cpus:

            is_matching_processor_id = True
            if processor_id > -1:
                is_matching_processor_id = system_host_cpu.get_processor() == processor_id

            is_matching_assigned_function = True
            if assigned_function:
                is_matching_assigned_function = system_host_cpu.get_assigned_function() == assigned_function

            # If the system_host_cpu matches all the required criteria, add it to the target list.
            if is_matching_processor_id and is_matching_assigned_function:
                target_system_host_cpu_objects.append(system_host_cpu)

        return target_system_host_cpu_objects

    def get_system_host_cpu_from_log_core(self, log_core: int) -> SystemHostCPUObject:
        """
        This function will return the SystemHostCPUObject associated with the log_core specified.
        Args:
            log_core: Log Core index associated with the core of interest.

        Returns: SystemHostCPUObject

        """
        for system_host_cpu in self.system_host_cpus:
            if system_host_cpu.get_log_core() == log_core:
                return system_host_cpu

        raise ValueError(f"There is no system_host_cpu with the log_core {log_core}")

    def get_number_of_logical_cores(self, processor_id: int = -1, assigned_function: str = None) -> List[SystemHostCPUObject]:
        """
        This function will return the number of Logical Cores associated with the specified processor_id and matching the
        assigned_function (if specified).

        Args:
            processor_id (optional): The ID (e.g. 0)  of the processor of interest. (-1 means any processor)
            assigned_function (optional): If we want to limit the CPUs returned to specific functions.

        Returns: The number of Logical Cores matching the parameters.

        """

        target_system_host_cpu_objects = self.get_system_host_cpu_objects(processor_id, assigned_function)
        number_of_matching_logical_cores = len(target_system_host_cpu_objects)

        return number_of_matching_logical_cores

    def get_number_of_physical_cores(self, processor_id: int = -1, assigned_function: str = None) -> List[SystemHostCPUObject]:
        """
        This function will return the number of Physical Cores associated with the specified processor_id and matching the
        assigned_function (if specified). If the host is hyperthreaded, then each physical core will be mapped to two logical
        cores. (Entries in the CPU Output.)

        Args:
            processor_id (optional): The ID (e.g. 0)  of the processor of interest. (-1 means any processor)
            assigned_function (optional): If we want to limit the CPUs returned to specific functions.

        Returns: The number of Physical Cores matching the parameters.

        """

        target_system_host_cpu_objects = self.get_system_host_cpu_objects(processor_id, assigned_function)
        number_of_matching_logical_cores = len(target_system_host_cpu_objects)
        number_of_matching_physical_cores = number_of_matching_logical_cores
        if self.is_host_hyperthreaded():
            number_of_matching_physical_cores = int(number_of_matching_physical_cores / 2)

        return number_of_matching_physical_cores

    def is_host_hyperthreaded(self):
        """
        This function will find the list of Thread IDs associated with this host.
        If there is multiple Threads in use, then the host is hyperthreaded.

        Returns: True if there are multiple different Threads associated with this host.

        """

        distinct_thread_ids = set([system_host_cpu.get_thread() for system_host_cpu in self.system_host_cpus])
        is_hyperthreaded = len(distinct_thread_ids) > 1
        return is_hyperthreaded

    def get_processor_count(self) -> int:
        """
        This function will find the major CPU index in the CPU information list associated with this host and then adds
        one to determine the number of CPUs in this host, since the CPU index starts from zero.

        Returns: The number of CPUs in this host.

        """
        return max([item.processor for item in self.system_host_cpus]) + 1

    def has_minimum_number_processors(self, min_num_processors) -> bool:
        """
        This function verifies if this host has at least <min_num_processors> CPUs.

        Returns: True if this host has at least <min_num_processors> CPUs, False otherwise.

        """
        return self.get_processor_count() >= min_num_processors

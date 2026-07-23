from typing import List

from framework.exceptions.keyword_exception import KeywordException
from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.system.host.objects.system_host_cpu_object import SystemHostCPUObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostCPUOutput:
    """
    This class parses the output of 'system host-cpu-list' commands into a list of SystemHostCPUObject
    """

    def __init__(self, system_host_cpu_output: str):
        """
        Constructor

        Args:
            system_host_cpu_output(str): String output of 'system host-cpu-list' command

        Raises:
            KeywordException: on error
        """
        if isinstance(system_host_cpu_output, RestResponse):  # came from REST and is already in dict form
            json_object = system_host_cpu_output.get_json_content()
            if "icpus" in json_object:
                cpus = json_object["icpus"]
            else:
                cpus = [json_object]
        else:  # this came from a system command and must be parsed

            system_table_parser = SystemTableParser(system_host_cpu_output)
            cpus = system_table_parser.get_output_values_list()

        self.system_host_cpus: list[SystemHostCPUObject] = []

        for value in cpus:

            if "uuid" not in value:
                raise KeywordException(f"The output line {value} was not valid because it is missing an 'uuid'.")

            system_host_cpu_object = SystemHostCPUObject(value["uuid"])

            if "log_core" in value:
                system_host_cpu_object.set_log_core(int(value["log_core"]))
            elif "cpu" in value:  # value in Rest field
                system_host_cpu_object.set_log_core(int(value["cpu"]))

            if "processor" in value:
                system_host_cpu_object.set_processor(int(value["processor"]))
            elif "numa_node" in value:  # value in Rest field
                system_host_cpu_object.set_processor(int(value["numa_node"]))

            if "phy_core" in value:
                system_host_cpu_object.set_phy_core(int(value["phy_core"]))
            if "core" in value:  # value in Rest field
                system_host_cpu_object.set_phy_core(int(value["core"]))

            if "thread" in value:
                system_host_cpu_object.set_thread(int(value["thread"]))

            if "processor_model" in value:
                system_host_cpu_object.set_processor_model(value["processor_model"])
            elif "cpu_model" in value:  # value in Rest field
                system_host_cpu_object.set_processor_model(value["cpu_model"])

            if "assigned_function" in value:
                system_host_cpu_object.set_assigned_function(value["assigned_function"])
            elif "allocated_function" in value:  # value in Rest field
                system_host_cpu_object.set_assigned_function(value["allocated_function"])

            self.system_host_cpus.append(system_host_cpu_object)

    def get_system_host_cpu_objects(self, processor_id: int = -1, assigned_function: str = None) -> List[SystemHostCPUObject]:
        """
        This function will return the list of SystemHostCPU objects matching the specified parmeters.

        Args:
            processor_id (int): The ID (e.g. 0)  of the processor of interest. (-1 means any processor)
            assigned_function (str): If we want to limit the CPUs returned to specific functions.

        Returns:
            List[SystemHostCPUObject]: List of SystemHostCPU objects matching the parameters.

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
            log_core(int): Log Core index associated with the core of interest.

        Returns:
            SystemHostCPUObject: the SystemHostCPUObject

        Raises:
            ValueError: on parsing error

        """
        for system_host_cpu in self.system_host_cpus:
            if system_host_cpu.get_log_core() == log_core:
                return system_host_cpu

        raise ValueError(f"There is no system_host_cpu with the log_core {log_core}")

    def get_number_of_logical_cores(self, processor_id: int = -1, assigned_function: str = None) -> List[SystemHostCPUObject]:
        """
        This function will return the number of Logical Cores associated with the specified processor_id.

        Args:
            processor_id (int): The ID (e.g. 0)  of the processor of interest. (-1 means any processor)
            assigned_function (str): If we want to limit the CPUs returned to specific functions.

        Returns:
            List[SystemHostCPUObject]: The number of Logical Cores matching the parameters.

        """
        target_system_host_cpu_objects = self.get_system_host_cpu_objects(processor_id, assigned_function)
        number_of_matching_logical_cores = len(target_system_host_cpu_objects)

        return number_of_matching_logical_cores

    def get_number_of_physical_cores(self, processor_id: int = -1, assigned_function: str = None) -> List[SystemHostCPUObject]:
        """
        This function will return the number of Physical Cores.

        This function will the number of Physical Cores return associated with the specified processor_id and matching the
        assigned_function (if specified). If the host is hyperthreaded, then each physical core will be mapped to two logical
        cores. (Entries in the CPU Output.)

        Args:
            processor_id (int): The ID (e.g. 0)  of the processor of interest. (-1 means any processor)
            assigned_function (str): If we want to limit the CPUs returned to specific functions.

        Returns:
            List[SystemHostCPUObject]: The number of Physical Cores matching the parameters.

        """
        target_system_host_cpu_objects = self.get_system_host_cpu_objects(processor_id, assigned_function)
        number_of_matching_logical_cores = len(target_system_host_cpu_objects)
        number_of_matching_physical_cores = number_of_matching_logical_cores
        if self.is_host_hyperthreaded():
            number_of_matching_physical_cores = int(number_of_matching_physical_cores / 2)

        return number_of_matching_physical_cores

    def is_host_hyperthreaded(self) -> bool:
        """
        This function will find the list of Thread IDs associated with this host.

        If there is multiple Threads in use, then the host is hyperthreaded.

        Returns:
            bool: True if there are multiple different Threads associated with this host.

        """
        distinct_thread_ids = set([system_host_cpu.get_thread() for system_host_cpu in self.system_host_cpus])
        is_hyperthreaded = len(distinct_thread_ids) > 1
        return is_hyperthreaded

    def get_processor_count(self) -> int:
        """
        This function will find the major CPU index in the CPU information list.

        This function will find the major CPU index in the CPU information list associated with this host and then adds
        one to determine the number of CPUs in this host, since the CPU index starts from zero.

        Returns: The number of CPUs in this host.

        """
        if self.system_host_cpus:
            return max([item.processor for item in self.system_host_cpus]) + 1

        return 0

    def has_minimum_number_processors(self, min_num_processors) -> bool:
        """
        This function verifies if this host has at least <min_num_processors> CPUs.

        Returns: True if this host has at least <min_num_processors> CPUs, False otherwise.

        """
        return self.get_processor_count() >= min_num_processors

    def get_log_cores_for_assigned_function(self, assigned_function: str) -> set:
        """
        Get the set of logical core IDs for CPUs assigned to a specific function.

        Args:
            assigned_function (str): The function to filter by (e.g. 'Application-isolated').

        Returns:
            set: set of logical core IDs assigned to the specified function.
        """
        return {cpu.get_log_core() for cpu in self.get_system_host_cpu_objects(assigned_function=assigned_function)}

    def get_number_of_paired_cores(self, cpuset: set) -> int:
        """
        Count the number of CPUs in the cpuset that share a physical core with another CPU in the cpuset.

        On a hyperthreaded system, each physical core has multiple logical CPUs (siblings).
        This function counts how many CPUs in the given cpuset have at least one sibling
        also present in the cpuset.

        Args:
            cpuset (set): set of logical CPU IDs to analyze.

        Returns:
            int: count of CPUs that have at least one sibling also in the cpuset.

        Example:
            Given cpuset {0, 1, 4} where:
            - CPU 0 and CPU 16 share physical core 0
            - CPU 1 and CPU 17 share physical core 1
            - CPU 4 and CPU 20 share physical core 4

            Result: 0 (none of the CPUs have their HT sibling in the cpuset)

            Given cpuset {0, 16, 1, 17} where:
            - CPU 0 and CPU 16 share physical core 0
            - CPU 1 and CPU 17 share physical core 1

            Result: 4 (all CPUs are paired: 0-16 and 1-17)
        """
        paired = 0
        for cpu_id in sorted(cpuset):
            # Get the CPU object for this logical CPU ID
            cpu = self.get_system_host_cpu_from_log_core(cpu_id)

            # Find all logical CPUs that share the same physical core (siblings)
            siblings = {c.get_log_core() for c in self.get_system_host_cpu_objects(processor_id=cpu.get_processor()) if c.get_phy_core() == cpu.get_phy_core()}

            # If more than one sibling is in the cpuset, this CPU is paired
            if len(cpuset.intersection(siblings)) > 1:
                paired += 1
        return paired

    def get_number_of_singleton_cores(self, cpuset: set) -> int:
        """
        Count the number of CPUs in the cpuset whose HT sibling is not in the cpuset.

        On a hyperthreaded system, each physical core has multiple logical CPUs (siblings).
        This function counts how many CPUs in the given cpuset do NOT have any sibling
        also present in the cpuset (i.e., they are alone without their HT pair).

        Args:
            cpuset (set): set of logical CPU IDs to analyze.

        Returns:
            int: count of CPUs whose physical core sibling is not in the cpuset.

        Example:
            Given cpuset {0, 1, 4} where:
            - CPU 0 and CPU 16 share physical core 0
            - CPU 1 and CPU 17 share physical core 1
            - CPU 4 and CPU 20 share physical core 4

            Result: 3 (all CPUs are singletons since none have their HT sibling in the cpuset)

            Given cpuset {0, 16, 1} where:
            - CPU 0 and CPU 16 share physical core 0
            - CPU 1 and CPU 17 share physical core 1

            Result: 1 (CPU 1 is singleton, CPUs 0 and 16 are paired)
        """
        singletons = 0
        for cpu_id in sorted(cpuset):
            # Get the CPU object for this logical CPU ID
            cpu = self.get_system_host_cpu_from_log_core(cpu_id)

            # Find all logical CPUs that share the same physical core (siblings)
            siblings = {c.get_log_core() for c in self.get_system_host_cpu_objects(processor_id=cpu.get_processor()) if c.get_phy_core() == cpu.get_phy_core()}

            # If only one sibling is in the cpuset, this CPU is a singleton
            if len(cpuset.intersection(siblings)) == 1:
                singletons += 1
        return singletons

    def get_function_count(self, assigned_function: str) -> int:
        """
        Count the number of CPUs assigned to a specific function.

        Args:
            assigned_function (str): The name of the function to filter CPUs by.
                                     The comparison is case-insensitive.

        Returns:
            int: The total number of CPUs where `assigned_function` matches
                 the given function name.
        """
        return sum(1 for item in self.system_host_cpus if item.assigned_function.lower() == assigned_function.lower())

    def get_thread_count(self) -> int:
        """Return the number of distinct thread IDs across all CPUs.

        On a hyperthreaded host each physical core exposes two logical threads
        (thread 0 and thread 1). This count is therefore 1 on a non-HT host
        and 2 on a hyperthreaded host.

        Returns:
            int: Number of distinct thread IDs.
        """
        return len({c.get_thread() for c in self.system_host_cpus})

    def get_cpu_ids_as_range_string(self, assigned_function: str = None, processor_id: int = -1) -> str:
        """Get logical CPU IDs for a given function as a compact range string.

        Combines :meth:`get_system_host_cpu_objects` filtering with
        :meth:`normalize_cpu_list` formatting so callers can obtain a
        CPU affinity string in a single call.

        Args:
            assigned_function (str): Filter by assigned function
                (e.g. ``'Application-isolated'``). ``None`` returns all CPUs.
            processor_id (int): Filter by processor/NUMA node. ``-1`` returns
                CPUs from all processors.

        Returns:
            str: Compact range string, e.g. ``'2-5,8,10-12'``.
        """
        cpus = [c.get_log_core() for c in self.get_system_host_cpu_objects(processor_id=processor_id, assigned_function=assigned_function)]
        return self.normalize_cpu_list(cpus)

    @staticmethod
    def normalize_cpu_list(cpus: list) -> str:
        """Convert a list of CPU IDs to a compact range string.

        Consecutive IDs are collapsed into ``lo-hi`` ranges only when the
        span is 3 or more (e.g. ``[2,3,4]`` → ``'2-4'``); shorter spans are
        left as comma-separated values (e.g. ``[2,3]`` → ``'2,3'``).

        Args:
            cpus (list): List of integer CPU IDs.  Duplicates are removed and
                the list is sorted before processing.

        Returns:
            str: Compact range string, e.g. ``'0,2-5,8,10-12'``, or ``''``
                if *cpus* is empty.
        """
        if not cpus:
            return ""
        if len(cpus) < 3:
            return ",".join(str(c) for c in sorted(set(cpus)))
        unique = sorted(set(cpus))
        ranges = []
        beg = prv = unique[0]
        for c in unique[1:]:
            if c > prv + 1:
                ranges.append((beg, prv))
                beg = c
            prv = c
        ranges.append((beg, unique[-1]))
        parts = []
        for lo, hi in ranges:
            if hi < lo + 3:
                parts.append(",".join(str(n) for n in range(lo, hi + 1)))
            else:
                parts.append(f"{lo}-{hi}")
        return ",".join(parts)

    @staticmethod
    def calculate_range_length(cores_range: str) -> int:
        """Count the number of CPUs described by a range string.

        Parses a string like ``'2-15,16-20,25'`` and returns the total
        number of CPU IDs it represents (``14 + 5 + 1 = 20`` in this
        example).

        Args:
            cores_range (str): CPU range string using commas and hyphens,
                e.g. ``'0-3,5,8-11'``.

        Returns:
            int: Total number of CPU IDs represented by the range string.
        """
        total = 0
        for part in cores_range.split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = part.split("-", 1)
                total += int(hi) - int(lo) + 1
            else:
                total += 1
        return total

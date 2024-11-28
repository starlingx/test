import json5
from keywords.cloud_platform.system.host.objects.host_capabilities_object import HostCapabilities


class SystemHostObject:
    """
    Class to hold attributes of a system host as returned by system host list command
    """

    def __init__(
        self,
        id: int,
        host_name: str,
        personality: str,
        administrative: str,
        operational: str,
        availability: str,
    ):
        self.id = id
        self.host_name = host_name
        self.personality = personality
        self.administrative = administrative
        self.operational = operational
        self.availability = availability
        self.capabilities: HostCapabilities = None
        self.uptime: int = 0
        self.sub_functions: [str] = []
        self.bm_ip = None
        self.bm_username = None

    def get_id(self) -> int:
        """
        Getter for id
        Returns: the id

        """
        return self.id

    def get_host_name(self) -> str:
        """
        Getter for host name
        Returns: the name of the host

        """
        return self.host_name

    def get_personality(self) -> str:
        """
        Getter for personality
        Returns: the personality

        """
        return self.personality

    def get_administrative(self) -> str:
        """
        Getter for administrative
        Returns: the administrative value

        """
        return self.administrative

    def get_operational(self) -> str:
        """
        Getter for operational
        Returns: operational

        """
        return self.operational

    def get_availability(self) -> str:
        """
        Getter for availability
        Returns: availability

        """
        return self.availability

    def set_capabilities(self, capabilities):
        """
        Setter for host capabilities
        Args:
            capabilities (): the string of capabilities from the system host-list command (json format)

        Returns:

        """
        # sometimes capabilities are set to None and this will break the json format
        if capabilities.__contains__('None'):
            capabilities = capabilities.replace("None", '"None"')
        json_output = json5.loads(capabilities)

        host_capability = HostCapabilities()
        if 'is_max_cpu_configurable' in json_output:
            host_capability.set_is_max_cpu_configurable(json_output['is_max_cpu_configurable'])
        if 'min_cpu_mhz_allowed' in json_output:
            host_capability.set_min_cpu_mhz_allowed(json_output['min_cpu_mhz_allowed'])
        if 'max_cpu_mhz_allowed' in json_output:
            host_capability.set_max_cpu_mhz_allowed(json_output['max_cpu_mhz_allowed'])
        if 'cstates_available' in json_output:
            host_capability.set_cstates_available(json_output['cstates_available'])
        if 'stor_function' in json_output:
            host_capability.set_stor_function(json_output['stor_function'])
        if 'Personality' in json_output:
            host_capability.set_personality(json_output['Personality'])

        self.capabilities = host_capability

    def get_capabilities(self) -> HostCapabilities:
        """
        Getter for capabilities
        Returns:

        """
        return self.capabilities

    def set_uptime(self, uptime: int):
        """
        Setter for uptime
        Args:
            uptime (): the uptime

        Returns:

        """
        self.uptime = uptime

    def get_uptime(self) -> int:
        """
        Getter for uptime
        Returns:

        """
        return self.uptime

    def set_sub_functions(self, sub_functions: [str]):
        """
        Set the sub functions
        Args:
            sub_functions (): the list of sub functions

        Returns:

        """
        self.sub_functions = sub_functions

    def get_sub_functions(self) -> [str]:
        """
        Getter for subfunctions
        Returns:

        """
        return self.sub_functions

    def has_sub_function(self, sub_function: str) -> bool:
        """
        Returns true if this host has sub_function
        Args:
            sub_function (): the sub function

        Returns:

        """
        return sub_function in self.sub_functions

    def set_bm_ip(self, bm_ip: str):
        """
        Setter for bm ip
        Args:
            bm_ip (): the bm ip

        Returns:

        """
        self.bm_ip = bm_ip

    def get_bm_ip(self) -> str:
        """
        Getter for bm ip
        Returns:

        """
        return self.bm_ip

    def set_bm_username(self, bm_username):
        """
        Setter for bm username
        Args:
            bm_username (): the bm username

        Returns:

        """
        self.bm_username = bm_username

    def get_bm_username(self) -> str:
        """
        Getter for bm username
        Returns:

        """
        return self.bm_username

    def is_host_healthy(self) -> bool:
        """
        Checks if the host has availability==available, administrative=unlocked and operational==enabled
        Returns: true if the host has availability==available, administrative=unlocked and operational==enabled

        """
        return self.get_availability() == 'available' and self.get_administrative() == 'unlocked' and self.get_operational() == 'enabled'

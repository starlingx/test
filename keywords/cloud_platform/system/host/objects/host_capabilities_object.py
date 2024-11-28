class HostCapabilities:
    """
    Class for host capabilities
    """

    def __init__(self):
        self.is_max_cpu_configurable = None
        self.min_cpu_mhz_allowed = None
        self.max_cpu_mhz_allowed = None
        self.cstates_available = None
        self.stor_function = None
        self.personality = None
        self.mgmt_ipsec = None

    def set_is_max_cpu_configurable(self, is_max_cpu_configurable: str):
        """
        Setter for is_max_cpu_configurable
        Args:
            is_max_cpu_configurable ():

        Returns:

        """
        self.is_max_cpu_configurable = is_max_cpu_configurable

    def get_is_max_cpu_configurable(self) -> str:
        """
        Getter for is max cpu configurable
        Returns:

        """
        return self.is_max_cpu_configurable

    def set_min_cpu_mhz_allowed(self, min_cpu_mhz_allowed: int):
        """
        Setter for min_cpu_mhz_allowed
        Args:
            min_cpu_mhz_allowed:

        Returns:

        """
        self.min_cpu_mhz_allowed = min_cpu_mhz_allowed

    def get_min_cpu_mhz_allowed(self) -> int:
        """
        Getter for min cpu mhz allowed
        Returns:

        """
        return self.min_cpu_mhz_allowed

    def set_max_cpu_mhz_allowed(self, max_cpu_mhz_allowed: int):
        """
        Setter for max_cpu_mhz_allowed
        Args:
            max_cpu_mhz_allowed:

        Returns:

        """
        self.max_cpu_mhz_allowed = max_cpu_mhz_allowed

    def get_max_cpu_mhz_allowed(self) -> int:
        """
        Getter for Max cpu mhz allowed
        Returns:

        """
        return self.max_cpu_mhz_allowed

    def set_cstates_available(self, cstates_available: str):
        """
        Setter for cstates_available
        Args:
            cstates_available:

        Returns:

        """
        self.cstates_available = cstates_available

    def get_cstates_available(self) -> str:
        """
        Getter for cstates available
        Returns:

        """
        return self.cstates_available

    def set_stor_function(self, stor_function):
        """
        Setter for stor function
        Args:
            stor_function ():

        Returns:

        """
        self.stor_function = stor_function

    def get_stor_function(self) -> str:
        """
        Getter for stor function
        Returns:

        """
        return self.stor_function

    def set_personality(self, personality: str):
        """
        Setter for personality
        Args:
            personality (): the personality

        Returns:

        """
        self.personality = personality

    def get_personality(self) -> str:
        """
        Getter for personality
        Returns:

        """
        return self.personality

    def set_mgmt_ipsec(self, mgmt_ipsec: str):
        """
        Setter for mgmt_ipsec, IPsec status for the management interface.
        Args:
            mgmt_ipsec (str):

        Returns:

        """
        self.mgmt_ipsec = mgmt_ipsec

    def get_mgmt_ipsec(self) -> str:
        """
        Getter for mgmt_ipsec, IPsec status for the management interface.
        Returns:

        """
        return self.mgmt_ipsec

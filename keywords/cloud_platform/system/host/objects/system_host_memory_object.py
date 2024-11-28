class SystemHostMemoryObject:
    """
    This class represents a Host Memory as an object.
    This is typically a line in the system host-memory-list output table.
    """

    def __init__(self):
        self.processor: int = -1
        self.mem_total: int = -1
        self.mem_platform: int = -1
        self.mem_avail: int = -1
        self.is_hugepages_configured: bool = False
        self.vs_hp_size: int = -1
        self.vs_hp_total: int = -1
        self.vs_hp_avail: int = -1
        self.vs_hp_reqd: int = -1
        self.app_total_4K: int = -1
        self.is_app_hp_as_percentage: bool = False
        self.app_hp_total_2M: int = -1
        self.app_hp_avail_2M: int = -1
        self.app_hp_pending_2M: int = -1
        self.app_hp_total_1G: int = -1
        self.app_hp_avail_1G: int = -1
        self.app_hp_pending_1G: int = -1
        self.app_hp_use_1G: bool = False

    def set_processor(self, processor: int) -> None:
        """
        Setter for processor
        Args:
            processor:
        """
        self.processor = processor

    def get_processor(self) -> int:
        """
        Getter for processor
        """
        return self.processor

    def set_mem_total(self, mem_total: int) -> None:
        """
        Setter for mem_total
        Args:
            mem_total:
        """
        self.mem_total = mem_total

    def get_mem_total(self) -> int:
        """
        Getter for mem_total
        """
        return self.mem_total

    def set_mem_platform(self, mem_platform: int) -> None:
        """
        Setter for mem_platform
        Args:
            mem_platform:
        """
        self.mem_platform = mem_platform

    def get_mem_platform(self) -> int:
        """
        Getter for mem_platform
        """
        return self.mem_platform

    def set_mem_avail(self, mem_avail: int) -> None:
        """
        Setter for mem_avail
        Args:
            mem_avail:
        """
        self.mem_avail = mem_avail

    def get_mem_avail(self) -> int:
        """
        Getter for mem_avail
        """
        return self.mem_avail

    def set_is_hugepages_configured(self, is_hugepages_configured: bool) -> None:
        """
        Setter for is_hugepages_configured
        Args:
            is_hugepages_configured:
        """
        self.is_hugepages_configured = is_hugepages_configured

    def get_is_hugepages_configured(self) -> bool:
        """
        Getter for is_hugepages_configured
        """
        return self.is_hugepages_configured

    def set_vs_hp_size(self, vs_hp_size: int) -> None:
        """
        Setter for vs_hp_size
        Args:
            vs_hp_size:
        """
        self.vs_hp_size = vs_hp_size

    def get_vs_hp_size(self) -> int:
        """
        Getter for vs_hp_size
        """
        return self.vs_hp_size

    def set_vs_hp_total(self, vs_hp_total: int) -> None:
        """
        Setter for vs_hp_total
        Args:
            vs_hp_total:
        """
        self.vs_hp_total = vs_hp_total

    def get_vs_hp_total(self) -> int:
        """
        Getter for vs_hp_total
        """
        return self.vs_hp_total

    def set_vs_hp_avail(self, vs_hp_avail: int) -> None:
        """
        Setter for vs_hp_avail
        Args:
            vs_hp_avail:
        """
        self.vs_hp_avail = vs_hp_avail

    def get_vs_hp_avail(self) -> int:
        """
        Getter for vs_hp_avail
        """
        return self.vs_hp_avail

    def set_vs_hp_reqd(self, vs_hp_reqd: int) -> None:
        """
        Setter for vs_hp_reqd
        Args:
            vs_hp_reqd:
        """
        self.vs_hp_reqd = vs_hp_reqd

    def get_vs_hp_reqd(self) -> int:
        """
        Getter for vs_hp_reqd
        """
        return self.vs_hp_reqd

    def set_app_total_4K(self, app_total_4K: int) -> None:
        """
        Setter for app_total_4K
        Args:
            app_total_4K:
        """
        self.app_total_4K = app_total_4K

    def get_app_total_4K(self) -> int:
        """
        Getter for app_total_4K
        """
        return self.app_total_4K

    def set_is_app_hp_as_percentage(self, is_app_hp_as_percentage: bool) -> None:
        """
        Setter for is_app_hp_as_percentage
        Args:
            is_app_hp_as_percentage:
        """
        self.is_app_hp_as_percentage = is_app_hp_as_percentage

    def get_is_app_hp_as_percentage(self) -> bool:
        """
        Getter for is_app_hp_as_percentage
        """
        return self.is_app_hp_as_percentage

    def set_app_hp_total_2M(self, app_hp_total_2M: int) -> None:
        """
        Setter for app_hp_total_2M
        Args:
            app_hp_total_2M:
        """
        self.app_hp_total_2M = app_hp_total_2M

    def get_app_hp_total_2M(self) -> int:
        """
        Getter for app_hp_total_2M
        """
        return self.app_hp_total_2M

    def set_app_hp_avail_2M(self, app_hp_avail_2M: int) -> None:
        """
        Setter for app_hp_avail_2M
        Args:
            app_hp_avail_2M:
        """
        self.app_hp_avail_2M = app_hp_avail_2M

    def get_app_hp_avail_2M(self) -> int:
        """
        Getter for app_hp_avail_2M
        """
        return self.app_hp_avail_2M

    def set_app_hp_pending_2M(self, app_hp_pending_2M: int) -> None:
        """
        Setter for app_hp_pending_2M
        Args:
            app_hp_pending_2M:
        """
        self.app_hp_pending_2M = app_hp_pending_2M

    def get_app_hp_pending_2M(self) -> int:
        """
        Getter for app_hp_pending_2M
        """
        return self.app_hp_pending_2M

    def set_app_hp_total_1G(self, app_hp_total_1G: int) -> None:
        """
        Setter for app_hp_total_1G
        Args:
            app_hp_total_1G:
        """
        self.app_hp_total_1G = app_hp_total_1G

    def get_app_hp_total_1G(self) -> int:
        """
        Getter for app_hp_total_1G
        """
        return self.app_hp_total_1G

    def set_app_hp_avail_1G(self, app_hp_avail_1G: int) -> None:
        """
        Setter for app_hp_avail_1G
        Args:
            app_hp_avail_1G:
        """
        self.app_hp_avail_1G = app_hp_avail_1G

    def get_app_hp_avail_1G(self) -> int:
        """
        Getter for app_hp_avail_1G
        """
        return self.app_hp_avail_1G

    def set_app_hp_pending_1G(self, app_hp_pending_1G: str) -> int:
        """
        Setter for app_hp_pending_1G
        Args:
            app_hp_pending_1G:
        """
        self.app_hp_pending_1G = app_hp_pending_1G

    def get_app_hp_pending_1G(self) -> int:
        """
        Getter for app_hp_pending_1G
        """
        return self.app_hp_pending_1G

    def set_app_hp_use_1G(self, app_hp_use_1G: bool) -> None:
        """
        Setter for app_hp_use_1G
        Args:
            app_hp_use_1G:
        """
        self.app_hp_use_1G = app_hp_use_1G

    def get_app_hp_use_1G(self) -> bool:
        """
        Getter for app_hp_use_1G
        """
        return self.app_hp_use_1G

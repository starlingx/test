class SystemCapabilitiesObject:
    """
    Class for System Capabilities Object
    """
    def __init__(self):
        
        self.region_config: bool = False
        self.vswitch_type: str = 'none'
        self.shared_services: list[str] = []
        self.sdn_enabled: bool = False
        self.https_enabled: bool = False
        self.bm_region: str = None

    def set_region_config(self, region_config: bool):
        """
        Setter for region config
        Args:
            region_config () - the region config
        """
        self.region_config = region_config

    def get_region_config(self) -> bool:
        """
        Getter for region config
        
        Returns: boolean 
        """
        return self.region_config
    
    def set_vswitch_type(self, vswitch_type):
        """
        Setter for vswitch_type
        Args:
            vswitch_type () - the vswitch_type
        """
        self.vswitch_type = vswitch_type

    def get_vswitch_type(self) -> str:
        """
        Getter for vswitch_type
        
        Returns: str  
        """
        return self.vswitch_type
    
    def set_shared_services(self, shared_services: list[str]):
        """
        Setter for shared_services
        Args:
            shared_services () - the shared_services
        """
        self.shared_services = shared_services

    def get_shared_services(self) -> list[str]:
        """
        Getter for shared_services
        
        Returns: list[str]  
        """
        return self.shared_services
    
    def set_sdn_enabled(self, sdn_enabled: bool):
        """
        Setter for sdn_enabled
        Args:
            sdn_enabled () - the sdn_enabled
        """
        self.sdn_enabled = sdn_enabled

    def get_sdn_enabled(self) -> bool:
        """
        Getter for sdn_enabled
        
        Returns: bool  
        """
        return self.sdn_enabled
    
    def set_https_enabled(self, https_enabled: bool):
        """
        Setter for https_enabled
        Args:
            https_enabled () - the https_enabled
        """
        self.https_enabled = https_enabled

    def get_https_enabled(self) -> bool:
        """
        Getter for https_enabled
        
        Returns: bool  
        """
        return self.https_enabled
    
    def set_bm_region(self, bm_region: str):
        """
        Setter for bm_region
        Args:
            bm_region () - the bm_region
        """
        self.bm_region = bm_region

    def get_bm_region(self) -> str:
        """
        Getter for bm_region
        
        Returns: str  
        """
        return self.bm_region



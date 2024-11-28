from keywords.base_keyword import BaseKeyword
from config.configuration_manager import ConfigurationManager


class GetRestUrlKeywords(BaseKeyword):

    def __init__(self) -> None:
        # get the rest api config
        self.rest_api_config = ConfigurationManager.get_rest_api_config()

        # get the lab conifg
        lab_config = ConfigurationManager.get_lab_config()

        # set the base url
        self.base_url = f'https://{lab_config.get_floating_ip()}'
        # if lab is ipv6 put the port in []
        if lab_config.is_ipv6():
            self.base_url = f'https://[{lab_config.get_floating_ip()}]'

    
    def get_keystone_url(self) -> str:
        """
        Return the keystone url
        """
        return f'{self.base_url}:{self.rest_api_config.get_keystone_base()}'
    

    def get_bare_metal_url(self) -> str:
        """
        Returns the bare metal url
        """
        return f'{self.base_url}:{self.rest_api_config.get_bare_metal_base()}'
    
    def get_configuration_url(self) -> str:
        """
        Returns the configuration url
        """
        return f'{self.base_url}:{self.rest_api_config.get_configuration_base()}'
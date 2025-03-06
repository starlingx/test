import json5


class SecurityConfig:
    """
    Class to hold configuration for Security tests
    """

    def __init__(self, config):

        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the security config file: {config}")
            raise

        security_dict = json5.load(json_data)
        self.dns_name = security_dict["dns_name"]

    def get_dns_name(self) -> str:
        """
        Getter for the dns name

        Returns:
            str: the dns name
        """
        return self.dns_name

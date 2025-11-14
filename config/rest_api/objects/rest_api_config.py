import json5


class RestAPIConfig:
    """
    Class to hold configuration for rest api posts and versions
    """

    def __init__(self, config):
        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the rest api config file: {config}")
            raise

        rest_dict = json5.load(json_data)

        self.keystone_base = rest_dict["keystone_base"]
        self.bare_metal_base = rest_dict["bare_metal_base"]
        self.configuration_base = rest_dict["configuration_base"]
        self.fm_base = rest_dict["fm_base"]
        self.dc_base = rest_dict["dc_base"]
        self.node_interface_metrics_exporter_base = rest_dict["node_interface_metrics_exporter_base"]
        self.nfv_base = rest_dict["nfv_base"]
        self.barbican_base = rest_dict["barbican_base"]
        self.software_update_base = rest_dict["software_update_base"]
        self.usm_base = rest_dict["usm_base"]
        self.vim_base = rest_dict["vim_base"]
        self.high_availability_base = rest_dict["high_availability_base"]

    def get_keystone_base(self) -> str:
        """
        Getter for the keystone_base
        """
        return self.keystone_base

    def get_bare_metal_base(self) -> str:
        """
        Getter for bare_metal_base.

        Returns:
            str: the bare_metal_base
        """
        return self.bare_metal_base

    def get_configuration_base(self) -> str:
        """
        Getter for configuration_base.

        Returns:
            str: the configuration_base
        """
        return self.configuration_base

    def get_fm_base(self) -> str:
        """
        Getter for fm_base.

        Returns:
            str: the fm_base
        """
        return self.fm_base

    def get_dc_base(self) -> str:
        """
        Getter for dc_base.

        Returns:
            str: the dc_base
        """
        return self.dc_base

    def get_node_interface_metrics_exporter_base(self) -> str:
        """
        Getter for node_interface_metrics_exporter_base.

        Returns:
            str: the node_interface_metrics_exporter_base
        """
        return self.node_interface_metrics_exporter_base

    def get_nfv_base(self) -> str:
        """
        Getter for nfv_base.

        Returns:
            str: the nfv_base
        """
        return self.nfv_base

    def get_barbican_base(self) -> str:
        """
        Getter for barbican_base.

        Returns:
            str: the barbican_base
        """
        return self.barbican_base

    def get_software_update_base(self) -> str:
        """
        Getter for software_update_base.

        Returns:
            str: the software_update_base
        """
        return self.software_update_base

    def get_usm_base(self) -> str:
        """
        Getter for usm_base.

        Returns:
            str: the usm_base
        """
        return self.usm_base

    def get_vim_base(self) -> str:
        """
        Getter for vim_base.

        Returns:
            str: the vim_base
        """
        return self.vim_base

    def get_high_availability_base(self) -> str:
        """
        Getter for high_availability_base.

        Returns:
            str: the high_availability_base
        """
        return self.high_availability_base

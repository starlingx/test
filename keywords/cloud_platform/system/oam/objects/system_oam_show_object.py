class SystemOamShowObject:
    """
    System Oam Object
    """

    def __init__(self):
        self.created_at = None
        self.isystem_uuid = None
        self.oam_c0_ip = None
        self.oam_c1_ip = None
        self.oam_floating_ip = None
        self.oam_gateway_ip = None
        self.oam_subnet = None
        self.updated_at = None
        self.uuid = None
        self.oam_ip = None

    def set_created_at(self, created_at: str):
        """
        Setter for created at
        Args:
            created_at (): created at value

        Returns:

        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for created at
        Returns: created at

        """
        return self.created_at

    def set_isystem_uuid(self, isystem_uuid: str):
        """
        Setter for isystem uuid
        Args:
            isystem_uuid (): the isystem uuid value

        Returns:

        """
        self.isystem_uuid = isystem_uuid

    def get_isystem_uuid(self) -> str:
        """
        Getter for isystem uuid
        Returns:

        """
        return self.isystem_uuid

    def set_oam_c0_ip(self, ip: str):
        """
        Setter for oam c0 ip
        Args:
            ip (): the ip

        Returns:

        """
        self.oam_c0_ip = ip

    def get_oam_c0_ip(self) -> str:
        """
        Getter for oam c0 ip
        Returns:

        """
        return self.oam_c0_ip

    def set_oam_c1_ip(self, ip: str):
        """
        Setter for oam c1 ip
        Args:
            ip (): the ip

        Returns:

        """
        self.oam_c1_ip = ip

    def get_oam_c1_ip(self) -> str:
        """
        Getter for oam c1 ip
        Returns:

        """
        return self.oam_c1_ip

    def set_oam_floating_ip(self, floating_ip: str):
        """
        Setter for oam floating ip
        Args:
            floating_ip (): the floating ip

        Returns:

        """
        self.oam_floating_ip = floating_ip

    def get_oam_floating_ip(self) -> str:
        """
        Getter for oam floating ip
        Returns:

        """
        return self.oam_floating_ip

    def set_oam_gateway_ip(self, gateway_ip: str):
        """
        Setter for oam gateway ip
        Args:
            gateway_ip (): the gateway ip

        Returns:

        """
        self.oam_gateway_ip = gateway_ip

    def get_oam_gateway_ip(self) -> str:
        """
        Getter for oam gateway ip
        Returns:

        """
        return self.oam_gateway_ip

    def set_oam_subnet(self, oam_subnet: str):
        """
        Setter for oam subnet
        Args:
            oam_subnet (): oam subnet

        Returns:

        """
        self.oam_subnet = oam_subnet

    def get_oam_subnet(self) -> str:
        """
        Getter for oam subnet
        Returns:

        """
        return self.oam_subnet

    def set_updated_at(self, updated_at: str):
        """
        Setter for updated at
        Args:
            updated_at (): updated at value

        Returns:

        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for updated at
        Returns:

        """
        return self.updated_at

    def set_uuid(self, uuid: str):
        """
        Setter for uuid
        Args:
            uuid (): the uuid

        Returns:

        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for uuid
        Returns:

        """
        return self.uuid

    def set_oam_ip(self, oam_ip: str):
        """
        Setter for oam_ip
        Args:
            oam_ip (): the oam_ip

        Returns:

        """
        self.oam_ip = oam_ip

    def get_oam_ip(self) -> str:
        """
        Getter for oam_ip
        Returns:

        """
        return self.oam_ip

"""WadConnectorConfig object for WAD (Windows Active Directory) connector."""

from config.security.objects.dex_connector_attrs import DexConnectorAttrs


class WadConnectorConfig(DexConnectorAttrs):
    """WAD (Windows Active Directory) connector configuration."""

    def __init__(self, wad_dict: dict):
        """Initialize WAD connector config.

        Args:
            wad_dict (dict): WAD connector configuration dictionary.
        """
        super().__init__(wad_dict)
        self._wad_server = wad_dict.get("wad_server", "")
        self._bind_dn = wad_dict.get("bind_dn", "")
        self._bind_pw = wad_dict.get("bind_pw", "")
        self._user_search_base = wad_dict.get("user_search_base", "")
        self._group_search_base = wad_dict.get("group_search_base", "")
        self._connector_id = wad_dict.get("connector_id", "wad")

    def get_wad_server(self) -> str:
        """Get WAD server address.

        Returns:
            str: WAD server hostname or IP.
        """
        return self._wad_server

    def get_bind_dn(self) -> str:
        """Get WAD bind DN.

        Returns:
            str: Bind distinguished name.
        """
        return self._bind_dn

    def get_bind_pw(self) -> str:
        """Get WAD bind password.

        Returns:
            str: Bind password.
        """
        return self._bind_pw

    def get_user_search_base(self) -> str:
        """Get user search base DN.

        Returns:
            str: User search base.
        """
        return self._user_search_base

    def get_group_search_base(self) -> str:
        """Get group search base DN.

        Returns:
            str: Group search base.
        """
        return self._group_search_base

    def get_connector_id(self) -> str:
        """Get connector ID used in oidc-auth backend selection.

        Returns:
            str: Connector ID (e.g. 'wad').
        """
        return self._connector_id

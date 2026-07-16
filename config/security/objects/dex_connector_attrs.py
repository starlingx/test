"""DexConnectorAttrs object for DEX connector attribute mappings."""


class DexConnectorAttrs:
    """Attribute mappings for a DEX connector."""

    def __init__(self, attrs_dict: dict):
        """Initialize connector attributes.

        Args:
            attrs_dict (dict): Attribute mapping dictionary.
        """
        self._email_attr = attrs_dict.get("email_attr", "")
        self._username_attr = attrs_dict.get("username_attr", "")
        self._name_attr = attrs_dict.get("name_attr", "")

    def get_email_attr(self) -> str:
        """Get emailAttr mapping value.

        Returns:
            str: Email attribute name.
        """
        return self._email_attr

    def get_username_attr(self) -> str:
        """Get usernameAttr mapping value.

        Returns:
            str: Username attribute name.
        """
        return self._username_attr

    def get_name_attr(self) -> str:
        """Get nameAttr mapping value.

        Returns:
            str: Name attribute name.
        """
        return self._name_attr

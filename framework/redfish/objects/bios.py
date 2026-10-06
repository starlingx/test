class Bios:
    """Represents a Redfish BIOS resource (``/redfish/v1/Systems/{id}/Bios``).

    Models the attributes currently in effect, the registry that describes
    their allowable values, and the pending-settings resource used to stage
    a change (``@Redfish.Settings``), including which apply-times (e.g.
    ``OnReset``) that resource advertises support for, if any.
    """

    def __init__(self, data: dict):
        """Initialize a Bios object from a Bios resource's raw JSON body.

        Args:
            data (dict): The Bios resource body, as returned by a GET on
                its ``@odata.id``.

        Raises:
            ValueError: If data is None or empty.
        """
        if not data:
            raise ValueError("Bios resource data cannot be None or empty")

        self.id = data.get("@odata.id", "")
        self.attributes = data.get("Attributes", {}) or {}
        self.attribute_registry = data.get("AttributeRegistry", "")

        settings_data = data.get("@Redfish.Settings", {}) or {}
        self.settings_uri = self._extract_settings_uri(settings_data, self.id)
        self.supported_apply_times = self._extract_supported_apply_times(settings_data)

    @staticmethod
    def _extract_settings_uri(settings_data: dict, bios_id: str) -> str:
        """Determine the pending-settings URI for this Bios resource.

        Prefers the URI the resource itself advertises via
        ``@Redfish.Settings.SettingsObject``. Falls back to the
        conventional ``<bios_id>/Settings`` path when the resource does
        not advertise one, matching common BMC behavior.

        Args:
            settings_data (dict): The ``@Redfish.Settings`` block, if any.
            bios_id (str): This Bios resource's own ``@odata.id``.

        Returns:
            str: The URI to PATCH in order to stage attribute changes.
        """
        settings_object = settings_data.get("SettingsObject") or {}
        settings_uri = settings_object.get("@odata.id")
        if settings_uri:
            return settings_uri
        return bios_id.rstrip("/") + "/Settings"

    @staticmethod
    def _extract_supported_apply_times(settings_data: dict) -> list:
        """Extract the apply-times this resource advertises support for.

        Different BMCs spell this slightly differently, so a few common
        keys are checked. Returns an empty list (not None) when the
        resource does not advertise apply-time support at all, so callers
        can distinguish "no times listed" from "no settings data at all"
        without a None check.

        Args:
            settings_data (dict): The ``@Redfish.Settings`` block, if any.

        Returns:
            list: The advertised apply-time values (e.g. ``["OnReset"]``),
            or an empty list if none are advertised.
        """
        return (
            settings_data.get("SupportedApplyTimes")
            or settings_data.get("@Redfish.SettingsApplyTimes")
            or (settings_data.get("@Redfish.SettingsApplyTime") or {}).get("SupportedApplyTimes")
            or []
        )

    def get_id(self) -> str:
        """Get this Bios resource's own ``@odata.id``.

        Returns:
            str: The Bios resource URI.
        """
        return self.id

    def set_id(self, id: str) -> None:
        """Set this Bios resource's own ``@odata.id``.

        Args:
            id (str): The Bios resource URI.
        """
        self.id = id

    def get_attributes(self) -> dict:
        """Get all current BIOS attribute values.

        Returns:
            dict: Mapping of attribute name to its current value.
        """
        return self.attributes

    def set_attributes(self, attributes: dict) -> None:
        """Set the current BIOS attribute values.

        Args:
            attributes (dict): Mapping of attribute name to current value.
        """
        self.attributes = attributes

    def get_attribute_value(self, name: str) -> str | None:
        """Get a single attribute's current value by name.

        Args:
            name (str): The BIOS attribute name.

        Returns:
            Optional[str]: The attribute's current value, or None if this
            resource has no attribute with that name.
        """
        return self.attributes.get(name)

    def find_attribute_names(self, token: str) -> list[str]:
        """Find attribute names containing the given token (case-insensitive).

        General-purpose name search over this resource's attributes (e.g.
        used to find every NUMA-related attribute by matching "numa").

        Args:
            token (str): Substring to match against attribute names.

        Returns:
            list[str]: Matching attribute names, sorted.
        """
        token_lower = token.lower()
        return sorted(name for name in self.attributes if token_lower in name.lower())

    def get_attribute_registry(self) -> str:
        """Get the name of the AttributeRegistry describing allowable values.

        Returns:
            str: The AttributeRegistry name (e.g.
            "BiosAttributeRegistry.v1_0_0"), or an empty string if this
            resource does not publish one.
        """
        return self.attribute_registry

    def set_attribute_registry(self, attribute_registry: str) -> None:
        """Set the name of the AttributeRegistry describing allowable values.

        Args:
            attribute_registry (str): The AttributeRegistry name.
        """
        self.attribute_registry = attribute_registry

    def get_settings_uri(self) -> str:
        """Get the pending-settings URI to PATCH in order to stage changes.

        Returns:
            str: The settings resource URI.
        """
        return self.settings_uri

    def set_settings_uri(self, settings_uri: str) -> None:
        """Set the pending-settings URI.

        Args:
            settings_uri (str): The settings resource URI.
        """
        self.settings_uri = settings_uri

    def get_supported_apply_times(self) -> list:
        """Get the apply-times this resource advertises support for.

        Returns:
            list: Advertised apply-time values (e.g. ``["OnReset"]"``), or
            an empty list if this resource does not advertise any.
        """
        return self.supported_apply_times

    def set_supported_apply_times(self, supported_apply_times: list) -> None:
        """Set the apply-times this resource advertises support for.

        Args:
            supported_apply_times (list): Advertised apply-time values.
        """
        self.supported_apply_times = supported_apply_times

    def supports_apply_time(self, apply_time: str) -> bool:
        """Check whether a specific apply-time is advertised as supported.

        Args:
            apply_time (str): The apply-time to check (e.g. "OnReset").

        Returns:
            bool: True if advertised as supported, False if an apply-time
            list is advertised but does not include ``apply_time``, or if
            no apply-time list is advertised at all (unknown support).
        """
        return apply_time in self.supported_apply_times

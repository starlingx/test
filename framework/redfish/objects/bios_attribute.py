class BiosAttribute:
    """Represents a single BIOS attribute, combining its live state (from
    the Bios resource) with its registry-published metadata (allowable
    values, display names, type).

    Different BMCs disagree on which value form a PATCH must use: some
    accept the registry's ``ValueName`` (e.g. HPE's "Enabled"), while
    others (observed on Supermicro) require the ``ValueDisplayName`` (e.g.
    "NPS2") even though the registry also lists a distinct ``ValueName``
    ("2"). :meth:`resolve_value` encapsulates that translation so callers
    can accept either form from a user and send the form this attribute's
    resource actually expects.
    """

    def __init__(self, name: str, current_value: str | None, pending_value: str | None = None, value_pairs: list[tuple] | None = None, attribute_type: str | None = None):
        """Initialize a BiosAttribute.

        Args:
            name (str): The attribute name (e.g. "SubNumaClustering").
            current_value (Optional[str]): The attribute's current value,
                as reported by the Bios resource.
            pending_value (Optional[str]): The attribute's pending value,
                as reported by the pending-settings resource, if any
                change is staged.
            value_pairs (Optional[list[tuple]]): ``(value_name,
                value_display_name)`` tuples from the AttributeRegistry,
                for Enumeration-type attributes. None if the registry does
                not describe this attribute (e.g. non-enum types, or no
                registry available).
            attribute_type (Optional[str]): The registry-published type
                (e.g. "Enumeration", "Integer", "String"), if known.
        """
        self.name = name
        self.current_value = current_value
        self.pending_value = pending_value
        self.value_pairs = value_pairs or []
        self.attribute_type = attribute_type

    def get_name(self) -> str:
        """Get the attribute name.

        Returns:
            str: The attribute name.
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Set the attribute name.

        Args:
            name (str): The attribute name.
        """
        self.name = name

    def get_current_value(self) -> str | None:
        """Get the attribute's current (in-effect) value.

        Returns:
            Optional[str]: The current value.
        """
        return self.current_value

    def set_current_value(self, current_value: str | None) -> None:
        """Set the attribute's current (in-effect) value.

        Args:
            current_value (Optional[str]): The current value.
        """
        self.current_value = current_value

    def get_pending_value(self) -> str | None:
        """Get the attribute's pending (staged, not-yet-applied) value.

        Returns:
            Optional[str]: The pending value, or None if nothing is staged.
        """
        return self.pending_value

    def set_pending_value(self, pending_value: str | None) -> None:
        """Set the attribute's pending value.

        Args:
            pending_value (Optional[str]): The pending value.
        """
        self.pending_value = pending_value

    def get_value_pairs(self) -> list[tuple]:
        """Get the registry's (value_name, value_display_name) pairs.

        Returns:
            list[tuple]: The allowable value pairs, or an empty list if
            the registry does not describe this attribute.
        """
        return self.value_pairs

    def set_value_pairs(self, value_pairs: list[tuple]) -> None:
        """Set the registry's (value_name, value_display_name) pairs.

        Args:
            value_pairs (list[tuple]): The allowable value pairs.
        """
        self.value_pairs = value_pairs

    def get_allowable_value_names(self) -> list[str]:
        """Get the allowable values in ValueName form.

        Returns:
            list[str]: Every non-None ``value_name`` from the registry's
            value pairs.
        """
        return [name for name, _ in self.value_pairs if name is not None]

    def get_allowable_display_names(self) -> list[str]:
        """Get the allowable values in ValueDisplayName form.

        Returns:
            list[str]: Every non-None ``value_display_name`` from the
            registry's value pairs.
        """
        return [display for _, display in self.value_pairs if display is not None]

    def get_attribute_type(self) -> str | None:
        """Get the registry-published attribute type.

        Returns:
            Optional[str]: The type (e.g. "Enumeration"), or None if
            unknown.
        """
        return self.attribute_type

    def set_attribute_type(self, attribute_type: str | None) -> None:
        """Set the registry-published attribute type.

        Args:
            attribute_type (Optional[str]): The attribute type.
        """
        self.attribute_type = attribute_type

    def is_known_value(self, requested: str) -> bool:
        """Check whether a value matches either known form for this attribute.

        Args:
            requested (str): A value supplied by a caller, in either the
                ValueName or ValueDisplayName form.

        Returns:
            bool: True if ``requested`` matches a ValueName or
            ValueDisplayName in this attribute's value pairs, or if this
            attribute has no registry value pairs at all (nothing to
            validate against, so the value is not rejected here).
        """
        if not self.value_pairs:
            return True
        return any(requested in (name, display) for name, display in self.value_pairs)

    def resolve_value(self, requested: str) -> str:
        """Translate a requested value to the form this attribute's
        resource expects.

        Accepts a value the caller supplied as either the ``ValueName`` or
        the ``ValueDisplayName`` and returns the form the BIOS Settings
        resource is observed to use. This attribute's own
        ``current_value`` is the signal: if it matches a known
        ``ValueDisplayName``, the resource stores/expects display names
        (observed on Supermicro), so the display name is returned;
        otherwise the ValueName is returned (the HPE/Dell default).

        Args:
            requested (str): The value to resolve, in either form.

        Returns:
            str: The value to send in a PATCH, in the form this resource
            expects. If this attribute has no registry value pairs (e.g.
            non-enum types), ``requested`` is returned unchanged.

        Raises:
            ValueError: If ``requested`` does not match any known
                ValueName or ValueDisplayName for this attribute.
        """
        if not self.value_pairs:
            return requested

        matched = next(((name, display) for name, display in self.value_pairs if requested in (name, display)), None)
        if matched is None:
            raise ValueError(f"'{requested}' is not an allowable value for '{self.name}'. Allowable (name/display) pairs: {self.value_pairs}")

        name, display = matched
        resource_uses_display_names = any(self.current_value == d for _, d in self.value_pairs if d is not None)
        if resource_uses_display_names and display is not None:
            return display
        return name if name is not None else display

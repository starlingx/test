from typing import Optional


class NumaAttributeReport:
    """One NUMA-related BIOS attribute, as discovered over Redfish.

    Exposes its fields through getters rather than public attributes, to
    follow the repository's convention for strong result objects (e.g.
    :class:`SystemInfo`, :class:`BiosAttribute`).
    """

    def __init__(self, attribute: str, current_value: Optional[str], pending_value: Optional[str], allowable_values: Optional[list[str]]):
        """Initialize a NumaAttributeReport.

        Args:
            attribute (str): The BIOS attribute name.
            current_value (Optional[str]): The attribute's current value.
            pending_value (Optional[str]): The attribute's pending value,
                or None if no change is staged.
            allowable_values (Optional[list[str]]): The BMC-reported
                allowable values (ValueName form), or None if the BMC
                does not publish an AttributeRegistry for it.
        """
        self.attribute = attribute
        self.current_value = current_value
        self.pending_value = pending_value
        self.allowable_values = allowable_values

    def get_attribute(self) -> str:
        """Get the BIOS attribute name.

        Returns:
            str: The attribute name.
        """
        return self.attribute

    def get_current_value(self) -> Optional[str]:
        """Get the attribute's current value.

        Returns:
            Optional[str]: The current value.
        """
        return self.current_value

    def get_pending_value(self) -> Optional[str]:
        """Get the attribute's pending value.

        Returns:
            Optional[str]: The pending value, or None if no change is staged.
        """
        return self.pending_value

    def get_allowable_values(self) -> Optional[list[str]]:
        """Get the BMC-reported allowable values (ValueName form).

        Returns:
            Optional[list[str]]: The allowable values, or None if the BMC
            does not publish an AttributeRegistry for this attribute.
        """
        return self.allowable_values

class SncProfile:
    """A per-vendor sub-NUMA clustering (SNC/NPS) BIOS profile.

    The BIOS attribute that controls sub-NUMA clustering, and the values
    that mean "enabled" and "disabled", differ per BMC vendor:

        Vendor        Attribute             Enable value      Disable value
        ------------  --------------------  ----------------  -------------
        HPE (iLO)     SubNumaClustering     Enabled           Disabled
        Dell (iDRAC)  SubNumaCluster        4-Way or 2-Way    Disabled
        AMD/SMC       NUMANodesPerSocket    NPS2 or NPS4      NPS1

    For AMD/NPS there is no literal "Disabled"; sub-NUMA OFF == NPS1 (one
    node per socket).

    The enable value is expressed as an ordered list of candidates because
    some vendors offer more than one "on" level and not every platform
    supports every level (e.g. some Dell boxes offer 4-Way and 2-Way,
    others only 2-Way). The caller selects the first candidate the specific
    BMC actually lists as allowable, so a single profile adapts across
    hardware without per-lab configuration.
    """

    def __init__(self, manufacturer: str, attribute: str, enable_candidates: list[str], disable: str):
        """Initialize an SncProfile.

        Args:
            manufacturer (str): Substring matched (case-insensitive)
                against the BMC-reported Manufacturer to select this
                profile (e.g. "hpe", "dell", "supermicro").
            attribute (str): The BIOS attribute name that controls SNC.
            enable_candidates (list[str]): Ordered "enable" values, most
                preferred first. The caller picks the first one the BMC
                lists as allowable.
            disable (str): The attribute value that disables sub-NUMA.
        """
        self.manufacturer = manufacturer
        self.attribute = attribute
        self.enable_candidates = enable_candidates
        self.disable = disable

    def get_manufacturer(self) -> str:
        """Get the manufacturer match substring.

        Returns:
            str: The manufacturer substring for this profile.
        """
        return self.manufacturer

    def get_attribute(self) -> str:
        """Get the BIOS attribute name that controls SNC.

        Returns:
            str: The attribute name.
        """
        return self.attribute

    def get_enable_candidates(self) -> list[str]:
        """Get the ordered "enable" value candidates (most preferred first).

        Returns:
            list[str]: The enable candidates.
        """
        return self.enable_candidates

    def select_enable_value(self, allowable_values: list[str] | None) -> str | None:
        """Choose the enable value this BMC supports, honoring preference order.

        Returns the first enable candidate present in ``allowable_values``.
        When ``allowable_values`` is empty or None (the BMC published no
        allowable list), the most-preferred candidate is returned as a
        best-effort default.

        Args:
            allowable_values (list[str] | None): The BMC-allowable values
                (ValueName form) for this profile's attribute, or None.

        Returns:
            str | None: The chosen enable value, or None if an allowable
            list was provided but contained none of the candidates.
        """
        if not allowable_values:
            return self.enable_candidates[0]
        return next((candidate for candidate in self.enable_candidates if candidate in allowable_values), None)

    def get_disable_value(self) -> str:
        """Get the attribute value that disables sub-NUMA.

        Returns:
            str: The disable value.
        """
        return self.disable

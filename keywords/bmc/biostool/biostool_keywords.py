from typing import Optional, Type

from keywords.base_keyword import BaseKeyword
from keywords.bmc.biostool.biostool_keywords_implementation import BiosToolKeywordsImplementation
from keywords.bmc.biostool.objects.bios_tool_system_info import BiosToolSystemInfo
from keywords.bmc.biostool.objects.numa_attribute_report import NumaAttributeReport


class BiosToolKeywords(BaseKeyword):
    """Public interface for BIOS/BMC operations over Redfish.

    The actual logic lives in :class:`BiosToolKeywordsImplementation` (or
    a subclass of it), which talks to the BMC natively over Redfish. This
    class is the stable entry point that callers use; it forwards each
    public method to the active implementation -- the same
    interface/implementation split used by :class:`PowerKeywords`.

    External users can swap in a custom implementation by calling
    :meth:`set_implementation_class` with a subclass of
    :class:`BiosToolKeywordsImplementation` (e.g. the ACE framework
    registers an implementation that rejects BIOS/BMC operations on
    VM-backed labs, since SNC/NPS BIOS control has no meaning without
    real hardware).
    """

    implementation_class: Type[BiosToolKeywordsImplementation] = BiosToolKeywordsImplementation

    @classmethod
    def set_implementation_class(cls, implementation_class: Optional[Type[BiosToolKeywordsImplementation]]) -> None:
        """Register the implementation class to use for biostool keywords.

        Args:
            implementation_class (Optional[Type[BiosToolKeywordsImplementation]]):
                A subclass of :class:`BiosToolKeywordsImplementation` to
                use for new :class:`BiosToolKeywords` instances, or
                ``None`` to fall back to the default implementation.

        Raises:
            TypeError: If ``implementation_class`` is not ``None`` and is
                not a subclass of :class:`BiosToolKeywordsImplementation`.
        """
        if implementation_class is None:
            BiosToolKeywords.implementation_class = BiosToolKeywordsImplementation
            return

        if not (isinstance(implementation_class, type) and issubclass(implementation_class, BiosToolKeywordsImplementation)):
            raise TypeError("implementation_class must be a subclass of BiosToolKeywordsImplementation")

        BiosToolKeywords.implementation_class = implementation_class

    def __init__(self, bm_ip: str, bm_username: str, bm_password: str):
        """Constructor.

        Args:
            bm_ip (str): The BMC IP address or hostname.
            bm_username (str): The BMC username for Basic Authentication.
            bm_password (str): The BMC password for Basic Authentication.
        """
        self.bm_ip = bm_ip
        self.implementation = BiosToolKeywords.implementation_class(bm_ip, bm_username, bm_password)

    def get_implementation(self) -> BiosToolKeywordsImplementation:
        """Return the implementation instance backing this keyword object.

        Returns:
            BiosToolKeywordsImplementation: The implementation instance
            constructed for this :class:`BiosToolKeywords`.
        """
        return self.implementation

    def sysinfo(self) -> BiosToolSystemInfo:
        """Get the BMC-reported system Manufacturer and Model.

        Returns:
            BiosToolSystemInfo: manufacturer and model fields.

        Raises:
            KeywordException: If connecting to/authenticating with the BMC fails.
        """
        return self.implementation.sysinfo()

    def discover_numa_attributes(self) -> list[NumaAttributeReport]:
        """Discover every BIOS attribute whose name contains 'numa'.

        Returns:
            list[NumaAttributeReport]: one entry per discovered attribute.

        Raises:
            KeywordException: If no matching attribute is found, or
                connecting to the BMC fails.
        """
        return self.implementation.discover_numa_attributes()

    def set_numa_attributes(self, attribute_values: dict[str, str]) -> None:
        """Stage one or more NUMA BIOS attribute changes.

        Args:
            attribute_values (dict[str, str]): {attribute_name: target_value}.
                Every pair is validated against discovered NUMA attributes
                and their BMC-allowable values before any change is staged.

        Raises:
            KeywordException: If any name/value pair is invalid, or the
                underlying Redfish request fails.
        """
        self.implementation.set_numa_attributes(attribute_values)

    def reset_host(self) -> None:
        """Reboot the host via the BMC, preferring a graceful restart.

        Raises:
            KeywordException: If the reset cannot be completed over the BMC.
        """
        self.implementation.reset_host()

from typing import Optional

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.redfish.operations.bios_operations import BiosOperations
from framework.redfish.operations.get_system_info import GetSystemInfo
from keywords.bmc.biostool.objects.bios_tool_system_info import BiosToolSystemInfo
from keywords.bmc.biostool.objects.numa_attribute_report import NumaAttributeReport


class BiosToolKeywordsImplementation:
    """Default (hardware/Redfish) implementation backing BiosToolKeywords.

    This class discovers and sets NUMA/SNC related BIOS attributes, and
    resets the host via the BMC, on any Redfish-capable BMC vendor
    (AMD/Intel/Dell/HPE/Supermicro). It does so natively, in-process, via
    :class:`BiosOperations` -- no external CLI or subprocess is involved.

    It is intentionally a plain class (not a ``BaseKeyword`` subclass) so
    that the keyword logging hook only fires once at the ``BiosToolKeywords``
    interface boundary rather than being wrapped a second time when the
    interface delegates here -- the same reasoning documented on
    :class:`PowerKeywordsImplementation`.

    This talks to the BMC directly over the management network; it does
    not run on the StarlingX host, so this class takes BMC connection
    details directly rather than an ``SSHConnection``.

    Users can extend this class to override behavior on a per-method
    basis and register the subclass via
    :meth:`BiosToolKeywords.set_implementation_class`. Anything not
    overridden falls through to the behavior implemented here.
    """

    # Substring matched (case-insensitive) against BIOS attribute names to
    # find every NUMA/SNC/NPS related attribute (e.g. SubNumaClustering,
    # SubNumaCluster, NUMANodesPerSocket, ACPISRATL3CacheAsNUMADomain).
    # "numa" is the one token common to all of them across vendors.
    NUMA_ATTRIBUTE_TOKEN = "numa"

    def __init__(self, bm_ip: str, bm_username: str, bm_password: str):
        """Constructor.

        Args:
            bm_ip (str): The BMC IP address or hostname.
            bm_username (str): The BMC username for Basic Authentication.
            bm_password (str): The BMC password for Basic Authentication.

        Raises:
            KeywordException: If ``bm_ip`` is not set (e.g. the lab
                config node has no ``bm_ip`` configured).
        """
        if not bm_ip:
            raise KeywordException(
                "No BMC IP address was provided; cannot discover/set BIOS "
                "attributes without a configured bm_ip for this host."
            )
        self.bm_ip = bm_ip
        self.bm_username = bm_username
        self.bm_password = bm_password

    def sysinfo(self) -> BiosToolSystemInfo:
        """Get the BMC-reported system Manufacturer and Model.

        Returns:
            BiosToolSystemInfo: manufacturer and model fields.

        Raises:
            KeywordException: If connecting/authenticating to the BMC
                fails, or the BMC does not report this information.
        """
        try:
            get_system_info = GetSystemInfo(self.bm_ip, self.bm_username, self.bm_password)
            # get_system_info() reads self.system_id, which GetSystemInfo
            # only populates lazily in get_system_id(). Prime it first --
            # the same ordering RedFishChassisPowerKeywords relies on --
            # otherwise the subsequent GET is issued against a None path.
            get_system_info.get_system_id()
            system_info = get_system_info.get_system_info()
        except Exception as ex:  # noqa: BLE001 - translate any Redfish failure to a KeywordException
            raise KeywordException(f"Failed to get system info from BMC {self.bm_ip}: {ex}") from ex
        return BiosToolSystemInfo(
            manufacturer=system_info.get_manufacturer() or None,
            model=system_info.get_model() or None,
        )

    def discover_numa_attributes(self) -> list[NumaAttributeReport]:
        """Discover every BIOS attribute whose name contains 'numa'.

        Returns:
            list[NumaAttributeReport]: one entry per discovered attribute,
            each with its name, current value, pending value (if any),
            and BMC-reported allowable values (if the BMC publishes an
            AttributeRegistry). For attributes with distinct ValueName/
            ValueDisplayName forms (e.g. Supermicro's NPS* attributes),
            allowable_values reports the ValueName form, matching the
            BMC's AttributeRegistry.

        Raises:
            KeywordException: If no BIOS attribute name matching "numa"
                is found on this BMC, or if the discovery request fails.
        """
        try:
            attributes = self._get_bios_operations().find_attributes(self.NUMA_ATTRIBUTE_TOKEN)
        except Exception as ex:  # noqa: BLE001 - translate any Redfish failure to a KeywordException
            raise KeywordException(f"Failed to discover NUMA-related BIOS attributes on BMC {self.bm_ip}: {ex}") from ex

        if not attributes:
            raise KeywordException(f"No BIOS attribute names matching '{self.NUMA_ATTRIBUTE_TOKEN}' were found on BMC {self.bm_ip}.")

        return [
            NumaAttributeReport(
                attribute=attribute.get_name(),
                current_value=attribute.get_current_value(),
                pending_value=attribute.get_pending_value(),
                allowable_values=attribute.get_allowable_value_names() or None,
            )
            for attribute in attributes
        ]

    def set_numa_attributes(self, attribute_values: dict[str, str]) -> None:
        """Stage one or more NUMA BIOS attribute changes.

        Every name is validated against this BMC's discovered NUMA
        attributes before any PATCH is attempted. Each value is accepted
        in either the registry's ValueName or ValueDisplayName form (e.g.
        Supermicro's "NPS2" or "2") and translated to whichever form this
        BMC's Settings resource is observed to expect -- see
        :meth:`BiosAttribute.resolve_value`.

        The change is only staged; it does not take effect until
        :meth:`reset_host` is called.

        Args:
            attribute_values (dict[str, str]): {attribute_name: target_value}.

        Raises:
            KeywordException: If any name is not a discovered NUMA
                attribute, if any value is not an allowable value for its
                attribute, or if the underlying PATCH fails.
        """
        if not attribute_values:
            get_logger().log_info("set_numa_attributes called with no attributes; nothing to do.")
            return

        discovered_names = {report.get_attribute() for report in self.discover_numa_attributes()}
        for name in attribute_values:
            if name not in discovered_names:
                raise KeywordException(f"'{name}' is not a discovered NUMA attribute on BMC {self.bm_ip}. Discovered attributes: {sorted(discovered_names)}")

        try:
            self._get_bios_operations().set_attributes(attribute_values)
        except Exception as ex:  # noqa: BLE001 - translate any Redfish failure to a KeywordException
            raise KeywordException(f"Failed to stage NUMA attribute change(s) {attribute_values} on BMC {self.bm_ip}: {ex}") from ex
        get_logger().log_info(f"Staged NUMA attribute change(s) on BMC {self.bm_ip}: {attribute_values}")

    def reset_host(self) -> None:
        """Reboot the host via the BMC, preferring a graceful restart.

        This is the action that applies any change staged by
        :meth:`set_numa_attributes`.

        Raises:
            KeywordException: If the BMC advertises no usable ResetType,
                or rejects the reset action.
        """
        try:
            self._get_bios_operations().reset_host()
        except Exception as ex:  # noqa: BLE001 - translate any Redfish failure to a KeywordException
            raise KeywordException(f"Failed to reset host via BMC {self.bm_ip}: {ex}") from ex
        get_logger().log_info(f"Reset action accepted by BMC {self.bm_ip}.")

    # --- internal helpers ---

    def _get_bios_operations(self) -> BiosOperations:
        """Build a BiosOperations for this BMC.

        A fresh instance is used per call (matching the rest of this
        keyword's stateless-per-call style) rather than cached on
        ``self``, since :class:`BiosOperations` itself re-resolves the
        system_id on construction, which is cheap relative to the BIOS
        operations performed afterward.

        Returns:
            BiosOperations: A new operations instance for this BMC.
        """
        return BiosOperations(self.bm_ip, self.bm_username, self.bm_password)

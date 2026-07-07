from typing import Iterable, List, Optional, Tuple

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object import DcManagerSubcloudListObject
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_sync_enum import DcManagerSubcloudListSyncEnum
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_show_object import DcManagerSubcloudShowObject
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_management_enum import DcManagerSubcloudListManagementEnum
from keywords.cloud_platform.dcmanager.objects.subcloud_pick_result import SubcloudPickResult
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass


class SubcloudPickerKeywords(BaseKeyword):
    """Selects subclouds matching a declarative filter set.

    Filters ``management_status``, ``availability`` and ``in_sync`` are
    evaluated against the output of ``dcmanager subcloud list``.
    ``dcmanager subcloud show`` is only invoked when the ``load`` filter is
    used (to read ``software_version``). The picker also intersects the
    selection with the subclouds declared in ``LabConfig`` when
    ``present_in_config`` is True (default).

    Public API: ``pick_one(...)`` and ``pick_all(...)``.
    """

    _IN_SYNC_VALUE: str = DcManagerSubcloudListSyncEnum.IN_SYNC.value
    _OUT_OF_SYNC_VALUE: str = DcManagerSubcloudListSyncEnum.OUT_OF_SYNC.value

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active
                controller of the central cloud. Reused as-is for the
                ``dcmanager subcloud list`` and ``dcmanager subcloud show``
                invocations; no new SSH connections are created.
        """
        self.ssh_connection = ssh_connection
        self._list_kw = DcManagerSubcloudListKeywords(ssh_connection)
        self._show_kw = DcManagerSubcloudShowKeywords(ssh_connection)
        self._version_mgr = CloudPlatformVersionManagerClass()

    def pick_one(
        self,
        *,
        management_status: Optional[DcManagerSubcloudListManagementEnum] = None,
        availability: Optional[DcManagerSubcloudListAvailabilityEnum] = None,
        in_sync: Optional[bool] = None,
        load: Optional[str] = None,
        lab_type: Optional[LabTypeEnum] = None,
        present_in_config: bool = True,
    ) -> SubcloudPickResult:
        """Return the lowest-id subcloud satisfying every supplied filter.

        Args:
            management_status (Optional[DcManagerSubcloudListManagementEnum]):
                Required management state from ``dcmanager subcloud list``
                (e.g. MANAGED).
            availability (Optional[DcManagerSubcloudListAvailabilityEnum]):
                Required availability state from ``dcmanager subcloud list``
                (e.g. ONLINE).
            in_sync (Optional[bool]): When True, only subclouds whose ``sync``
                column equals ``"in-sync"`` are accepted. When False, only
                subclouds whose ``sync`` column equals ``"out-of-sync"`` are
                accepted. When None (default), the sync state is not checked.
            load (Optional[str]): Software version filter. Accepts the
                literal ``"N-1"`` (resolved against the central cloud version
                manager) or an explicit version string (e.g. ``"24.09"``).
                When provided, ``dcmanager subcloud show <name>`` is called
                per surviving candidate.
            lab_type (Optional[LabTypeEnum]): Lab type filter (e.g. SIMPLEX,
                DUPLEX). When provided, only subclouds whose lab type in the
                config matches are accepted. Requires ``present_in_config=True``.
            present_in_config (bool): When True (default), the subcloud must
                also appear in ``LabConfig.get_subcloud_names()``.

        Returns:
            SubcloudPickResult: The selected subcloud.

        Raises:
            KeywordException: If parameters are invalid, the central cloud
                returns no subclouds, or no subcloud satisfies the filter set.
        """
        results = self._pick(
            management_status=management_status,
            availability=availability,
            in_sync=in_sync,
            load=load,
            lab_type=lab_type,
            present_in_config=present_in_config,
        )
        return results[0]

    def pick_all(
        self,
        *,
        management_status: Optional[DcManagerSubcloudListManagementEnum] = None,
        availability: Optional[DcManagerSubcloudListAvailabilityEnum] = None,
        in_sync: Optional[bool] = None,
        load: Optional[str] = None,
        lab_type: Optional[LabTypeEnum] = None,
        present_in_config: bool = True,
    ) -> List[SubcloudPickResult]:
        """Return all subclouds satisfying every supplied filter, ordered by id.

        Args:
            management_status: see ``pick_one``.
            availability: see ``pick_one``.
            in_sync: see ``pick_one``.
            load: see ``pick_one``.
            lab_type: see ``pick_one``.
            present_in_config: see ``pick_one``.

        Returns:
            List[SubcloudPickResult]: Selected subclouds, sorted by numeric
            dcmanager id ascending.

        Raises:
            KeywordException: Same conditions as ``pick_one``.
        """
        return list(
            self._pick(
                management_status=management_status,
                availability=availability,
                in_sync=in_sync,
                load=load,
                lab_type=lab_type,
                present_in_config=present_in_config,
            )
        )

    def _pick(
        self,
        *,
        management_status: Optional[DcManagerSubcloudListManagementEnum],
        availability: Optional[DcManagerSubcloudListAvailabilityEnum],
        in_sync: Optional[bool],
        load: Optional[str],
        lab_type: Optional[LabTypeEnum],
        present_in_config: bool,
    ) -> List[SubcloudPickResult]:
        """Run the full filter pipeline. See ``pick_one``/``pick_all``."""
        self.validate_argument(
            management_status=management_status,
            availability=availability,
            in_sync=in_sync,
            load=load,
            lab_type=lab_type,
            present_in_config=present_in_config,
        )
        load_resolved = self._resolve_load(load)
        if in_sync is True:
            expected_sync = self._IN_SYNC_VALUE
        elif in_sync is False:
            expected_sync = self._OUT_OF_SYNC_VALUE
        else:
            expected_sync = None

        filter_set = {
            "management_status": management_status.value if management_status is not None else None,
            "availability": availability.value if availability is not None else None,
            "in_sync": in_sync,
            "load": self._format_load_for_log(load, load_resolved),
            "lab_type": lab_type.value if lab_type is not None else None,
            "present_in_config": present_in_config,
        }
        get_logger().log_info(f"SubcloudPickerKeywords: applied filters: {filter_set}")

        all_subclouds = self._get_subcloud_list_once()
        if not all_subclouds:
            raise KeywordException(
                "SubcloudPickerKeywords: 'dcmanager subcloud list' returned zero subclouds. "
                f"Applied filters: {filter_set}."
            )

        configured_names = self._get_configured_subcloud_names() if present_in_config else None

        survivors, rejections = self._apply_list_filters(
            subclouds=all_subclouds,
            management_status=management_status,
            availability=availability,
            expected_sync=expected_sync,
            lab_type=lab_type,
            present_in_config=present_in_config,
            configured_names=configured_names,
        )

        if load_resolved is not None:
            survivors, show_rejections = self._apply_load_filter(
                survivors=survivors,
                load_resolved=load_resolved,
            )
            rejections.extend(show_rejections)

        if not survivors:
            raise KeywordException(self._format_rejection_report(filter_set, rejections))

        survivors.sort(key=lambda item: int(item[0].get_id()))
        return [self._build_result(list_obj, show_obj) for list_obj, show_obj in survivors]

    def validate_argument(
        self,
        *,
        management_status: Optional[DcManagerSubcloudListManagementEnum],
        availability: Optional[DcManagerSubcloudListAvailabilityEnum],
        in_sync: Optional[bool],
        load: Optional[str],
        lab_type: Optional[LabTypeEnum],
        present_in_config: bool,
    ) -> None:
        """Reject invalid parameter types before any SSH activity occurs."""
        if management_status is not None and not isinstance(management_status, DcManagerSubcloudListManagementEnum):
            raise KeywordException(
                "SubcloudPickerKeywords: invalid parameter 'management_status': "
                f"expected None or DcManagerSubcloudListManagementEnum, received {type(management_status).__name__} ({management_status!r})."
            )
        if availability is not None and not isinstance(availability, DcManagerSubcloudListAvailabilityEnum):
            raise KeywordException(
                "SubcloudPickerKeywords: invalid parameter 'availability': "
                f"expected None or DcManagerSubcloudListAvailabilityEnum, received {type(availability).__name__} ({availability!r})."
            )
        if in_sync is not None and type(in_sync) is not bool:
            raise KeywordException(
                "SubcloudPickerKeywords: invalid parameter 'in_sync': "
                f"expected None or bool, received {type(in_sync).__name__} ({in_sync!r})."
            )
        if lab_type is not None and not isinstance(lab_type, LabTypeEnum):
            raise KeywordException(
                "SubcloudPickerKeywords: invalid parameter 'lab_type': "
                f"expected None or LabTypeEnum, received {type(lab_type).__name__} ({lab_type!r})."
            )
        if lab_type is not None and not present_in_config:
            raise KeywordException(
                "SubcloudPickerKeywords: invalid parameter combination: 'lab_type' requires 'present_in_config=True' "
                "since lab type is resolved from the lab config."
            )
        if type(present_in_config) is not bool:
            raise KeywordException(
                "SubcloudPickerKeywords: invalid parameter 'present_in_config': "
                f"expected bool, received {type(present_in_config).__name__} ({present_in_config!r})."
            )
        if load is not None and not isinstance(load, str):
            raise KeywordException(
                "SubcloudPickerKeywords: invalid parameter 'load': "
                f"expected None or str, received {type(load).__name__} ({load!r})."
            )
        if isinstance(load, str) and load == "":
            raise KeywordException(
                "SubcloudPickerKeywords: invalid parameter 'load': must be None, 'N-1' or a non-empty explicit version."
            )

    def _resolve_load(self, load: Optional[str]) -> Optional[str]:
        """Resolve the ``load`` filter into a concrete software version string.

        Args:
            load (Optional[str]): Raw filter value. ``None`` or an explicit
                version is returned unchanged. The literal ``"N"`` is resolved
                to the current system version. The literal ``"N-1"`` is
                resolved against the version manager.

        Returns:
            Optional[str]: ``None`` when no load filter was requested, else
            a concrete software version string for textual comparison
            against ``DcManagerSubcloudShowObject.get_software_version()``.
        """
        if load is None:
            return None
        if load == "N":
            return self._version_mgr.get_sw_version().get_name()
        if load != "N-1":
            return load

        sw_version_name = self._version_mgr.get_sw_version().get_name()
        last_major_name = self._version_mgr.get_last_major_release().get_name()
        if last_major_name != sw_version_name:
            return last_major_name
        return self._version_mgr.get_second_last_major_release().get_name()

    def _get_subcloud_list_once(self) -> List[DcManagerSubcloudListObject]:
        """Fetch the ``dcmanager subcloud list`` output once for this call."""
        return self._list_kw.get_dcmanager_subcloud_list().get_dcmanager_subcloud_list_objects()

    def _get_subcloud_show_once(self, name: str) -> DcManagerSubcloudShowObject:
        """Fetch ``dcmanager subcloud show <name>`` for the given subcloud."""
        return self._show_kw.get_dcmanager_subcloud_show(name).get_dcmanager_subcloud_show_object()

    def _get_configured_subcloud_names(self) -> List[str]:
        """Resolve the user-declared subcloud names from the lab config."""
        lab_config = ConfigurationManager.get_lab_config()
        names = lab_config.get_subcloud_names() if lab_config is not None else []
        return list(names) if names is not None else []

    def _apply_list_filters(
        self,
        *,
        subclouds: Iterable[DcManagerSubcloudListObject],
        management_status: Optional[DcManagerSubcloudListManagementEnum],
        availability: Optional[DcManagerSubcloudListAvailabilityEnum],
        expected_sync: Optional[str],
        lab_type: Optional[LabTypeEnum],
        present_in_config: bool,
        configured_names: Optional[List[str]],
    ) -> Tuple[List[Tuple[DcManagerSubcloudListObject, Optional[DcManagerSubcloudShowObject]]], List[Tuple[str, str]]]:
        """Apply the filters that only require ``dcmanager subcloud list``.

        Returns ``(survivors, rejections)``. Each survivor is a tuple
        ``(list_object, None)`` so the ``load`` step can later attach the
        ``dcmanager subcloud show`` object.
        """
        survivors: List[Tuple[DcManagerSubcloudListObject, Optional[DcManagerSubcloudShowObject]]] = []
        rejections: List[Tuple[str, str]] = []
        configured_set = set(configured_names) if configured_names is not None else None

        # Build lab type lookup from config if lab_type filter is active
        lab_config = ConfigurationManager.get_lab_config() if lab_type is not None else None

        for sc in subclouds:
            name = sc.get_name()
            if present_in_config and configured_set is not None and name not in configured_set:
                rejections.append((name, "not present in LabConfig.get_subcloud_names()"))
                continue
            if management_status is not None and sc.get_management() != management_status.value:
                rejections.append(
                    (
                        name,
                        f"management={sc.get_management()} (expected {management_status.value})",
                    )
                )
                continue
            if availability is not None and sc.get_availability() != availability.value:
                rejections.append(
                    (
                        name,
                        f"availability={sc.get_availability()} (expected {availability.value})",
                    )
                )
                continue
            if expected_sync is not None and sc.get_sync() != expected_sync:
                rejections.append(
                    (
                        name,
                        f"sync={sc.get_sync()} (expected {expected_sync})",
                    )
                )
                continue
            if lab_type is not None:
                sc_config = lab_config.get_subcloud(name)
                if sc_config.get_lab_type() != lab_type.value:
                    rejections.append(
                        (
                            name,
                            f"lab_type={sc_config.get_lab_type()} (expected {lab_type.value})",
                        )
                    )
                    continue
            survivors.append((sc, None))
        return survivors, rejections

    def _apply_load_filter(
        self,
        *,
        survivors: List[Tuple[DcManagerSubcloudListObject, Optional[DcManagerSubcloudShowObject]]],
        load_resolved: str,
    ) -> Tuple[List[Tuple[DcManagerSubcloudListObject, Optional[DcManagerSubcloudShowObject]]], List[Tuple[str, str]]]:
        """Resolve ``software_version`` per candidate via ``dcmanager subcloud show``."""
        new_survivors: List[Tuple[DcManagerSubcloudListObject, Optional[DcManagerSubcloudShowObject]]] = []
        rejections: List[Tuple[str, str]] = []

        for list_obj, _ in survivors:
            name = list_obj.get_name()
            show_obj = self._get_subcloud_show_once(name)
            actual_version = show_obj.get_software_version()
            if actual_version != load_resolved:
                rejections.append(
                    (
                        name,
                        f"software_version={actual_version} (expected {load_resolved})",
                    )
                )
                continue
            new_survivors.append((list_obj, show_obj))
        return new_survivors, rejections

    @staticmethod
    def _build_result(
        list_obj: DcManagerSubcloudListObject,
        show_obj: Optional[DcManagerSubcloudShowObject],
    ) -> SubcloudPickResult:
        """Build a ``SubcloudPickResult`` from list/show objects."""
        software_version: Optional[str] = None
        if show_obj is not None:
            software_version = show_obj.get_software_version()
        return SubcloudPickResult(
            name=list_obj.get_name(),
            dcmanager_id=int(list_obj.get_id()),
            software_version=software_version,
            list_object=list_obj,
            show_object=show_obj,
        )

    @staticmethod
    def _format_load_for_log(load_input: Optional[str], load_resolved: Optional[str]) -> Optional[str]:
        """Render the ``load`` filter for diagnostic messages."""
        if load_input is None:
            return None
        if load_input == "N-1":
            return f"N-1 (resolved to {load_resolved})"
        return load_input

    @staticmethod
    def _format_rejection_report(filter_set: dict, rejections: List[Tuple[str, str]]) -> str:
        """Build the multi-line message used when no subcloud satisfies the filters."""
        lines = [
            "SubcloudPickerKeywords: No subclouds match the filters.",
            f"Filters applied: {filter_set}",
        ]
        if rejections:
            lines.append("Evaluated candidates:")
            for name, reason in sorted(rejections, key=lambda pair: pair[0]):
                lines.append(f"  {name}: rejected - {reason}")
        else:
            lines.append("Evaluated candidates: none survived the 'subcloud list' pre-filter.")
        return "\n".join(lines)


def pick_subcloud_with_fallback(
    *,
    availability: Optional[DcManagerSubcloudListAvailabilityEnum] = None,
    management_status: Optional[DcManagerSubcloudListManagementEnum] = None,
    in_sync: Optional[bool] = None,
    load: Optional[str] = None,
    lab_type: Optional[LabTypeEnum] = None,
    present_in_config: bool = True,
) -> Tuple[SSHConnection, "SubcloudPickResult"]:
    """Pick a subcloud with automatic fallback to secondary system controller.

    Tries the primary system controller first. If no subcloud matches and a
    secondary system controller is configured, retries on the secondary.
    This supports post-rehoming scenarios where subclouds may have moved
    to the peer cloud.

    When no secondary system controller is configured, behaves identically
    to calling SubcloudPickerKeywords.pick_one() directly.

    Args:
        availability (Optional[DcManagerSubcloudListAvailabilityEnum]): Availability filter.
        management_status (Optional[DcManagerSubcloudListManagementEnum]): Management filter.
        in_sync (Optional[bool]): Sync filter. None = skip, True = in-sync, False = out-of-sync.
        load (Optional[str]): Software version filter. "N", "N-1", or explicit version.
        lab_type (Optional[LabTypeEnum]): Lab type filter (SIMPLEX, DUPLEX).
        present_in_config (bool): Whether subcloud must be in lab config.

    Returns:
        Tuple[SSHConnection, SubcloudPickResult]: The SSH connection to the system
            controller that owns the subcloud, and the pick result.

    Raises:
        KeywordException: If no subcloud matches on either system controller.
    """
    from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()

    try:
        result = SubcloudPickerKeywords(system_controller_ssh).pick_one(
            availability=availability,
            management_status=management_status,
            in_sync=in_sync,
            load=load,
            lab_type=lab_type,
            present_in_config=present_in_config,
        )
        return system_controller_ssh, result
    except KeywordException:
        secondary_config = ConfigurationManager.get_lab_config().get_secondary_system_controller()
        if secondary_config is None:
            raise
        get_logger().log_info("No matching subcloud on primary SC, falling back to secondary system controller")
        system_controller_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()
        result = SubcloudPickerKeywords(system_controller_ssh).pick_one(
            availability=availability,
            management_status=management_status,
            in_sync=in_sync,
            load=load,
            lab_type=lab_type,
            present_in_config=present_in_config,
        )
        return system_controller_ssh, result

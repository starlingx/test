from framework.logging.automation_logger import get_logger
from framework.redfish.client.redfish_client import RedFishClient
from framework.redfish.objects.bios import Bios
from framework.redfish.objects.bios_attribute import BiosAttribute
from framework.redfish.operations.get_system_info import GetSystemInfo

# Property name used to request that a BIOS settings PATCH only take
# effect on the next host reset, rather than immediately. Most BMCs honor
# this even when they do not explicitly advertise support for it via
# Bios.supported_apply_times; a minority (observed on Supermicro) reject
# the property outright with an HTTP 400 "unknown property" error.
_SETTINGS_APPLY_TIME_PROPERTY = "@Redfish.SettingsApplyTime"
_SETTINGS_APPLY_TIME_ON_RESET = {"ApplyTime": "OnReset"}

# ResetType values to try, in preference order: graceful first, then an
# immediate/forceful fallback if the BMC does not support the graceful one.
_RESET_TYPE_PREFERENCE = ["GracefulRestart", "ForceRestart"]


class BiosOperations:
    """Operations for discovering and changing BIOS attributes over Redfish.

    Mirrors :class:`BootOrderOperations` for discovery (fetch a
    sub-resource, wrap each entry in its own object) and the reset-action
    pattern used by ``RedFishChassisPowerKeywords`` for applying a staged
    change. This is the native (no external CLI/subprocess) equivalent of
    the bundled ``biostool`` script's Redfish logic.
    """

    def __init__(self, bmc_ip: str, username: str, password: str):
        """Initialize BiosOperations for a given BMC.

        Args:
            bmc_ip (str): The BMC IP address or hostname.
            username (str): The BMC username for Basic Authentication.
            password (str): The BMC password for Basic Authentication.
        """
        self.redfish_client = RedFishClient(bmc_ip, username, password)
        self.sys_info = GetSystemInfo(bmc_ip, username, password)
        self.system_id = self.sys_info.get_system_id()

    def get_bios(self) -> Bios:
        """Fetch this system's Bios resource.

        Returns:
            Bios: The current Bios resource.

        Raises:
            RuntimeError: If the Bios resource could not be fetched.
        """
        bios_uri = f"{self.system_id}/Bios"
        resp = self.redfish_client.get(bios_uri)
        if resp.status != 200:
            raise RuntimeError(f"GET {bios_uri} failed with HTTP status {resp.status}")
        return Bios(resp.dict)

    def get_attribute(self, name: str, bios: Bios | None = None) -> BiosAttribute:
        """Fetch a single BIOS attribute, fully populated.

        Combines the attribute's current value (from the Bios resource),
        its pending value (from the pending-settings resource, if a
        change is staged), and its allowable value pairs and type (from
        the AttributeRegistry, if the BMC publishes one).

        Args:
            name (str): The BIOS attribute name.
            bios (Optional[Bios]): A previously-fetched Bios resource to
                reuse, to avoid a redundant GET when the caller already
                has one. Fetched fresh if not provided.

        Returns:
            BiosAttribute: The fully populated attribute.

        Raises:
            KeyError: If no attribute with this name exists on the Bios
                resource.
            RuntimeError: If a required Redfish request fails.
        """
        bios = bios or self.get_bios()
        if name not in bios.get_attributes():
            raise KeyError(f"'{name}' is not a BIOS attribute on this system. Published attributes: {sorted(bios.get_attributes().keys())}")
        registry_doc = self._fetch_attribute_registry(bios.get_attribute_registry())
        return self._build_bios_attribute(name, bios, registry_doc)

    def find_attributes(self, token: str) -> list[BiosAttribute]:
        """Find and fully populate every attribute whose name contains ``token``.

        Args:
            token (str): Substring to match against attribute names
                (case-insensitive).

        Returns:
            list[BiosAttribute]: The matching attributes, fully populated,
            in the order their names sort.
        """
        bios = self.get_bios()
        matching_names = bios.find_attribute_names(token)
        registry_doc = self._fetch_attribute_registry(bios.get_attribute_registry())
        return [self._build_bios_attribute(name, bios, registry_doc) for name in matching_names]

    def set_attributes(self, changes: dict[str, str]) -> None:
        """Stage one or more BIOS attribute changes.

        Each requested value is resolved (via :meth:`BiosAttribute.resolve_value`)
        to the form this BMC's Settings resource expects before the PATCH is
        sent. The change is only staged; it does not take effect until
        :meth:`reset_host` is called.

        Args:
            changes (dict[str, str]): Mapping of attribute name to the
                requested target value (either ValueName or
                ValueDisplayName form is accepted for enum attributes).

        Raises:
            KeyError: If any name is not a BIOS attribute on this system.
            ValueError: If any value does not match an allowable value
                for its attribute.
            RuntimeError: If the PATCH ultimately fails.
        """
        if not changes:
            get_logger().log_info("set_attributes called with no changes; nothing to do.")
            return

        bios = self.get_bios()
        registry_doc = self._fetch_attribute_registry(bios.get_attribute_registry())

        resolved_changes = {}
        for name, requested_value in changes.items():
            attribute = self._build_bios_attribute(name, bios, registry_doc)
            resolved_value = attribute.resolve_value(requested_value)
            if resolved_value == attribute.get_current_value():
                get_logger().log_info(f"Attribute '{name}' is already set to '{resolved_value}'; no change needed.")
                continue
            if resolved_value != requested_value:
                get_logger().log_info(f"Translated requested value '{requested_value}' to '{resolved_value}' (the form this BMC's resource expects) for '{name}'.")
            resolved_changes[name] = resolved_value

        if not resolved_changes:
            get_logger().log_info("No changes to apply; all requested values already match.")
            return

        self._patch_settings(bios, resolved_changes)
        get_logger().log_info(f"Staged attribute(s) {resolved_changes} via {bios.get_settings_uri()}.")

    def reset_host(self) -> None:
        """Reboot the host, preferring a graceful restart.

        This is the action that applies any change staged by
        :meth:`set_attributes`.

        Raises:
            RuntimeError: If the system does not publish a usable
                ComputerSystem.Reset action, or the BMC rejects every
                attempted ResetType.
        """
        resp = self.redfish_client.get(self.system_id)
        if resp.status != 200:
            raise RuntimeError(f"GET {self.system_id} failed with HTTP status {resp.status}")

        reset_action = (resp.dict.get("Actions") or {}).get("#ComputerSystem.Reset")
        if not reset_action:
            raise RuntimeError(f"System {self.system_id} does not publish a #ComputerSystem.Reset action.")

        target = reset_action.get("target")
        allowable = reset_action.get("ResetType@Redfish.AllowableValues") or []
        if not target or not allowable:
            raise RuntimeError(f"#ComputerSystem.Reset action on {self.system_id} is missing a target or allowable ResetType values.")

        reset_type = next((candidate for candidate in _RESET_TYPE_PREFERENCE if candidate in allowable), None)
        if reset_type is None:
            raise RuntimeError(f"None of the preferred reset types {_RESET_TYPE_PREFERENCE} are in the BMC's allowable ResetType values: {allowable}")

        get_logger().log_info(f"Resetting host via {target} with ResetType='{reset_type}'.")
        post_resp = self.redfish_client.post(target, body={"ResetType": reset_type})
        if post_resp.status not in (200, 202, 204):
            raise RuntimeError(f"POST {target} with ResetType='{reset_type}' failed with HTTP status {post_resp.status}")

    # --- internal helpers ---

    def _fetch_attribute_registry(self, registry_name: str) -> dict | None:
        """Fetch the full AttributeRegistry document by name.

        Walks ``/redfish/v1/Registries`` to find the member matching
        ``registry_name`` (ignoring any trailing ``.vX_Y_Z`` version
        suffix), then fetches and returns its document.

        Args:
            registry_name (str): The registry name as published by the
                Bios resource's ``AttributeRegistry`` field.

        Returns:
            Optional[dict]: The registry document, or None if no registry
            name was given, no matching member was found, or any request
            in the lookup chain failed.
        """
        if not registry_name:
            return None

        target_base = self._registry_base_name(registry_name)
        resp = self.redfish_client.get("/redfish/v1/Registries")
        if resp.status != 200:
            get_logger().log_debug(f"GET /redfish/v1/Registries failed with HTTP status {resp.status}; proceeding without allowable-value metadata.")
            return None

        for member in resp.dict.get("Members") or []:
            member_uri = member.get("@odata.id")
            if not member_uri:
                continue
            entry_resp = self.redfish_client.get(member_uri)
            if entry_resp.status != 200:
                continue
            entry = entry_resp.dict
            entry_id_base = self._registry_base_name(entry.get("Id") or "")
            entry_name_base = self._registry_base_name(entry.get("Name") or "")
            if target_base != entry_id_base and target_base != entry_name_base:
                continue
            for location in entry.get("Location") or []:
                registry_uri = (location.get("Uri") or {}).get("@odata.id") if isinstance(location.get("Uri"), dict) else location.get("Uri")
                if not registry_uri:
                    continue
                doc_resp = self.redfish_client.get(registry_uri)
                if doc_resp.status == 200:
                    return doc_resp.dict
        return None

    @staticmethod
    def _registry_base_name(name: str) -> str:
        """Strip a trailing ".vX_Y_Z" version suffix from a registry name.

        Args:
            name (str): The registry name, with or without a version suffix.

        Returns:
            str: The base name, with any version suffix removed.
        """
        return name.split(".")[0] if name else name

    def _build_bios_attribute(self, name: str, bios: Bios, registry_doc: dict | None) -> BiosAttribute:
        """Build a fully populated BiosAttribute from a Bios resource and registry.

        Args:
            name (str): The attribute name.
            bios (Bios): The Bios resource that has this attribute's
                current value.
            registry_doc (Optional[dict]): The AttributeRegistry document,
                or None if unavailable.

        Returns:
            BiosAttribute: The populated attribute. Its ``pending_value``
            is best-effort: left as None if the pending-settings resource
            could not be read.
        """
        current_value = bios.get_attribute_value(name)
        value_pairs, attribute_type = self._extract_registry_entry(registry_doc, name)
        pending_value = self._fetch_pending_value(bios, name)
        return BiosAttribute(name=name, current_value=current_value, pending_value=pending_value, value_pairs=value_pairs, attribute_type=attribute_type)

    @staticmethod
    def _extract_registry_entry(registry_doc: dict | None, name: str) -> tuple[list[tuple], str | None]:
        """Extract one attribute's (value_name, value_display_name) pairs and type.

        Args:
            registry_doc (Optional[dict]): The AttributeRegistry document.
            name (str): The attribute name to look up.

        Returns:
            tuple: ``(value_pairs, attribute_type)``. ``value_pairs`` is an
            empty list if the registry or attribute is unavailable, or if
            the attribute is not an Enumeration type.
        """
        if not registry_doc:
            return [], None
        for attr in (registry_doc.get("RegistryEntries") or {}).get("Attributes") or []:
            if attr.get("AttributeName") == name:
                attribute_type = attr.get("Type")
                pairs = [(v.get("ValueName"), v.get("ValueDisplayName")) for v in attr.get("Value") or [] if v.get("ValueName") is not None or v.get("ValueDisplayName") is not None]
                return pairs, attribute_type
        return [], None

    def _fetch_pending_value(self, bios: Bios, name: str) -> str | None:
        """Best-effort fetch of an attribute's pending value from the Settings resource.

        Args:
            bios (Bios): The Bios resource (for its settings_uri).
            name (str): The attribute name.

        Returns:
            Optional[str]: The pending value, or None if nothing is
            staged, the Settings resource could not be read, or the
            attribute is not present in it.
        """
        resp = self.redfish_client.get(bios.get_settings_uri())
        if resp.status != 200:
            return None
        return (resp.dict.get("Attributes") or {}).get(name)

    def _patch_settings(self, bios: Bios, resolved_changes: dict[str, str]) -> None:
        """PATCH the Settings resource, adapting apply-time to BMC support.

        Tries the PATCH with ``@Redfish.SettingsApplyTime: OnReset`` first
        (the proven HPE/Dell behavior, and the common case even for BMCs
        that do not explicitly advertise support for it). If the BMC
        rejects that property as unknown (observed on Supermicro), retries
        without it; the change then applies on the next reset by the
        BMC's own default behavior.

        Args:
            bios (Bios): The Bios resource (for its settings_uri).
            resolved_changes (dict[str, str]): Attribute name -> value,
                already resolved to the form this BMC expects.

        Raises:
            RuntimeError: If the PATCH fails for a reason other than an
                apply-time property rejection, or if the retry without the
                property also fails.
        """
        settings_uri = bios.get_settings_uri()
        base_payload = {"Attributes": resolved_changes}

        with_apply_time = dict(base_payload)
        with_apply_time[_SETTINGS_APPLY_TIME_PROPERTY] = _SETTINGS_APPLY_TIME_ON_RESET

        resp = self.redfish_client.patch(settings_uri, body=with_apply_time)
        if resp.status in (200, 202, 204):
            return

        if self._looks_like_apply_time_unsupported(resp):
            get_logger().log_warning("BMC rejected @Redfish.SettingsApplyTime as an unknown property; retrying the BIOS settings PATCH without it (the change will apply on the next reset, per this BMC's default behavior).")
            retry_resp = self.redfish_client.patch(settings_uri, body=dict(base_payload))
            if retry_resp.status in (200, 202, 204):
                return
            raise RuntimeError(f"PATCH {settings_uri} failed with HTTP status {retry_resp.status} (also failed without @Redfish.SettingsApplyTime): {retry_resp.dict}")

        raise RuntimeError(f"PATCH {settings_uri} failed with HTTP status {resp.status}: {resp.dict}")

    @staticmethod
    def _looks_like_apply_time_unsupported(resp) -> bool:
        """Heuristic: does this failed PATCH response mean apply-time is unsupported?

        Args:
            resp: The Redfish response object from the failed PATCH.

        Returns:
            bool: True if the response indicates
            ``@Redfish.SettingsApplyTime`` is not a valid property for
            this BMC's Settings resource.
        """
        text = str(resp.dict)
        return "SettingsApplyTime" in text and ("PropertyUnknown" in text or "not in the list of valid properties" in text)

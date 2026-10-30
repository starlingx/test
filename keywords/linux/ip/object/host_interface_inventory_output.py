"""Independent host interface and sysfs identity evidence."""

import json
import re
from copy import deepcopy
from pathlib import PurePosixPath


class HostInterfaceInventoryOutput:
    """Parse interface flags/types and PF/VF device paths."""

    PCI_PATTERN = re.compile(r"[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]")

    def __init__(self, link_output: str | list[str]):
        """Select admin-UP interfaces independently of exporter metrics.

        Args:
            link_output (str | list[str]): JSON from ip -d -j link show.
        """
        links = json.loads("\n".join(link_output) if isinstance(link_output, list) else link_output)
        self.interfaces = {}
        for link in links:
            flags = link["flags"]
            if "UP" not in flags or "LOOPBACK" in flags or link.get("linkinfo", {}).get("info_kind") == "veth":
                continue
            name = link["ifname"]
            if not name or "/" in name or name in self.interfaces:
                raise ValueError("Missing, unsafe or duplicate host interface name")
            self.interfaces[name] = {"pciaddr": "", "vfs": {}}
        if not self.interfaces:
            raise ValueError("Host returned no eligible interface identities")

    def get_interface_names(self) -> tuple[str, ...]:
        """Return selected host interface names.

        Returns:
            tuple[str, ...]: Interface names to resolve through sysfs.
        """
        return tuple(self.interfaces)

    def set_device_paths(self, interface: str, output: str | list[str]) -> None:
        """Parse the device path followed by virtfn-index/resolved-path rows.

        Args:
            interface (str): Selected interface name.
            output (str | list[str]): Checked sysfs command output; empty for virtual devices.
        """
        lines = ("\n".join(line.rstrip("\r\n") for line in output) if isinstance(output, list) else output).splitlines()
        if not lines:
            return
        device_path = PurePosixPath(lines[0])
        self.interfaces[interface]["pciaddr"] = next((part for part in reversed(device_path.parts) if self.PCI_PATTERN.fullmatch(part)), "")
        vfs = {}
        for line in lines[1:]:
            link, path = line.split()
            if not re.fullmatch(r"virtfn[0-9]+", link) or not self.PCI_PATTERN.fullmatch(PurePosixPath(path).name) or link[6:] in vfs:
                raise ValueError("Invalid or duplicate VF sysfs identity")
            vfs[link[6:]] = PurePosixPath(path).name
        self.interfaces[interface]["vfs"] = vfs

    def get_interfaces(self) -> dict[str, dict]:
        """Return independent PF/VF identities without exposing mutable state.

        Returns:
            dict[str, dict]: Interface PCI address and indexed VF PCI addresses.
        """
        return deepcopy(self.interfaces)

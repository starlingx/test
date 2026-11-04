"""Strict parsing of the exporter's numeric OpenMetrics samples."""

import math
import re

from keywords.cloud_platform.applications.object.interface_metric_sample import InterfaceMetricSample


class InterfaceMetricsOutput:
    """Preserve exact sample identities; reject ambiguous or malformed evidence."""

    SAMPLE_PATTERN = re.compile(r'([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{((?:[^"{}]|"(?:\\.|[^"\\])*")*)\})?\s+([^\s]+)(?:\s+([0-9]+))?')
    LABEL_PATTERN = re.compile(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)="((?:[^"\\]|\\[\\"n])*)"\s*(?:,|$)')

    def __init__(self, body: str):
        """Parse a nonempty scrape, allowing comments and escaped label values.

        Args:
            body (str): Successful HTTP response body.
        """
        self.samples = {}
        seen_device_identities = set()
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = self.SAMPLE_PATTERN.fullmatch(line)
            if not match:
                raise ValueError(f"Malformed exporter sample: {line!r}")
            name, raw_labels, raw_sample_value, _ = match.groups()
            labels, label_offset = {}, 0
            raw_labels = raw_labels or ""
            while label_offset < len(raw_labels):
                label = self.LABEL_PATTERN.match(raw_labels, label_offset)
                if not label or label[1] in labels:
                    raise ValueError(f"Malformed or duplicate metric label: {line!r}")
                labels[label[1]] = re.sub(r'\\([\\"n])', lambda item: "\n" if item[1] == "n" else item[1], label[2])
                label_offset = label.end()
            if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", raw_sample_value):
                raise ValueError(f"Invalid numeric exporter value: {raw_sample_value!r}")
            value = float(raw_sample_value)
            identity = (name, tuple(sorted(labels.items())))
            if not math.isfinite(value) or identity in self.samples:
                raise ValueError(f"Nonfinite or duplicate exporter sample: {line!r}")
            if name in ("network_interface_device_info", "network_interface_vf_device_info"):
                required_identity_labels = ("device", "vf", "pciaddr") if name == "network_interface_vf_device_info" else ("device",)
                if any(not labels.get(key) for key in required_identity_labels):
                    raise ValueError(f"Missing exporter identity labels: {line!r}")
                device_identity = (name, labels["device"], labels.get("vf"))
                if device_identity in seen_device_identities or value != 1:
                    raise ValueError(f"Contradictory exporter identity: {line!r}")
                seen_device_identities.add(device_identity)
            self.samples[identity] = InterfaceMetricSample(name, labels, value)
        if not self.samples:
            raise ValueError("Exporter returned no numeric samples")

    def get_samples(self) -> list[InterfaceMetricSample]:
        """Return the parsed metric sample objects.

        Returns:
            list[InterfaceMetricSample]: Validated samples.
        """
        return list(self.samples.values())

    def require_sample(self, name: str, labels: dict[str, str]) -> float:
        """Require exactly one sample matching a family and independent identity.

        Args:
            name (str): Exact metric name, never a prefix.
            labels (dict[str, str]): Expected labels from independent host inventory.

        Returns:
            float: Finite numeric value of the unique matching sample.
        """
        matching_sample_values = [sample.get_value() for sample in self.samples.values() if sample.get_name() == name and labels.items() <= sample.get_labels().items()]
        if len(matching_sample_values) != 1:
            raise ValueError(f"Expected one {name} sample for {labels}, found {len(matching_sample_values)}")
        return matching_sample_values[0]

    def verify_interfaces(self, inventory: dict[str, dict]) -> None:
        """Check PF/VF identity records against a nonempty independent inventory.

        The caller selects the interfaces relevant to its endpoint. VF coverage
        is required only when that inventory includes VFs.

        Args:
            inventory (dict[str, dict]): Device records with pciaddr and vf PCI mappings.
        """
        if not inventory:
            raise ValueError("Independent interface inventory must not be empty")
        for device, record in inventory.items():
            labels = {"device": device}
            if record["pciaddr"]:
                labels["pciaddr"] = record["pciaddr"]
            if self.require_sample("network_interface_device_info", labels) != 1:
                raise ValueError(f"Invalid device identity value for {device}")
            for vf_index, vf_pci_address in record.get("vfs", {}).items():
                if self.require_sample("network_interface_vf_device_info", {"device": device, "vf": str(vf_index), "pciaddr": vf_pci_address}) != 1:
                    raise ValueError(f"Invalid VF identity value for {device}/{vf_index}")

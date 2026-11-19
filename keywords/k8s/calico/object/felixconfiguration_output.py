"""Output object for FelixConfiguration CR."""

import yaml


class FelixConfigurationOutput:
    """Parsed output from kubectl get felixconfiguration default -o yaml."""

    def __init__(self, raw_output: str | list[str]):
        """Parse raw YAML output.

        Args:
            raw_output (str | list[str]): Raw SSH command output.
        """
        content = "".join(raw_output) if isinstance(raw_output, list) else raw_output
        self.data = yaml.safe_load(content) or {}
        self.spec = self.data.get("spec") or {}

    def get_default_endpoint_to_host_action(self) -> str:
        """Get defaultEndpointToHostAction value.

        Returns:
            str: Action string (e.g. "Accept").
        """
        return self.spec.get("defaultEndpointToHostAction", "")

    def get_log_severity_screen(self) -> str:
        """Get logSeverityScreen value.

        Returns:
            str: Log severity string (e.g. "Warning").
        """
        return self.spec.get("logSeverityScreen", "")

    def get_iptables_backend(self) -> str:
        """Get iptablesBackend value.

        Returns:
            str: Backend string (e.g. "Auto").
        """
        return self.spec.get("iptablesBackend", "")

    def get_failsafe_inbound_ports(self) -> list:
        """Get the failsafe inbound host ports as (protocol, port) tuples.

        Returns:
            list: (protocol, port) tuples, e.g. [("TCP", 22), ("UDP", 68)].
        """
        return [(entry.get("protocol", ""), entry.get("port")) for entry in self.spec.get("failsafeInboundHostPorts", [])]

    def get_failsafe_outbound_ports(self) -> list:
        """Get the failsafe outbound host ports as (protocol, port) tuples.

        Returns:
            list: (protocol, port) tuples, e.g. [("UDP", 53), ("TCP", 179)].
        """
        return [(entry.get("protocol", ""), entry.get("port")) for entry in self.spec.get("failsafeOutboundHostPorts", [])]

    def __str__(self) -> str:
        """Human-readable representation of the FelixConfiguration.

        Returns:
            str: Summary of the key FelixConfiguration spec fields.
        """
        return f"FelixConfiguration(defaultEndpointToHostAction={self.get_default_endpoint_to_host_action()}, logSeverityScreen={self.get_log_severity_screen()}, iptablesBackend={self.get_iptables_backend()})"

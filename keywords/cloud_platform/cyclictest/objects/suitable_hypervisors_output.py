from typing import Dict, List, Optional

from keywords.cloud_platform.system.host.objects.system_host_cpu_output import SystemHostCPUOutput


class SuitableHypervisorsOutput:
    """Holds the result of a suitable-hypervisors scan.

    Performed by
    :meth:`~keywords.cloud_platform.cyclictest.cyclictest_keywords.CyclictestKeywords.get_suitable_hypervisors`.

    Each entry maps a hostname to the :class:`SystemHostCPUOutput` collected
    for that host, with additional test-run metadata attached as typed
    attributes (``isolated_cores``, ``vm_cores``, ``personalities``, etc.).
    """

    def __init__(self) -> None:
        """Constructor — starts with an empty hypervisor map."""
        self._hypervisors: Dict[str, SystemHostCPUOutput] = {}

    def add_hypervisor(self, hostname: str, cpu_output: SystemHostCPUOutput) -> None:
        """Register a hypervisor and its associated CPU output.

        Args:
            hostname (str): Hostname of the hypervisor, e.g. ``'controller-0'``.
            cpu_output (SystemHostCPUOutput): Parsed CPU output for *hostname*,
                with ``isolated_cores``, ``vm_cores``, ``personalities``,
                ``num_threads``, ``num_cores``, and ``for_host_test``
                attributes attached by the caller.
        """
        self._hypervisors[hostname] = cpu_output

    def get_hostnames(self) -> List[str]:
        """Return the list of registered hypervisor hostnames.

        Returns:
            List[str]: Hostnames in insertion order.
        """
        return list(self._hypervisors.keys())

    def get_cpu_output(self, hostname: str) -> Optional[SystemHostCPUOutput]:
        """Return the :class:`SystemHostCPUOutput` for a specific hostname.

        Args:
            hostname (str): Hostname to look up.

        Returns:
            Optional[SystemHostCPUOutput]: The CPU output object, or ``None``
                if *hostname* is not registered.
        """
        return self._hypervisors.get(hostname)

    def get_all_cpu_outputs(self) -> Dict[str, SystemHostCPUOutput]:
        """Return the full hostname → :class:`SystemHostCPUOutput` mapping.

        Returns:
            Dict[str, SystemHostCPUOutput]: A shallow copy of the internal map.
        """
        return dict(self._hypervisors)

    def is_empty(self) -> bool:
        """Return ``True`` if no hypervisors have been registered.

        Returns:
            bool: ``True`` when the hypervisor map is empty.
        """
        return len(self._hypervisors) == 0

    def __contains__(self, hostname: str) -> bool:
        """Support the ``in`` operator for hostname membership tests.

        Args:
            hostname (str): Hostname to check.

        Returns:
            bool: ``True`` if *hostname* is registered.
        """
        return hostname in self._hypervisors

    def __iter__(self):
        """Iterate over registered hostnames."""
        return iter(self._hypervisors)

    def __len__(self) -> int:
        """Return the number of registered hypervisors."""
        return len(self._hypervisors)

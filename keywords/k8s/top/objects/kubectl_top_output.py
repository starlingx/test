from typing import List

from keywords.k8s.top.objects.kubectl_top_object import KubectlTopObject


class KubectlTopOutput:
    """
    Parses the output of `kubectl top nodes` / `kubectl top pods` into KubectlTopObjects.

    Unlike most k8s tables, `kubectl top` cells never contain spaces (a quantity is a single
    token such as "445m" or "8996Mi"), so the rows are split on whitespace by column position
    rather than sliced at header offsets. This is both simpler and more robust than the
    offset-based table parser, which assumes the header and every data row are
    character-aligned - something real top output does not guarantee as values change width.

    Column layout by resource:
        nodes: NAME CPU(cores) CPU(%) MEMORY(bytes) MEMORY(%)
        pods:  NAME CPU(cores) MEMORY(bytes)
    So CPU is always column 1, and memory is column 3 for nodes and column 2 for pods.
    """

    _MEMORY_COLUMN = {"nodes": 3, "pods": 2}

    def __init__(self, kubectl_top_output: str, resource: str):
        """
        Constructor.

        Args:
            kubectl_top_output (str): raw output from a kubectl top command, including the
                header line.
            resource (str): the resource the table describes, "nodes" or "pods".

        Raises:
            ValueError: if resource is not "nodes" or "pods".
        """
        if resource not in self._MEMORY_COLUMN:
            raise ValueError(f"resource must be 'nodes' or 'pods', got {resource!r}")
        self.resource = resource
        self.kubectl_top_entries: List[KubectlTopObject] = []

        memory_column = self._MEMORY_COLUMN[resource]
        lines = kubectl_top_output if isinstance(kubectl_top_output, list) else str(kubectl_top_output).splitlines()
        for line in lines:
            fields = str(line).split()
            # Skip the header row and any blank line. Data rows have the name plus at least
            # the CPU and the memory column.
            if not fields or fields[0] == "NAME" or len(fields) <= memory_column:
                continue
            entry = KubectlTopObject(fields[0])
            entry.set_cpu(fields[1])
            entry.set_memory(fields[memory_column])
            self.kubectl_top_entries.append(entry)

    def get_resource(self) -> str:
        """
        Getter for the resource this table describes.

        Returns:
            str: "nodes" or "pods".
        """
        return self.resource

    def get_entries(self) -> List[KubectlTopObject]:
        """
        Get all parsed top entries.

        Returns:
            List[KubectlTopObject]: one object per node or pod row.
        """
        return self.kubectl_top_entries

    def get_entry(self, name: str) -> KubectlTopObject:
        """
        Get the top entry with the given name.

        Args:
            name (str): the node or pod name.

        Returns:
            KubectlTopObject: the matching entry.

        Raises:
            ValueError: if no entry with that name is present.
        """
        entries = list(filter(lambda entry: entry.get_name() == name, self.kubectl_top_entries))
        if len(entries) == 0:
            raise ValueError(f"No top entry named {name!r} in the {self.resource} output")
        return entries[0]

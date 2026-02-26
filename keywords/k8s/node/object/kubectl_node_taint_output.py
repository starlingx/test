from keywords.k8s.node.object.kubectl_node_taint_object import KubectlNodeTaintObject


class KubectlNodeTaintOutput:
    """
    Parses the output from kubectl get nodes with taint information

    Methods:
        get_taints(): Returns list of parsed taint objects
    """

    def __init__(self, raw_output: str | list):
        """
        Initialize with raw output and parse it.

        Args:
            raw_output (str | list): The raw command output
        """
        if isinstance(raw_output, list):
            raw_output = "".join(raw_output)
        self.raw_output = raw_output
        self.taints = self._parse_output(self.raw_output)

    def _parse_output(self, output: str) -> list[KubectlNodeTaintObject]:
        """
        Parses the kubectl output into taint objects

        Args:
            output (str): Raw command output

        Returns:
            list[KubectlNodeTaintObject]: List of parsed taint objects
        """
        taints = []
        for line in output.strip().splitlines():
            if not line.strip() or ("Node" in line and "Taint" in line):
                continue
            # Split by tab or multiple spaces
            parts = line.split('\t') if '\t' in line else line.split()
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                node = parts[0]
                # All remaining parts are taint strings
                taint_strs = parts[1:]
                for taint_str in taint_strs:
                    if "=" in taint_str and ":" in taint_str:
                        taint_obj = KubectlNodeTaintObject()
                        taint_obj.set_node(node)
                        key_value, effect = taint_str.rsplit(":", 1)
                        key, value = key_value.split("=", 1)
                        taint_obj.set_key(key)
                        taint_obj.set_value(value)
                        taint_obj.set_effect(effect)
                        taints.append(taint_obj)
        return taints

    def get_taints(self) -> list[KubectlNodeTaintObject]:
        """
        Returns the list of parsed taint objects

        Returns:
            list[KubectlNodeTaintObject]: List of taint objects
        """
        return self.taints

    def is_taints_enabled(self, key: str, effect: str = None) -> bool:
        """
        Check if any node has a specific taint

        Args:
            key (str): Taint key to check
            effect (str): Optional taint effect to check

        Returns:
            bool: True if taint exists, False otherwise
        """
        for taint in self.taints:
            if taint.get_key() == key:
                if effect is None or taint.get_effect() == effect:
                    return True
        return False

    def count_taints(self, key: str = None) -> int:
        """
        Count taints, optionally filtered by key

        Args:
            key (str): Optional taint key to filter

        Returns:
            int: Count of taints
        """
        if key is None:
            return len(self.taints)
        return sum(1 for t in self.taints if t.get_key() == key)

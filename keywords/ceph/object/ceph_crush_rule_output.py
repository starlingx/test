import json
from typing import List, Union

from framework.exceptions.keyword_exception import KeywordException

# CRUSH rule steps that pick the failure domain, e.g. {"op": "chooseleaf_firstn", "type": "host"}.
CHOOSE_OPS = ("choose_firstn", "chooseleaf_firstn", "choose_indep", "chooseleaf_indep")


class CephCrushRuleOutput:
    """Parses the output of the 'ceph osd crush rule dump <rule> -f json' command.

    Example::

        {
            "rule_id": 2,
            "rule_name": "kube-rbd_host",
            "type": 1,
            "steps": [
                {"op": "take", "item": -2, "item_name": "storage-tier"},
                {"op": "chooseleaf_firstn", "num": 0, "type": "host"},
                {"op": "emit"}
            ]
        }

    The 'take' step names the root (and optionally a device class, as
    'root~class') the rule starts from, and the 'choose'/'chooseleaf' step
    names the bucket type replicas are spread across (the failure domain).
    """

    def __init__(self, ceph_crush_rule_output: Union[str, List[str]]):
        """Constructor.

        Args:
            ceph_crush_rule_output (Union[str, List[str]]): Raw output from
                running the 'ceph osd crush rule dump <rule> -f json' command.
        """
        content = "\n".join(ceph_crush_rule_output) if isinstance(ceph_crush_rule_output, list) else str(ceph_crush_rule_output)
        rule = json.loads(content)
        self.rule_name: str = rule["rule_name"]
        self.steps: List[dict] = rule["steps"]

    def get_rule_name(self) -> str:
        """Get the name of the CRUSH rule.

        Returns:
            str: The rule name, e.g. 'kube-rbd_host'.
        """
        return self.rule_name

    def get_failure_domain(self) -> str:
        """Get the failure domain (bucket type) the rule spreads replicas across.

        Returns:
            str: The bucket type of the rule's choose/chooseleaf step, e.g. 'host' or 'osd'.

        Raises:
            KeywordException: If the rule has no choose/chooseleaf step.
        """
        for step in self.steps:
            if step.get("op") in CHOOSE_OPS:
                return step["type"]
        raise KeywordException(f"CRUSH rule '{self.rule_name}' has no choose/chooseleaf step, so its failure domain cannot be determined.")

    def get_root(self) -> str:
        """Get the CRUSH root the rule starts from.

        Returns:
            str: The root name, e.g. 'storage-tier'.

        Raises:
            KeywordException: If the rule has no 'take' step.
        """
        root, _ = self._get_take_item()
        return root

    def get_device_class(self) -> str:
        """Get the device class the rule is restricted to, if any.

        Returns:
            str: The device class (e.g. 'ssd'), or an empty string when the rule has none.

        Raises:
            KeywordException: If the rule has no 'take' step.
        """
        _, device_class = self._get_take_item()
        return device_class

    def _get_take_item(self) -> tuple[str, str]:
        """Split the 'take' step item name into root and device class.

        Returns:
            tuple[str, str]: (root, device_class). device_class is empty when the rule has none.

        Raises:
            KeywordException: If the rule has no 'take' step.
        """
        for step in self.steps:
            if step.get("op") == "take":
                root, _, device_class = step["item_name"].partition("~")
                return root, device_class
        raise KeywordException(f"CRUSH rule '{self.rule_name}' has no 'take' step, so its root cannot be determined.")

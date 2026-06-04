"""Security Group CRUD keywords via OpenStack SDK."""

from typing import Optional

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.security_groups.object.security_group_object import SecurityGroupObject
from keywords.openstack.resources.security_groups.object.security_group_output import SecurityGroupOutput


class SecurityGroupKeywords(BaseKeyword):
    """CRUD operations for Neutron security groups and rules via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection) -> None:
        """Initialize SecurityGroupKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def list_security_groups(self, name: Optional[str] = None) -> SecurityGroupOutput:
        """List security groups, optionally filtered by name.

        Args:
            name (Optional[str]): Filter by security group name.

        Returns:
            SecurityGroupOutput: Parsed security group collection.
        """
        network = self.openstack_connection.get_network()
        if name:
            sgs = list(network.security_groups(name=name))
        else:
            sgs = list(network.security_groups())

        objects = []
        for sg in sgs:
            obj = SecurityGroupObject()
            obj.set_id(sg.id)
            obj.set_name(sg.name)
            obj.set_rules(sg.security_group_rules or [])
            objects.append(obj)

        return SecurityGroupOutput(objects)

    def create_allow_all_ingress_rule(self, security_group_name: str) -> Optional[str]:
        """Add an allow-all ingress rule to a security group.

        Checks if the rule already exists before creating. No-op if present.

        Args:
            security_group_name (str): Security group name.

        Returns:
            Optional[str]: Created rule ID, or None if already exists or SG not found.
        """
        output = self.list_security_groups(name=security_group_name)
        sg_obj = output.find_by_name(security_group_name)

        if not sg_obj:
            get_logger().log_warning(f"Security group '{security_group_name}' not found")
            return None

        if sg_obj.has_allow_all_ingress_rule():
            get_logger().log_info(f"Allow-all ingress rule already exists on '{security_group_name}'")
            return None

        get_logger().log_info(f"Adding allow-all ingress rule to '{security_group_name}'")
        network = self.openstack_connection.get_network()
        rule = network.create_security_group_rule(
            security_group_id=sg_obj.get_id(),
            direction="ingress",
            remote_ip_prefix="0.0.0.0/0",
        )
        return rule.id

    def delete_security_group_rule(self, rule_id: str) -> None:
        """Delete a security group rule by ID.

        Args:
            rule_id (str): Security group rule ID.
        """
        get_logger().log_info(f"Deleting security group rule: {rule_id}")
        network = self.openstack_connection.get_network()
        network.delete_security_group_rule(rule_id)

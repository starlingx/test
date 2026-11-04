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

    def list_security_groups(self, name: Optional[str] = None, project_id: Optional[str] = None) -> SecurityGroupOutput:
        """List security groups, optionally filtered by name and/or project.

        On a multi-project lab there is one security group named ``default`` per
        project, so filtering by name alone is ambiguous. Pass ``project_id`` to
        resolve the group that belongs to a specific project.

        Args:
            name (Optional[str]): Filter by security group name.
            project_id (Optional[str]): Filter by owning project (tenant) id.

        Returns:
            SecurityGroupOutput: Parsed security group collection.
        """
        network = self.openstack_connection.get_network()
        query = {}
        if name:
            query["name"] = name
        if project_id:
            query["project_id"] = project_id
        sgs = list(network.security_groups(**query))

        objects = []
        for sg in sgs:
            obj = SecurityGroupObject()
            obj.set_id(sg.id)
            obj.set_name(sg.name)
            obj.set_rules(sg.security_group_rules or [])
            objects.append(obj)

        return SecurityGroupOutput(objects)

    def create_allow_all_ingress_rule(self, security_group_name: str, project_id: Optional[str] = None) -> Optional[str]:
        """Add an allow-all ingress rule to a security group.

        Checks if the rule already exists before creating. No-op if present.

        The lookup is scoped to a single project. When ``project_id`` is not
        given it defaults to the project the OpenStack connection is
        authenticated as. This disambiguates the per-project ``default`` groups:
        on a multi-project lab several groups are named ``default``, and an
        unscoped name lookup could return the wrong project's group and land the
        rule on a security group the workload VMs never use.

        Args:
            security_group_name (str): Security group name.
            project_id (Optional[str]): Owning project (tenant) id to scope the
                lookup to. Defaults to the connection's current project.

        Returns:
            Optional[str]: Created rule ID, or None if already exists or SG not found.
        """
        if project_id is None:
            project_id = self.openstack_connection.get_auth_details().get("project_id")

        output = self.list_security_groups(name=security_group_name, project_id=project_id)
        sg_obj = output.find_by_name(security_group_name)

        if not sg_obj:
            get_logger().log_warning(f"Security group '{security_group_name}' not found in project '{project_id}'")
            return None

        if sg_obj.has_allow_all_ingress_rule():
            get_logger().log_info(f"Allow-all ingress rule already exists on '{security_group_name}'")
            return None

        get_logger().log_info(f"Adding allow-all ingress rule to '{security_group_name}' (id={sg_obj.get_id()}, project={project_id})")
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

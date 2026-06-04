"""Project, User, and Role CRUD keywords via OpenStack SDK."""

from typing import List, Optional

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.projects.object.project_object import ProjectObject
from keywords.openstack.resources.projects.object.user_object import UserObject


class ProjectKeywords(BaseKeyword):
    """CRUD operations for Keystone projects, users, and roles via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection) -> None:
        """Initialize ProjectKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def find_project(self, project_name: str, domain: str = "default") -> Optional[ProjectObject]:
        """Find a project by name.

        Args:
            project_name (str): Project name.
            domain (str): Domain ID or name.

        Returns:
            Optional[ProjectObject]: Project object or None if not found.
        """
        identity = self.openstack_connection.get_identity()
        project = identity.find_project(project_name, domain_id=domain)
        if project:
            obj = ProjectObject()
            obj.set_id(project.id)
            obj.set_name(project.name)
            obj.set_domain_id(getattr(project, "domain_id", domain))
            obj.set_description(getattr(project, "description", ""))
            return obj
        return None

    def create_project(self, project_name: str, domain: str = "default", description: str = "") -> ProjectObject:
        """Create a project.

        Args:
            project_name (str): Project name.
            domain (str): Domain ID or name.
            description (str): Project description.

        Returns:
            ProjectObject: Created project.
        """
        get_logger().log_info(f"Creating project: {project_name}")
        identity = self.openstack_connection.get_identity()
        project = identity.create_project(
            name=project_name,
            domain_id=domain,
            description=description or project_name,
        )
        obj = ProjectObject()
        obj.set_id(project.id)
        obj.set_name(project.name)
        obj.set_domain_id(getattr(project, "domain_id", domain))
        return obj

    def delete_project(self, project_name: str, domain: str = "default") -> None:
        """Delete a project.

        Args:
            project_name (str): Project name.
            domain (str): Domain ID or name.
        """
        get_logger().log_info(f"Deleting project: {project_name}")
        identity = self.openstack_connection.get_identity()
        project = identity.find_project(project_name, domain_id=domain)
        if project:
            identity.delete_project(project.id)

    def find_user(self, user_name: str, domain: str = "default") -> Optional[UserObject]:
        """Find a user by name.

        Args:
            user_name (str): User name.
            domain (str): Domain ID or name.

        Returns:
            Optional[UserObject]: User object or None if not found.
        """
        identity = self.openstack_connection.get_identity()
        user = identity.find_user(user_name, domain_id=domain)
        if user:
            obj = UserObject()
            obj.set_id(user.id)
            obj.set_name(user.name)
            obj.set_domain_id(getattr(user, "domain_id", domain))
            return obj
        return None

    def create_user(
        self,
        user_name: str,
        password: str,
        project_name: str,
        domain: str = "default",
        email: Optional[str] = None,
    ) -> UserObject:
        """Create a user.

        Args:
            user_name (str): User name.
            password (str): User password.
            project_name (str): Default project name.
            domain (str): Domain ID or name.
            email (Optional[str]): User email.

        Returns:
            UserObject: Created user.
        """
        get_logger().log_info(f"Creating user: {user_name}")
        identity = self.openstack_connection.get_identity()
        project = identity.find_project(project_name, domain_id=domain)
        user = identity.create_user(
            name=user_name,
            password=password,
            domain_id=domain,
            default_project=project.id if project else None,
            email=email,
        )
        obj = UserObject()
        obj.set_id(user.id)
        obj.set_name(user.name)
        obj.set_domain_id(getattr(user, "domain_id", domain))
        return obj

    def delete_user(self, user_name: str, domain: str = "default") -> None:
        """Delete a user.

        Args:
            user_name (str): User name.
            domain (str): Domain ID or name.
        """
        get_logger().log_info(f"Deleting user: {user_name}")
        identity = self.openstack_connection.get_identity()
        user = identity.find_user(user_name, domain_id=domain)
        if user:
            identity.delete_user(user.id)

    def is_role_assigned(self, project_id: str, user_id: str, role_name: str) -> bool:
        """Check if a role is already assigned to a user on a project.

        Args:
            project_id (str): Project ID.
            user_id (str): User ID.
            role_name (str): Role name.

        Returns:
            bool: True if role is already assigned.
        """
        identity = self.openstack_connection.get_identity()
        role_assignments = list(identity.role_assignments(
            project_id=project_id, user_id=user_id
        ))
        role = identity.find_role(role_name)
        if not role:
            return False
        return any(
            getattr(ra, "role", {}).get("id") == role.id
            for ra in role_assignments
        )

    def assign_role(self, project_name: str, user_name: str, role_name: str, domain: str = "default") -> None:
        """Assign a role to a user on a project. No-op if already assigned.

        Args:
            project_name (str): Project name.
            user_name (str): User name.
            role_name (str): Role name.
            domain (str): Domain ID or name.
        """
        identity = self.openstack_connection.get_identity()
        project = identity.find_project(project_name, domain_id=domain)
        if not project:
            get_logger().log_warning(f"Cannot assign role '{role_name}': project '{project_name}' not found")
            return

        user = identity.find_user(user_name, domain_id=domain)
        if not user:
            get_logger().log_warning(f"Cannot assign role '{role_name}': user '{user_name}' not found")
            return

        if self.is_role_assigned(project.id, user.id, role_name):
            get_logger().log_info(f"Role '{role_name}' already assigned to '{user_name}' on '{project_name}'")
            return

        get_logger().log_info(f"Assigning role '{role_name}' to '{user_name}' on '{project_name}'")
        identity.assign_project_role_to_user(
            project=project.id, user=user.id, role=role_name
        )

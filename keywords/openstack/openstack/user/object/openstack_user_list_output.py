from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser
from keywords.openstack.openstack.user.object.openstack_user_list_object import OpenstackUserListObject


class OpenstackUserListOutput:
    """
    Class to parse and handle the output of 'openstack user list' command.
    """

    def __init__(self, output: str):
        """
        Constructor.

        Args:
            output (str): Raw output from 'openstack user list' command
        """
        self.output = output.split("\n") if isinstance(output, str) else output
        self.table_parser = OpenStackTableParser(self.output)
        self.users = self._build_user_objects()

    def _build_user_objects(self) -> list:
        """
        Build list of OpenstackUserListObject from parsed table data.

        Returns:
            list: List of OpenstackUserListObject instances
        """
        output_values_list = self.table_parser.get_output_values_list()
        users = []

        for item in output_values_list:
            if item.get("ID", "").strip():  # Only create objects for valid entries
                user = OpenstackUserListObject()
                user.set_id(item.get("ID", ""))
                user.set_name(item.get("Name", ""))
                user.set_domain_id(item.get("Domain ID", ""))
                user.set_enabled(item.get("Enabled", ""))
                users.append(user)

        return users

    def get_users(self) -> list:
        """
        Get list of user objects.

        Returns:
            list: List of OpenstackUserListObject instances
        """
        return self.users

    def get_user_ids(self) -> list:
        """
        Extract all user IDs from the user objects.

        Returns:
            list: List of user IDs
        """
        return [user.get_id() for user in self.users]

    def get_user_names(self) -> list:
        """
        Extract all user names from the user objects.

        Returns:
            list: List of user names
        """
        return [user.get_name() for user in self.users]

    def get_raw_output(self) -> str:
        """
        Get the raw output from the command.

        Returns:
            str: Raw command output
        """
        return self.output

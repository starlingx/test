from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser
from keywords.openstack.openstack.token.object.openstack_token_issue_object import OpenstackTokenIssueObject


class OpenstackTokenIssueOutput:
    """
    Class to parse and handle the output of 'openstack token issue' command.
    """

    def __init__(self, output: str):
        """
        Constructor.

        Args:
            output (str): Raw output from 'openstack token issue' command
        """
        self.output = output.split("\n") if isinstance(output, str) else output
        self.table_parser = OpenStackTableParser(self.output)
        self.token = self._build_token_object()

    def _build_token_object(self) -> OpenstackTokenIssueObject:
        """
        Build OpenstackTokenIssueObject from parsed table data.

        Returns:
            OpenstackTokenIssueObject: Token object instance
        """
        output_values_list = self.table_parser.get_output_values_list()
        token = OpenstackTokenIssueObject()

        for item in output_values_list:
            field = item.get("Field", "")
            value = item.get("Value", "")

            if field == "id":
                token.set_id(value)
            elif field == "expires":
                token.set_expires(value)
            elif field == "project_id":
                token.set_project_id(value)
            elif field == "user_id":
                token.set_user_id(value)

        return token

    def get_token(self) -> OpenstackTokenIssueObject:
        """
        Get the token object.

        Returns:
            OpenstackTokenIssueObject: Token object instance
        """
        return self.token

    def get_token_id(self) -> str:
        """
        Extract the token ID from the token object.

        Returns:
            str: Token ID

        Raises:
            KeywordException: If token ID is not found or token parsing failed
        """
        token_id = self.token.get_id()
        if not token_id:
            raise KeywordException("Failed to parse token ID from OpenStack token issue output")
        return token_id

    def get_raw_output(self) -> str:
        """
        Get the raw output from the command.

        Returns:
            str: Raw command output
        """
        return self.output

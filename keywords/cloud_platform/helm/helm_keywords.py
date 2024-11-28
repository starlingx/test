from config.configuration_manager import ConfigurationManager
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class HelmKeywords(BaseKeyword):
    """
    Class for helm keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def helm_upload(self, repo_name: str, helm_file: str):
        """
        Runs the helm-upload command
        Args:
            repo_name (): the name of the repo ex. starlingx
            helm_file (): the helm tar file

        Returns:

        """

        # setup expected prompts for password request
        password_prompt = PromptResponse("assword", ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
        password_completed = PromptResponse("@")
        expected_prompts = [password_prompt, password_completed]

        output_list = self.ssh_connection.send_expect_prompts(f'helm-upload {repo_name} {helm_file}', expected_prompts)

        # At this time the this will only fail. Once we have a passing test we can check if there are better assertion values
        assert not any('Error' in output for output in output_list), f"There was an error running the command helm-upload {repo_name} {helm_file}"

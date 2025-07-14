from config.configuration_manager import ConfigurationManager
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class KernelKeywords(BaseKeyword):
    """
    Class for linux kernal related command keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def trigger_kernel_crash(self):
        """
        Makes the system crash, secondary kernel will be loaded, then will produce a vmcore and reboot.
        """
        # Setup expected prompts for password request and echo command
        password_prompt = PromptResponse("Password:", ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
        root_cmd = PromptResponse("root@", "echo c > /proc/sysrq-trigger")
        expected_prompts = [password_prompt, root_cmd]

        # Run echo command to crash standby controller
        self.ssh_connection.send_expect_prompts("sudo su", expected_prompts)

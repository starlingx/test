import codecs
import re
import time
from typing import List

import paramiko
from paramiko.client import SSHClient
from paramiko.sftp_client import SFTPClient

from config.host.objects.host_configuration import HostConfiguration
from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.threading.thread_manager import ThreadManager


class SSHConnection:
    """
    This class holds information and actions for an ssh connection.
    """

    def __init__(
        self,
        name: str,
        host: str,
        user: str,
        password: str,
        timeout: int = 30,
        ssh_port: int = 22,
        jump_host: HostConfiguration = None,
    ):
        """
        Initialize the SSH connection object.

        This sets up the basic configuration used to create an SSH session, optionally through a jump host.

        Args:
            name (str): The name of the connection.
            host (str): The target host to connect to.
            user (str): The SSH username.
            password (str): The SSH password.
            timeout (int): The timeout for establishing a connection, in seconds.
            ssh_port (int): The port used for SSH. Defaults to 22.
            jump_host (HostConfiguration, optional): Configuration for a jump host, if needed.
        """
        self.client = SSHClient()
        self.name = name
        self.host = host
        self.user = user
        self.password = password
        self.timeout = timeout
        self.ssh_port = ssh_port
        self.jump_host = jump_host
        self.is_connected = False

        self.last_return_code = None  # The last Return Code

        # these are values are used for commands that require ssh pass on remote nodes
        self.use_ssh_pass = False
        self.ssh_pass_host = None
        self.ssh_pass_username = None
        self.ssh_pass_password = None
        self.output_start_line = -1  # for parsing out lines that come by default when using ssh pass

    def _connect_to_jump_host(self, allow_agent: bool = True, look_for_keys: bool = True) -> None:
        """
        Connect to the configured jump host using SSH.

        Uses paramiko to establish the SSH session with the jump host, based on
        credentials provided in the `jump_host` configuration.

        Args:
            allow_agent (bool): Connect to SSH agent (Paramiko arg). Default is True.
            look_for_keys (bool): Re-use saved private keys (Paramiko arg). Default is True.

        Returns:
            None:
        """
        try:
            host = self.jump_host.get_host()
            user_name = self.jump_host.get_credentials().get_user_name()
            password = self.jump_host.get_credentials().get_password()
            jump_host_ssh_port = self.jump_host.get_ssh_port()
            self.client.connect(
                host,
                username=user_name,
                password=password,
                timeout=self.timeout,
                allow_agent=allow_agent,
                look_for_keys=look_for_keys,
                port=jump_host_ssh_port,
            )

        except BaseException as exception:
            get_logger().log_error(f"Failed to Connect to Jump-Host {host} with username/password =" f" {user_name}/{password} with timeout {self.timeout}s")
            get_logger().log_error(f"Exception: {exception}")
            raise BaseException("Failed to connect to Jump-Host")

    def connect(self, allow_agent: bool = True, look_for_keys: bool = False) -> bool:
        """
        Create an SSH connection to the target host.

        Args:
            allow_agent (bool): Use SSH agent forwarding (Paramiko arg). Default is True.
            look_for_keys (bool): Search for saved private keys (Paramiko arg). Default is False.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        is_connection_success = True
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        sock = None
        try:
            # if a jump host is configured, create that connection first
            if self.jump_host:
                self._connect_to_jump_host(allow_agent, look_for_keys)
                sock = self.client.get_transport().open_channel("direct-tcpip", (self.host, self.ssh_port), ("", 0), timeout=self.timeout)

            self.client.connect(
                self.host,
                username=self.user,
                password=self.password,
                timeout=self.timeout,
                allow_agent=allow_agent,
                look_for_keys=look_for_keys,
                port=self.ssh_port,
                sock=sock,
            )
            self.is_connected = True
        except BaseException as exception:
            get_logger().log_error(f"Failed to Connect to host {self.host} with username/password =" f" {self.user}/{self.password} with timeout {self.timeout}s")
            get_logger().log_error(f"Exception: {exception}")
            is_connection_success = False
            # connection failed but if a jump host is used, we may still have that connection. Reset the client object
            self.client = SSHClient()
            self.is_connected = False

        return is_connection_success

    def send(self, cmd: str, reconnect_timeout: int = 600, get_pty: bool = False) -> str:
        """
        Send a command to the SSH session and return the output.

        Retries the connection for up to `reconnect_timeout` seconds
        if the session is lost.

        Args:
            cmd (str): The command to execute.
            reconnect_timeout (int): Time in seconds to retry the connection.
            get_pty (bool): Defaults to False. Whether to request a terminal when running a 'send' command.

        Returns:
            str: The output of the command.
        """
        return self._execute_command("SEND", cmd, reconnect_timeout=reconnect_timeout, get_pty=get_pty)

    def send_as_sudo(self, cmd: str, reconnect_timeout: int = 600) -> str:
        """
        Sends a command using sudo and returns the output. Waits for reconnect timeout.

        Args:
            cmd (str): The command to send.
            reconnect_timeout (int): How long to wait for SSH reconnection if needed.

        Returns:
            str: Output of the executed command.
        """
        return self._execute_command("SEND_SUDO", cmd, reconnect_timeout=reconnect_timeout)

    def send_expect_prompts(self, cmd: str, prompts: List[PromptResponse], reconnect_timeout: int = 600) -> str:
        """
        Sends a command, waits for prompts and returns the output.

        Waits for the reconnect timeout in case of SSH disconnects.

        Args:
            cmd (str): The command to send.
            prompts (List[PromptResponse]): The prompts to expect.
            reconnect_timeout (int): The amount of time in seconds to wait for SSH connection.

        Returns:
            str: The output of the command.
        """
        return self._execute_command("SEND_EXPECT_PROMPTS", cmd, prompts=prompts, reconnect_timeout=reconnect_timeout)

    def _execute_command(
        self,
        action: str,
        cmd: str,
        reconnect_timeout: int = 600,
        prompts: List[PromptResponse] = None,
        get_pty: bool = False,
    ) -> str:
        """
        Executes the given action with the given command.

        Waits for reconnect timeout in case of SSH disconnects.

        Args:
            action (str): The action to execute, e.g., SEND, SEND_SUDO, SEND_EXPECT_PROMPTS.
            cmd (str): The command to run.
            reconnect_timeout (int): The time in seconds to wait for SSH connection.
            prompts (List[PromptResponse], optional): Expected prompts, if any.
            get_pty (bool): Defaults to False. Whether to request a terminal when running a 'send' command.

        Returns:
            str: The output of the command.
        """
        timeout = time.time() + reconnect_timeout
        refresh_timeout = 5

        # if we are using ssh pass, we need to wrap the call
        if self.use_ssh_pass:
            if action == "SEND_SUDO":  # if it a sudo call we need further changes to avoid password prompt
                cmd = f'{self.get_ssh_pass_str()} "echo "{self.ssh_pass_password}" | sudo -S {cmd}"'
                # since we do not need prompts or to prepend sudo now, change Action to just 'SEND'
                action = "SEND"
            else:
                cmd = f"{self.get_ssh_pass_str()} '{cmd}'"

        while time.time() < timeout:
            try:

                if not self.is_connected:
                    self.connect()

                thread_manager = ThreadManager(timeout=reconnect_timeout / 10)

                if action == "SEND":
                    thread_manager.start_thread("SSH_Command", self._send, cmd, get_pty=get_pty)
                elif action == "SEND_SUDO":
                    thread_manager.start_thread("SSH_Command", self._send_as_sudo, cmd)
                elif action == "SEND_EXPECT_PROMPTS":
                    thread_manager.start_thread("SSH_Command", self._send_expect_prompts, cmd, prompts)
                else:
                    raise ValueError(f"{action} is not a supported command for an SSHConnection.")

                thread_manager.join_all_threads()
                output = thread_manager.get_thread_object("SSH_Command").get_result()

                # if we use ssh pass we want to skip the preamble before sending back ouput
                if self.use_ssh_pass and self.output_start_line != -1:  # if -1 it's the call to get preamble so return whole output
                    output = output[self.output_start_line :]
                return output

            except Exception as e:
                get_logger().log_info(f"SSH command failed to execute. Reconnecting and trying again in {refresh_timeout} seconds. " f"Exception: {str(e)}")
                time.sleep(refresh_timeout)
                self.is_connected = False

    def _send(self, cmd: str, timeout: int = 30, get_pty: bool = False) -> str:
        """
        Sends the given command with the specified timeout.

        Args:
            cmd (str): The command to send.
            timeout (int): The timeout in seconds for command execution.
            get_pty (bool): Defaults to False. Whether to request a terminal when running a 'send' command.

        Returns:
            str: The output of the command.
        """
        get_logger().log_ssh(cmd)

        stdin, stdout, stderr = self.client.exec_command(cmd, timeout=timeout, get_pty=get_pty)
        stdout.channel.set_combine_stderr(True)
        self.last_return_code = stdout.channel.recv_exit_status()
        output = stdout.readlines()

        for line in output:
            clean_line = line.rstrip("\n")
            get_logger().log_ssh(clean_line)

        return output

    def _send_as_sudo(self, cmd: str) -> str:
        """
        Sends the specified command using sudo and handles the password prompt.

        Args:
            cmd (str): The command to execute with sudo.

        Returns:
            str: The output of the command.
        """
        # Deliberately skipping the "P" in the password as some prompts have
        # different cases
        sudo_password_prompt = PromptResponse("assword", self.password)
        sudo_completed = PromptResponse("@")
        sudo_prompts = [sudo_password_prompt, sudo_completed]
        return self.send_expect_prompts("sudo {}".format(cmd), sudo_prompts)

    def _send_expect_prompts(self, cmd: str, prompts: List[PromptResponse], timeout: int = 30) -> str:
        """
        Send the command and wait for the specified prompts in order.

        Args:
            cmd (str): The command to execute.
            prompts (List[PromptResponse]): An ordered list of prompts we expect and
                the associated responses.
            timeout (int): Timeout in seconds to wait for each prompt.

        Returns:
            str: The SSH output generated before the last prompt. If there are
            intermediate prompts, returns the output between the last two prompts.
        """
        if not prompts or len(prompts) < 1:
            raise ValueError("You must specify a list with at least one prompt to call this " "function. Otherwise, please call 'send' instead.")

        code = -1

        # Open up a channel to control the SSH connection and send the command.
        channel = self.client.invoke_shell()
        self.__send_in_channel(channel, cmd)

        # Keep going until we have matched every prompt in order
        # Or we timeout from receiving output from the ssh connection
        for prompt in prompts:
            is_prompt_match = False
            output_since_last_prompt = ""

            while not is_prompt_match:
                # Read the response from the server.
                code, output_buffer = self.__read_from_channel(channel, timeout)

                if code != 0:
                    get_logger().log_warning(f"Failed to match prompt of {prompt.get_prompt_substring()}")
                    break

                # Log the current console output.
                get_logger().log_info(output_buffer.rstrip())

                # Add the currently read buffer to the output
                output_since_last_prompt += output_buffer
                prompt.set_complete_output(output_since_last_prompt)
                is_prompt_match = prompt.get_prompt_substring() in output_since_last_prompt

                # If we match the prompt, send the associated response if any.
                if is_prompt_match and prompt.get_prompt_response():
                    self.__send_in_channel(channel, prompt.get_prompt_response())

        self.last_return_code = code

        complete_output = prompts[-1].get_complete_output()

        # output is a long string, break into list using line breaks but add back the line break as it's needed
        # for table parsing
        output_list = [line + "\n" for line in complete_output.split("\n") if line]

        return output_list

    def __send_in_channel(self, ssh_channel: paramiko.Channel, cmd: str) -> None:
        """
        Send a command through the given SSH channel.

        This method assumes the channel was opened via `invoke_shell()` and waits
        until the channel is ready before sending the command.

        Args:
            ssh_channel (paramiko.Channel): The SSH channel obtained from
                `self.client.invoke_shell()`.
            cmd (str): The command to send.
        """
        while not ssh_channel.send_ready():
            time.sleep(0.009)  # Avoid spamming the channel. Value taken from paramiko-expect.
        get_logger().log_info(f"Sending command: {cmd}")
        ssh_channel.send(cmd)
        ssh_channel.send("\n")

    def __read_from_channel(self, ssh_channel: paramiko.Channel, timeout: int) -> tuple[int, str]:
        """
        Read data from an SSH channel opened via `invoke_shell()`.

        Waits for the channel to be ready and reads the output. Times out if no
        response is received in the given number of seconds.

        Args:
            ssh_channel (paramiko.Channel): The SSH channel obtained from
                `self.client.invoke_shell()`.
            timeout (int): Time in seconds to wait for a response.

        Returns:
            tuple[int, str]: A tuple of return code and string output.
                - Return code: 0 on success, -1 on timeout or connection closed.
                - Output: The response string read from the SSH channel.
        """
        # Setup Variables
        decoder = codecs.getincrementaldecoder("utf-8")()
        base_time = time.time()

        # Avoids paramiko hang when recv is not ready yet
        while not ssh_channel.recv_ready():
            time.sleep(0.009)  # Avoid spamming the channel. Value taken from paramiko-expect.
            if time.time() >= (base_time + timeout):
                get_logger().log_warning("SSH output read timed out — buffer may be incomplete or prompt unmatched.")
                return -1, "Timeout Exceeded"

        # Read some of the output - increased buffer size for large outputs
        current_buffer = ssh_channel.recv(8192)

        # If we have an empty buffer, then the SSH session has been closed
        if len(current_buffer) == 0:
            get_logger().log_warning("SSH session closed: received empty buffer from remote channel")
            return -1, "Connection has been closed"

        # Convert the buffer to our chosen encoding
        current_buffer_decoded = decoder.decode(current_buffer)

        # Strip ANSI escape sequences added by shell commands like sudo or colored prompts
        # These sequences are common in interactive `invoke_shell()` sessions
        current_buffer_decoded = self._strip_ansi_sequences(current_buffer_decoded)

        # Strip all ugly \r (Ctrl-M making) characters from the current read
        current_buffer_decoded = current_buffer_decoded.replace("\r", "")

        return 0, current_buffer_decoded

    def get_return_code(self) -> str:
        """
        Return the last return code captured by this SSH connection.

        Returns:
            str: The last return code from the most recent SSH command.
        """
        return self.last_return_code

    def close(self) -> None:
        """
        Close the SSH connection.

        This shuts down the underlying Paramiko SSH client.

        Returns:
            None:
        """
        self.client.close()

    def set_name(self, name: str) -> None:
        """
        Sets the name of this SSH connection

        Args:
            name (str): Name to assign to this SSH connection

        """
        self.name = name

    def get_name(self) -> str:
        """
        Get the name of this SSH connection.

        Returns:
            str: The name of the connection.
        """
        return self.name

    def get_sftp_client(self, reconnect_timeout: int = 600) -> SFTPClient:
        """
        Get an SFTP client for file operations.

        Retries the connection for up to `reconnect_timeout` seconds if disconnected.

        Args:
            reconnect_timeout (int): The number of seconds to retry connecting.

        Returns:
            SFTPClient: A Paramiko SFTP client for performing file operations.
        """
        timeout = time.time() + reconnect_timeout
        refresh_timeout = 5

        sftp_client: SFTPClient = None
        while time.time() < timeout:
            try:
                if not self.is_connected:
                    self.connect()
                sftp_client = self.client.open_sftp()
                if sftp_client:
                    return sftp_client
                else:
                    raise "SFTP Client was None"  # should be caught in the except block which tries to reconnect
            except Exception as e:
                get_logger().log_info(f"Failed to get sftp client. Reconnecting and trying again in {refresh_timeout} seconds. " f"Exception: {str(e)}")
                time.sleep(refresh_timeout)
                self.is_connected = False

        return sftp_client

    def setup_ssh_pass(self, host_name: str, host_user_name: str, host_password: str) -> None:
        """
        Set up the connection to use sshpass for remote authentication.

        Stores SSH credentials and calculates the starting line number to strip
        connection preamble in subsequent SSH commands.

        Args:
            host_name (str): The host to use sshpass on.
            host_user_name (str): The username for SSH authentication.
            host_password (str): The password for SSH authentication.
        """
        # setup this ssh connection with ssh pass parameters
        self.use_ssh_pass = True
        self.ssh_pass_host = host_name
        self.ssh_pass_username = host_user_name
        self.ssh_pass_password = host_password

        # get preamble so we can parse it out
        output = self.send("\n")
        self.output_start_line = len(output)

    def get_ssh_pass_str(self) -> str:
        """
        Return the SSH pass command string.

        This wraps SSH calls with `sshpass` to support automated password-based login.

        Returns:
            str: The formatted SSH pass command string.
        """
        return f"sshpass -p '{self.ssh_pass_password}' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {self.ssh_pass_username}@{self.ssh_pass_host}"

    def __str__(self) -> str:
        """
        Return the string representation of this connection.

        Returns:
            str: A string identifying this SSH connection.
        """
        return f"ssh_con:{self.name}"

    @staticmethod
    def _strip_ansi_sequences(text: str) -> str:
        """
        Remove ANSI escape sequences from a string.

        This is a commonly used regular expression for matching ANSI terminal
        control codes (e.g., color codes, cursor movement, etc.). These are
        typically found in output from interactive shell commands.

        Regex pattern adapted from:
        - https://stackoverflow.com/a/14693789
        - https://github.com/chalk/ansi-regex/blob/main/index.js

        Args:
            text (str): A string that may contain ANSI escape sequences.

        Returns:
            str: Cleaned string without ANSI sequences.
        """
        ansi_escape_pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape_pattern.sub("", text)

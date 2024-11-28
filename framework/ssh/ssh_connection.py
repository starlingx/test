import codecs
import time
from typing import List

import paramiko
from config.host.objects.host_configuration import HostConfiguration
from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.threading.thread_manager import ThreadManager
from paramiko.client import SSHClient
from paramiko.sftp_client import SFTPClient


class SSHConnection:
    """
    This class holds information and actions for an ssh connection
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
        Initialization of ssh connection
        Args:
            name: the name of the connection
            host: the host of the connection
            user: the user to connect with
            password: the password
            timeout: Amount of time to wait for the connection to the lab
            jump_host: the configuration of the jump host if it's needed
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

    def _connect_to_jump_host(self, allow_agent=True, look_for_keys=True):
        """
        This function will connect to the jump_host
        Args:
            allow_agent: connect to SSH agent (Paramiko arg). True by default
            look_for_keys: Re-use saved private keys. (Paramiko arg).

        Returns: None

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

    def connect(self, allow_agent=True, look_for_keys=True) -> bool:
        """
        Creates a connection
        Args:
            allow_agent: connect to SSH agent (Paramiko arg). True by default
            look_for_keys: Re-use saved private keys. (Paramiko arg).
        Returns: True if the connection was successful, false otherwise.

        """
        is_connection_success = True
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        sock = None
        try:
            # if a jump host is configured, create that connection first
            if self.jump_host:
                self._connect_to_jump_host(allow_agent, look_for_keys)
                sock = self.client.get_transport().open_channel("direct-tcpip", (self.host, self.ssh_port), ('', 0), timeout=self.timeout)

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

    def send(self, cmd: str, reconnect_timeout: int = 600) -> str:
        """
        Sends a command and returns the output. Waits for the reconnect timeout in case of ssh disconnects
        Args:
            cmd (): the cmd to send
            reconnect_timeout (): the amount of time in secs to wait for ssh connection

        Returns: the output of the command

        """
        return self._execute_command("SEND", cmd, reconnect_timeout=reconnect_timeout)

    def send_as_sudo(self, cmd: str, reconnect_timeout: int = 600) -> str:
        """
        Sends a command using sudo and returns the output. Waits for the reconnect timeout in case of ssh disconnects
        Args:
            cmd (): the cmd to send
            reconnect_timeout (): the amount of time in secs to wait for ssh connection

        Returns: the output of the command

        """
        return self._execute_command("SEND_SUDO", cmd, reconnect_timeout=reconnect_timeout)

    def send_expect_prompts(self, cmd: str, prompts: List[PromptResponse], reconnect_timeout: int = 600) -> str:
        """
        Sends a command, waits for prompts and returns the output. Wait for the reconnect timeout in case of ssh disconnects
        Args:
            cmd (): the cmd to send
            prompts: the prompts to expect
            reconnect_timeout (): the amount of time in secs to wait for ssh connection

        Returns: the output of the command

        """
        return self._execute_command("SEND_EXPECT_PROMPTS", cmd, prompts=prompts, reconnect_timeout=reconnect_timeout)

    def _execute_command(
        self,
        action: str,
        cmd: str,
        reconnect_timeout: int = 600,
        prompts: List[PromptResponse] = None,
    ) -> str:
        """
        Executes the given action with the given command. Waits for reconnect timeout for ssh connection
        Args:
            action (): the actions ex. SEND, SEND_SUDO, SEND_EXPECT_PROMPTS
            cmd (): the cmd to run
            reconnect_timeout (): the time to wait for ssh connection
            prompts (): expected prompts if any

        Returns:the output of the command

        """
        timeout = time.time() + reconnect_timeout
        refresh_timeout = 5

        while time.time() < timeout:
            try:

                if not self.is_connected:
                    self.connect()

                thread_manager = ThreadManager(timeout=reconnect_timeout / 10)

                if action == 'SEND':
                    thread_manager.start_thread("SSH_Command", self._send, cmd)
                elif action == 'SEND_SUDO':
                    thread_manager.start_thread("SSH_Command", self._send_as_sudo, cmd)
                elif action == 'SEND_EXPECT_PROMPTS':
                    thread_manager.start_thread("SSH_Command", self._send_expect_prompts, cmd, prompts)
                else:
                    raise ValueError(f"{action} is not a supported command for an SSHConnection.")

                thread_manager.join_all_threads()
                output = thread_manager.get_thread_object("SSH_Command").get_result()
                return output

            except Exception as e:
                get_logger().log_info(f"SSH command failed to execute. Reconnecting and trying again in {refresh_timeout} seconds. " f"Exception: {str(e)}")
                time.sleep(refresh_timeout)
                self.is_connected = False

    def _send(self, cmd: str, timeout: int = 30) -> str:
        """
        Sends the given cmd with the given timeout
        Args:
            cmd: the command to send
            timeout: the timeout

        Returns: the output

        """
        get_logger().log_ssh(cmd)

        stdin, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)

        stdout.channel.set_combine_stderr(True)
        self.last_return_code = stdout.channel.recv_exit_status()
        output = stdout.readlines()

        for line in output:
            clean_line = line.rstrip('\n')
            get_logger().log_ssh(clean_line)

        return output

    def _send_as_sudo(self, cmd: str) -> str:
        """
        This function will send the command specified as sudo and answer the password prompt.
        Args:
            cmd: The command to be executed. "sudo cmd"

        Returns (str): The output of the command.

        """
        # Deliberately skipping the "P" in the password as some prompts have
        # different cases
        sudo_password_prompt = PromptResponse("assword", self.password)
        sudo_completed = PromptResponse("@")
        sudo_prompts = [sudo_password_prompt, sudo_completed]
        return self.send_expect_prompts("sudo {}".format(cmd), sudo_prompts)

    def _send_expect_prompts(self, cmd: str, prompts: List[PromptResponse], timeout: int = 30) -> str:
        """
        This function will send the cmd specified and wait for the specified prompts in order.
        Args:
            cmd (str): The command to execute
            prompts (list[PromptResponse]): An ordered list of prompts that we expect and the
                                            associated responses
            timeout (int): Timeout waiting for the output of our command

        Returns (str): The SSH output generated before the last prompt.
                       If there are intermediate prompts, it will return the output between the
                       last two prompts

        """
        if not prompts or len(prompts) < 1:
            raise ValueError("You must specify a list with at least one prompt to call this " "function. Otherwise, please call 'send' instead.")

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
                    print("Failed to match prompt of {}".format(prompt.get_prompt_substring()))
                    break

                # Log the current console output.
                print(output_buffer, end="")

                # Add the currently read buffer to the output
                output_since_last_prompt += output_buffer
                prompt.set_complete_output(output_since_last_prompt)
                is_prompt_match = prompt.get_prompt_substring() in output_since_last_prompt

                # If we match the prompt, send the associated response if any.
                if is_prompt_match and prompt.get_prompt_response():
                    self.__send_in_channel(channel, prompt.get_prompt_response())

        complete_output = prompts[-1].get_complete_output()

        # output is a long string, break into list using line breaks but add back the line break as it's needed
        # for table parsing
        output_list = [line + '\n' for line in complete_output.split('\n') if line]

        return output_list

    def __send_in_channel(self, ssh_channel, cmd: str):
        """
        Given a channel that was opened via self.client.invoke_shell(), this function
        will send the 'cmd' specified to the channel.
        Args:
            ssh_channel: The ssh channel obtained from self.client.invoke_shell()
            cmd: The command to send through the channel.

        Returns: None

        """

        while not ssh_channel.send_ready():
            time.sleep(0.009)  # Avoid spamming the channel. Value taken from paramiko-expect.
        print(cmd)
        ssh_channel.send(cmd)
        ssh_channel.send("\n")

    def __read_from_channel(self, ssh_channel, timeout: int) -> (int, str):
        """
        Given a channel that was opened via self.client.invoke_shell(), this function
        will read data returned from the channel.
        Args:
            ssh_channel: The ssh channel obtained from self.client.invoke_shell()
            timeout (int): The amount of time in seconds to wait for a response from the channel.

        Returns (int, str): Tuple(Return Code, Channel String Output)
            ---- Return Code; 0 is Success, -1 is timeout of connection closed.
            ---- String output sent from the channel.

        """

        # Setup Variables
        decoder = codecs.getincrementaldecoder("utf-8")()
        base_time = time.time()

        # Avoids paramiko hang when recv is not ready yet
        while not ssh_channel.recv_ready():
            time.sleep(0.009)  # Avoid spamming the channel. Value taken from paramiko-expect.
            if time.time() >= (base_time + timeout):
                print('Timeout Exceeded waiting for SSH output to return: {}s'.format(timeout))
                return -1, "Timeout Exceeded"

        # Read some of the output
        current_buffer = ssh_channel.recv(1024)

        # If we have an empty buffer, then the SSH session has been closed
        if len(current_buffer) == 0:
            print('SSH Connection has been closed')
            return -1, "Connection has been closed"

        # Convert the buffer to our chosen encoding
        current_buffer_decoded = decoder.decode(current_buffer)

        # Strip all ugly \r (Ctrl-M making) characters from the current read
        current_buffer_decoded = current_buffer_decoded.replace('\r', '')

        return 0, current_buffer_decoded

    def get_return_code(self) -> str:
        """
        This function will return the last return code captured by this SSH connection.
        Returns: the last return code captured by this SSH connection.

        """
        return self.last_return_code

    def close(self):
        """
        Closes the connection
        Returns:

        """
        self.client.close()

    def get_name(self) -> str:
        """
        Getter for the name
        Returns: the name

        """
        return self.name

    def get_sftp_client(self, reconnect_timeout: int = 600) -> SFTPClient:
        """
        Getter for sftp client for us in file operations
        Args:
            reconnect_timeout (): the reconnect timeout

        Returns: the sftp_client

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

    def __str__(self):
        """
        Overwrites the default string representation.

        Returns: String representation of this connection.

        """
        return f"ssh_con:{self.name}"

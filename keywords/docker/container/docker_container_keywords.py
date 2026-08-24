"""Keywords for managing docker containers on a target host."""

import shlex

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword


class DockerContainerKeywords(BaseKeyword):
    """Keywords for docker container lifecycle operations.

    Complements the existing image-level keywords (pull, load, push, tag) with
    run, stop, remove, exec and readiness helpers. Container operations require
    root, so every command is sent through the non-interactive sudo channel.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Active SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def run_container(self, image: str, container_name: str, use_host_network: bool = False, environment: dict = None, command: str = None, detached: bool = True) -> str:
        """Run a docker container.

        Args:
            image (str): Image reference to run (e.g. quay.io/keycloak/keycloak:26.7.0).
            container_name (str): Name to assign to the container.
            use_host_network (bool): Attach to the host network namespace instead of a
                bridge. Required on hosts where published-port mapping does not take
                effect. Defaults to False.
            environment (dict): Environment variables to pass to the container.
                Defaults to None.
            command (str): Command and arguments to run inside the container, appended
                after the image reference. Defaults to None.
            detached (bool): Run in the background. Defaults to True.

        Returns:
            str: The container ID reported by docker.
        """
        args = []
        if detached:
            args.append("-d")
        args.append(f"--name {shlex.quote(container_name)}")
        if use_host_network:
            args.append("--network host")
        if environment:
            for key, value in environment.items():
                args.append(f"-e {shlex.quote(f'{key}={value}')}")
        args.append(image)
        if command:
            args.append(command)

        output = self._send_docker_command(f"docker run {' '.join(args)}")
        self.validate_success_return_code(self.ssh_connection)
        container_id = self._last_non_empty_line(output)
        get_logger().log_info(f"Started container '{container_name}' with id {container_id}")
        return container_id

    def stop_container(self, container_name: str) -> None:
        """Stop a running container.

        Args:
            container_name (str): Name of the container to stop.
        """
        self._send_docker_command(f"docker stop {shlex.quote(container_name)}")
        self.validate_success_return_code(self.ssh_connection)

    def remove_container(self, container_name: str, force: bool = True) -> None:
        """Remove a container.

        Args:
            container_name (str): Name of the container to remove.
            force (bool): Remove even if running. Defaults to True.
        """
        force_flag = "-f " if force else ""
        self._send_docker_command(f"docker rm {force_flag}{shlex.quote(container_name)}")
        self.validate_success_return_code(self.ssh_connection)

    def cleanup_container(self, container_name: str) -> None:
        """Remove a container if it exists, taking no action otherwise.

        Safe to call from a teardown finalizer even when the container was never
        created.

        Args:
            container_name (str): Name of the container to remove.
        """
        if self.container_exists(container_name):
            self.remove_container(container_name, force=True)
            get_logger().log_info(f"Removed container '{container_name}'")
        else:
            get_logger().log_info(f"Container '{container_name}' not present, nothing to remove")

    def container_exists(self, container_name: str) -> bool:
        """Check whether a container exists in any state.

        Args:
            container_name (str): Name of the container.

        Returns:
            bool: True if the container exists, running or stopped.
        """
        output = self._send_docker_command(f"docker ps -a --filter name=^{container_name}$ --format {{{{.Names}}}}")
        return container_name in output

    def is_container_running(self, container_name: str) -> bool:
        """Check whether a container is currently running.

        Args:
            container_name (str): Name of the container.

        Returns:
            bool: True if the container is running.
        """
        output = self._send_docker_command(f"docker ps --filter name=^{container_name}$ --format {{{{.Names}}}}")
        return container_name in output

    def exec_in_container(self, container_name: str, command: str) -> str:
        """Execute a command inside a running container.

        Args:
            container_name (str): Name of the container.
            command (str): Command to execute inside the container.

        Returns:
            str: Output of the command.
        """
        output = self._send_docker_command(f"docker exec {shlex.quote(container_name)} {command}")
        self.validate_success_return_code(self.ssh_connection)
        return output

    def get_container_logs(self, container_name: str, tail_lines: int = 50) -> str:
        """Get the tail of a container's logs.

        Args:
            container_name (str): Name of the container.
            tail_lines (int): Number of trailing lines to return. Defaults to 50.

        Returns:
            str: The container log output, including output written to stderr.
        """
        # Containers commonly log to stderr, so it is merged into stdout inside an
        # inner shell. Merging it outside would lose it, because the non-interactive
        # sudo path discards stderr to suppress the password prompt.
        inner = f"docker logs --tail {tail_lines} {shlex.quote(container_name)} 2>&1"
        return self._send_docker_command(f"sh -c {shlex.quote(inner)}")

    def wait_for_container_running(self, container_name: str, timeout: int = 120, polling_sleep_time: int = 5) -> None:
        """Wait until a container reports the running state.

        Args:
            container_name (str): Name of the container.
            timeout (int): Maximum time to wait in seconds. Defaults to 120.
            polling_sleep_time (int): Seconds between polls. Defaults to 5.
        """
        validate_equals_with_retry(
            lambda: self.is_container_running(container_name),
            True,
            f"Container '{container_name}' is running",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

    def _send_docker_command(self, cmd: str) -> str:
        """Send a docker command with sudo via the non-interactive channel.

        Docker requires root here, and the interactive sudo path matches '@' as a
        command-complete marker, which corrupts output containing '@' or a shell
        prompt. The non-interactive path feeds the password via stdin and discards
        sudo's own prompt, so the returned output is clean enough to parse as JSON.

        Args:
            cmd (str): The docker command to run, without the sudo prefix.

        Returns:
            str: The command output as a single string.
        """
        return self._as_text(self.ssh_connection.send_as_sudo_non_interactive(cmd))

    def _as_text(self, output: str | list) -> str:
        """Normalize command output to a single string.

        Args:
            output (str | list): Raw output from the SSH connection.

        Returns:
            str: The output as a single string.
        """
        return "\n".join(output) if isinstance(output, list) else output

    def _last_non_empty_line(self, output: str | list) -> str:
        """Return the last non-empty line of command output.

        docker run echoes the container ID as its final line.

        Args:
            output (str | list): Raw output from the SSH connection.

        Returns:
            str: The last non-empty line, or an empty string if there is none.
        """
        lines = [line.strip() for line in self._as_text(output).splitlines() if line.strip()]
        return lines[-1] if lines else ""

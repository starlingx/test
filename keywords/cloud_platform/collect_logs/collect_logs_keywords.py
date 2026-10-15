from typing import List, Optional, Union

from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.collect_logs.objects.collect_logs_output import CollectLogsOutput
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.linux.tar.tar_keywords import TarKeywords


class CollectLogsKeywords(BaseKeyword):
    """Keywords wrapping the StarlingX ``collect`` log-collection CLI.

    Supports the collection variants exercised by the DC collect-log tests:
    ``collect --all``, ``collect --subcloud <name>``, ``collect --subcloud
    --list <names>``, ``collect --continue``, the ``--inline`` modifier and a
    custom bundle ``--name``.

    The command is always run over the supplied SSH connection (reused as-is;
    no new connections are created). Tar-bundle verification is delegated to
    the shared ``TarKeywords`` rather than re-implementing ``tar`` handling.
    """

    # Marker echoed after collect returns so the interactive PTY read knows the
    # command has finished (collect only flushes its summary at the very end).
    _COLLECT_END_MARKER = "COLLECT_CMD_DONE"

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the (central)
                active controller where ``collect`` runs.
        """
        self.ssh_connection = ssh_connection
        self._tar = TarKeywords(ssh_connection)

    def collect(
        self,
        *,
        all_hosts: bool = False,
        subcloud: Optional[Union[str, List[str]]] = None,
        subcloud_list: Optional[List[str]] = None,
        continue_collect: bool = False,
        inline: bool = False,
        collect_file_name: Optional[str] = None,
        verbose: bool = True,
        password: Optional[str] = None,
        validate_rc: bool = True,
        command_timeout: int = 1800,
    ) -> CollectLogsOutput:
        """Run a ``collect`` command and return its parsed output.

        Args:
            all_hosts (bool): Add ``--all`` to collect from all hosts.
            subcloud (Optional[Union[str, List[str]]]): One or more subcloud
                names passed via ``--subcloud``. A list is space-joined.
            subcloud_list (Optional[List[str]]): Subcloud names passed via
                ``--subcloud --list``.
            continue_collect (bool): Add ``--continue`` (uses an existing
                ``/tmp/collect_continue.lst``).
            inline (bool): Add ``--inline`` to force sequential collection.
            collect_file_name (Optional[str]): Custom bundle name via ``--name``.
            verbose (bool): Add ``--verbose`` (default True). collect is
                otherwise silent for minutes while gathering/tarring; verbose
                output keeps the interactive PTY read from starving (the
                framework's expect path uses a fixed 30s per-read timeout, so
                long silent gaps would otherwise abort the command).
            password (Optional[str]): Password supplied at collect's
                ``[sudo] password for <user>:`` prompt. Defaults to the SSH
                connection password. Pass a wrong value to exercise collect's
                invalid-password error path.
            validate_rc (bool): When True (default) assert the command returned
                success. Set False for negative/error-path tests (e.g. invalid
                password or insufficient scratch space) where collect is
                expected to fail and the caller inspects the output instead.
            command_timeout (int): Maximum time in seconds to wait for the
                synchronous ``collect`` command to finish. collect bundles can
                take many minutes (its own bundle timeout defaults to 20 min),
                so the default is 1800 (30 minutes).

        Returns:
            CollectLogsOutput: Parsed collect output (bundle path, collected
            names, execution time).
        """
        cmd = self._build_command(
            all_hosts=all_hosts,
            subcloud=subcloud,
            subcloud_list=subcloud_list,
            continue_collect=continue_collect,
            inline=inline,
            collect_file_name=collect_file_name,
            verbose=verbose,
        )
        get_logger().log_info(f"Running collect command: {cmd}")

        # ``collect`` prompts for the sudo password interactively (one or more
        # times) and does NOT support NOPASSWD sudo. It must therefore be driven
        # over a PTY, answering each "[sudo] password for <user>:" prompt. A
        # trailing end marker guarantees we only return once collect has fully
        # finished (it buffers its summary until the very end).
        prompt_password = password if password is not None else self.ssh_connection.password
        full_cmd = f"{source_openrc(cmd)}; echo {self._COLLECT_END_MARKER}"
        prompts = [
            PromptResponse("assword", prompt_password),
            PromptResponse(self._COLLECT_END_MARKER),
        ]
        output = self.ssh_connection.send_expect_prompts(full_cmd, prompts, command_timeout=command_timeout)
        if validate_rc:
            self.validate_success_return_code(self.ssh_connection)
        return CollectLogsOutput(output)

    def _build_command(
        self,
        *,
        all_hosts: bool,
        subcloud: Optional[Union[str, List[str]]],
        subcloud_list: Optional[List[str]],
        continue_collect: bool,
        inline: bool,
        collect_file_name: Optional[str],
        verbose: bool = False,
    ) -> str:
        """Assemble the ``collect`` command string from the given options.

        Args:
            all_hosts (bool): If True, add ``--all`` to collect from all hosts.
            subcloud (Optional[Union[str, List[str]]]): Subcloud name(s) to collect
                from, or the sentinel "all" to add a bare ``--subcloud`` flag.
            subcloud_list (Optional[List[str]]): Subcloud names for ``--subcloud --list``.
            continue_collect (bool): If True, add ``--continue``.
            inline (bool): If True, add ``--inline``.
            collect_file_name (Optional[str]): Bundle name for ``--name``.
            verbose (bool): If True, add ``--verbose``.

        Returns:
            str: The composed collect command (without auth wrapping).
        """
        parts = ["collect"]
        if all_hosts:
            parts.append("--all")
        if subcloud is not None:
            # The sentinel "all" means "every subcloud": collect expects a bare
            # ``--subcloud`` flag (``collect --all --subcloud``), NOT a subcloud
            # literally named "all".
            if subcloud == "all":
                parts.append("--subcloud")
            else:
                names = subcloud if isinstance(subcloud, str) else " ".join(subcloud)
                parts.append(f"--subcloud {names}")
        if subcloud_list is not None:
            parts.append("--subcloud --list {}".format(" ".join(subcloud_list)))
        if continue_collect:
            parts.append("--continue")
        if inline:
            parts.append("--inline")
        if collect_file_name is not None:
            parts.append(f"--name {collect_file_name}")
        if verbose:
            parts.append("--verbose")
        return " ".join(parts)

    def verify_collected_names_in_tar(self, tar_file_path: str, expected_names: List[str]) -> None:
        """Assert each expected subcloud/host appears inside the collected tar.

        Lists the tar contents verbosely (via the shared ``TarKeywords``) and
        asserts every expected name is present.

        Args:
            tar_file_path (str): Path to the collected ``.tar`` bundle.
            expected_names (List[str]): Subcloud/host names expected inside.
        """
        contents = self._tar.list_files_verbosely(tar_file_path)
        missing = [name for name in expected_names if name not in contents]
        validate_equals(missing, [], f"All expected names present in tar {tar_file_path}")

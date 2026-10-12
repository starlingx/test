import re
from typing import List, Optional


class CollectLogsOutput:
    """Parser for the output of the StarlingX ``collect`` command.

    Real ``collect`` wording (StarlingX Log Collection Tool v3.1), host run::

        collecting data from 1 host: controller-1
        collecting controller-1_20261009.033521 ... done (00:03:43  194M   2%)
        collected from 1 host
        creating single-node tarball /scratch/controller-1_20261009.033521.tar ... done (00:03:45  194M   2%)

    Subcloud run::

        collecting data from 1 subcloud: subcloud3
        monitoring subcloud collect ; please standby ........
        collected subcloud3_20261009.033957 ... done  (00:02:52   64M   2%)
        collected from 1 subcloud
        creating single-subcloud tarball /scratch/subcloud3_20261009.033957.tar ... done (00:02:52   64M   2%)

    Multiple-subcloud run (note: a single *combined* bundle is produced, named
    ``SELECT_SUBCLOUDS_<ts>.tar`` — NOT one tar per subcloud)::

        collecting data from 2 subclouds: subcloud1 subcloud3
        monitoring subcloud collect ; please standby ........
        collected subcloud1_20261009.060656 ... done (...)
        collected subcloud3_20261009.060656 ... done (...)
        collected from 2 subclouds
        creating selected-subcloud tarball /scratch/SELECT_SUBCLOUDS_20261009.060656.tar ... done (...)

    This object exposes the raw text plus a few helpers so test code does not
    have to re-implement regex parsing. It keeps no SSH state; callers pass the
    command output in.
    """

    # Final bundle path is the one named on the "creating ... tarball <path>"
    # line. This is the only reliable anchor across all collect modes: for
    # multiple subclouds collect first writes per-subcloud intermediate tars
    # (which it then rolls into, and removes for, the combined bundle), so a
    # naive "first *.tar" match would pick a transient path. We take the LAST
    # "creating ... tarball <path>" occurrence (the outermost/final bundle).
    _CREATING_TARBALL_PATTERN = r"creating\s+[\w-]*\s*tarball\s+(/\S+\.tar)"
    # Fallback: any /scratch/....tar path, used only if no "creating tarball"
    # line is present in the captured output.
    _TAR_PATH_PATTERN = r"(/\S+\.tar)"
    # Per-host/subcloud progress line. Hosts use "collecting <name>_<ts> ... done"
    # and subclouds use "collected <name>_<ts> ... done"; accept either verb and
    # require a digit after the underscore so the trailing timestamp is matched
    # (not an arbitrary name containing underscores).
    _COLLECTED_PATTERN = r"collect(?:ed|ing)\s+(\S+?)_\d"
    # Duration is embedded in the final "done (HH:MM:SS  <size>  <pct>)" marker.
    _DONE_DURATION_PATTERN = r"done\s*\(\s*(\d{2}):(\d{2}):(\d{2})"

    def __init__(self, output: List[str]):
        """Constructor.

        Args:
            output (List[str]): Raw stdout lines returned by SSHConnection.send().
        """
        self.output_lines = output if output is not None else []
        self.output_text = "".join(self.output_lines)

    def get_output_text(self) -> str:
        """Return the full command output as a single string.

        Returns:
            str: Joined output text.
        """
        return self.output_text

    def get_tar_file_path(self) -> Optional[str]:
        """Return the path of the produced tar bundle, if present.

        Prefers the path named on the final ``creating ... tarball <path>``
        line (correct for every collect mode, including the combined
        ``SELECT_SUBCLOUDS_*.tar`` produced for multiple subclouds). Falls back
        to any ``*.tar`` path only when no such line is present.

        Returns:
            Optional[str]: The final bundle path, or None if the collect output
            did not report one.
        """
        creating = re.findall(self._CREATING_TARBALL_PATTERN, self.output_text)
        if creating:
            return creating[-1]
        match = re.search(self._TAR_PATH_PATTERN, self.output_text)
        return match.group(1) if match else None

    def get_collected_names(self) -> List[str]:
        """Return the subcloud/host names reported as collected.

        Returns:
            List[str]: Names extracted from each "collect(ed|ing) <name>_<ts>"
            progress line, in the order they appear.
        """
        return re.findall(self._COLLECTED_PATTERN, self.output_text)

    def is_name_collected(self, name: str) -> bool:
        """Return True if the given subcloud/host was reported as collected.

        Matches both the subcloud form ("collected <name>_...") and the host
        form ("collecting <name>_...").

        Args:
            name (str): Subcloud or host name (e.g. "subcloud3", "controller-1").

        Returns:
            bool: True if a matching progress line is present.
        """
        return re.search(r"collect(?:ed|ing)\s+{}_\d".format(re.escape(name)), self.output_text) is not None

    def get_execution_time(self) -> Optional[int]:
        """Return the collect duration in seconds, if present.

        collect does not print an "elapsed time was N secs" line; instead the
        duration appears inside the final ``done (HH:MM:SS  <size>  <pct>)``
        marker. The last such marker (the tarball-creation line) is used.

        Returns:
            Optional[int]: Duration in seconds, or None if no duration marker
            was found.
        """
        matches = re.findall(self._DONE_DURATION_PATTERN, self.output_text)
        if not matches:
            return None
        hours, minutes, seconds = matches[-1]
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

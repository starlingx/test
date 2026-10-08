import json
from typing import List, Optional

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.ansible_playbook.object.backup_size_estimation_object import BackupSizeEstimationObject


class BackupSizeEstimationOutput:
    """Parses the platform backup size-estimation records from an ansible ``-vv`` log.

    The platform backup playbook (``backup.yml`` -> role ``backup/backup-system``)
    performs a free-space pre-check before archiving. It runs ``du`` on each
    directory it will back up, accumulates ``total_platform_size_estimation``, then
    fails if that estimate exceeds the free space in the backup directory.

    On a System Controller, the dc-vault is measured separately with a singular
    ``du -sh -k {{ dc_vault_permdir }} --exclude '<exclude_targets>' ...`` command.
    The dc-vault ``du`` must apply the ``--exclude`` list so that ``exclude_dirs`` is
    honoured by BOTH the archive and the size estimate; otherwise the reservation is
    inflated by the excluded content.

    The parsing result is a single ``BackupSizeEstimationObject`` holding:
      - the dc-vault ``du`` command string (to confirm ``--exclude`` was applied),
      - the dc-vault ``du`` result in KiB,
      - the final ``total_platform_size_estimation`` (KiB),
      - the ``available_disk_size`` (KiB),
      - whether the "not enough free space" gate passed (was skipped).

    Log line shape (``-vv``)::

        <ts> p=<pid> u=sysadmin n=ansible INFO| <status>: [localhost] [=> (item=<dir>)] => {<json>}
    """

    def __init__(self, log_lines: List[str], dc_vault_permdir: str = "/opt/dc-vault"):
        """Parse the relevant records out of the ansible log lines.

        Args:
            log_lines (List[str]): Lines of the ansible log (already scoped to the run of interest).
            dc_vault_permdir (str): The dc-vault path the playbook measures. Defaults to "/opt/dc-vault".
        """
        self.dc_vault_permdir = dc_vault_permdir
        self.backup_size_estimation = BackupSizeEstimationObject(dc_vault_permdir=dc_vault_permdir)
        self._parse(log_lines)

    def _extract_json(self, line: str) -> Optional[dict]:
        """Extract and decode the trailing JSON object from a log line.

        Args:
            line (str): A single ansible log line.

        Returns:
            Optional[dict]: The decoded object, or None if the line has no JSON payload.
        """
        marker = " => {"
        index = line.find(marker)
        if index == -1:
            return None
        json_text = line[index + len(marker) - 1 :].strip()
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None

    def _parse(self, log_lines: List[str]) -> None:
        """Populate the estimation object from the log lines.

        Args:
            log_lines (List[str]): Lines of the ansible log.
        """
        for line in log_lines:
            record = self._extract_json(line)
            if record is None:
                continue

            # dc-vault singular du task: cmd + stdout at top level. The playbook
            # command is: du -sh -k  {{ dc_vault_permdir }} --exclude '...' | awk ...
            command = record.get("cmd")
            if command and "du -sh -k" in command and self.dc_vault_permdir in command and "--exclude" in command:
                stdout = record.get("stdout", "").strip()
                if stdout.isdigit():
                    self.backup_size_estimation.set_dc_vault_du_command(command)
                    self.backup_size_estimation.set_dc_vault_size_kib(int(stdout))

            ansible_facts = record.get("ansible_facts")
            if isinstance(ansible_facts, dict):
                if "total_platform_size_estimation" in ansible_facts:
                    try:
                        self.backup_size_estimation.set_total_platform_size_estimation(int(ansible_facts["total_platform_size_estimation"]))
                    except (TypeError, ValueError):
                        get_logger().log_info("Could not parse total_platform_size_estimation from log record")
                if "available_disk_size" in ansible_facts:
                    try:
                        self.backup_size_estimation.set_available_disk_size_kib(int(ansible_facts["available_disk_size"]))
                    except (TypeError, ValueError):
                        get_logger().log_info("Could not parse available_disk_size from log record")

            # The "fail if not enough free space" gate. If it is skipped, the
            # condition (available < estimate) was False -> enough space.
            false_condition = record.get("false_condition")
            if false_condition and "available_disk_size|int < total_platform_size_estimation|int" in false_condition:
                self.backup_size_estimation.set_space_precheck_passed(True)

    def get_backup_size_estimation(self) -> BackupSizeEstimationObject:
        """Return the parsed estimation object.

        Returns:
            BackupSizeEstimationObject: The values parsed from the ansible log.
        """
        return self.backup_size_estimation

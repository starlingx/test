from enum import Enum


class DcManagerSubcloudListBackupEnum(Enum):
    """
    Enum class for possible values for the 'backup status' column of the table displayed as output of the
    'dcmanager subcloud list' command.

    """

    NONE = 'None'  # No recent backup was performed.
    COMPLETED = 'backup-completed'  # The backup process completed successfully.
    FAILED = 'backup-failed'  # The backup process failed.
    IN_PROGRESS = 'backup-in-progress'  # The backup process is currently ongoing.

from enum import Enum


class DcManagerSubcloudListPrestageEnum(Enum):
    """
    Enum class for possible values for the 'prestage status' column of the table displayed as output of the
    'dcmanager subcloud list' command.

    """

    NONE = 'None'  # No prestaging process has been performed or is needed.
    COMPLETED = 'prestage-completed'  # The prestage process completed successfully.
    FAILED = 'prestage-failed'  # The prestage process failed.
    IN_PROGRESS = 'prestage-in-progress'  # The prestage process is currently ongoing.

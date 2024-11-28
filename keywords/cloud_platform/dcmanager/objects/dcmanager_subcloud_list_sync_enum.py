from enum import Enum


class DcManagerSubcloudListSyncEnum(Enum):
    """
    Enum class for possible values for the 'sync' column of the table displayed as output of the
    'dcmanager subcloud list' command.

    """

    IN_SYNC = 'in-sync'  # The subcloud is synchronized with the central cloud.
    SYNCING = 'syncing'  # The synchronization is in progress.
    OUT_OF_SYNC = 'out-of-sync'  # The subcloud is not synchronized and may need updates or fixes.

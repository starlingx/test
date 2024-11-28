from enum import Enum


class DcManagerSubcloudListManagementEnum(Enum):
    """
    Enum class for possible values for the 'management' column of the table displayed as output of the
    'dcmanager subcloud list' command.

    """

    MANAGED = "managed"  # The subcloud is being managed by the central cloud.
    UNMANAGED = "unmanaged"  # The subcloud is currently not managed by the central cloud.

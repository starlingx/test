from enum import Enum


class DcManagerSubcloudListAvailabilityEnum(Enum):
    """
    Enum class for possible values for the 'availability' column of the table displayed as output of the
    'dcmanager subcloud list' command.

    """

    ONLINE = "online"  # The subcloud is operational and accessible.
    OFFLINE = "offline"  # The subcloud is not accessible.
    DEGRADED = "degraded"  # The subcloud is accessible but experiencing performance issues or partial service failures.

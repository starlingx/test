from enum import Enum


class DcManagerSubcloudListDeployEnum(Enum):
    """
    Enum class for possible values for the 'deploy status' column of the table displayed as output of the
    'dcmanager subcloud list' command.

    """

    COMPLETE = 'complete'  # The deployment process finished successfully.
    DEPLOYING = 'deploying'  # The deployment process is currently ongoing.
    FAILED = 'failed'  # The deployment process failed.
    RE_DEPLOYING = 're-deploying'  # The subcloud is undergoing a redeployment process.

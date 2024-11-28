from enum import Enum


class TransferDirection(Enum):
    """
    Enum class to support the possible values of the 'transfer_direction' property of the SecureTransferFileInputObject class.
    Possible values:

    FROM_LOCAL_TO_REMOTE: a 'put' SFTP command will be used to transfer the file.
    FROM_REMOTE_TO_LOCAL: a 'get' SFTP command will be used to transfer the file.

    """

    FROM_LOCAL_TO_REMOTE = 1
    FROM_REMOTE_TO_LOCAL = 2

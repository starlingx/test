from enum import Enum


class SystemApplicationStatusEnum(Enum):
    """Enum representing the possible statuses of a StarlingX system application."""

    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    UPLOAD_FAILED = "upload-failed"
    APPLYING = "applying"
    APPLY_FAILED = "apply-failed"
    APPLIED = "applied"
    UPDATING = "updating"
    UPDATE_FAILED = "update-failed"
    REMOVING = "removing"
    REMOVE_FAILED = "remove-failed"
    DELETING = "deleting"

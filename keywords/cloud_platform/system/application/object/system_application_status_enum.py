from enum import Enum


class SystemApplicationStatusEnum(Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    UPLOAD_FAILED = 'upload-failed'
    APPLYING = "applying"
    APPLY_FAILED = "apply-failed"
    APPLIED = "applied"
    REMOVING = 'removing'
    REMOVE_FAILED = 'remove-failed'
    DELETING = 'deleting'

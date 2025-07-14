from enum import Enum


class OpenstackStackStatusEnum(Enum):
    CREATE_IN_PROGRESS = "create_in_progress"
    CREATE_COMPLETE = "create_complete"
    CREATE_FAILED = "create_failed"
    DELETE_IN_PROGRESS = "delete_in_progress"
    DELETE_COMPLETE = "delete_complete"
    DELETE_FAILED = "delete_failed"
    UPDATE_IN_PROGRESS = "update_in_progress"
    UPDATE_COMPLETE = "update_complete"
    UPDATE_FAILED = "update_failed"
    ROLLBACK_IN_PROGRESS = "rollback_in_progress"
    ROLLBACK_COMPLETE = "rollback_complete"
    ROLLBACK_FAILED = "rollback_failed"
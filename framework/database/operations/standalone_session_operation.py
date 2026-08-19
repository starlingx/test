import uuid
from datetime import datetime, timezone
from typing import Optional

from framework.database.connection.database_operation_manager import DatabaseOperationManager


class StandaloneSessionOperation:
    """
    Database operations for creating standalone test sessions.
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def create_standalone_session(
        self,
        run_id: int,
        lab_id: int,
        tag: str,
        lab_runtime_config_id: int,
        session_info_id: Optional[int] = None,
        sys_type: Optional[str] = None,
        kubernetes_version: Optional[str] = None,
        ceph_version: Optional[str] = None,
    ) -> str:
        """
        Creates a standalone test session in the database.

        Args:
            run_id: Run ID from create_standalone_run.
            lab_id: execution_target_id of the lab.
            tag: Descriptive tag for the session.
            session_info_id: Maps to a TestPlan's session_info_id.
                Defaults to -1 if not provided.
            sys_type: System type (e.g. 'AIO-DX', 'Standard').
            kubernetes_version: K8s version.
            ceph_version: Ceph version.
            lab_runtime_config_id: ID from create_lab_runtime_config.

        Returns:
            str: The session_id (UUID string).

        Raises:
            ValueError: If unable to insert the session.
        """
        session_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        session_info_id = session_info_id if session_info_id is not None else -1
        sys_type = f"'{sys_type}'" if sys_type is not None else "NULL"
        kubernetes_version = f"'{kubernetes_version}'" if kubernetes_version is not None else "NULL"
        ceph_version = f"'{ceph_version}'" if ceph_version is not None else "NULL"

        insert_query = (
            "INSERT INTO test_session ("
            "id, run_id, lab_id, session_info_id, tag, "
            "sys_type, kubernetes_version, ceph_version, "
            "lab_runtime_config_id, created_at"
            ") VALUES ("
            f"'{session_id}', {run_id}, {lab_id}, {session_info_id}, '{tag}', "
            f"{sys_type}, {kubernetes_version}, {ceph_version}, "
            f"{lab_runtime_config_id}, '{created_at}'"
            ") RETURNING id"
        )

        results = self.database_operation_manager.execute_query(insert_query)

        if results:
            return str(results[0][0])

        raise ValueError("Unable to insert standalone session.")

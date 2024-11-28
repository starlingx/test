from contextlib import contextmanager

import psycopg2
from config.configuration_manager import ConfigurationManager


class DatabaseConnectionManager:

    def __init__(self):
        db_config = ConfigurationManager.get_database_config()
        self.host = db_config.get_host_name()
        self.dbname = db_config.get_db_name()
        self.db_port = db_config.get_db_port()
        self.user = db_config.get_user_name()
        self.password = db_config.get_password()

    @contextmanager
    def open_conn_and_get_cur(
        self,
        autocommit=True,
        close_cur=True,
        close_conn=True,
        cursor_factory=None,
    ):
        """This function will establish a connection to the database. It can be used in a
        'with open_conn_and_get_cur' statement to keep the connection alive for the duration
        of the block.
        """

        conn = cursor = None
        try:
            conn = psycopg2.connect(
                f"dbname='{self.dbname}' port={self.db_port} user='{self.user}' host='{self.host}' password='{self.password}'",
                connect_timeout=60,
                cursor_factory=cursor_factory,
            )
            if autocommit:
                conn.set_session(autocommit=True)
            cursor = conn.cursor()
            yield cursor
        finally:
            if close_cur and cursor is not None:
                cursor.close()
            if close_conn and conn is not None:
                conn.close()

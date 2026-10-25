import pandas as pd
import psycopg2


class PostgresConnectorContextManager:

    def __init__(self, db_host: str, db_name: str, db_user: str, db_password: str, db_port: int = 5432):
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.conn = None

    def __enter__(self):
        self.conn = psycopg2.connect(
            host=self.db_host,
            port=self.db_port,
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_password,
            connect_timeout=10,
        )
        self.conn.set_session(readonly=True, autocommit=True)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self.conn is not None:
            self.conn.close()
            self.conn = None
        return False

    def get_data_sql(self, sql: str, params=None) -> pd.DataFrame:
        if self.conn is None:
            raise RuntimeError("No active connection. Use the connector inside a 'with' block!")
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [col.name for col in cursor.description]
            rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=columns)
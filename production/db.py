import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

def getConnection():
    databaseHost = os.getenv("DB_HOST")
    databasePort = os.getenv("DB_PORT", "5432")
    databaseName = os.getenv("DB_NAME", "postgres")
    databaseUser = os.getenv("DB_USER")
    databasePassword = os.getenv("DB_PASSWORD")
    databaseSslMode = os.getenv("DB_SSLMODE", "require")

    return psycopg2.connect(
        host=databaseHost,
        port=databasePort,
        dbname=databaseName,
        user=databaseUser,
        password=databasePassword,
        sslmode=databaseSslMode,
        cursor_factory=RealDictCursor
    )

@contextmanager
def openTransaction(externalConnection=None):
    if externalConnection is not None:
        yield externalConnection
        return

    isRequestScoped = False
    try:
        from flask import has_request_context, g
        if has_request_context():
            if not hasattr(g, "dbConnection") or g.dbConnection is None or g.dbConnection.closed != 0:
                g.dbConnection = getConnection()
            conn = g.dbConnection
            isRequestScoped = True
        else:
            conn = getConnection()
    except Exception:
        conn = getConnection()

    try:
        yield conn
        if not isRequestScoped:
            conn.commit()
    except Exception:
        if not isRequestScoped:
            conn.rollback()
        raise
    finally:
        if not isRequestScoped:
            conn.close()

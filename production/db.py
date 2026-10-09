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
    isCallerOwned = externalConnection is not None
    activeConnection = externalConnection if isCallerOwned else getConnection()
    try:
        yield activeConnection
        if not isCallerOwned:
            activeConnection.commit()
    except Exception:
        if not isCallerOwned:
            activeConnection.rollback()
        raise
    finally:
        if not isCallerOwned:
            activeConnection.close()

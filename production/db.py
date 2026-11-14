import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("production.db")

_dbPool = None

def getPool():
    global _dbPool
    if _dbPool is None or _dbPool.closed:
        databaseHost = os.getenv("DB_HOST")
        databasePort = os.getenv("DB_PORT", "5432")
        databaseName = os.getenv("DB_NAME", "postgres")
        databaseUser = os.getenv("DB_USER")
        databasePassword = os.getenv("DB_PASSWORD")
        databaseSslMode = os.getenv("DB_SSLMODE", "require")

        _dbPool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=databaseHost,
            port=databasePort,
            dbname=databaseName,
            user=databaseUser,
            password=databasePassword,
            sslmode=databaseSslMode,
            cursor_factory=RealDictCursor
        )
    return _dbPool

def checkoutConnection():
    pool = getPool()
    conn = pool.getconn()
    if conn.closed != 0:
        try:
            pool.putconn(conn, close=True)
        except Exception:
            pass
        conn = pool.getconn()
    return conn

def releaseConnection(conn, error=False):
    if conn is None:
        return
    pool = getPool()
    if error or conn.closed != 0:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            pool.putconn(conn, close=(conn.closed != 0))
        except Exception:
            pass
    else:
        try:
            conn.commit()
            pool.putconn(conn)
        except Exception:
            try:
                pool.putconn(conn, close=True)
            except Exception:
                pass

def getConnection():
    return checkoutConnection()

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
                g.dbConnection = checkoutConnection()
            conn = g.dbConnection
            isRequestScoped = True
        else:
            conn = checkoutConnection()
    except Exception:
        conn = checkoutConnection()

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
            releaseConnection(conn)

def _normalizeDbParams(params):
    if params is None:
        return ()
    if isinstance(params, (list, tuple, dict)):
        return params
    return (params,)

def fetchAll(sql, params=None, conn=None):
    cleanParams = _normalizeDbParams(params)
    try:
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, cleanParams)
                return cursor.fetchall()
    except Exception as err:
        snippet = " ".join(sql.split())[:90]
        print(f"[DB Error] FetchAll failed: {err} | SQL: {snippet} | Params: {cleanParams}")
        logger.exception("DB FetchAll error: %s | SQL: %s", err, snippet)
        raise

def fetchOne(sql, params=None, conn=None):
    cleanParams = _normalizeDbParams(params)
    try:
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, cleanParams)
                return cursor.fetchone()
    except Exception as err:
        snippet = " ".join(sql.split())[:90]
        print(f"[DB Error] FetchOne failed: {err} | SQL: {snippet} | Params: {cleanParams}")
        logger.exception("DB FetchOne error: %s | SQL: %s", err, snippet)
        raise

def execute(sql, params=None, conn=None):
    cleanParams = _normalizeDbParams(params)
    try:
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, cleanParams)
                return cursor.rowcount
    except Exception as err:
        snippet = " ".join(sql.split())[:90]
        print(f"[DB Error] Execute failed: {err} | SQL: {snippet} | Params: {cleanParams}")
        logger.exception("DB Execute error: %s | SQL: %s", err, snippet)
        raise

def executeReturning(sql, params=None, conn=None):
    cleanParams = _normalizeDbParams(params)
    try:
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, cleanParams)
                return cursor.fetchone()
    except Exception as err:
        snippet = " ".join(sql.split())[:90]
        print(f"[DB Error] ExecuteReturning failed: {err} | SQL: {snippet} | Params: {cleanParams}")
        logger.exception("DB ExecuteReturning error: %s | SQL: %s", err, snippet)
        raise

import os
import pymysql
from pymysql.cursors import DictCursor
from flask import g, current_app
from config import Config

def get_db_connection():
    """
    Establish and return a new PyMySQL connection.
    Uses DictCursor so results are accessed as Python dictionaries.
    """
    try:
        connection = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=False
        )
        return connection
    except pymysql.MySQLError as e:
        try:
            current_app.logger.error(f"Database connection error: {e}")
        except Exception:
            pass
        raise e

def get_db():
    """
    Get or create a database connection for the current Flask request context.
    Stores the active connection in Flask's global 'g' object.
    """
    if 'db' not in g:
        g.db = get_db_connection()
    return g.db

def close_db(e=None):
    """
    Closes the database connection at the end of the request context.
    """
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass

def query_db(query, args=(), one=False):
    """
    Execute a SELECT query and return dictionary results.
    :param query: SQL query with %s placeholders
    :param args: tuple or list of arguments
    :param one: if True, returns only the first record or None
    """
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(query, args)
        rv = cursor.fetchall()
        return (rv[0] if rv else None) if one else rv

def execute_db(query, args=(), commit=True):
    """
    Execute an INSERT, UPDATE, or DELETE query.
    :param query: SQL query with %s placeholders
    :param args: tuple or list of arguments
    :param commit: whether to commit the transaction
    :return: lastrowid on INSERT, rowcount on UPDATE/DELETE
    """
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(query, args)
            if commit:
                db.commit()
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount
    except pymysql.MySQLError as e:
        if commit:
            db.rollback()
        raise e

def init_db(schema_file=None):
    """
    Initializes the MySQL database using the provided schema.sql file.
    Creates the database if it does not exist, connects, and runs DDL & seed scripts.
    """
    if schema_file is None:
        schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql')

    # Step 1: Connect to MySQL server without selecting database to ensure DB exists
    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        charset='utf8mb4',
        autocommit=True
    )
    with conn.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    conn.close()

    # Step 2: Connect to the database and execute statements from schema.sql
    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset='utf8mb4',
        autocommit=True
    )
    with open(schema_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Split SQL file by statements (handling semicolons)
    statements = []
    current_statement = []
    for line in sql_content.splitlines():
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith('--') or line_stripped.startswith('/*'):
            continue
        current_statement.append(line)
        if line_stripped.endswith(';'):
            stmt = '\n'.join(current_statement).strip()
            if stmt:
                statements.append(stmt)
            current_statement = []

    with conn.cursor() as cursor:
        for stmt in statements:
            if stmt.strip():
                cursor.execute(stmt)
    conn.close()

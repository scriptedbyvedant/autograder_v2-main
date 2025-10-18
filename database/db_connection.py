# File: database/db_connection.py
import yaml
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_params(config_path: str = "credentials.yaml") -> dict:
    """
    Load database connection parameters from a YAML file.
    """
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    return {
        "host":     cfg.get("host", "localhost"),
        "port":     cfg.get("port", 5432),
        "database": cfg.get("database"),
        "user":     cfg.get("user"),
        "password": cfg.get("password")
    }

def get_connection() -> psycopg2.extensions.connection:
    """
    Establish and return a new PostgreSQL connection using credentials.yaml.
    """
    params = get_db_params()
    conn = psycopg2.connect(**params)
    return conn

def get_dict_cursor(conn: psycopg2.extensions.connection) -> RealDictCursor:
    """
    Return a RealDictCursor for the given connection.
    """
    return conn.cursor(cursor_factory=RealDictCursor)

import os
import json
import sys
import logging
import re
from trino.dbapi import connect
from trino.auth import BasicAuthentication
import psycopg2 
from psycopg2 import sql

# --- LOGGING CONFIGURATION ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- TRINO CONFIGURATION ---
JSON_FILE = os.getenv("JSON_FILE", "/etc/trino/register/register_table.json")
TRINO_HOST = os.getenv("TRINO_HOST")
TRINO_PORT = os.getenv("TRINO_PORT", "8443")
TRINO_USER = os.getenv("TRINO_USER", "admin")
TRINO_PASSWORD = os.getenv("TRINO_PASSWORD")
SSL_CERT_PATH = os.getenv("SSL_CERT_PATH")

# --- POSTGRES CONFIGURATION (Hive Metastore) ---
PG_HOST = os.getenv("POSTGRES_HOST")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_USER = os.getenv("POSTGRES_USER", "postgres")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")
PG_DB = os.getenv("POSTGRES_DB", "metastore")
PG_SSL_MODE = os.getenv("POSTGRES_SSL_MODE", "require")
PG_CA_CERT = os.getenv("PG_CA_CERT") 

def get_trino_password():
    raw_val = os.getenv("TRINO_PASSWORD")
    if not raw_val:
        return None
    if raw_val.strip().startswith('{'):
        try:
            password_map = json.loads(raw_val)
            return password_map.get(TRINO_USER)
        except Exception:
            pass
    return raw_val

def get_trino_connection():
    trino_password = get_trino_password()
    if not trino_password:
        logger.error("Could not retrieve Trino password.")
        sys.exit(1)
    try:
        return connect(
            host=TRINO_HOST,
            port=int(TRINO_PORT),
            user=TRINO_USER,
            auth=BasicAuthentication(TRINO_USER, trino_password),
            http_scheme="https" if SSL_CERT_PATH else "http",
            verify=SSL_CERT_PATH if SSL_CERT_PATH else True
        )
    except Exception as e:
        logger.error(f"Failed to connect to Trino: {e}")
        sys.exit(1)

def get_postgres_connection():
    logger.info(f"Connecting to PostgreSQL at {PG_HOST}:{PG_PORT}...")
    try:
        conn_params = {
            "host": PG_HOST, "port": PG_PORT, "user": PG_USER,
            "password": PG_PASSWORD, "dbname": PG_DB, "sslmode": PG_SSL_MODE
        }
        if PG_CA_CERT:
            conn_params["sslrootcert"] = PG_CA_CERT
        return psycopg2.connect(**conn_params)
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return None

def extract_catalog_name(catalog_key, content):
    """
    Handles both the YAML-string style and the new JSON-dictionary style.
    """
    if isinstance(content, str):
        # Case: The catalog content is a block of properties text
        match = re.search(r"hive\.metastore\.thrift\.catalog-name\s*=\s*([^\s\n]+)", content)
        return match.group(1) if match else catalog_key
    # Case: The catalog content is a dictionary (your new JSON)
    # We use the key directly as the catalog name
    return catalog_key

def register_catalogs_to_postgres(pg_conn, catalogs_dict):
    """Inserts the catalog keys from JSON into the 'CTLGS' table."""
    if not pg_conn:
        return

    cursor = pg_conn.cursor()
    for catalog_key, content in catalogs_dict.items():
        # We only insert into Postgres if the content is a dictionary 
        # (meaning it represents a full catalog structure)
        if not isinstance(content, dict):
            continue

        catalog_name = extract_catalog_name(catalog_key, content)
        
        # Metadata for the CTLGS table
        description = f"Catalog: {catalog_name}"
        # Updated location URI format
        location_uri = f"file:/opt/hive/data/warehouse/{catalog_name}"

        insert_sql = """
        INSERT INTO "CTLGS" (
            "CTLG_ID", "NAME", "DESC", "LOCATION_URI", "CREATE_TIME"
        ) 
        VALUES (
            (SELECT COALESCE(MAX("CTLG_ID"), 0) + 1 FROM "CTLGS"),
            %s, %s, %s, extract(epoch from now())::bigint
        );
        """
        
        try:
            logger.info(f"Inserting catalog '{catalog_name}' into PostgreSQL 'CTLGS'...")
            cursor.execute(insert_sql, (catalog_name, description, location_uri))
            pg_conn.commit()
            logger.info(f"Successfully registered catalog '{catalog_name}' in Postgres.")
        except Exception as e:
            logger.error(f"Failed to insert catalog '{catalog_name}' into Postgres: {e}")
            pg_conn.rollback()

def process_registrations(trino_conn, pg_conn, data):
    """Main loop for both Postgres registration and Trino table registration."""
    catalogs = data.get("catalogs", {})
    if not catalogs:
        logger.warning("No catalogs found in JSON.")
        return

    # 1. Postgres Registration
    register_catalogs_to_postgres(pg_conn, catalogs)

    # 2. Trino Registration
    cursor = trino_conn.cursor()
    for catalog_name, catalog_content in catalogs.items():
        # Skip if this is just a string configuration (already handled/not for Trino iteration)
        if not isinstance(catalog_content, dict):
            continue

        schemas = catalog_content.get("schemas", {})
        for schema_name, schema_content in schemas.items():
            # CREATE SCHEMA
            create_schema_sql = f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.{schema_name}"
            try:
                logger.info(f"Trino: Executing {create_schema_sql}")
                cursor.execute(create_schema_sql)
            except Exception as e:
                logger.error(f"Trino: Error creating schema {schema_name}: {e}")
                continue

            # REGISTER TABLES
            tables = schema_content.get("tables", {})
            for table_name, table_info in tables.items():
                location = table_info.get("location")
                if not location: continue

                register_sql = f"""
                CALL {catalog_name}.system.register_table(
                    schema_name => '{schema_name}',
                    table_name  => '{table_name}',
                    table_location => '{location}'
                )
                """
                try:
                    logger.info(f"Trino: Registering {catalog_name}.{schema_name}.{table_name}")
                    cursor.execute(register_sql)
                except Exception as e:
                    logger.error(f"Trino: Failed to register table {table_name}: {e}")

def main():
    logger.info("--- Starting Dual Registration (Postgres + Trino) ---")
    
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON: {e}")
        sys.exit(1)

    trino_conn = get_trino_connection()
    pg_conn = get_postgres_connection()

    try:
        process_registrations(trino_conn, pg_conn, data)
    finally:
        if trino_conn: trino_conn.close()
        if pg_conn: pg_conn.close()
        logger.info("Connections closed.")

    logger.info("--- Process Complete ---")

if __name__ == "__main__":
    main()
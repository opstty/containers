import os
import json
import requests
import sys
import urllib.parse
import logging

# --- LOGGING CONFIGURATION ---
# Set LOG_LEVEL env var to DEBUG or INFO. Defaults to INFO.
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
RULES_FILE = os.getenv("RULES_FILE", "/etc/trino/access-control/rules.json")
PASSWORD_FILE = os.getenv("PASSWORD_FILE", "/tmp/password.db")
ROLES_FILE = os.getenv("ROLES_FILE", "/etc/superset/access-control/roles.json")
SUPERSET_URL = os.getenv("SUPERSET_URL")
SUPERSET_USERNAME = os.getenv("SUPERSET_USERNAME", "admin")
SUPERSET_PASSWORD = os.getenv("SUPERSET_PASSWORD", "admin")
TRINO_HOST = os.getenv("TRINO_HOST")
TRINO_PORT = os.getenv("TRINO_PORT", "8443")
SSL_CERT_PATH = os.getenv("SSL_CERT_PATH", "/etc/superset/certificate-authority/root.ca") 

def get_auth_credentials():
    """Authenticates with Superset and retrieves Token + CSRF."""
    session = requests.Session()
    verify_ssl = SSL_CERT_PATH if SSL_CERT_PATH else True

    logger.info(f"Authenticating with Superset at {SUPERSET_URL}...")
    login_url = f"{SUPERSET_URL}/api/v1/security/login"
    login_payload = {"username": SUPERSET_USERNAME, "password": SUPERSET_PASSWORD, "provider": "db"}

    try:
        login_res = session.post(login_url, json=login_payload, verify=verify_ssl)
        login_res.raise_for_status()
        access_token = login_res.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {access_token}"})

        csrf_url = f"{SUPERSET_URL}/api/v1/security/csrf_token/"
        csrf_res = session.get(csrf_url, verify=verify_ssl)
        csrf_res.raise_for_status()
        csrf_token = csrf_res.json().get("result")
        logger.info("Authentication and CSRF successful.")
        return session, csrf_token
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        sys.exit(1)

def fetch_valid_permissions(session, csrf_token):
    """
    Fetches all valid permission-resource mappings and builds a nested map.
    Returns: dict { normalized_action: { resource_name: id } }
    """
    logger.info("Fetching valid permission-resource mappings from Superset...")
    perm_url = f"{SUPERSET_URL}/api/v1/security/permissions-resources/"
    headers = {"X-CSRFToken": csrf_token}
    
    nested_map = {}
    page = 0 
    page_size = 100

    try:
        while True:
            query = f"(page:{page},page_size:{page_size})"
            encoded_query = urllib.parse.quote(query)
            url = f"{perm_url}?q={encoded_query}"
            
            response = session.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("result", [])
            if not results:
                break
            
            for p in results:
                p_id = p.get("id")
                p_name = p.get("permission", {}).get("name")
                v_name = p.get("view_menu", {}).get("name")
                
                if p_id and p_name and v_name:
                    # Normalize action for easier lookup (e.g., 'can_read')
                    p_name_norm = p_name.replace(" ", "_").lower()
                    if p_name_norm not in nested_map:
                        nested_map[p_name_norm] = {}
                    nested_map[p_name_norm][v_name] = p_id
            
            total_count = data.get("count", 0)
            if (page + 1) * page_size >= total_count:
                break
            page += 1
            
        logger.info(f"Successfully loaded {len(nested_map)} unique permission actions.")
        logger.debug(f"Sample permission mapping: {list(nested_map.items())[:3]}")
        return nested_map
    except Exception as e:
        logger.error(f"Error fetching permissions: {e}")
        return {}

def find_id_in_map(perm_map, action, resource_name=None, catalog=None, sub_resource=None):
    """
    The core resolver that searches the nested map based on context.
    """
    action_norm = action.replace(" ", "_").lower()
    resources = perm_map.get(action_norm, {})
    
    if not resources:
        logger.debug(f"Action '{action_norm}' not found in permission map.")
        return None

    # Priority 1: Trino Scoping (Catalog/Schema/Database)
    if catalog:
        # Superset uses [trino_catalog_name] for the database display name
        base_pattern = f"[trino_{catalog}]"
        logger.debug(f"Searching Trino context: Action='{action_norm}', Base='{base_pattern}'")

        if sub_resource:
            # Handle segmented resources like [trino_cat].[system].[metadata]
            parts = sub_resource.split('.')
            target_pattern = base_pattern
            for part in parts:
                target_pattern += f".[{part}]"
            
            logger.debug(f"Targeting pattern (segmented): {target_pattern}")
            for res_name, p_id in resources.items():
                if target_pattern in res_name:
                    logger.debug(f"MATCH FOUND: {res_name} (ID: {p_id})")
                    return p_id
        else:
            # Handle base database access: [trino_cat]
            logger.debug(f"Targeting pattern (base): {base_pattern}")
            for res_name, p_id in resources.items():
                if base_pattern in res_name:
                    logger.debug(f"MATCH FOUND: {res_name} (ID: {p_id})")
                    return p_id
        return None

    # Priority 2: Global Scoping (Specific View Menu)
    if resource_name:
        logger.debug(f"Searching Global context: Action='{action_norm}', Resource='{resource_name}'")
        p_id = resources.get(resource_name)
        if p_id:
            logger.debug(f"MATCH FOUND: {resource_name} (ID: {p_id})")
        return p_id

    # Priority 3: Fallback (Return first available resource for this action)
    logger.debug(f"No specific resource provided for '{action_norm}'. Using fallback (first available).")
    return next(iter(resources.values())) if resources else None

def resolve_role_permissions(role_content, perm_map):
    """
    Iterates through the roles.json structure and collects permission IDs.
    Supports both string (old) and dict (new) global permission formats.
    """
    resolved_ids = set()

    # 1. Handle Global Permissions (top-level list)
    global_perms = role_content.get("permissions", [])
    for p in global_perms:
        p_id = None
        if isinstance(p, dict):
            # New Format: {"permission": "can_read", "view_menu": "Dashboard"}
            action = p.get("permission")
            res = p.get("view_menu")
            if action and res:
                logger.debug(f"Resolving dict-based global permission: {action} on {res}")
                p_id = find_id_in_map(perm_map, action, resource_name=res)
        elif isinstance(p, str):
            # Old Format: "can_read"
            logger.debug(f"Resolving string-based global permission: {p}")
            p_id = find_id_in_map(perm_map, p)

        if p_id:
            resolved_ids.add(p_id)
        else:
            logger.warning(f"Could not resolve global permission: {p}")

    # 2. Handle Catalog-level Permissions (nested dict)
    catalogs = role_content.get("catalogs", {})
    for cat_name, cat_data in catalogs.items():
        logger.debug(f"Processing catalog: {cat_name}")
        cat_perms = cat_data.get("permissions", {})
        
        for action, value in cat_perms.items():
            if value is True:
                # Special case: catalog_access: true means [trino_cat].[cat_name]
                if action == "catalog_access":
                    p_id = find_id_in_map(perm_map, action, catalog=cat_name, sub_resource=cat_name)
                else:
                    # database_access: true means [trino_cat]
                    p_id = find_id_in_map(perm_map, action, catalog=cat_name)
                
                if p_id: 
                    resolved_ids.add(p_id)
                else: 
                    logger.warning(f"Could not resolve {action} (boolean) for {cat_name}")
            
            elif isinstance(value, list):
                # List of sub-resources: e.g., ['system', 'system.metadata']
                for sub in value:
                    p_id = find_id_in_map(perm_map, action, catalog=cat_name, sub_resource=sub)
                    if p_id: 
                        resolved_ids.add(p_id)
                    else: 
                        logger.warning(f"Could not resolve {action} on {sub} for {cat_name}")
    
    return list(resolved_ids)

def add_database_to_superset(session, csrf_token, catalog_name, trino_user, trino_password):
    """Adds a Trino database to Superset."""
    db_url = f"{SUPERSET_URL}/api/v1/database/"
    safe_password = urllib.parse.quote(trino_password)
    sqlalchemy_uri = f"trino://{trino_user}:{safe_password}@{TRINO_HOST}:{TRINO_PORT}/{catalog_name}"
    display_name = f"trino_{catalog_name}"

    headers = {"X-CSRFToken": csrf_token, "Content-Type": "application/json"}
    extra_config = {"engine_params": {"connect_args": {"verify": SSL_CERT_PATH, "http_scheme": "https"}}} if SSL_CERT_PATH else {}

    payload = {
        "database_name": display_name,
        "sqlalchemy_uri": sqlalchemy_uri,
        "engine": "trino",
        "extra": json.dumps(extra_config)
    }

    try:
        logger.info(f"Syncing Database: {display_name}")
        response = session.post(db_url, json=payload, headers=headers)
        if response.status_code == 201:
            logger.info(f"Successfully created DB: {display_name}")
        elif response.status_code == 409 or "already exists" in response.text:
            logger.info(f"Skipped DB: {display_name} (Already exists)")
        else:
            logger.error(f"DB Error {display_name}: {response.text}")
    except Exception as e:
        logger.error(f"Connection error for {display_name}: {e}")

def sync_role_to_superset(session, csrf_token, role_name, permission_ids):
    """Creates/Updates a role and its permissions using IDs."""
    roles_url = f"{SUPERSET_URL}/api/v1/security/roles/"
    headers = {"X-CSRFToken": csrf_token, "Content-Type": "application/json"}

    if not permission_ids:
        logger.warning(f"Skipping role sync for '{role_name}': No valid permission IDs found.")
        return

    try:
        logger.info(f"Syncing Role: {role_name} ({len(permission_ids)} permissions)")
        roles_resp = session.get(roles_url, headers=headers)
        roles_resp.raise_for_status()
        existing_roles = roles_resp.json().get("result", [])
        role_id = next((r['id'] for r in existing_roles if r['name'] == role_name), None)

        if role_id:
            logger.debug(f"Role '{role_name}' found (ID: {role_id}). Updating...")
            session.put(f"{roles_url}{role_id}", json={"name": role_name}, headers=headers).raise_for_status()
            perm_url = f"{roles_url}{role_id}/permissions"
            session.post(perm_url, json={"permission_view_menu_ids": permission_ids}, headers=headers).raise_for_status()
            logger.info(f"Role '{role_name}' updated successfully.")
        else:
            logger.debug(f"Role '{role_name}' not found. Creating new role...")
            create_resp = session.post(roles_url, json={"name": role_name}, headers=headers)
            create_resp.raise_for_status()
            new_role_id = create_resp.json().get("id")
            perm_url = f"{roles_url}{new_role_id}/permissions"
            session.post(perm_url, json={"permission_view_menu_ids": permission_ids}, headers=headers).raise_for_status()
            logger.info(f"Role '{role_name}' created and synced.")
    except Exception as e:
        logger.error(f"Role API error for '{role_name}': {e}")

def main():
    logger.info("--- Starting Access Control Sync ---")
    try:
        with open(RULES_FILE, 'r') as f: rules_data = json.load(f)
        with open(PASSWORD_FILE, 'r') as f: password_map = json.load(f)
        with open(ROLES_FILE, 'r') as f: roles_data = json.load(f)
        logger.debug("Configuration files loaded successfully.")
    except Exception as e:
        logger.error(f"File loading error: {e}")
        return

    session, csrf_token = get_auth_credentials()
    perm_map = fetch_valid_permissions(session, csrf_token)

    # 1. Sync Databases
    catalogs = rules_data.get("catalogs", [])
    if catalogs:
        logger.info(f"--- Starting Database Sync ({len(catalogs)} catalogs) ---")
        for entry in catalogs:
            catalog, user = entry.get("catalog"), entry.get("user")
            if catalog and user:
                password = password_map.get(user)
                if password:
                    add_database_to_superset(session, csrf_token, catalog, user, password)
                else:
                    logger.error(f"No password found for user: {user}")

    # 2. Sync Roles
    roles_config = roles_data.get("roles", {})
    if roles_config:
        logger.info(f"--- Starting Role Sync ({len(roles_config)} roles) ---")
        for role_name, role_content in roles_config.items():
            permission_ids = resolve_role_permissions(role_content, perm_map)
            sync_role_to_superset(session, csrf_token, role_name, permission_ids)
    else:
        logger.warning("No roles found in roles.json.")

    logger.info("--- Process Complete ---")

if __name__ == "__main__":
    main()

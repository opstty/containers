import os
import json
import bcrypt
import sys

# --- CONFIGURATION ---
# Source file (JSON containing the passwords)
INPUT_PASSWORD_FILE = os.getenv("INPUT_PASSWORD_FILE", "/tmp/password.db")
# Destination file for Trino
OUTPUT_PASSWORD_FILE = os.getenv("OUTPUT_PASSWORD_FILE", "/etc/trino/auth/password/password.db")
# Bcrypt hashing cost (equivalent to -C 10)
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", 10))
# ---------------------

def generate_trino_password_db():
    """
    Reads a JSON file, hashes passwords with Bcrypt,
    and writes the file in htpasswd format for Trino.
    """
    
    # 1. Read source file
    print(f"[*] Reading source passwords from {INPUT_PASSWORD_FILE}...")
    try:
        with open(INPUT_PASSWORD_FILE, 'r') as f:
            # Read the entire content
            content = f.read().strip()
            
            # Equivalent of 'sed s/}.*/}/':
            # If the file contains text after the last '}', truncate it.
            if '}' in content:
                content = content[:content.rfind('}') + 1]
            
            password_map = json.loads(content)
    except FileNotFoundError:
        print(f"[!] Error: Source file {INPUT_PASSWORD_FILE} not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[!] Error: Failed to parse JSON from {INPUT_PASSWORD_FILE}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Unexpected error reading source: {e}")
        sys.exit(1)

    # 2. Process and hash
    print(f"[*] Hashing {len(password_map)} credentials using Bcrypt (rounds={BCRYPT_ROUNDS})...")
    htpasswd_lines = []
    
    try:
        for user, password in password_map.items():
            # Convert string to bytes for bcrypt
            password_bytes = str(password).encode('utf-8')
            
            # Generate salt and hash (equivalent to htpasswd -B)
            salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
            hashed_password = bcrypt.hashpw(password_bytes, salt)
            
            # Format for the file: user:hash
            # Decode the hash to utf-8 for text output
            line = f"{user}:{hashed_password.decode('utf-8')}"
            htpasswd_lines.append(line)
            
    except Exception as e:
        print(f"[!] Error during hashing process: {e}")
        sys.exit(1)

    # 3. Write destination file
    print(f"[*] Writing to {OUTPUT_PASSWORD_FILE}...")
    try:
        # Ensure the destination directory exists
        os.makedirs(os.path.dirname(OUTPUT_PASSWORD_FILE), exist_ok=True)
        
        with open(OUTPUT_PASSWORD_FILE, 'w') as f:
            for line in htpasswd_lines:
                f.write(line + "\n")
        
        # 4. Set file permissions (equivalent to chmod 644)
        os.chmod(OUTPUT_PASSWORD_FILE, 0o644)
        print(f"[+] Successfully created {OUTPUT_PASSWORD_FILE} with permissions 644.")

    except Exception as e:
        print(f"[!] Error writing password file: {e}")
        sys.exit(1)

def main():
    generate_trino_password_db()
    print("[*] Done.")

if __name__ == "__main__":
    main()

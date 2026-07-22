import os
import json
import bcrypt
import sys

# --- CONFIGURATION ---
# Le fichier source (le JSON contenant les mots de passe)
INPUT_PASSWORD_FILE = os.getenv("INPUT_PASSWORD_FILE", "/tmp/password.db")
# Le fichier de destination pour Trino
OUTPUT_PASSWORD_FILE = os.getenv("OUTPUT_PASSWORD_FILE", "/etc/trino/auth/password/password.db")
# Coût de hachage pour Bcrypt (équivalent à -C 10)
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", 10))
# ---------------------

def generate_trino_password_db():
    """
    Lit un fichier JSON, hache les mots de passe avec Bcrypt 
    et écrit le fichier au format htpasswd pour Trino.
    """
    
    # 1. Lecture du fichier source
    print(f"[*] Reading source passwords from {INPUT_PASSWORD_FILE}...")
    try:
        with open(INPUT_PASSWORD_FILE, 'r') as f:
            # On lit tout le contenu
            content = f.read().strip()
            
            # Simulation du 'sed s/}.*/}/' : 
            # Si le fichier contient du texte après le dernier '}', on le tronque.
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

    # 2. Traitement et Hachage
    print(f"[*] Hashing {len(password_map)} credentials using Bcrypt (rounds={BCRYPT_ROUNDS})...")
    htpasswd_lines = []
    
    try:
        for user, password in password_map.items():
            # Conversion de la string en bytes pour bcrypt
            password_bytes = str(password).encode('utf-8')
            
            # Génération du salt et hachage (équivalent à htpasswd -B)
            salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
            hashed_password = bcrypt.hashpw(password_bytes, salt)
            
            # Formatage pour le fichier : user:hash
            # On décode le hash en utf-8 pour pouvoir l'écrire en texte
            line = f"{user}:{hashed_password.decode('utf-8')}"
            htpasswd_lines.append(line)
            
    except Exception as e:
        print(f"[!] Error during hashing process: {e}")
        sys.exit(1)

    # 3. Écriture du fichier de destination
    print(f"[*] Writing to {OUTPUT_PASSWORD_FILE}...")
    try:
        # S'assurer que le répertoire de destination existe
        os.makedirs(os.path.dirname(OUTPUT_PASSWORD_FILE), exist_ok=True)
        
        with open(OUTPUT_PASSWORD_FILE, 'w') as f:
            for line in htpasswd_lines:
                f.write(line + "\n")
        
        # 4. Gestion des permissions (équivalent à chmod 644)
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

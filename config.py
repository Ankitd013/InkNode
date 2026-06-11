import os

# Figure out the exact folder where this file lives so we use absolute paths
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

def load_env():
    """Reads settings from the .env file and returns them as a clean dictionary."""
    config = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                # Ignore empty lines or comment lines starting with '#'
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    config[key.strip()] = val.strip()
    return config

def save_env(updates):
    """
    Non-destructive environment saver. 
    Updates specific keys from the dictionary, leaves manual additions intact,
    and preserves comments in the .env file.
    """
    env_path = os.path.join(BASE_DIR, '.env')
    existing_lines = []
    
    # 1. Read existing lines into memory
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            existing_lines = f.readlines()
            
    new_lines = []
    updated_keys = set()
    
    # 2. Scan and replace only the keys that were passed in
    for line in existing_lines:
        # Ignore empty lines and comments
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=', 1)[0].strip()
            
            if key in updates:
                # Inject the new value from the web UI
                new_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
            else:
                # Keep the existing manual variable exactly as it is
                new_lines.append(line)
        else:
            # Preserve comments and whitespace
            new_lines.append(line)
            
    # 3. Append any brand new variables that didn't exist in the file yet
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")
            
    # 4. Write it back safely
    with open(env_path, 'w') as f:
        f.writelines(new_lines)

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

def save_env(new_config):
    """Takes a dictionary of settings and writes them cleanly back to the .env file."""
    with open(ENV_FILE, "w") as f:
        for key, val in new_config.items():
            f.write(f"{key}={val}\n")

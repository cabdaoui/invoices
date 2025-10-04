import os
import json

def load_env():
    """
    Charge le fichier env/env.json avec encodage UTF-8 (gestion BOM).
    """
    env_path = os.path.join("env", "env.json")
    with open(env_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

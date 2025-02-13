import json
CONFIG_FILENAME = "config.json"

def load_config():
    try:
        with open(CONFIG_FILENAME, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []
    

def save_config(items):
    with open(CONFIG_FILENAME, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=4)

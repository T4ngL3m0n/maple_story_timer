import os, json
CONFIG_FILENAME = "config.json"

def load_config():
        if os.path.exists(CONFIG_FILENAME):
            with open(CONFIG_FILENAME, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            iniconfig = [{
                "text": "新的項目",
                "play_mode": "文字",
                "tts_text": "新的項目",
                "audio_path": "",
                "countdown": 30,
                "infinite_loop": False,
                "volume": 50}]
            return iniconfig
    

def save_config(items):
    with open(CONFIG_FILENAME, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=4)

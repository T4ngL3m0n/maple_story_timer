from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from hotkey_utils import canonicalize_hotkey

CONFIG_FILENAME = "config.json"
CONFIG_VERSION = 2

DEFAULT_GLOBAL_HOTKEYS = {
    "stop_all": "Ctrl+Shift+S",
    "show_window": "Ctrl+Shift+M",
}

DEFAULT_UI = {
    "theme": "dark_game",
    "language": "zh-TW",
}


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _normalize_play_mode(value: Any) -> str:
    return "音檔" if value == "音檔" else "文字"


def _new_item(index: int) -> dict:
    return {
        "id": str(uuid4()),
        "name": f"項目 {index + 1}",
        "play_mode": "文字",
        "tts_text": "新的項目",
        "audio_path": "",
        "countdown_sec": 30,
        "infinite_loop": False,
        "volume": 80,
        "hotkey": f"Ctrl+F{index + 1}" if index < 12 else None,
        "sort_order": index,
    }


def default_config() -> dict:
    item = _new_item(0)
    item["name"] = "新的項目"
    return {
        "config_version": CONFIG_VERSION,
        "items": [item],
        "global_hotkeys": DEFAULT_GLOBAL_HOTKEYS.copy(),
        "ui": DEFAULT_UI.copy(),
    }


def _backup_file(config_path: Path, tag: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = config_path.with_name(f"{config_path.stem}.backup.{tag}.{timestamp}{config_path.suffix}")
    backup_path.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path


def _normalize_item(raw_item: Any, fallback_index: int) -> dict:
    if not isinstance(raw_item, dict):
        raw_item = {}

    item_id = str(raw_item.get("id") or uuid4())
    name = str(raw_item.get("name") or raw_item.get("text") or "").strip() or "未命名項目"

    play_mode = _normalize_play_mode(raw_item.get("play_mode"))
    tts_text = str(raw_item.get("tts_text") or "")
    audio_path = str(raw_item.get("audio_path") or "")

    countdown_candidate = raw_item.get("countdown_sec", raw_item.get("countdown", 30))
    countdown_sec = _clamp(_safe_int(countdown_candidate, 30), 1, 359999)

    volume = _clamp(_safe_int(raw_item.get("volume", 80), 80), 0, 100)
    sort_order = _safe_int(raw_item.get("sort_order", fallback_index), fallback_index)

    raw_hotkey = raw_item.get("hotkey")
    hotkey = canonicalize_hotkey(str(raw_hotkey)) if raw_hotkey else None

    return {
        "id": item_id,
        "name": name,
        "play_mode": play_mode,
        "tts_text": tts_text,
        "audio_path": audio_path,
        "countdown_sec": countdown_sec,
        "infinite_loop": bool(raw_item.get("infinite_loop", False)),
        "volume": volume,
        "hotkey": hotkey,
        "sort_order": sort_order,
    }


def migrate_legacy_list(legacy_items: list) -> dict:
    migrated_items = []

    for index, raw_item in enumerate(legacy_items):
        normalized_item = _normalize_item(raw_item, index)
        normalized_item["hotkey"] = f"Ctrl+F{index + 1}" if index < 12 else None
        normalized_item["sort_order"] = index
        migrated_items.append(normalized_item)

    config = {
        "config_version": CONFIG_VERSION,
        "items": migrated_items,
        "global_hotkeys": DEFAULT_GLOBAL_HOTKEYS.copy(),
        "ui": DEFAULT_UI.copy(),
    }
    return normalize_config(config)


def normalize_config(raw_config: Any) -> dict:
    if not isinstance(raw_config, dict):
        return default_config()

    raw_items = raw_config.get("items", [])
    if not isinstance(raw_items, list):
        raw_items = []

    normalized_items = []
    seen_ids = set()

    for index, raw_item in enumerate(raw_items):
        item = _normalize_item(raw_item, index)
        while item["id"] in seen_ids:
            item["id"] = str(uuid4())
        seen_ids.add(item["id"])
        normalized_items.append(item)

    normalized_items.sort(key=lambda item: item.get("sort_order", 0))
    for index, item in enumerate(normalized_items):
        item["sort_order"] = index

    global_hotkeys = raw_config.get("global_hotkeys", {})
    stop_all_hotkey = canonicalize_hotkey(str(global_hotkeys.get("stop_all", ""))) or DEFAULT_GLOBAL_HOTKEYS["stop_all"]
    show_window_hotkey = canonicalize_hotkey(str(global_hotkeys.get("show_window", ""))) or DEFAULT_GLOBAL_HOTKEYS["show_window"]

    ui_config = raw_config.get("ui", {})
    theme = str(ui_config.get("theme", DEFAULT_UI["theme"]))
    language = str(ui_config.get("language", DEFAULT_UI["language"]))

    return {
        "config_version": CONFIG_VERSION,
        "items": normalized_items,
        "global_hotkeys": {
            "stop_all": stop_all_hotkey,
            "show_window": show_window_hotkey,
        },
        "ui": {
            "theme": theme,
            "language": language,
        },
    }


def load_config() -> dict:
    config_path = Path(CONFIG_FILENAME)

    if not config_path.exists():
        config = default_config()
        save_config(config)
        return config

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        _backup_file(config_path, "broken")
        config = default_config()
        save_config(config)
        return config

    if isinstance(raw, list):
        _backup_file(config_path, "v1")
        config = migrate_legacy_list(raw)
        save_config(config)
        return config

    normalized = normalize_config(raw)
    if raw != normalized:
        save_config(normalized)
    return normalized


def save_config(app_config: dict) -> None:
    config_path = Path(CONFIG_FILENAME)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(app_config, ensure_ascii=False, indent=4), encoding="utf-8")

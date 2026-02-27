import json

import data_manager


def test_legacy_list_migrates_and_backups(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    legacy_items = []
    for index in range(13):
        legacy_items.append(
            {
                "text": f"item-{index + 1}",
                "play_mode": "文字",
                "tts_text": "hello",
                "audio_path": "",
                "countdown": 5,
                "infinite_loop": False,
                "volume": "80",
            }
        )

    config_path.write_text(json.dumps(legacy_items, ensure_ascii=False, indent=2), encoding="utf-8")
    monkeypatch.setattr(data_manager, "CONFIG_FILENAME", str(config_path))

    migrated = data_manager.load_config()

    assert migrated["config_version"] == 2
    assert len(migrated["items"]) == 13
    assert migrated["items"][0]["hotkey"] == "Ctrl+F1"
    assert migrated["items"][11]["hotkey"] == "Ctrl+F12"
    assert migrated["items"][12]["hotkey"] is None

    backup_files = list(tmp_path.glob("config.backup.v1.*.json"))
    assert backup_files


def test_invalid_v2_values_are_normalized(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    invalid_config = {
        "config_version": 2,
        "items": [
            {
                "id": "same-id",
                "name": "",
                "play_mode": "bad",
                "countdown_sec": -10,
                "volume": 999,
                "hotkey": "F1",
                "sort_order": 3,
            },
            {
                "id": "same-id",
                "name": "ok",
                "play_mode": "音檔",
                "countdown_sec": 10,
                "volume": 10,
                "hotkey": "Ctrl+1",
                "sort_order": 1,
            },
        ],
        "global_hotkeys": {
            "stop_all": "Ctrl+Shift+S",
            "show_window": "Ctrl+Shift+M",
        },
    }

    config_path.write_text(json.dumps(invalid_config, ensure_ascii=False, indent=2), encoding="utf-8")
    monkeypatch.setattr(data_manager, "CONFIG_FILENAME", str(config_path))

    normalized = data_manager.load_config()

    assert normalized["config_version"] == 2
    assert len(normalized["items"]) == 2
    assert normalized["items"][0]["sort_order"] == 0
    assert normalized["items"][1]["sort_order"] == 1
    for item in normalized["items"]:
        assert item["countdown_sec"] >= 1
        assert 0 <= item["volume"] <= 100

    hotkeys = {item["hotkey"] for item in normalized["items"]}
    assert hotkeys == {None, "Ctrl+1"}
    assert normalized["items"][0]["id"] != normalized["items"][1]["id"]

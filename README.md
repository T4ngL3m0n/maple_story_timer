# Maple Story Timer

桌面倒數工具（PySide6），支援多項目並行倒數、TTS/音檔提醒、Windows 全域熱鍵。

## Author & Source

- Developer: L3m0nT4ng
- GitHub: https://github.com/T4ngL3m0n/maple_story_timer

## Features

- 單頁工作台 UI（左側清單 / 中間控制 / 右側即時編輯）
- 多個倒數項目可同時執行
- 每個項目可自訂全域熱鍵（`Ctrl/Alt/Shift + F1~F12/A~Z/0~9`）
- 全域控制熱鍵
- `Ctrl+Shift+S`：停止全部
- `Ctrl+Shift+M`：顯示主視窗
- 拖曳排序、複製項目、即時自動儲存
- 設定檔自動升級（v1 list -> v2 object）並備份
- 到點通知支援：
- 文字模式（gTTS）
- 音檔模式（mp3/wav/ogg）

## Environment

- OS: Windows（全域熱鍵使用 Windows API）
- Python: 3.10+

## Installation

```powershell
python -m pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

## Config

設定檔為 `config.json`，目前格式為 `config_version = 2`。

```json
{
  "config_version": 2,
  "items": [
    {
      "id": "uuid",
      "name": "項目名稱",
      "play_mode": "文字",
      "tts_text": "提醒內容",
      "audio_path": "",
      "countdown_sec": 30,
      "infinite_loop": false,
      "volume": 80,
      "hotkey": "Ctrl+F1",
      "sort_order": 0
    }
  ],
  "global_hotkeys": {
    "stop_all": "Ctrl+Shift+S",
    "show_window": "Ctrl+Shift+M"
  },
  "ui": {
    "theme": "dark_game",
    "language": "zh-TW"
  }
}
```

舊版 `config.json`（list 結構）在啟動時會自動：

- 轉換為 v2 格式
- 產生備份檔：`config.backup.v1.YYYYMMDD-HHMMSS.json`
- 前 12 筆項目預設熱鍵：`Ctrl+F1` ~ `Ctrl+F12`

## Test

```powershell
python -m pytest -q -p no:cacheprovider tests
```

## Build (PyInstaller)

```powershell
pyinstaller --clean --onefile --noconsole --name=MS_TimerApp --collect-all PySide6 --collect-all pygame --hidden-import=gtts main.py
```

## Notes

- 關閉主視窗會直接停止所有計時並退出程式（不進系統匣）。
- 第一次安裝 `PySide6` 可能較久，因為 Qt 套件體積較大。


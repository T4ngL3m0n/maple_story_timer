from __future__ import annotations

from typing import Dict

from PySide6.QtCore import QObject, QTimer, Signal

from audio_manager import play_audio, speak_text


class TimerManager(QObject):
    timer_tick = Signal(str, int, int)
    timer_state_changed = Signal(str, str)

    STATE_IDLE = "idle"
    STATE_RUNNING = "running"
    STATE_LOOPING = "looping"
    STATE_STOPPED = "stopped"

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.active_timers: Dict[str, Dict] = {}
        self.remaining_by_item: Dict[str, int] = {}
        self.total_by_item: Dict[str, int] = {}
        self.state_by_item: Dict[str, str] = {}

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._on_tick)

    def start_item(self, item: Dict) -> None:
        item_id = str(item.get("id"))
        countdown_sec = max(1, int(item.get("countdown_sec", 30)))

        timer_payload = {
            "item_id": item_id,
            "remaining": countdown_sec,
            "countdown_sec": countdown_sec,
            "infinite_loop": bool(item.get("infinite_loop", False)),
            "audio_path": item.get("audio_path", ""),
            "tts_text": item.get("tts_text", ""),
            "play_mode": item.get("play_mode", "文字"),
            "volume": max(0, min(100, int(item.get("volume", 80)))),
        }

        self.active_timers[item_id] = timer_payload
        self.total_by_item[item_id] = countdown_sec
        self.remaining_by_item[item_id] = countdown_sec

        state = self.STATE_LOOPING if timer_payload["infinite_loop"] else self.STATE_RUNNING
        self.state_by_item[item_id] = state
        self.timer_state_changed.emit(item_id, state)
        self.timer_tick.emit(item_id, countdown_sec, countdown_sec)

        if not self._tick_timer.isActive():
            self._tick_timer.start()

    def toggle_item(self, item: Dict) -> None:
        item_id = str(item.get("id"))
        if self.is_running(item_id):
            self.stop_item(item_id)
        else:
            self.start_item(item)

    def stop_item(self, item_id: str) -> None:
        payload = self.active_timers.pop(item_id, None)
        if payload is None and item_id not in self.state_by_item:
            return

        total = self.total_by_item.get(item_id)
        if total is None and payload is not None:
            total = int(payload.get("countdown_sec", 0))
            self.total_by_item[item_id] = total
        if total is None:
            total = 0

        self.remaining_by_item[item_id] = 0
        self.state_by_item[item_id] = self.STATE_STOPPED
        self.timer_tick.emit(item_id, 0, total)
        self.timer_state_changed.emit(item_id, self.STATE_STOPPED)

        if not self.active_timers and self._tick_timer.isActive():
            self._tick_timer.stop()

    def stop_all(self) -> None:
        for item_id in list(self.active_timers.keys()):
            self.stop_item(item_id)

    def remove_item(self, item_id: str) -> None:
        if self.is_running(item_id):
            self.stop_item(item_id)
        self.active_timers.pop(item_id, None)
        self.remaining_by_item.pop(item_id, None)
        self.total_by_item.pop(item_id, None)
        self.state_by_item.pop(item_id, None)

    def is_running(self, item_id: str) -> bool:
        return item_id in self.active_timers

    def get_remaining(self, item_id: str, default_total: int) -> int:
        if item_id in self.remaining_by_item:
            return self.remaining_by_item[item_id]

        state = self.state_by_item.get(item_id, self.STATE_IDLE)
        if state == self.STATE_STOPPED:
            return 0
        return default_total

    def get_state(self, item_id: str) -> str:
        return self.state_by_item.get(item_id, self.STATE_IDLE)

    def _on_tick(self) -> None:
        for item_id, payload in list(self.active_timers.items()):
            payload["remaining"] -= 1
            remaining = payload["remaining"]
            total = payload["countdown_sec"]

            if remaining > 0:
                self.remaining_by_item[item_id] = remaining
                self.timer_tick.emit(item_id, remaining, total)
                continue

            self._play_notification(payload)

            if payload["infinite_loop"]:
                payload["remaining"] = total
                self.remaining_by_item[item_id] = total
                self.state_by_item[item_id] = self.STATE_LOOPING
                self.timer_state_changed.emit(item_id, self.STATE_LOOPING)
                self.timer_tick.emit(item_id, total, total)
            else:
                self.active_timers.pop(item_id, None)
                self.remaining_by_item[item_id] = 0
                self.state_by_item[item_id] = self.STATE_STOPPED
                self.timer_tick.emit(item_id, 0, total)
                self.timer_state_changed.emit(item_id, self.STATE_STOPPED)

        if not self.active_timers and self._tick_timer.isActive():
            self._tick_timer.stop()

    @staticmethod
    def _play_notification(payload: Dict) -> None:
        volume = max(0.0, min(1.0, int(payload.get("volume", 80)) / 100.0))
        play_mode = payload.get("play_mode", "文字")

        if play_mode == "音檔":
            audio_path = str(payload.get("audio_path", "")).strip()
            if audio_path:
                play_audio(audio_path, volume)
            return

        tts_text = str(payload.get("tts_text", "")).strip()
        if tts_text:
            speak_text(tts_text, volume)

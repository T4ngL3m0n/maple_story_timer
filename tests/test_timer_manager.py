import pytest

qtcore = pytest.importorskip("PySide6.QtCore")

from timer_manager import TimerManager


def _ensure_app():
    app = qtcore.QCoreApplication.instance()
    if app is None:
        app = qtcore.QCoreApplication([])
    return app


def test_timer_stops_after_countdown():
    _ensure_app()
    manager = TimerManager()

    states = []
    ticks = []

    manager.timer_state_changed.connect(lambda item_id, state: states.append((item_id, state)))
    manager.timer_tick.connect(lambda item_id, remaining, total: ticks.append((item_id, remaining, total)))

    item = {
        "id": "item-1",
        "countdown_sec": 2,
        "infinite_loop": False,
        "play_mode": "文字",
        "tts_text": "",
        "audio_path": "",
        "volume": 80,
    }

    manager.start_item(item)
    manager._on_tick()
    manager._on_tick()

    assert not manager.is_running("item-1")
    assert states[-1] == ("item-1", "stopped")
    assert ticks[-1] == ("item-1", 0, 2)


def test_infinite_loop_keeps_timer_running():
    _ensure_app()
    manager = TimerManager()

    item = {
        "id": "loop-item",
        "countdown_sec": 1,
        "infinite_loop": True,
        "play_mode": "文字",
        "tts_text": "",
        "audio_path": "",
        "volume": 80,
    }

    manager.start_item(item)
    manager._on_tick()

    assert manager.is_running("loop-item")
    assert manager.get_state("loop-item") == "looping"
    assert manager.get_remaining("loop-item", 1) == 1

    manager.stop_all()

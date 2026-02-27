from __future__ import annotations

import hashlib
import os
import threading
from pathlib import Path

from gtts import gTTS
import pygame

MIXER_READY = False
CACHE_DIR = Path(".tts_cache")


def _ensure_mixer() -> bool:
    global MIXER_READY
    if MIXER_READY:
        return True

    try:
        pygame.mixer.init()
        MIXER_READY = True
        return True
    except Exception as exc:
        print(f"初始化音效裝置失敗: {exc}")
        return False


def play_audio(file_path: str, volume: float) -> None:
    def _play() -> None:
        if not _ensure_mixer():
            return

        try:
            sound = pygame.mixer.Sound(file_path)
            sound.set_volume(max(0.0, min(1.0, float(volume))))
            sound.play()
        except Exception as exc:
            print(f"播放音檔時發生錯誤: {exc}")

    threading.Thread(target=_play, daemon=True).start()


def _tts_cache_path(text: str, lang: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(f"{lang}:{text}".encode("utf-8")).hexdigest()
    return CACHE_DIR / f"tts_{digest}.mp3"


def speak_text(text: str, volume: float, lang: str = "zh-TW") -> None:
    def _speak() -> None:
        if not text.strip():
            return

        cache_file = _tts_cache_path(text, lang)

        try:
            if not cache_file.exists():
                tts = gTTS(text=text, lang=lang, tld="com.au")
                tts.save(str(cache_file))
            play_audio(str(cache_file), volume)
        except Exception as exc:
            print(f"TTS 發聲失敗: {exc}")

    threading.Thread(target=_speak, daemon=True).start()

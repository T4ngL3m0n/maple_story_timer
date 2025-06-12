# audio_manager.py
import threading
import os
from gtts import gTTS
import pygame
import traceback

# 在 module 載入時初始化一次 mixer
pygame.mixer.init()

def play_audio(file_path: str, volume: float):
    """非阻塞播放音檔，支援同時多重播放。"""
    def _play():
        try:
            # print(file_path)
            # print(volume)
            sound = pygame.mixer.Sound(file_path)
            sound.set_volume(volume)  # 0.0–1.0
            sound.play()              # 非阻塞
        except Exception as e:
            print(f"播放音檔時發生錯誤: {e}")
            print(traceback.format_exc())

    threading.Thread(target=_play, daemon=True).start()

def speak_text(text: str, volume: float, lang: str = "zh-TW"):
    """產生或重用 MP3，再非阻塞播放。"""
    def _speak():
        try:
            # 以 uuid 避免檔名衝突、或特殊字元問題
            filename = f"./tts_{text}.mp3"
            # 產生檔案
            if not os.path.exists(filename):
                tts = gTTS(text=text, lang=lang, tld="com.au")
                tts.save(filename)
            # 播放完後可選擇刪除檔案，或留給下一次重用
            play_audio(filename, volume)
        except Exception as e:
            print(f"TTS 發聲失敗: {e}")

    threading.Thread(target=_speak, daemon=True).start()

if __name__ == "__main__":
    speak_text("三三三", 0.8)
    import time
    time.sleep(1)
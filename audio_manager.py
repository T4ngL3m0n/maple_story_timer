# audio_manager.py
import threading
import pyttsx3  # pip install pyttsx3
import pygame

def play_audio(file_path):
    def _play():
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"播放音檔時發生錯誤: {e}")

    threading.Thread(target=_play).start()

def speak_text(text):
    def _speak():
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"TTS 發聲失敗: {e}")

    threading.Thread(target=_speak).start()

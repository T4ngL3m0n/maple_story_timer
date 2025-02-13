# timer_manager.py
import threading
import time
from audio_manager import play_audio, speak_text

class TimerManager:
    def __init__(self):
        # timers 字典: key = item_id, value = { "thread": 執行緒, "stop_flag": threading.Event() }
        self.timers = {}

    def start_item(self, item_id, countdown, infinite_loop, audio_path, text_for_tts, play_mode, on_update_label):
        """
        新增參數:
          - text_for_tts: 要 TTS 的文字
          - play_mode: "text" or "audio"
        """
        # 如果此 item 已有執行中的 thread，就先停止
        if item_id in self.timers:
            self.stop_item(item_id)

        stop_flag = threading.Event()
        self.timers[item_id] = {
            "thread": None,
            "stop_flag": stop_flag
        }

        def timer_thread():
            while not stop_flag.is_set():
                remaining = countdown
                # 進行一次 "倒數 -> 播放音檔或TTS"
                while remaining > 0 and not stop_flag.is_set():
                    # 更新 GUI (顯示倒數時間)
                    on_update_label(remaining)
                    time.sleep(1)
                    remaining -= 1

                # 如果被停止，就跳出
                if stop_flag.is_set():
                    break

                # 倒數結束，依 play_mode 決定要播放音檔或TTS
                if play_mode == "音檔":
                    if audio_path:
                        play_audio(audio_path)
                elif play_mode == "文字":
                    if text_for_tts.strip():
                        speak_text(text_for_tts)
                else:
                    print("沒有指定有效的播放模式 (audio/text)")

                # 如果不是無限循環，播放完就結束
                if not infinite_loop:
                    break

            # 離開前，顯示 0 或清空
            on_update_label(0)
            print(f"Item {item_id} 計時結束")

        t = threading.Thread(target=timer_thread, daemon=True)
        self.timers[item_id]["thread"] = t
        t.start()

    def stop_item(self, item_id):
        """
        停止指定 item_id 的計時。
        """
        if item_id in self.timers:
            timer_info = self.timers[item_id]
            stop_flag = timer_info["stop_flag"]
            stop_flag.set()

            thread = timer_info["thread"]
            if thread and thread.is_alive():
                thread.join(timeout=0.1)

            del self.timers[item_id]

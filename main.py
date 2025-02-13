# main.py
import tkinter as tk

from data_manager import load_config, save_config
from settings_window import open_settings_window
from timer_manager import TimerManager
from tkinter import filedialog

def check_audio_files_exist(item):
    """
    只針對 play_mode == '音檔' 的 item 檢查 audio_path 是否存在。
    若不存在，就讓使用者重新選擇檔案，並馬上存檔。
    """
    if not item.get("audio_path", "") :
        new_path = filedialog.askopenfilename(
            title=f"選擇 {item['text']} 的音檔",
            filetypes=[("MP3 files", "*.mp3")]
        )
        if new_path:
            item["audio_path"] = new_path

    

def format_time(sec):
    m = sec // 60
    s = sec % 60
    return f"{m:02d}:{s:02d}"

def main():
    root = tk.Tk()
    root.title("倒數計時器 - build by DC: l3m0nt4ng")

    items = load_config()
    if not items:
        # 若 config.pkl 不存在或是空的，就建立預設 5 個
        items = []
        for i in range(5):
            items.append({
                "text": f"Item{i+1}",
                "countdown": 5,
                "audio_path": "",
                "infinite_loop": False,
                "play_mode": "文字",  # 預設為文字模式
                "tts_text": f"Item{i+1}"   # 預設 TTS 文字 (可自行調整)
            })
        save_config(items)

    # 檢查 audio_path 是否遺失 (僅對 play_mode == "音檔")

    # 建立 TimerManager
    timer_manager = TimerManager()

    # 建立主視窗顯示容器
    items_frame = tk.Frame(root)
    items_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    item_rows = []

    def create_item_row(index, item):
        """
        產生單列UI：顯示 text, 倒數時間Label, [開始][停止], 以及模式
        """
        frame = tk.Frame(items_frame, bd=1, relief=tk.GROOVE, pady=5)
        frame.pack(fill=tk.X, padx=5, pady=2)

        label_text = tk.Label(frame, text=item.get("text", f"Item{index+1}"), width=20)
        label_text.pack(side=tk.LEFT)

        label_countdown = tk.Label(frame, text="00:00", width=8)
        label_countdown.pack(side=tk.LEFT, padx=5)

        btn_start = tk.Button(frame, text="開始", command=lambda: on_start(index))
        btn_start.pack(side=tk.LEFT, padx=5)

        btn_stop = tk.Button(frame, text="停止", command=lambda: on_stop(index))
        btn_stop.pack(side=tk.LEFT, padx=5)

        # 顯示播放模式
        play_mode = item.get('play_mode', '文字')
        label_mode = tk.Label(frame, text=f"模式:{play_mode}")
        label_mode.pack(side=tk.LEFT, padx=5)

        return (frame, label_countdown)

    def on_start(item_id):
        """
        按下「開始」時，啟動該 item 的倒數
        """

        item = items[item_id]
        countdown = item.get("countdown", 5)
        infinite_loop = item.get("infinite_loop", False)
        audio_path = item.get("audio_path", "")
        play_mode = item.get("play_mode", "文字")
        tts_text = item.get("tts_text", "")  # 用於 TTS 的文字
        if play_mode == '音檔':
            item = check_audio_files_exist(item)
            items[item_id] = item
            save_config(items)

        label_countdown = item_rows[item_id][1]

        def update_label(remaining_sec):
            root.after(0, lambda: label_countdown.config(text=format_time(remaining_sec)))

        # 這裡將 TTS 文字與音檔路徑都帶入 TimerManager
        # 讓 TimerManager 執行「倒數 -> 播放/發音 -> 無限循環」
        timer_manager.start_item(
            item_id=item_id,
            countdown=countdown,
            infinite_loop=infinite_loop,
            audio_path=audio_path,
            text_for_tts=tts_text,
            play_mode=play_mode,
            on_update_label=update_label
        )

    def on_stop(item_id):
        timer_manager.stop_item(item_id)

    def refresh_items_ui():
        """
        重新繪製所有 Item row
        """
        for c in items_frame.winfo_children():
            c.destroy()
        item_rows.clear()
        for idx, itm in enumerate(items):
            row_ui = create_item_row(idx, itm)
            item_rows.append(row_ui)

    refresh_items_ui()

    def open_settings():
        def save_callback(new_items):
            """
            設定視窗點「儲存更新」或「儲存並關閉」時呼叫
            """
            nonlocal items
            items = new_items
            save_config(items)
            refresh_items_ui()

        open_settings_window(root, items, save_callback)

    btn_setting = tk.Button(root, text="設定", command=open_settings)
    btn_setting.pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()

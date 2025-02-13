# settings_window.py
import tkinter as tk
from tkinter import filedialog, messagebox
import shutil
import os
from tkinter import ttk  # Combobox

current_selected_index = None  # 用於記錄最後有效選取的 index

def open_settings_window(parent, items, save_callback):
    """
    打開設定視窗。
    items: list of dict，每個 dict = {
        "text": "項目名稱(只顯示)",
        "play_mode": "文字" or "音檔",
        "tts_text": "若 play_mode == '文字' 時要唸出的文字",
        "audio_path": "若 play_mode == '音檔' 時 mp3 檔路徑",
        "countdown": int (總秒數),
        "infinite_loop": bool
    }
    save_callback: 呼叫後會將 items 寫回 config.pkl，並更新主視窗
    """
    win = tk.Toplevel(parent)
    win.title("設定項目")
    win.geometry("700x450")

    # 左側 Listbox + scrollbar
    list_frame = tk.Frame(win)
    list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=listbox.yview)

    # 右側詳細設定區
    detail_frame = tk.Frame(win)
    detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 1) 項目名稱
    tk.Label(detail_frame, text="項目名稱:").grid(row=0, column=0, sticky=tk.W, pady=2)
    entry_item_name = tk.Entry(detail_frame, width=30)
    entry_item_name.grid(row=0, column=1, columnspan=2, sticky=tk.W)

    # 2) 播放模式: 下拉 (文字 / 音檔)
    tk.Label(detail_frame, text="播放模式:").grid(row=1, column=0, sticky=tk.W, pady=2)
    play_mode_var = tk.StringVar()  # "文字" or "音檔"
    combo_mode = ttk.Combobox(detail_frame, textvariable=play_mode_var,
                              values=["文字", "音檔"], state="readonly", width=10)
    combo_mode.grid(row=1, column=1, sticky=tk.W)
    combo_mode.set("文字")  # 預設

    # 3) TTS 要唸出的文字 (僅在 "文字" 時顯示)
    label_tts = tk.Label(detail_frame, text="文字:")
    entry_tts = tk.Entry(detail_frame, width=30)

    # 4) 音檔路徑 (僅在 "音檔" 時顯示)
    label_audio = tk.Label(detail_frame, text="音檔路徑:")
    entry_audio = tk.Entry(detail_frame, width=30)
    btn_browse_audio = tk.Button(detail_frame, text="選擇檔案", command=lambda: browse_audio_file(entry_audio))

    # 5) 倒數時間 (分、秒)
    tk.Label(detail_frame, text="倒數-分:").grid(row=3, column=0, sticky=tk.W, pady=2)
    entry_minute = tk.Entry(detail_frame, width=5)
    entry_minute.grid(row=3, column=1, sticky=tk.W)
    tk.Label(detail_frame, text="秒:").grid(row=3, column=2, sticky=tk.W)
    entry_second = tk.Entry(detail_frame, width=5)
    entry_second.grid(row=3, column=3, sticky=tk.W)

    # 6) 無限循環
    infinite_loop_var = tk.BooleanVar()
    tk.Checkbutton(detail_frame, text="無限循環", variable=infinite_loop_var)\
        .grid(row=4, column=1, sticky=tk.W, pady=2)

    # 按鈕們
    btn_new = tk.Button(detail_frame, text="新增項目", command=lambda: add_item())
    btn_new.grid(row=5, column=0, pady=5)

    btn_delete = tk.Button(detail_frame, text="刪除選取", command=lambda: delete_item())
    btn_delete.grid(row=5, column=1, pady=5)

    btn_save = tk.Button(detail_frame, text="儲存更新(目前選取)", command=lambda: update_item())
    btn_save.grid(row=6, column=0, pady=5)

    btn_save_close = tk.Button(detail_frame, text="儲存並關閉", command=lambda: on_save_close())
    btn_save_close.grid(row=6, column=1, pady=5)

    # ---------------- 初始化 ListBox ----------------
    def refresh_listbox():
        listbox.delete(0, tk.END)
        for i, item in enumerate(items):
            listbox.insert(tk.END, f"{i+1}. {item.get('text', '')}")

    refresh_listbox()

    # -------------- 工具函式 --------------
    def browse_audio_file(entry_widget):
        file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if file_path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, file_path)

    def copy_file_to_local(src_path):
        if not src_path:
            return ""
        if not os.path.exists(src_path):
            return ""

        file_name = os.path.basename(src_path)
        dest_path = os.path.join(os.getcwd(), file_name)
        if os.path.abspath(src_path) == os.path.abspath(dest_path):
            return file_name  # 同檔案路徑就不重複複製

        try:
            shutil.copy2(src_path, dest_path)
        except Exception as e:
            messagebox.showerror("檔案複製失敗", str(e))
            return ""
        return file_name

    # 動態顯示/隱藏 TTS / 音檔 欄位
    def update_mode_ui(*args):
        current_mode = play_mode_var.get()
        if current_mode == "文字":
            # 顯示 TTS 欄位
            label_tts.grid(row=2, column=0, sticky=tk.W, pady=2)
            entry_tts.grid(row=2, column=1, columnspan=2, sticky=tk.W)
            # 隱藏音檔
            label_audio.grid_remove()
            entry_audio.grid_remove()
            btn_browse_audio.grid_remove()
        else:
            # 顯示音檔
            label_audio.grid(row=2, column=0, sticky=tk.W, pady=2)
            entry_audio.grid(row=2, column=1, sticky=tk.W)
            btn_browse_audio.grid(row=2, column=2, sticky=tk.W)
            # 隱藏 TTS
            label_tts.grid_remove()
            entry_tts.grid_remove()

    combo_mode.bind("<<ComboboxSelected>>", update_mode_ui)

    def show_item_detail(index):
        """
        顯示指定 item 的細節到右側欄位
        """
        if 0 <= index < len(items):
            item = items[index]
            # 項目名稱
            entry_item_name.delete(0, tk.END)
            entry_item_name.insert(0, item.get('text', ''))

            # 播放模式
            play_mode = item.get('play_mode', '文字')
            play_mode_var.set(play_mode)

            # TTS 文字
            tts_text = item.get('tts_text', '')
            entry_tts.delete(0, tk.END)
            entry_tts.insert(0, tts_text)

            # 音檔路徑
            audio_path = item.get('audio_path', '')
            entry_audio.delete(0, tk.END)
            entry_audio.insert(0, audio_path)

            # 倒數時間(秒 -> 分:秒)
            countdown = item.get('countdown', 0)
            minutes = countdown // 60
            seconds = countdown % 60
            entry_minute.delete(0, tk.END)
            entry_minute.insert(0, str(minutes))
            entry_second.delete(0, tk.END)
            entry_second.insert(0, str(seconds))

            # 無限循環
            infinite_loop_var.set(item.get('infinite_loop', False))

            update_mode_ui()

    def clear_detail():
        entry_item_name.delete(0, tk.END)
        entry_tts.delete(0, tk.END)
        entry_audio.delete(0, tk.END)
        entry_minute.delete(0, tk.END)
        entry_second.delete(0, tk.END)
        infinite_loop_var.set(False)
        play_mode_var.set("文字")
        update_mode_ui()

    # ----------------- 新增、刪除、更新 -----------------
    def add_item():
        new_item = {
            "text": "新的項目",
            "play_mode": "文字",
            "tts_text": "",
            "audio_path": "",
            "countdown": 30,
            "infinite_loop": False
        }
        items.append(new_item)
        refresh_listbox()
        listbox.select_clear(0, tk.END)
        listbox.select_set(tk.END)
        show_item_detail(len(items) - 1)

    def delete_item():
        sel = listbox.curselection()
        if not sel:
            return
        index = sel[0]
        if 0 <= index < len(items):
            items.pop(index)
            refresh_listbox()
            clear_detail()
            messagebox.showinfo("刪除", f"已刪除第 {index+1} 個項目")
            # 若要即時寫檔，可在此呼叫 save_callback(items)

    def update_item():
        """
        只把右側輸入框的值，更新到目前選取 (或最後有效選取) 的 item，
        並立即呼叫 save_callback(items)。
        """
        global current_selected_index
        sel = listbox.curselection()
        if not sel:
            if current_selected_index is not None:
                sel = (current_selected_index,)
            else:
                messagebox.showwarning("警告", "請先選取要更新的項目")
                return

        index = sel[0]
        if not (0 <= index < len(items)):
            messagebox.showwarning("警告", "請先選取要更新的項目")
            return

        item = items[index]

        # 1) 項目名稱
        item['text'] = entry_item_name.get()

        # 2) 播放模式
        item['play_mode'] = play_mode_var.get()

        # 3) TTS 文字
        if item['play_mode'] == "文字":
            item['tts_text'] = entry_tts.get()
        else:
            item['tts_text'] = ""  # 若切到音檔模式，可清空

        # 4) 音檔
        user_path = entry_audio.get().strip()
        if item['play_mode'] == "音檔" and user_path:
            copied_file_name = copy_file_to_local(user_path)
            if copied_file_name:
                item['audio_path'] = os.path.join(os.getcwd(), copied_file_name)
            else:
                # 若複製失敗，可清空或保留原值
                pass
        else:
            item['audio_path'] = ""

        # 5) 倒數時間
        try:
            m = int(entry_minute.get())
        except:
            m = 0
        try:
            s = int(entry_second.get())
        except:
            s = 0
        total_sec = max(0, m*60 + s)
        item['countdown'] = total_sec

        # 6) 無限循環
        item['infinite_loop'] = infinite_loop_var.get()

        # 更新 ListBox 顯示
        refresh_listbox()
        listbox.select_clear(0, tk.END)
        listbox.select_set(index)
        show_item_detail(index)

        # 立刻呼叫回傳，寫檔
        save_callback(items)
        messagebox.showinfo("更新", f"第 {index+1} 個項目已更新並保存")

    def on_save_close():
        # 防止使用者忘了按「儲存更新」
        update_item()
        win.destroy()

    # ----------------- ListBox 事件 -----------------
    def on_listbox_select(evt):
        global current_selected_index
        w = evt.widget
        sel = w.curselection()
        if sel:
            current_selected_index = sel[0]
            show_item_detail(current_selected_index)
            entry_item_name.focus_set()

    listbox.bind("<<ListboxSelect>>", on_listbox_select)

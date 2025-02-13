import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
from data_manager import load_config, save_config
from timer_manager import TimerManager

class TimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("倒數計時器 - build by DC: l3m0nt4ng")

        self.items = load_config()
        self.timer_manager = TimerManager()
        self.current_selected_index = None

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 建立兩個分頁：計時管理與設定
        self.frame_timer = tk.Frame(self.notebook)
        self.frame_settings = tk.Frame(self.notebook)

        self.notebook.add(self.frame_timer, text="計時管理")
        self.notebook.add(self.frame_settings, text="設定")

        self.setup_timer_tab()
        self.setup_settings_tab()

    # ----------------- 計時管理分頁 -----------------
    def setup_timer_tab(self):
        self.items_frame = tk.Frame(self.frame_timer)
        self.items_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.item_rows = []
        self.refresh_items_ui()

    def create_item_row(self, index, item):
        frame = tk.Frame(self.items_frame, bd=1, relief=tk.GROOVE, pady=5)
        frame.pack(fill=tk.X, padx=5, pady=2)

        # 項目名稱
        label_text = tk.Label(frame, text=item.get("text", f"Item{index+1}"), width=15)
        label_text.pack(side=tk.LEFT, padx=5)

        # 取得總倒數時間並格式化
        total_seconds = item.get("countdown", 5)
        total_str = self.format_time(total_seconds)

        # 顯示「目前剩餘時間 / 總時間」，初始「目前剩餘時間」先顯示 00:00
        label_current_and_total = tk.Label(frame, text=f"{total_str} / {total_str}", width=12)
        label_current_and_total.pack(side=tk.LEFT, padx=5)

        # 開始、停止按鈕
        btn_start = tk.Button(frame, text="開始", command=lambda: self.on_start(index))
        btn_start.pack(side=tk.LEFT, padx=5)

        btn_stop = tk.Button(frame, text="停止", command=lambda: self.on_stop(index))
        btn_stop.pack(side=tk.LEFT, padx=5)

        # 模式 (文字 / 音檔)
        play_mode = item.get('play_mode', '文字')
        label_mode = tk.Label(frame, text=f"模式:{play_mode}")
        label_mode.pack(side=tk.LEFT, padx=5)

        # 無限循環: 是/否
        infinite_loop = item.get('infinite_loop', False)
        loop_text = "單次" if infinite_loop else "循環"
        label_loop = tk.Label(frame, text=loop_text)
        label_loop.pack(side=tk.LEFT, padx=5)

        # 回傳這個 row 的主要元件
        # 注意：第二個元素要能在 on_start() 時拿來更新「目前剩餘時間」
        return (frame, label_current_and_total)

    def refresh_items_ui(self):
        for c in self.items_frame.winfo_children():
            c.destroy()
        self.item_rows.clear()
        for idx, itm in enumerate(self.items):
            row_ui = self.create_item_row(idx, itm)
            self.item_rows.append(row_ui)

    def on_start(self, item_id):
        item = self.items[item_id]
        countdown = item.get("countdown", 5)
        infinite_loop = item.get("infinite_loop", False)
        audio_path = item.get("audio_path", "")
        play_mode = item.get("play_mode", "文字")
        tts_text = item.get("tts_text", "")

        # 取得「目前剩餘時間 / 總時間」的 Label
        label_current_and_total = self.item_rows[item_id][1]
        total_str = self.format_time(countdown)

        def update_label(remaining_sec):
            # 只更新剩餘時間那部分，後面維持 "/ 總時間"
            remain_str = self.format_time(remaining_sec)
            self.root.after(0, lambda: label_current_and_total.config(text=f"{remain_str} / {total_str}"))

        self.timer_manager.start_item(
            item_id=item_id,
            countdown=countdown,
            infinite_loop=infinite_loop,
            audio_path=audio_path,
            text_for_tts=tts_text,
            play_mode=play_mode,
            on_update_label=update_label
        )

    def on_stop(self, item_id):
        self.timer_manager.stop_item(item_id)

    @staticmethod
    def format_time(sec):
        m = sec // 60
        s = sec % 60
        return f"{m:02d}:{s:02d}"

    # ----------------- 設定分頁（整合 settings_window UI） -----------------
    def setup_settings_tab(self):
        # 左側：Listbox（項目列表）
        self.settings_left_frame = tk.Frame(self.frame_settings)
        self.settings_left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(self.settings_left_frame)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar = tk.Scrollbar(self.settings_left_frame, command=self.listbox.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.listbox.config(exportselection=False)
        self.listbox.bind("<<ListboxSelect>>", self.on_listbox_select)

        # 右側：詳細設定區
        self.settings_right_frame = tk.Frame(self.frame_settings)
        self.settings_right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 1) 項目名稱
        tk.Label(self.settings_right_frame, text="項目名稱:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.entry_item_name = tk.Entry(self.settings_right_frame, width=30)
        self.entry_item_name.grid(row=0, column=1, columnspan=2, sticky=tk.W)
        bind_ctrl_a_to_entry(self.entry_item_name)

        # 2) 播放模式
        tk.Label(self.settings_right_frame, text="播放模式:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.play_mode_var = tk.StringVar(value="文字")
        self.combo_mode = ttk.Combobox(self.settings_right_frame, textvariable=self.play_mode_var,
                                       values=["文字", "音檔"], state="readonly", width=10)
        self.combo_mode.grid(row=1, column=1, sticky=tk.W)
        self.combo_mode.bind("<<ComboboxSelected>>", self.update_mode_ui)

        # 3) TTS 文字與 4) 音檔路徑（動態顯示）
        self.label_tts = tk.Label(self.settings_right_frame, text="文字:")
        self.entry_tts = tk.Entry(self.settings_right_frame, width=30)

        self.label_audio = tk.Label(self.settings_right_frame, text="音檔路徑:")
        self.entry_audio = tk.Entry(self.settings_right_frame, width=30)
        self.btn_browse_audio = tk.Button(self.settings_right_frame, text="選擇檔案", command=self.browse_audio_file)

        # 初始預設顯示文字欄位
        self.label_tts.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.entry_tts.grid(row=2, column=1, columnspan=2, sticky=tk.W)

        # 5) 倒數時間 (分、秒)
        tk.Label(self.settings_right_frame, text="倒數-分:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.entry_minute = tk.Entry(self.settings_right_frame, width=5)
        self.entry_minute.grid(row=3, column=1, sticky=tk.W)
        tk.Label(self.settings_right_frame, text="秒:").grid(row=3, column=2, sticky=tk.W)
        self.entry_second = tk.Entry(self.settings_right_frame, width=5)
        self.entry_second.grid(row=3, column=3, sticky=tk.W)

        # 6) 無限循環
        self.infinite_loop_var = tk.BooleanVar()
        self.chk_infinite = tk.Checkbutton(self.settings_right_frame, text="無限循環", variable=self.infinite_loop_var)
        self.chk_infinite.grid(row=4, column=1, sticky=tk.W, pady=2)

        # 按鈕們
        self.btn_new = tk.Button(self.settings_right_frame, text="新增項目", command=self.add_item)
        self.btn_new.grid(row=5, column=0, pady=5)

        self.btn_delete = tk.Button(self.settings_right_frame, text="刪除選取", command=self.delete_item)
        self.btn_delete.grid(row=5, column=1, pady=5)

        self.btn_save = tk.Button(self.settings_right_frame, text="儲存並更新", command=self.save_settings_from_detail)
        self.btn_save.grid(row=6, column=1, pady=5)

        self.refresh_listbox()

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for i, item in enumerate(self.items):
            self.listbox.insert(tk.END, f"{i+1}. {item.get('text', '')}")

    def on_listbox_select(self, event):
        sel = self.listbox.curselection()
        if sel:
            self.btn_delete.config(state='normal')
            index = sel[0]
            self.current_selected_index = index
            self.show_item_detail(index)
        else:
            self.btn_delete.config(state='disabled')

    def show_item_detail(self, index):
        if 0 <= index < len(self.items):
            item = self.items[index]
            self.entry_item_name.delete(0, tk.END)
            self.entry_item_name.insert(0, item.get('text', ''))

            play_mode = item.get('play_mode', '文字')
            self.play_mode_var.set(play_mode)
            self.update_mode_ui()

            self.entry_tts.delete(0, tk.END)
            self.entry_tts.insert(0, item.get('tts_text', ''))

            self.entry_audio.delete(0, tk.END)
            self.entry_audio.insert(0, item.get('audio_path', ''))

            countdown = item.get('countdown', 0)
            minutes = countdown // 60
            seconds = countdown % 60
            self.entry_minute.delete(0, tk.END)
            self.entry_minute.insert(0, str(minutes))
            self.entry_second.delete(0, tk.END)
            self.entry_second.insert(0, str(seconds))

            self.infinite_loop_var.set(item.get('infinite_loop', False))

    def update_mode_ui(self, event=None):
        current_mode = self.play_mode_var.get()
        if current_mode == "文字":
            # 顯示 TTS 欄位，隱藏音檔相關元件
            self.label_tts.grid(row=2, column=0, sticky=tk.W, pady=2)
            self.entry_tts.grid(row=2, column=1, columnspan=2, sticky=tk.W)
            self.label_audio.grid_forget()
            self.entry_audio.grid_forget()
            self.btn_browse_audio.grid_forget()
        else:
            # 顯示音檔欄位，隱藏 TTS 欄位
            self.label_audio.grid(row=2, column=0, sticky=tk.W, pady=2)
            self.entry_audio.grid(row=2, column=1, sticky=tk.W)
            self.btn_browse_audio.grid(row=2, column=2, sticky=tk.W)
            self.label_tts.grid_forget()
            self.entry_tts.grid_forget()

    def browse_audio_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if file_path:
            self.entry_audio.delete(0, tk.END)
            self.entry_audio.insert(0, file_path)

    def copy_file_to_local(self, src_path):
        if not src_path or not os.path.exists(src_path):
            return ""
        file_name = os.path.basename(src_path)
        dest_path = os.path.join(os.getcwd(), file_name)
        if os.path.abspath(src_path) == os.path.abspath(dest_path):
            return file_name
        try:
            shutil.copy2(src_path, dest_path)
        except Exception as e:
            messagebox.showerror("檔案複製失敗", str(e))
            return ""
        return file_name

    def add_item(self):
        new_item = {
            "text": "新的項目",
            "play_mode": "文字",
            "tts_text": "",
            "audio_path": "",
            "countdown": 30,
            "infinite_loop": False
        }
        self.items.append(new_item)
        self.refresh_listbox()
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(tk.END)
        self.show_item_detail(len(self.items) - 1)

    def delete_item(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        index = sel[0]
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.refresh_listbox()
            self.clear_detail()
            messagebox.showinfo("刪除", f"已刪除第 {index+1} 個項目")

    def update_item(self):
        sel = self.listbox.curselection()
        if not sel:
            if self.current_selected_index is not None:
                index = self.current_selected_index
            else:
                messagebox.showwarning("警告", "請先選取要更新的項目")
                return
        else:
            index = sel[0]
        if not (0 <= index < len(self.items)):
            messagebox.showwarning("警告", "請先選取要更新的項目")
            return

        item = self.items[index]
        item['text'] = self.entry_item_name.get()
        item['play_mode'] = self.play_mode_var.get()
        if item['play_mode'] == "文字":
            item['tts_text'] = self.entry_tts.get()
            item['audio_path'] = ""
        else:
            item['tts_text'] = ""
            user_path = self.entry_audio.get().strip()
            if user_path:
                copied_file_name = self.copy_file_to_local(user_path)
                if copied_file_name:
                    item['audio_path'] = os.path.join(os.getcwd(), copied_file_name)
            else:
                item['audio_path'] = ""

        try:
            m = int(self.entry_minute.get())
        except:
            m = 0
        try:
            s = int(self.entry_second.get())
        except:
            s = 0
        total_sec = max(0, m * 60 + s)
        item['countdown'] = total_sec
        item['infinite_loop'] = self.infinite_loop_var.get()

        self.refresh_listbox()
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(index)
        self.show_item_detail(index)
        save_config(self.items)
        messagebox.showinfo("更新", f"第 {index+1} 個項目已更新並保存")

    def clear_detail(self):
        self.entry_item_name.delete(0, tk.END)
        self.entry_tts.delete(0, tk.END)
        self.entry_audio.delete(0, tk.END)
        self.entry_minute.delete(0, tk.END)
        self.entry_second.delete(0, tk.END)
        self.infinite_loop_var.set(False)
        self.play_mode_var.set("文字")
        self.update_mode_ui()

    def save_settings_from_detail(self):
        self.update_item()
        save_config(self.items)
        self.refresh_items_ui()
        messagebox.showinfo("成功", "設定已更新")

def bind_ctrl_a_to_entry(entry_widget):
    def select_all(event):
        # 讓此 Entry 全選
        entry_widget.select_range(0, tk.END)
        # 游標移到最後
        entry_widget.icursor(tk.END)
        # return 'break' 可以阻止事件繼續傳遞
        return 'break'
    # 綁定 Ctrl+a
    entry_widget.bind('<Control-a>', select_all)
if __name__ == "__main__":
    root = tk.Tk()
    app = TimerApp(root)
    root.mainloop()

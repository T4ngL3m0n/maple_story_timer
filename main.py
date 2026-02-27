from __future__ import annotations

import copy
import sys
from uuid import uuid4

from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QColor, QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data_manager import load_config, save_config
from hotkey_manager import GlobalHotkeyService
from hotkey_utils import canonicalize_hotkey
from timer_manager import TimerManager

STATE_LABELS = {
    TimerManager.STATE_IDLE: "Idle",
    TimerManager.STATE_RUNNING: "Running",
    TimerManager.STATE_LOOPING: "Looping",
    TimerManager.STATE_STOPPED: "Stopped",
}

STATE_COLORS = {
    TimerManager.STATE_IDLE: "#5f7388",
    TimerManager.STATE_RUNNING: "#00c896",
    TimerManager.STATE_LOOPING: "#4aa3ff",
    TimerManager.STATE_STOPPED: "#ff5d73",
}


def format_seconds(total_seconds: int) -> str:
    safe_value = max(0, int(total_seconds))
    minute = safe_value // 60
    second = safe_value % 60
    return f"{minute:02d}:{second:02d}"


class ReorderableTreeWidget(QTreeWidget):
    order_changed = Signal(list)

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        ordered_ids = []
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            item_id = item.data(0, Qt.UserRole)
            if item_id:
                ordered_ids.append(item_id)
        self.order_changed.emit(ordered_ids)


class HotkeyRecorderLineEdit(QLineEdit):
    hotkey_captured = Signal(str)
    hotkey_cleared = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setPlaceholderText("按下 Ctrl/Alt/Shift + 鍵")

    def keyPressEvent(self, event) -> None:
        key = event.key()

        if key in (Qt.Key_Backspace, Qt.Key_Delete):
            self.clear()
            self.hotkey_cleared.emit()
            event.accept()
            return

        key_text = self._key_to_text(key)
        if not key_text:
            event.ignore()
            return

        modifiers = []
        if event.modifiers() & Qt.ControlModifier:
            modifiers.append("Ctrl")
        if event.modifiers() & Qt.AltModifier:
            modifiers.append("Alt")
        if event.modifiers() & Qt.ShiftModifier:
            modifiers.append("Shift")

        if not modifiers:
            event.ignore()
            return

        hotkey = "+".join(modifiers + [key_text])
        self.setText(hotkey)
        self.hotkey_captured.emit(hotkey)
        event.accept()

    @staticmethod
    def _key_to_text(key: int) -> str | None:
        if Qt.Key_F1 <= key <= Qt.Key_F12:
            return f"F{key - Qt.Key_F1 + 1}"
        if Qt.Key_0 <= key <= Qt.Key_9:
            return str(key - Qt.Key_0)
        if Qt.Key_A <= key <= Qt.Key_Z:
            return chr(key)
        return None


class TimerMainWindow(QMainWindow):
    REPO_URL = "https://github.com/T4ngL3m0n/maple_story_timer"
    APP_VERSION = "v1.0.0"

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Maple Story Timer {self.APP_VERSION} | by L3m0nT4ng")
        self.resize(1600, 900)

        self.config = load_config()
        self.items = sorted(self.config.get("items", []), key=lambda item: item.get("sort_order", 0))
        self._rebuild_item_lookup()

        self.timer_manager = TimerManager(self)
        self.timer_manager.timer_tick.connect(self._on_timer_tick)
        self.timer_manager.timer_state_changed.connect(self._on_timer_state_changed)

        self.hotkey_service = GlobalHotkeyService(QApplication.instance())
        self.hotkey_service.hotkey_triggered.connect(self._on_hotkey_triggered)

        self._loading_editor = False

        self._build_ui()
        self._apply_styles()
        self._refresh_tree()
        self._register_global_hotkeys()
        self._register_item_hotkeys()

        if self.items:
            self._select_item(self.items[0]["id"])
        else:
            self._clear_editor()
            self._update_focus_panel(None)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        left_panel = QFrame(objectName="panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        left_title = QLabel("倒數項目")
        left_title.setObjectName("panelTitle")
        left_layout.addWidget(left_title)

        self.tree = ReorderableTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["名稱", "剩餘 / 總時", "狀態", "熱鍵", "操作"])
        self.tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setDefaultDropAction(Qt.MoveAction)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.order_changed.connect(self._on_order_changed)
        left_layout.addWidget(self.tree)

        list_actions = QHBoxLayout()
        self.btn_add = QPushButton("新增")
        self.btn_duplicate = QPushButton("複製")
        self.btn_delete = QPushButton("刪除")

        self.btn_add.clicked.connect(self._on_add_clicked)
        self.btn_duplicate.clicked.connect(self._on_duplicate_clicked)
        self.btn_delete.clicked.connect(self._on_delete_clicked)

        list_actions.addWidget(self.btn_add)
        list_actions.addWidget(self.btn_duplicate)
        list_actions.addWidget(self.btn_delete)
        left_layout.addLayout(list_actions)

        middle_panel = QFrame(objectName="panel")
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(12, 12, 12, 12)
        middle_layout.setSpacing(10)

        middle_title = QLabel("即時控制")
        middle_title.setObjectName("panelTitle")
        middle_layout.addWidget(middle_title)

        self.focus_name_label = QLabel("未選取項目")
        self.focus_name_label.setObjectName("focusName")
        middle_layout.addWidget(self.focus_name_label)

        self.focus_timer_label = QLabel("00:00 / 00:00")
        self.focus_timer_label.setObjectName("focusTimer")
        middle_layout.addWidget(self.focus_timer_label)

        self.focus_state_chip = QLabel("Idle")
        self.focus_state_chip.setObjectName("stateChip")
        self.focus_state_chip.setAlignment(Qt.AlignCenter)
        middle_layout.addWidget(self.focus_state_chip)

        selected_actions = QHBoxLayout()
        self.btn_start_selected = QPushButton("開始選取")
        self.btn_stop_selected = QPushButton("停止選取")
        self.btn_stop_all = QPushButton("全部停止")

        self.btn_start_selected.clicked.connect(self._start_selected_item)
        self.btn_stop_selected.clicked.connect(self._stop_selected_item)
        self.btn_stop_all.clicked.connect(self._stop_all_items)

        selected_actions.addWidget(self.btn_start_selected)
        selected_actions.addWidget(self.btn_stop_selected)
        selected_actions.addWidget(self.btn_stop_all)
        middle_layout.addLayout(selected_actions)

        global_hint_title = QLabel("全域熱鍵")
        global_hint_title.setObjectName("subTitle")
        middle_layout.addWidget(global_hint_title)

        self.lbl_global_stop = QLabel("Ctrl+Shift+S：全部停止")
        self.lbl_global_show = QLabel("Ctrl+Shift+M：顯示主視窗")
        middle_layout.addWidget(self.lbl_global_stop)
        middle_layout.addWidget(self.lbl_global_show)

        middle_layout.addStretch(1)

        self.feedback_label = QLabel("")
        self.feedback_label.setObjectName("feedback")
        self.feedback_label.setWordWrap(True)
        middle_layout.addWidget(self.feedback_label)

        self.source_label = QLabel(f'Source: <a href="{self.REPO_URL}">{self.REPO_URL}</a>')
        self.source_label.setObjectName("sourceLink")
        self.source_label.setTextFormat(Qt.RichText)
        self.source_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.source_label.setOpenExternalLinks(False)
        self.source_label.linkActivated.connect(self._open_repo_url)
        middle_layout.addWidget(self.source_label)

        right_panel = QFrame(objectName="panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        right_title = QLabel("項目設定（即時儲存）")
        right_title.setObjectName("panelTitle")
        right_layout.addWidget(right_title)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("輸入項目名稱")
        self.edit_name.textEdited.connect(self._on_editor_changed)
        form_layout.addRow("名稱", self.edit_name)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["文字", "音檔"])
        self.combo_mode.currentTextChanged.connect(self._on_mode_changed)
        form_layout.addRow("播放模式", self.combo_mode)

        self.edit_tts = QLineEdit()
        self.edit_tts.setPlaceholderText("倒數結束時播放的文字")
        self.edit_tts.textEdited.connect(self._on_editor_changed)
        self.tts_container = QWidget()
        tts_layout = QHBoxLayout(self.tts_container)
        tts_layout.setContentsMargins(0, 0, 0, 0)
        tts_layout.addWidget(self.edit_tts)
        form_layout.addRow("文字內容", self.tts_container)

        self.edit_audio_path = QLineEdit()
        self.edit_audio_path.setPlaceholderText("音檔路徑")
        self.edit_audio_path.textEdited.connect(self._on_editor_changed)
        self.btn_browse_audio = QPushButton("瀏覽")
        self.btn_browse_audio.clicked.connect(self._browse_audio)

        self.audio_container = QWidget()
        audio_layout = QHBoxLayout(self.audio_container)
        audio_layout.setContentsMargins(0, 0, 0, 0)
        audio_layout.addWidget(self.edit_audio_path)
        audio_layout.addWidget(self.btn_browse_audio)
        form_layout.addRow("音檔路徑", self.audio_container)

        countdown_container = QWidget()
        countdown_layout = QHBoxLayout(countdown_container)
        countdown_layout.setContentsMargins(0, 0, 0, 0)
        countdown_layout.setSpacing(6)

        self.spin_min = QSpinBox()
        self.spin_min.setRange(0, 999)
        self.spin_min.valueChanged.connect(self._on_editor_changed)

        self.spin_sec = QSpinBox()
        self.spin_sec.setRange(0, 59)
        self.spin_sec.valueChanged.connect(self._on_editor_changed)

        countdown_layout.addWidget(QLabel("分"))
        countdown_layout.addWidget(self.spin_min)
        countdown_layout.addSpacing(8)
        countdown_layout.addWidget(QLabel("秒"))
        countdown_layout.addWidget(self.spin_sec)
        countdown_layout.addStretch(1)
        form_layout.addRow("倒數時間", countdown_container)

        volume_container = QWidget()
        volume_layout = QHBoxLayout(volume_container)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(8)

        self.slider_volume = QSlider(Qt.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.valueChanged.connect(self._on_volume_changed)
        self.lbl_volume_value = QLabel("80")

        volume_layout.addWidget(self.slider_volume)
        volume_layout.addWidget(self.lbl_volume_value)
        form_layout.addRow("音量", volume_container)

        self.chk_infinite = QCheckBox("無限循環")
        self.chk_infinite.toggled.connect(self._on_editor_changed)
        form_layout.addRow("循環", self.chk_infinite)

        self.edit_hotkey = HotkeyRecorderLineEdit()
        self.edit_hotkey.hotkey_captured.connect(self._on_hotkey_captured)
        self.edit_hotkey.hotkey_cleared.connect(self._on_hotkey_cleared)
        form_layout.addRow("項目熱鍵", self.edit_hotkey)

        self.lbl_hotkey_help = QLabel("僅支援 Ctrl/Alt/Shift + F1~F12 / A~Z / 0~9")
        self.lbl_hotkey_help.setObjectName("hint")
        form_layout.addRow("", self.lbl_hotkey_help)

        right_layout.addLayout(form_layout)
        right_layout.addStretch(1)

        root_layout.addWidget(left_panel, 6)
        root_layout.addWidget(middle_panel, 4)
        root_layout.addWidget(right_panel, 5)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #0b131d;
                color: #d8e6ff;
            }
            QFrame#panel {
                background: #111d2a;
                border: 1px solid #223448;
                border-radius: 12px;
            }
            QLabel#panelTitle {
                font-size: 18px;
                font-weight: 700;
                color: #f0f6ff;
            }
            QLabel#subTitle {
                font-size: 14px;
                font-weight: 600;
                color: #9fc7ff;
            }
            QLabel#focusName {
                font-size: 22px;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel#focusTimer {
                font-size: 40px;
                font-weight: 700;
                color: #6fe9ff;
            }
            QLabel#stateChip {
                font-size: 14px;
                font-weight: 700;
                border-radius: 10px;
                padding: 8px;
                color: #ffffff;
                background: #5f7388;
            }
            QLabel#feedback {
                font-size: 13px;
                color: #9fc7ff;
                min-height: 38px;
            }
            QLabel#hint {
                font-size: 12px;
                color: #7f96af;
            }
            QLabel#sourceLink {
                font-size: 12px;
                color: #7f96af;
            }
            QLabel#sourceLink a {
                color: #8fd6ff;
                text-decoration: none;
            }
            QLabel#sourceLink a:hover {
                color: #c6ebff;
            }
            QTreeWidget {
                background: #0d1723;
                border: 1px solid #1f3043;
                border-radius: 8px;
                alternate-background-color: #122031;
            }
            QHeaderView::section {
                background: #1a2a3d;
                color: #d4e8ff;
                font-weight: 600;
                padding: 6px;
                border: none;
                border-right: 1px solid #223448;
            }
            QLineEdit, QSpinBox, QComboBox {
                background: #0d1723;
                border: 1px solid #2a3e56;
                border-radius: 6px;
                min-height: 30px;
                padding: 3px 8px;
                color: #e5f0ff;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 6px;
                background: #223448;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #49a5ff;
                border: none;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QPushButton {
                background: #1f8e73;
                border: none;
                border-radius: 6px;
                min-height: 30px;
                padding: 0 12px;
                font-weight: 600;
                color: #ffffff;
            }
            QPushButton:hover {
                background: #24a586;
            }
            QPushButton:pressed {
                background: #1a7a62;
            }
            QCheckBox {
                color: #d8e6ff;
            }
            """
        )
    def _rebuild_item_lookup(self) -> None:
        self.item_lookup = {item["id"]: item for item in self.items}

    def _refresh_tree(self, selected_item_id: str | None = None) -> None:
        if selected_item_id is None:
            selected_item_id = self._current_item_id()

        self.tree.blockSignals(True)
        self.tree.clear()

        for item in self.items:
            tree_item = QTreeWidgetItem()
            tree_item.setFlags(
                tree_item.flags()
                | Qt.ItemIsSelectable
                | Qt.ItemIsEnabled
                | Qt.ItemIsDragEnabled
                | Qt.ItemIsDropEnabled
            )
            tree_item.setData(0, Qt.UserRole, item["id"])
            self.tree.addTopLevelItem(tree_item)
            self._attach_row_action_buttons(tree_item, item["id"])
            self._update_row_visuals(item["id"], tree_item)

        self.tree.blockSignals(False)

        if not self.items:
            self._clear_editor()
            self._update_focus_panel(None)
            return

        target_id = selected_item_id if selected_item_id in self.item_lookup else self.items[0]["id"]
        self._select_item(target_id)

    def _attach_row_action_buttons(self, tree_item: QTreeWidgetItem, item_id: str) -> None:
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(4)

        btn_start = QPushButton("開始")
        btn_start.setFixedWidth(54)
        btn_stop = QPushButton("停止")
        btn_stop.setFixedWidth(54)

        btn_start.clicked.connect(lambda _checked=False, value=item_id: self._start_item(value))
        btn_stop.clicked.connect(lambda _checked=False, value=item_id: self._stop_item(value))

        action_layout.addWidget(btn_start)
        action_layout.addWidget(btn_stop)
        self.tree.setItemWidget(tree_item, 4, action_widget)

    def _update_row_visuals(self, item_id: str, tree_item: QTreeWidgetItem | None = None) -> None:
        item = self.item_lookup.get(item_id)
        if item is None:
            return

        if tree_item is None:
            tree_item = self._find_tree_item(item_id)
            if tree_item is None:
                return

        total = int(item.get("countdown_sec", 30))
        state = self.timer_manager.get_state(item_id)
        remaining = self.timer_manager.get_remaining(item_id, total)

        tree_item.setText(0, item.get("name", ""))
        tree_item.setText(1, f"{format_seconds(remaining)} / {format_seconds(total)}")
        tree_item.setText(2, STATE_LABELS.get(state, "Idle"))
        tree_item.setText(3, item.get("hotkey") or "-")
        tree_item.setForeground(2, QColor(STATE_COLORS.get(state, "#5f7388")))

    def _find_tree_item(self, item_id: str) -> QTreeWidgetItem | None:
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if item.data(0, Qt.UserRole) == item_id:
                return item
        return None

    def _select_item(self, item_id: str) -> None:
        target = self._find_tree_item(item_id)
        if target:
            self.tree.setCurrentItem(target)

    def _current_item_id(self) -> str | None:
        selected = self.tree.selectedItems()
        if not selected:
            return None
        return selected[0].data(0, Qt.UserRole)

    def _current_item(self) -> dict | None:
        item_id = self._current_item_id()
        if not item_id:
            return None
        return self.item_lookup.get(item_id)

    def _on_selection_changed(self) -> None:
        item = self._current_item()
        if item is None:
            self._clear_editor()
            self._update_focus_panel(None)
            return

        self._load_item_into_editor(item)
        self._update_focus_panel(item["id"])

    def _load_item_into_editor(self, item: dict) -> None:
        self._loading_editor = True

        self.edit_name.setText(str(item.get("name", "")))
        self.combo_mode.setCurrentText(item.get("play_mode", "文字"))
        self.edit_tts.setText(str(item.get("tts_text", "")))
        self.edit_audio_path.setText(str(item.get("audio_path", "")))

        countdown_sec = int(item.get("countdown_sec", 30))
        self.spin_min.setValue(countdown_sec // 60)
        self.spin_sec.setValue(countdown_sec % 60)

        volume = int(item.get("volume", 80))
        self.slider_volume.setValue(volume)
        self.lbl_volume_value.setText(str(volume))

        self.chk_infinite.setChecked(bool(item.get("infinite_loop", False)))
        self.edit_hotkey.setText(item.get("hotkey") or "")

        self._set_mode_visibility(self.combo_mode.currentText())
        self._loading_editor = False

    def _clear_editor(self) -> None:
        self._loading_editor = True
        self.edit_name.clear()
        self.combo_mode.setCurrentText("文字")
        self.edit_tts.clear()
        self.edit_audio_path.clear()
        self.spin_min.setValue(0)
        self.spin_sec.setValue(30)
        self.slider_volume.setValue(80)
        self.lbl_volume_value.setText("80")
        self.chk_infinite.setChecked(False)
        self.edit_hotkey.clear()
        self._set_mode_visibility("文字")
        self._loading_editor = False

    def _set_mode_visibility(self, mode: str) -> None:
        is_text_mode = mode == "文字"
        self.tts_container.setVisible(is_text_mode)
        self.audio_container.setVisible(not is_text_mode)

    def _on_mode_changed(self, _value: str) -> None:
        self._set_mode_visibility(self.combo_mode.currentText())
        self._on_editor_changed()

    def _on_volume_changed(self, value: int) -> None:
        self.lbl_volume_value.setText(str(value))
        self._on_editor_changed()

    def _on_editor_changed(self, *_args) -> None:
        if self._loading_editor:
            return

        item = self._current_item()
        if item is None:
            return

        if self.spin_min.value() == 0 and self.spin_sec.value() == 0:
            self._loading_editor = True
            self.spin_sec.setValue(1)
            self._loading_editor = False

        item["name"] = self.edit_name.text().strip() or "未命名項目"
        item["play_mode"] = self.combo_mode.currentText()
        item["tts_text"] = self.edit_tts.text().strip()
        item["audio_path"] = self.edit_audio_path.text().strip()
        item["countdown_sec"] = self.spin_min.value() * 60 + self.spin_sec.value()
        item["volume"] = self.slider_volume.value()
        item["infinite_loop"] = self.chk_infinite.isChecked()

        self._persist_config()
        self._update_row_visuals(item["id"])
        self._update_focus_panel(item["id"])

    def _browse_audio(self) -> None:
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "選擇音檔",
            "",
            "Audio Files (*.mp3 *.wav *.ogg);;All Files (*)",
        )
        if not file_path:
            return

        self.edit_audio_path.setText(file_path)
        self._on_editor_changed()

    def _on_hotkey_captured(self, hotkey_str: str) -> None:
        if self._loading_editor:
            return

        item = self._current_item()
        if item is None:
            return

        canonical = canonicalize_hotkey(hotkey_str)
        if canonical is None:
            self._restore_hotkey_editor(item)
            self._set_feedback("熱鍵格式無效，請使用 Ctrl/Alt/Shift + 單鍵", is_error=True)
            return

        if self._hotkey_conflict_exists(canonical, item["id"]):
            self._restore_hotkey_editor(item)
            self._set_feedback(f"熱鍵衝突：{canonical} 已被其他項目使用", is_error=True)
            return

        result = self.hotkey_service.register_item_hotkey(item["id"], canonical)
        if not result.ok:
            self._restore_hotkey_editor(item)
            self._set_feedback(f"熱鍵註冊失敗：{result.message}", is_error=True)
            return

        item["hotkey"] = canonical
        self._persist_config()
        self._update_row_visuals(item["id"])
        self._set_feedback(f"已綁定熱鍵 {canonical}", is_error=False)

    def _on_hotkey_cleared(self) -> None:
        if self._loading_editor:
            return

        item = self._current_item()
        if item is None:
            return

        self.hotkey_service.unregister_item_hotkey(item["id"])
        item["hotkey"] = None
        self._persist_config()
        self._update_row_visuals(item["id"])
        self._set_feedback("已清除項目熱鍵", is_error=False)

    def _restore_hotkey_editor(self, item: dict) -> None:
        self._loading_editor = True
        self.edit_hotkey.setText(item.get("hotkey") or "")
        self._loading_editor = False

    def _hotkey_conflict_exists(self, hotkey: str, current_item_id: str) -> bool:
        for item in self.items:
            if item["id"] == current_item_id:
                continue
            if item.get("hotkey") == hotkey:
                return True
        return False
    def _on_add_clicked(self) -> None:
        new_item = {
            "id": str(uuid4()),
            "name": "新的項目",
            "play_mode": "文字",
            "tts_text": "新的項目",
            "audio_path": "",
            "countdown_sec": 30,
            "infinite_loop": False,
            "volume": 80,
            "hotkey": None,
            "sort_order": len(self.items),
        }
        self.items.append(new_item)
        self._rebuild_item_lookup()
        self._persist_config()
        self._refresh_tree(selected_item_id=new_item["id"])
        self._set_feedback("已新增項目", is_error=False)

    def _on_duplicate_clicked(self) -> None:
        item = self._current_item()
        if item is None:
            return

        index = self.items.index(item)
        cloned = copy.deepcopy(item)
        cloned["id"] = str(uuid4())
        cloned["name"] = f"{item.get('name', '項目')} (副本)"
        cloned["hotkey"] = None

        self.items.insert(index + 1, cloned)
        self._rebuild_item_lookup()
        self._persist_config()
        self._refresh_tree(selected_item_id=cloned["id"])
        self._set_feedback("已複製項目（熱鍵已清空）", is_error=False)

    def _on_delete_clicked(self) -> None:
        item = self._current_item()
        if item is None:
            return

        item_id = item["id"]
        self.hotkey_service.unregister_item_hotkey(item_id)
        self.timer_manager.remove_item(item_id)

        self.items = [current for current in self.items if current["id"] != item_id]
        self._rebuild_item_lookup()
        self._persist_config()
        self._refresh_tree()
        self._set_feedback("已刪除項目", is_error=False)

    def _on_order_changed(self, ordered_ids: list) -> None:
        if len(ordered_ids) != len(self.items):
            return

        lookup = {item["id"]: item for item in self.items}
        if any(item_id not in lookup for item_id in ordered_ids):
            return

        selected_item_id = self._current_item_id()
        self.items = [lookup[item_id] for item_id in ordered_ids]
        self._rebuild_item_lookup()
        self._persist_config()
        self._refresh_tree(selected_item_id=selected_item_id)
        self._set_feedback("排序已儲存", is_error=False)

    def _start_selected_item(self) -> None:
        item = self._current_item()
        if item:
            self._start_item(item["id"])

    def _stop_selected_item(self) -> None:
        item = self._current_item()
        if item:
            self._stop_item(item["id"])

    def _start_item(self, item_id: str) -> None:
        item = self.item_lookup.get(item_id)
        if item is None:
            return

        self.timer_manager.start_item(item)
        self._update_row_visuals(item_id)
        self._update_focus_panel(item_id)

    def _stop_item(self, item_id: str) -> None:
        self.timer_manager.stop_item(item_id)
        self._update_row_visuals(item_id)
        self._update_focus_panel(item_id)

    def _toggle_item(self, item_id: str) -> None:
        if self.timer_manager.is_running(item_id):
            self._stop_item(item_id)
            return
        self._start_item(item_id)

    def _stop_all_items(self) -> None:
        self.timer_manager.stop_all()
        for item in self.items:
            self._update_row_visuals(item["id"])
        self._update_focus_panel(self._current_item_id())

    def _persist_config(self) -> None:
        for index, item in enumerate(self.items):
            item["sort_order"] = index
        self.config["items"] = self.items
        save_config(self.config)

    def _register_global_hotkeys(self) -> None:
        global_hotkeys = self.config.get("global_hotkeys", {})
        stop_hotkey = global_hotkeys.get("stop_all", "Ctrl+Shift+S")
        show_hotkey = global_hotkeys.get("show_window", "Ctrl+Shift+M")

        result = self.hotkey_service.register_global_hotkeys(stop_hotkey, show_hotkey)
        if not result.ok:
            self._set_feedback(f"全域熱鍵註冊失敗：{result.message}", is_error=True)

        self.config["global_hotkeys"] = {
            "stop_all": stop_hotkey,
            "show_window": show_hotkey,
        }

        self.lbl_global_stop.setText(f"{stop_hotkey}：全部停止")
        self.lbl_global_show.setText(f"{show_hotkey}：顯示主視窗")

    def _register_item_hotkeys(self) -> None:
        failed_items = []

        for item in self.items:
            hotkey = item.get("hotkey")
            if not hotkey:
                continue

            result = self.hotkey_service.register_item_hotkey(item["id"], hotkey)
            if result.ok:
                item["hotkey"] = result.canonical_hotkey
            else:
                failed_items.append((item.get("name", "未命名項目"), hotkey, result.message))
                item["hotkey"] = None

        if failed_items:
            self._persist_config()
            details = "\n".join([f"{name} ({hotkey}) -> {reason}" for name, hotkey, reason in failed_items])
            QMessageBox.warning(self, "熱鍵載入失敗", f"以下項目熱鍵已清空：\n{details}")

    def _on_hotkey_triggered(self, token: str) -> None:
        if token == GlobalHotkeyService.GLOBAL_STOP_TOKEN:
            self._stop_all_items()
            self._set_feedback("已透過全域熱鍵停止全部項目", is_error=False)
            return

        if token == GlobalHotkeyService.GLOBAL_SHOW_WINDOW_TOKEN:
            self.showNormal()
            self.raise_()
            self.activateWindow()
            self._set_feedback("已透過全域熱鍵顯示主視窗", is_error=False)
            return

        if token.startswith("item:"):
            item_id = token.split(":", 1)[1]
            if item_id in self.item_lookup:
                self._toggle_item(item_id)

    def _on_timer_tick(self, item_id: str, _remaining: int, _total: int) -> None:
        self._update_row_visuals(item_id)
        if self._current_item_id() == item_id:
            self._update_focus_panel(item_id)

    def _on_timer_state_changed(self, item_id: str, _state: str) -> None:
        self._update_row_visuals(item_id)
        if self._current_item_id() == item_id:
            self._update_focus_panel(item_id)

    def _update_focus_panel(self, item_id: str | None) -> None:
        if item_id is None:
            self.focus_name_label.setText("未選取項目")
            self.focus_timer_label.setText("00:00 / 00:00")
            self._set_state_chip(TimerManager.STATE_IDLE)
            return

        item = self.item_lookup.get(item_id)
        if item is None:
            self.focus_name_label.setText("未選取項目")
            self.focus_timer_label.setText("00:00 / 00:00")
            self._set_state_chip(TimerManager.STATE_IDLE)
            return

        total = int(item.get("countdown_sec", 30))
        remaining = self.timer_manager.get_remaining(item_id, total)
        state = self.timer_manager.get_state(item_id)

        self.focus_name_label.setText(item.get("name", "未命名項目"))
        self.focus_timer_label.setText(f"{format_seconds(remaining)} / {format_seconds(total)}")
        self._set_state_chip(state)

    def _set_state_chip(self, state: str) -> None:
        label = STATE_LABELS.get(state, "Idle")
        color = STATE_COLORS.get(state, "#5f7388")
        self.focus_state_chip.setText(label)
        self.focus_state_chip.setStyleSheet(
            f"background: {color}; color: #ffffff; border-radius: 10px; padding: 8px; font-weight: 700;"
        )

    def _set_feedback(self, message: str, is_error: bool) -> None:
        color = "#ff7a88" if is_error else "#8fd6ff"
        self.feedback_label.setText(message)
        self.feedback_label.setStyleSheet(f"color: {color};")

    def _open_repo_url(self, _url: str) -> None:
        QDesktopServices.openUrl(QUrl(self.REPO_URL))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.timer_manager.stop_all()
        self.hotkey_service.unregister_all()
        self._persist_config()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = TimerMainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

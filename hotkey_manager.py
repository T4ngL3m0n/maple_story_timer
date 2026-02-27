from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable, Dict

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

from hotkey_utils import canonicalize_hotkey, hotkey_to_vk_and_modifiers

WM_HOTKEY = 0x0312
USER32 = ctypes.windll.user32

USER32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
USER32.RegisterHotKey.restype = wintypes.BOOL
USER32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
USER32.UnregisterHotKey.restype = wintypes.BOOL


@dataclass
class HotkeyRegisterResult:
    ok: bool
    message: str = ""
    canonical_hotkey: str | None = None


@dataclass
class _Registration:
    token: str
    hotkey: str
    hotkey_id: int


class _NativeHotkeyEventFilter(QAbstractNativeEventFilter):
    def __init__(self, on_hotkey: Callable[[int], None]) -> None:
        super().__init__()
        self._on_hotkey = on_hotkey

    def nativeEventFilter(self, event_type, message):
        if event_type != b"windows_generic_MSG":
            return False, 0

        msg = wintypes.MSG.from_address(int(message))
        if msg.message == WM_HOTKEY:
            self._on_hotkey(int(msg.wParam))
            return True, 0

        return False, 0


class GlobalHotkeyService(QObject):
    hotkey_triggered = Signal(str)

    GLOBAL_STOP_TOKEN = "global:stop_all"
    GLOBAL_SHOW_WINDOW_TOKEN = "global:show_window"

    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        self._event_filter = _NativeHotkeyEventFilter(self._handle_hotkey_id)
        self._app.installNativeEventFilter(self._event_filter)

        self._next_hotkey_id = 1000
        self._token_to_registration: Dict[str, _Registration] = {}
        self._id_to_token: Dict[int, str] = {}

    def register_item_hotkey(self, item_id: str, hotkey_str: str) -> HotkeyRegisterResult:
        return self.register_hotkey(f"item:{item_id}", hotkey_str)

    def unregister_item_hotkey(self, item_id: str) -> None:
        self.unregister_token(f"item:{item_id}")

    def register_global_hotkeys(self, stop_all_hotkey: str, show_window_hotkey: str) -> HotkeyRegisterResult:
        stop_result = self.register_hotkey(self.GLOBAL_STOP_TOKEN, stop_all_hotkey)
        if not stop_result.ok:
            return HotkeyRegisterResult(False, f"無法註冊全停熱鍵: {stop_result.message}")

        show_result = self.register_hotkey(self.GLOBAL_SHOW_WINDOW_TOKEN, show_window_hotkey)
        if not show_result.ok:
            return HotkeyRegisterResult(False, f"無法註冊顯示視窗熱鍵: {show_result.message}")

        return HotkeyRegisterResult(True)

    def register_hotkey(self, token: str, hotkey_str: str) -> HotkeyRegisterResult:
        canonical = canonicalize_hotkey(hotkey_str)
        if canonical is None:
            return HotkeyRegisterResult(False, "熱鍵格式不支援")

        for existing_token, registration in self._token_to_registration.items():
            if existing_token != token and registration.hotkey == canonical:
                return HotkeyRegisterResult(False, f"熱鍵 {canonical} 已被其他項目使用")

        existing = self._token_to_registration.get(token)
        if existing and existing.hotkey == canonical:
            return HotkeyRegisterResult(True, canonical_hotkey=canonical)

        if existing:
            self._unregister_registration(existing)

        vk_result = hotkey_to_vk_and_modifiers(canonical)
        if vk_result is None:
            return HotkeyRegisterResult(False, "熱鍵格式不支援")

        vk, modifiers = vk_result
        hotkey_id = self._allocate_hotkey_id()

        success = USER32.RegisterHotKey(None, hotkey_id, modifiers, vk)
        if not success:
            error_code = ctypes.GetLastError()
            return HotkeyRegisterResult(False, f"RegisterHotKey 失敗，系統錯誤碼 {error_code}")

        registration = _Registration(token=token, hotkey=canonical, hotkey_id=hotkey_id)
        self._token_to_registration[token] = registration
        self._id_to_token[hotkey_id] = token
        return HotkeyRegisterResult(True, canonical_hotkey=canonical)

    def unregister_token(self, token: str) -> None:
        registration = self._token_to_registration.pop(token, None)
        if registration is None:
            return

        self._id_to_token.pop(registration.hotkey_id, None)
        USER32.UnregisterHotKey(None, registration.hotkey_id)

    def unregister_all(self) -> None:
        for registration in list(self._token_to_registration.values()):
            self._unregister_registration(registration)
        self._token_to_registration.clear()
        self._id_to_token.clear()

    def _unregister_registration(self, registration: _Registration) -> None:
        self._id_to_token.pop(registration.hotkey_id, None)
        USER32.UnregisterHotKey(None, registration.hotkey_id)

    def _allocate_hotkey_id(self) -> int:
        while self._next_hotkey_id in self._id_to_token:
            self._next_hotkey_id += 1
        value = self._next_hotkey_id
        self._next_hotkey_id += 1
        return value

    def _handle_hotkey_id(self, hotkey_id: int) -> None:
        token = self._id_to_token.get(hotkey_id)
        if token:
            self.hotkey_triggered.emit(token)

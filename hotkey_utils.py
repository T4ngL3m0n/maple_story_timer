from __future__ import annotations

from typing import Optional, Tuple

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004

MODIFIER_ORDER = ("Ctrl", "Alt", "Shift")


def _normalize_modifier(token: str) -> Optional[str]:
    value = token.strip().lower()
    if value in {"ctrl", "control"}:
        return "Ctrl"
    if value == "alt":
        return "Alt"
    if value == "shift":
        return "Shift"
    return None


def _normalize_base_key(token: str) -> Optional[str]:
    key = token.strip().upper()
    if len(key) == 1 and key.isalpha():
        return key
    if len(key) == 1 and key.isdigit():
        return key
    if key.startswith("F") and key[1:].isdigit():
        value = int(key[1:])
        if 1 <= value <= 12:
            return f"F{value}"
    return None


def canonicalize_hotkey(hotkey_str: str) -> Optional[str]:
    if not hotkey_str:
        return None

    tokens = [token.strip() for token in hotkey_str.split("+") if token.strip()]
    if len(tokens) < 2:
        return None

    modifiers = set()
    base_key = None

    for token in tokens:
        normalized_modifier = _normalize_modifier(token)
        if normalized_modifier:
            modifiers.add(normalized_modifier)
            continue

        normalized_key = _normalize_base_key(token)
        if normalized_key is None:
            return None
        if base_key is not None:
            return None
        base_key = normalized_key

    if not modifiers or base_key is None:
        return None

    ordered_modifiers = [name for name in MODIFIER_ORDER if name in modifiers]
    return "+".join(ordered_modifiers + [base_key])


def hotkey_to_vk_and_modifiers(hotkey_str: str) -> Optional[Tuple[int, int]]:
    canonical = canonicalize_hotkey(hotkey_str)
    if canonical is None:
        return None

    parts = canonical.split("+")
    key = parts[-1]
    modifier_tokens = parts[:-1]

    modifiers = 0
    if "Alt" in modifier_tokens:
        modifiers |= MOD_ALT
    if "Ctrl" in modifier_tokens:
        modifiers |= MOD_CONTROL
    if "Shift" in modifier_tokens:
        modifiers |= MOD_SHIFT

    if key.startswith("F"):
        vk = 0x70 + int(key[1:]) - 1
    elif key.isdigit():
        vk = ord(key)
    else:
        vk = ord(key)

    return vk, modifiers


def is_supported_hotkey(hotkey_str: str) -> bool:
    return canonicalize_hotkey(hotkey_str) is not None

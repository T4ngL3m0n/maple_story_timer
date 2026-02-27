from hotkey_utils import canonicalize_hotkey, hotkey_to_vk_and_modifiers


def test_canonicalize_hotkey_formats_tokens():
    assert canonicalize_hotkey("ctrl+f1") == "Ctrl+F1"
    assert canonicalize_hotkey("Alt + shift + a") == "Alt+Shift+A"
    assert canonicalize_hotkey("shift+ctrl+9") == "Ctrl+Shift+9"


def test_canonicalize_hotkey_rejects_invalid_inputs():
    assert canonicalize_hotkey("F1") is None
    assert canonicalize_hotkey("Ctrl") is None
    assert canonicalize_hotkey("Ctrl+Alt") is None
    assert canonicalize_hotkey("Ctrl+F13") is None


def test_hotkey_vk_mapping():
    assert hotkey_to_vk_and_modifiers("Ctrl+F2") == (0x71, 0x0002)
    assert hotkey_to_vk_and_modifiers("Alt+Shift+A") == (ord("A"), 0x0001 | 0x0004)
    assert hotkey_to_vk_and_modifiers("bad") is None

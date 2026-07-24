from __future__ import annotations

import pytest
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button

from app.scripts.registry.key_registry import KeyRegistry, KeySpec


@pytest.mark.parametrize(
    ("key", "expected_id"),
    [
        (KeyCode.from_char("a"), "a"),
        (KeyCode.from_char("Z"), "z"),
        (KeyCode.from_char("5"), "5"),
        (KeyCode.from_char(";"), ";"),
        (Key.f1, "f1"),
        (Key.caps_lock, "caps_lock"),
        (Key.up, "up"),
        (Key.down, "down"),
        (Key.left, "left"),
        (Key.right, "right"),
    ],
)
def test_keyboard_input_is_normalized(
    key: Key | KeyCode,
    expected_id: str,
) -> None:
    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(key)

    assert result is not None
    assert result.key_id == expected_id


@pytest.mark.parametrize("key", [Key.ctrl, Key.shift])
def test_unsupported_keyboard_input_returns_none(key: Key) -> None:
    assert KeyRegistry.pynput_key_to_keyspec(key) is None


@pytest.mark.parametrize(
    ("vk", "expected_id"),
    [
        (0x41, "a"),
        (0x35, "5"),
        (0xBA, ";"),
        (0xDB, "["),
        (0xDD, "]"),
        (0xDC, "\\"),
    ],
)
def test_virtual_key_fallback_is_normalized(vk: int, expected_id: str) -> None:
    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(
        KeyCode(vk=vk, char=None)
    )

    assert result is not None
    assert result.key_id == expected_id


@pytest.mark.parametrize(
    "key",
    [KeyCode(vk=0xF0, char=None), KeyCode(vk=None, char=None)],
)
def test_unknown_virtual_key_returns_none(key: KeyCode) -> None:
    assert KeyRegistry.pynput_key_to_keyspec(key) is None


@pytest.mark.parametrize(
    ("button", "expected_id"),
    [(Button.x1, "mouse_x1"), (Button.x2, "mouse_x2")],
)
def test_supported_mouse_input_is_normalized(
    button: Button,
    expected_id: str,
) -> None:
    result: KeySpec | None = KeyRegistry.pynput_mouse_to_keyspec(button)

    assert result is not None
    assert result.key_id == expected_id


@pytest.mark.parametrize("button", [Button.left, Button.right])
def test_unsupported_mouse_input_returns_none(button: Button) -> None:
    assert KeyRegistry.pynput_mouse_to_keyspec(button) is None


def test_unknown_key_id_raises() -> None:
    with pytest.raises(KeyError):
        KeyRegistry.get("not_a_real_key")


@pytest.mark.parametrize(
    ("key_id", "expected_type"),
    [("a", "char"), ("f9", "key"), ("mouse_x1", "mouse")],
)
def test_registered_key_is_resolved(key_id: str, expected_type: str) -> None:
    spec: KeySpec = KeyRegistry.get(key_id)

    assert spec.key_id == key_id
    assert spec.type == expected_type

from __future__ import annotations

import pytest
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button

from app.scripts.registry.key_registry import KeyRegistry, KeySpec


def _make_keycode(char: str | None, vk: int | None) -> KeyCode:
    """vk 폴백 검증용 char가 비어있는 실제 KeyCode 생성"""

    # pynput KeyCode 생성자에 char=None을 직접 넘겨 vk만 가진 입력 시뮬레이션
    return KeyCode(vk=vk, char=char)


def test_lowercase_alphabet_is_recognized() -> None:
    """소문자 알파벳 KeyCode가 ALPHABET_KEYS로 매핑된다"""

    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(KeyCode.from_char("a"))
    assert result is not None
    assert result.key_id == "a"


def test_uppercase_alphabet_is_normalized_to_lower() -> None:
    """대문자 입력도 소문자 키 ID로 정규화된다"""

    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(KeyCode.from_char("Z"))
    assert result is not None
    assert result.key_id == "z"


def test_number_key_is_recognized() -> None:
    """숫자 키가 NUMBER_KEYS로 매핑된다"""

    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(KeyCode.from_char("5"))
    assert result is not None
    assert result.key_id == "5"


def test_special_char_semicolon_is_recognized() -> None:
    """세미콜론 같은 특수 문자도 SPECIAL_KEYS로 매핑된다"""

    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(KeyCode.from_char(";"))
    assert result is not None
    assert result.key_id == ";"


def test_function_key_is_recognized() -> None:
    """기능 키 Key.f1이 F_KEYS로 매핑된다"""

    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(Key.f1)
    assert result is not None
    assert result.key_id == "f1"


def test_caps_lock_is_recognized() -> None:
    """CapsLock도 SPECIAL_KEYS로 매핑된다"""

    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(Key.caps_lock)
    assert result is not None
    assert result.key_id == "caps_lock"


def test_arrow_keys_are_recognized() -> None:
    """방향키 4종이 모두 매핑된다"""

    assert KeyRegistry.pynput_key_to_keyspec(Key.up).key_id == "up"
    assert KeyRegistry.pynput_key_to_keyspec(Key.down).key_id == "down"
    assert KeyRegistry.pynput_key_to_keyspec(Key.left).key_id == "left"
    assert KeyRegistry.pynput_key_to_keyspec(Key.right).key_id == "right"


def test_unsupported_special_key_returns_none() -> None:
    """등록되지 않은 특수키는 None 반환"""

    # ctrl, shift 같은 모디파이어는 별도 등록 없음
    assert KeyRegistry.pynput_key_to_keyspec(Key.ctrl) is None
    assert KeyRegistry.pynput_key_to_keyspec(Key.shift) is None


def test_vk_fallback_for_alphabet_when_char_is_none() -> None:
    """char가 None이고 vk로만 식별 가능한 알파벳 입력도 매핑된다

    Ctrl+A 같은 입력에서 KeyCode.char가 비어 있고 vk=0x41인 경우.
    """

    fake_key = _make_keycode(char=None, vk=0x41)  # 'A'
    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(fake_key)
    assert result is not None
    assert result.key_id == "a"


def test_vk_fallback_for_number() -> None:
    """vk 폴백으로 숫자 입력도 매핑된다"""

    fake_key = _make_keycode(char=None, vk=0x35)  # '5'
    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(fake_key)
    assert result is not None
    assert result.key_id == "5"


def test_vk_fallback_for_oem_semicolon() -> None:
    """OEM 세미콜론(VK_OEM_1) 폴백 매핑"""

    fake_key = _make_keycode(char=None, vk=0xBA)  # ;
    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(fake_key)
    assert result is not None
    assert result.key_id == ";"


def test_vk_fallback_for_oem_brackets() -> None:
    """OEM 대괄호 폴백 매핑"""

    fake_left = _make_keycode(char=None, vk=0xDB)  # [
    fake_right = _make_keycode(char=None, vk=0xDD)  # ]
    assert KeyRegistry.pynput_key_to_keyspec(fake_left).key_id == "["
    assert KeyRegistry.pynput_key_to_keyspec(fake_right).key_id == "]"


def test_vk_fallback_for_oem_backslash() -> None:
    """OEM 백슬래시 폴백 매핑"""

    fake_key = _make_keycode(char=None, vk=0xDC)
    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(fake_key)
    assert result is not None
    assert result.key_id == "\\"


def test_unknown_vk_returns_none() -> None:
    """매핑 표에 없는 vk는 None 반환"""

    fake_key = _make_keycode(char=None, vk=0xF0)  # 임의 vk
    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(fake_key)
    assert result is None


def test_keycode_with_empty_char_and_no_vk_returns_none() -> None:
    """char도 vk도 비어있으면 None 반환"""

    fake_key = _make_keycode(char=None, vk=None)
    result: KeySpec | None = KeyRegistry.pynput_key_to_keyspec(fake_key)
    assert result is None


def test_mouse_x1_recognized() -> None:
    """마우스 X1 버튼이 MOUSE_KEYS로 매핑된다"""

    result: KeySpec | None = KeyRegistry.pynput_mouse_to_keyspec(Button.x1)
    assert result is not None
    assert result.key_id == "mouse_x1"


def test_mouse_x2_recognized() -> None:
    """마우스 X2 버튼이 MOUSE_KEYS로 매핑된다"""

    result: KeySpec | None = KeyRegistry.pynput_mouse_to_keyspec(Button.x2)
    assert result is not None
    assert result.key_id == "mouse_x2"


def test_mouse_left_right_not_recognized() -> None:
    """일반 좌/우 클릭은 매크로 입력으로 인식되지 않는다"""

    # 매크로 시작/연계 키로 좌/우 클릭이 우연히 잡히면 안 됨
    assert KeyRegistry.pynput_mouse_to_keyspec(Button.left) is None
    assert KeyRegistry.pynput_mouse_to_keyspec(Button.right) is None


def test_get_unknown_key_id_raises() -> None:
    """등록되지 않은 key_id로 조회하면 KeyError"""

    with pytest.raises(KeyError):
        KeyRegistry.get("not_a_real_key")


def test_get_returns_alphabet_key_by_id() -> None:
    """알파벳 key_id로 조회 가능"""

    spec: KeySpec = KeyRegistry.get("a")
    assert spec.key_id == "a"
    assert spec.type == "char"


def test_get_returns_function_key_by_id() -> None:
    """기능 key_id로 조회 가능"""

    spec: KeySpec = KeyRegistry.get("f9")
    assert spec.key_id == "f9"
    assert spec.type == "key"


def test_get_returns_mouse_key_by_id() -> None:
    """마우스 key_id로 조회 가능"""

    spec: KeySpec = KeyRegistry.get("mouse_x1")
    assert spec.key_id == "mouse_x1"
    assert spec.type == "mouse"

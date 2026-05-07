from dataclasses import dataclass
from typing import ClassVar, Literal

from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button


@dataclass(frozen=True)
class KeySpec:
    """키 정보 클래스"""

    # 표시 이름
    display: str
    # 키 아이디
    key_id: str
    # 키 타입
    type: Literal["key", "char", "mouse"]
    # 키 값
    value: Key | KeyCode | Button

    @classmethod
    def from_key(cls, display: str, key_id: str, key: Key) -> "KeySpec":
        """특수키로 키 객체 생성"""

        return cls(display=display, key_id=key_id, type="key", value=key)

    @classmethod
    def from_char(cls, display: str, char: str) -> "KeySpec":
        """문자키로 키 객체 생성"""

        return cls(
            display=display, key_id=char, type="char", value=KeyCode.from_char(char)
        )

    @classmethod
    def from_mouse(cls, display: str, key_id: str, button: Button) -> "KeySpec":
        """마우스 버튼으로 키 객체 생성"""

        return cls(display=display, key_id=key_id, type="mouse", value=button)


@dataclass(frozen=True)
class KeyRegistry:
    """키 설정 레지스트리 클래스"""

    # fn 키
    F_KEYS: ClassVar[dict[str, KeySpec]] = {
        f"f{i}": KeySpec.from_key(f"F{i}", f"f{i}", getattr(Key, f"f{i}"))
        for i in range(1, 13)
    }

    # 알파벳 키
    ALPHABET_KEYS: ClassVar[dict[str, KeySpec]] = {
        char: KeySpec.from_char(char.upper(), char)
        for char in "abcdefghijklmnopqrstuvwxyz"
    }

    # 숫자 키
    NUMBER_KEYS: ClassVar[dict[str, KeySpec]] = {
        char: KeySpec.from_char(char, char) for char in "0123456789"
    }

    # 특수키
    SPECIAL_KEYS: ClassVar[dict[str, KeySpec]] = {
        "`": KeySpec.from_char("`", "`"),
        "-": KeySpec.from_char("-", "-"),
        "=": KeySpec.from_char("=", "="),
        "[": KeySpec.from_char("[", "["),
        "]": KeySpec.from_char("]", "]"),
        "\\": KeySpec.from_char("\\", "\\"),
        ";": KeySpec.from_char(";", ";"),
        "'": KeySpec.from_char("'", "'"),
        ",": KeySpec.from_char(",", ","),
        ".": KeySpec.from_char(".", "."),
        "/": KeySpec.from_char("/", "/"),
        "up": KeySpec.from_key("Up", "up", Key.up),
        "down": KeySpec.from_key("Down", "down", Key.down),
        "left": KeySpec.from_key("Left", "left", Key.left),
        "right": KeySpec.from_key("Right", "right", Key.right),
        "print_screen": KeySpec.from_key("PrtSc", "print_screen", Key.print_screen),
        "scroll_lock": KeySpec.from_key("ScrLk", "scroll_lock", Key.scroll_lock),
        "pause": KeySpec.from_key("Pause", "pause", Key.pause),
        "insert": KeySpec.from_key("Insert", "insert", Key.insert),
        "home": KeySpec.from_key("Home", "home", Key.home),
        "page_up": KeySpec.from_key("PageUp", "page_up", Key.page_up),
        "page_down": KeySpec.from_key("PageDown", "page_down", Key.page_down),
        "delete": KeySpec.from_key("Delete", "delete", Key.delete),
        "end": KeySpec.from_key("End", "end", Key.end),
        "caps_lock": KeySpec.from_key("CapsLock", "caps_lock", Key.caps_lock),
    }

    # 마우스 버튼
    MOUSE_KEYS: ClassVar[dict[str, KeySpec]] = {
        "mouse_x1": KeySpec.from_mouse("마우스 1", "mouse_x1", Button.x1),
        "mouse_x2": KeySpec.from_mouse("마우스 2", "mouse_x2", Button.x2),
    }

    # Windows VK → SPECIAL_KEYS key_id (US/KR QWERTY 기준)
    # Ctrl/Shift 등 모디파이어로 char가 변형됐을 때 vk로 역추적
    OEM_VK_TO_KEY_ID: ClassVar[dict[int, str]] = {
        0xBA: ";",  # VK_OEM_1
        0xBB: "=",  # VK_OEM_PLUS
        0xBC: ",",  # VK_OEM_COMMA
        0xBD: "-",  # VK_OEM_MINUS
        0xBE: ".",  # VK_OEM_PERIOD
        0xBF: "/",  # VK_OEM_2
        0xC0: "`",  # VK_OEM_3
        0xDB: "[",  # VK_OEM_4
        0xDC: "\\",  # VK_OEM_5
        0xDD: "]",  # VK_OEM_6
        0xDE: "'",  # VK_OEM_7
    }

    @classmethod
    def get(cls, key_id: str) -> KeySpec:
        """키 아이디로 KeySpec 반환"""

        # 내부 설정값 기준 키 조회 결과 구성
        key_spec: KeySpec | None = (
            cls.F_KEYS.get(key_id)
            or cls.ALPHABET_KEYS.get(key_id)
            or cls.NUMBER_KEYS.get(key_id)
            or cls.SPECIAL_KEYS.get(key_id)
            or cls.MOUSE_KEYS.get(key_id)
        )

        # 등록되지 않은 키 설정값 즉시 실패
        if key_spec is None:
            raise KeyError(key_id)

        return key_spec

    @classmethod
    def pynput_key_to_keyspec(cls, k: Key | KeyCode) -> KeySpec | None:
        """pynput 키를 KeySpec으로 변환"""

        # KeyCode: 일반 문자
        if isinstance(k, KeyCode):
            ch: str | None = k.char
            if ch:
                # 대소문자 입력 통합 처리
                normalized_char: str = ch.lower()

                if normalized_char in cls.ALPHABET_KEYS:
                    return cls.ALPHABET_KEYS[normalized_char]
                if normalized_char in cls.NUMBER_KEYS:
                    return cls.NUMBER_KEYS[normalized_char]
                if normalized_char in cls.SPECIAL_KEYS:
                    return cls.SPECIAL_KEYS[normalized_char]

            # Ctrl+문자 등 모디파이어로 char가 변형된 경우 vk 폴백
            vk: int | None = getattr(k, "vk", None)
            if vk is not None:
                if 0x41 <= vk <= 0x5A:
                    return cls.ALPHABET_KEYS[chr(vk).lower()]
                if 0x30 <= vk <= 0x39:
                    return cls.NUMBER_KEYS[chr(vk)]
                if vk in cls.OEM_VK_TO_KEY_ID:
                    return cls.SPECIAL_KEYS[cls.OEM_VK_TO_KEY_ID[vk]]

            return None

        # Key: 특수키
        key_name: str | None = k.name
        if key_name is None:
            return None

        # 지원하지 않는 특수키 입력 무시
        if key_name not in cls.F_KEYS and key_name not in cls.SPECIAL_KEYS:
            return None

        return cls.get(key_name)

    @classmethod
    def pynput_mouse_to_keyspec(cls, button: Button) -> KeySpec | None:
        """pynput 마우스 버튼을 KeySpec으로 변환"""

        # 등록된 마우스 버튼 기준 KeySpec 조회
        for key_spec in cls.MOUSE_KEYS.values():
            if button == key_spec.value:
                return key_spec

        return None

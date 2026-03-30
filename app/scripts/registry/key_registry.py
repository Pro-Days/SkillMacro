from dataclasses import dataclass
from typing import ClassVar, Literal

from pynput.keyboard import Key, KeyCode


@dataclass(frozen=True)
class KeySpec:
    """키 정보 클래스"""

    # 표시 이름
    display: str
    # 키 아이디
    key_id: str
    # 키 타입
    type: Literal["key", "char"]
    # 키 값
    value: Key | KeyCode

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
            if not ch:
                return None

            # 대소문자 입력 통합 처리
            normalized_char: str = ch.lower()

            # 지원하지 않는 문자 입력 무시
            if (
                normalized_char not in cls.ALPHABET_KEYS
                and normalized_char not in cls.NUMBER_KEYS
                and normalized_char not in cls.SPECIAL_KEYS
            ):
                return None

            return cls.get(normalized_char)

        # Key: 특수키
        key_name: str | None = k.name
        if key_name is None:
            return None

        # 지원하지 않는 특수키 입력 무시
        if key_name not in cls.F_KEYS and key_name not in cls.SPECIAL_KEYS:
            return None

        return cls.get(key_name)

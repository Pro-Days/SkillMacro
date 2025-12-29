from __future__ import annotations

import hashlib
import os
from typing import TYPE_CHECKING

from pynput import keyboard as pynput_keyboard
from PyQt6.QtGui import QColor, QFontDatabase, QFontMetrics, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton

from app.scripts.custom_classes import CustomFont
from app.scripts.macro_models import LinkKeyType

if TYPE_CHECKING:
    from app.scripts.shared_data import KeySpec, SharedData


# 스킬 아이콘 캐시
_SKILL_PIXMAP_CACHE: dict[str, QPixmap] = {}


def _get_unique_skill_color(skill_name: str) -> QColor:
    """스킬 이름으로 고유한 색상 생성"""

    # 해시 생성
    digest: bytes = hashlib.sha256(skill_name.encode("utf-8")).digest()

    # HSV 값 생성
    hue: int = int.from_bytes(digest[0:2], "big") % 360
    sat: int = 180 + (digest[2] % 60)  # 180..239
    val: int = 200 + (digest[3] % 56)  # 200..255

    return QColor.fromHsv(hue, sat, val, 255)


def _fill_transparent_pixels(pixmap: QPixmap, fill_color: QColor) -> QPixmap:
    """
    투명 영역을 빠르게 채운 픽스맵 반환.

    구현 방식:
    1) 새 픽스맵을 fill_color로 채움
    2) 그 위에 원본 pixmap을 그려서 투명한 부분이 배경색으로 보이도록 함
    """

    # 유효성 검사
    if pixmap.isNull():
        return pixmap

    # 불투명한 채우기 색상 생성
    opaque_fill = QColor(fill_color)
    opaque_fill.setAlpha(255)

    # 새 픽스맵 생성 및 채우기
    result = QPixmap(pixmap.size())
    result.setDevicePixelRatio(pixmap.devicePixelRatio())
    result.fill(opaque_fill)

    # 원본 픽스맵 그리기
    painter = QPainter(result)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()

    return result


def convert_skill_name_to_slot(shared_data: SharedData, skill_name: str) -> int:
    """스킬 이름을 슬롯 번호로 변환"""

    return (
        shared_data.equipped_skills.index(skill_name)
        if skill_name in shared_data.equipped_skills
        else -1
    )


def is_key_using(shared_data: SharedData, key: KeySpec) -> bool:
    """키가 사용중인지 확인"""

    # 사용중인 키 목록
    used_keys: list[KeySpec] = []

    # 시작 키
    used_keys.append(shared_data.start_key)

    # 스킬 사용 키
    used_keys.extend(shared_data.skill_keys)

    # 연계 스킬 키
    used_keys.extend(
        [
            shared_data.KEY_DICT[link_skill.key]
            for link_skill in shared_data.link_skills
            if link_skill.key_type == LinkKeyType.ON
            and link_skill.key is not None
            and link_skill.key in shared_data.KEY_DICT
        ]
    )

    return key in used_keys


def _key_to_KeySpec(
    shared_data: SharedData, k: pynput_keyboard.Key | pynput_keyboard.KeyCode | None
) -> KeySpec | None:

    if k is None:
        return None

    # KeyCode: 일반 문자
    if isinstance(k, pynput_keyboard.KeyCode):
        ch: str | None = k.char
        if not ch:
            return None

        return shared_data.KEY_DICT.get(ch, None)

    return shared_data.KEY_DICT.get(k.name, None)


def convert_resource_path(relative_path: str) -> str:
    """리소스 경로 변경"""

    base_path: str = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(base_path)

    return os.path.join(base_path, relative_path)


def set_default_fonts() -> None:
    """기본 폰트 설정"""

    font_path: str = convert_resource_path("resources\\font\\NotoSansKR-Regular.ttf")

    QFontDatabase.addApplicationFont(font_path)

    # print(QFontDatabase.families())


def get_skill_pixmap(shared_data: SharedData, skill_name: str = "") -> QPixmap:
    """스킬 아이콘 반환"""

    # skill_name == ""이면 빈 스킬 아이콘 반환
    if not skill_name:
        return QPixmap(convert_resource_path(f"resources\\image\\emptySkill.png"))

    # 스킬 이미지가 있으면 해당 이미지 반환
    if skill_name in shared_data.skill_images_dir:
        return QPixmap(shared_data.skill_images_dir[skill_name])

    # 스킬 이미지가 없으면 기본 스킬 아이콘을 고유 색상으로 채운 이미지 반환
    image_path: str = convert_resource_path("resources\\image\\skill_attack.png")

    # 스킬 이름을 캐시 키로 사용
    cache_key: str = skill_name
    cached: QPixmap | None = _SKILL_PIXMAP_CACHE.get(cache_key)

    # 캐시에 있으면 반환
    if cached is not None:
        return cached

    # 적용할 이미지 불러오기
    base_pixmap: QPixmap = QPixmap(image_path)
    if base_pixmap.isNull():
        return base_pixmap

    # 고유 색상 생성
    color: QColor = _get_unique_skill_color(skill_name)

    # 색 채우기
    colored: QPixmap = _fill_transparent_pixels(base_pixmap, color)

    # 캐시에 저장
    _SKILL_PIXMAP_CACHE[cache_key] = colored

    return colored


## 위젯 크기에 맞는 폰트로 변경
def adjust_font_size(
    widget: QPushButton | QLabel,
    text: str,
    maxSize: int,
    font_name="나눔스퀘어라운드 ExtraBold",
) -> None:
    # 텍스트 설정
    widget.setText(text)

    # "\n"이 포함되어 있으면 첫 줄만 사용
    if "\n" in text:
        text = text.split("\n")[0]

    # 위젯 크기가 0이거나 텍스트가 비어있으면 폰트 조정하지 않음
    if widget.width() == 0 or widget.height() == 0 or not text:
        return

    # 폰트 설정
    font_size = 1
    font = CustomFont(font_size)
    metrics = QFontMetrics(font)

    # 폰트 크기를 증가시키면서 위젯 크기에 맞는지 확인
    while font_size < maxSize:
        text_width: int = metrics.horizontalAdvance(text)
        text_height: int = metrics.height()

        # QPushButton이면 여백을 추가
        if isinstance(widget, QPushButton):
            text_width += 4
            text_height += 4

        # 위젯 크기를 초과하면 중지
        if text_width > widget.width() or text_height > widget.height():
            break

        font_size += 1
        font.setPointSize(font_size)
        metrics = QFontMetrics(font)

    # 폰트 크기 설정
    font.setPointSize(font_size - 1)
    widget.setFont(font)


def adjust_text_length(
    text: str, widget: QPushButton | QLabel, margin: int = 40
) -> str:
    """
    위젯 크기에 맞게 텍스트를 자름
    """

    font_metrics: QFontMetrics = widget.fontMetrics()
    max_width: int = widget.width() - margin

    for i in range(len(text), 0, -1):
        if font_metrics.boundingRect(text[:i]).width() < max_width:
            return text[:i]

    return ""


def set_var_to_ClassVar(var: list | dict, value: list | dict) -> None:
    """
    SharedData 클래스의 변수에 값을 설정
    """

    if isinstance(var, list) and isinstance(value, list):
        var.clear()
        for v in value:
            var.append(v)

    elif isinstance(var, dict) and isinstance(value, dict):
        var.clear()
        for key, v in value.items():
            var[key] = v

    else:
        raise TypeError("var와 value는 모두 list 또는 dict여야 합니다.")


def get_available_skills(shared_data: SharedData) -> list[str]:
    """
    서버, 직업에 따라 사용 가능한 스킬 목록 반환
    """

    return shared_data.skill_data[shared_data.server_ID]["skills"]


def get_every_skills(shared_data: SharedData) -> list[str]:
    """
    서버의 모든 스킬 목록 반환
    """

    return shared_data.skill_data[shared_data.server_ID]["skills"]


def get_skill_details(shared_data: SharedData, skill_name: str) -> dict:
    """
    서버, 직업에 따른 스킬 상세 정보 반환
    """

    return shared_data.skill_data[shared_data.server_ID]["skill_details"][skill_name]

from __future__ import annotations

import hashlib
import os
from typing import TYPE_CHECKING

from pynput import keyboard as pynput_keyboard
from PyQt6.QtGui import QColor, QFontDatabase, QFontMetrics, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton

from app.scripts.custom_classes import CustomFont
from app.scripts.macro_models import LinkKeyType, MacroPreset
from app.scripts.skill_registry import SkillDef, SkillRegistry

if TYPE_CHECKING:
    from app.scripts.shared_data import KeySpec, SharedData


# 스킬 아이콘 캐시
_SKILL_PIXMAP_CACHE: dict[str, QPixmap] = {}


def _get_unique_skill_color(skill_id: str) -> QColor:
    """스킬 ID로 고유한 색상 생성"""

    # 해시 생성
    digest: bytes = hashlib.sha256(skill_id.encode("utf-8")).digest()

    # 적당한 HSV 값 생성
    hue: int = int.from_bytes(digest[:2]) % 360
    sat: int = 192 + (digest[2] % 64)  # 192..255
    val: int = 192 + (digest[3] % 64)  # 192..255

    return QColor.fromHsv(hue, sat, val, 255)


def _fill_transparent_pixels(pixmap: QPixmap, fill_color: QColor) -> QPixmap:
    """
    투명 영역을 빠르게 채운 픽스맵 반환
    """

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


def _get_skill_registry(shared_data: SharedData) -> SkillRegistry:
    """현재 서버의 스킬 레지스트리 반환"""

    return shared_data.skill_registries[shared_data.server_ID]


def is_key_using(shared_data: SharedData, key: KeySpec) -> bool:
    """키가 사용중인지 확인"""

    preset: MacroPreset = shared_data.presets[shared_data.recent_preset]

    # 시작 키
    if key == preset.settings.start_key:
        return True

    # 스킬 사용 키
    if key in preset.skills.skill_keys:
        return True

    # 연계 스킬 키
    for link_skill in shared_data.link_skills:
        if (
            link_skill.key_type == LinkKeyType.ON
            and link_skill.key in shared_data.KEY_DICT
            and key == shared_data.KEY_DICT[link_skill.key]
        ):
            return True

    return False


def key_to_KeySpec(
    shared_data: SharedData, k: pynput_keyboard.Key | pynput_keyboard.KeyCode | None
) -> KeySpec | None:
    """pynput 키를 KeySpec으로 변환"""

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


def get_skill_pixmap(shared_data: SharedData, skill_id: str = "") -> QPixmap:
    """스킬 아이콘 반환"""

    # skill_id == ""이면 빈 스킬 아이콘 반환
    if not skill_id:
        return QPixmap(convert_resource_path(f"resources\\image\\emptySkill.png"))

    # 스킬 이미지가 있으면 해당 이미지 반환
    if skill_id in shared_data.skill_images_dir:
        return QPixmap(shared_data.skill_images_dir[skill_id])

    # 스킬 이미지가 없으면 기본 스킬 아이콘을 고유 색상으로 채운 이미지 반환
    image_path: str = convert_resource_path("resources\\image\\skill_attack.png")

    # 스킬 ID를 캐시 키로 사용
    cache_key: str = skill_id
    cached: QPixmap | None = _SKILL_PIXMAP_CACHE.get(cache_key)

    # 캐시에 있으면 반환
    if cached is not None:
        return cached

    # 적용할 이미지 불러오기
    base_pixmap: QPixmap = QPixmap(image_path)

    # 고유 색상 생성
    color: QColor = _get_unique_skill_color(skill_id)

    # 색 채우기
    colored: QPixmap = _fill_transparent_pixels(base_pixmap, color)

    # 캐시에 저장
    _SKILL_PIXMAP_CACHE[cache_key] = colored

    return colored


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


def get_every_skills(shared_data: SharedData) -> list[str]:
    """
    서버의 모든 스킬 ID 목록 반환
    """

    return _get_skill_registry(shared_data).all_skill_ids()


def get_skill(shared_data: SharedData, skill_id: str) -> SkillDef:
    """SkillDef 반환"""

    return _get_skill_registry(shared_data).get(skill_id)


def get_skill_name(shared_data: SharedData, skill_id: str) -> str:
    """스킬 ID로 이름 반환"""

    return _get_skill_registry(shared_data).name(skill_id)


def get_skill_details(shared_data: SharedData, skill_id: str) -> dict:
    """스킬 ID로 상세 정보 반환"""

    return _get_skill_registry(shared_data).details(skill_id)

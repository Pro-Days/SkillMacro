from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from PyQt6.QtGui import QColor, QFontDatabase, QPainter, QPixmap


def convert_resource_path(relative_path: str) -> str:
    """리소스 경로 변경"""
    # todo: pathlib로 변경

    base_path: str = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(base_path)
    base_path = os.path.dirname(base_path)

    return os.path.join(base_path, relative_path)


@dataclass
class ResourceRegistry:
    """
    리소스 파일 경로를 관리하는 레지스트리 클래스
    todo: 아이콘들 모두 여기에 추가
    """

    # 싱글톤 인스턴스
    # 프로그램 전체에서 단 하나의 상태 객체만 존재하도록 보장
    _instance: ResourceRegistry | None = None

    # 초기화 여부
    _initialized: bool = False

    # 스킬 아이콘 캐시
    _SKILL_PIXMAP_CACHE: dict[str, QPixmap] = field(default_factory=dict)

    # 폰트 디렉토리 등록
    font_path: str = convert_resource_path("resources\\font\\NotoSansKR-Regular.ttf")

    def __new__(cls) -> ResourceRegistry:
        if cls._instance is None:
            cls._instance = super(ResourceRegistry, cls).__new__(cls)
        return cls._instance

    def _ensure_initialized(self) -> None:
        """초기화 여부 확인 및 초기화 작업 수행"""

        if not self._initialized:
            self.initialize()
            self._initialized = True

    def initialize(self) -> None:
        """초기화 작업 수행"""

        # 빈 스킬 아이콘 로드
        self._SKILL_PIXMAP_CACHE[""] = QPixmap(
            convert_resource_path(f"resources\\image\\emptySkill.png")
        )

        # 폰트 등록
        QFontDatabase.addApplicationFont(self.font_path)

    def get_skill_pixmap(self, skill_id: str = "") -> QPixmap:
        """스킬 이미지 반환"""

        self._ensure_initialized()

        # 스킬 이미지가 있으면 해당 이미지 반환
        if skill_id in self._SKILL_PIXMAP_CACHE:
            return self._SKILL_PIXMAP_CACHE[skill_id]

        # 스킬 이미지가 없으면 기본 스킬 아이콘을 고유 색상으로 채운 이미지 반환
        image_path: str = convert_resource_path("resources\\image\\skill_attack.png")

        # 적용할 이미지 불러오기
        base_pixmap: QPixmap = QPixmap(image_path)

        # 고유 색상 생성
        color: QColor = self._get_unique_skill_color(skill_id)

        # 색 채우기
        colored: QPixmap = self._fill_transparent_pixels(base_pixmap, color)

        # 캐시에 저장
        self._SKILL_PIXMAP_CACHE[skill_id] = colored

        return colored

    def _get_unique_skill_color(self, skill_id: str) -> QColor:
        """스킬 ID로 고유한 색상 생성"""

        # 해시 생성
        digest: bytes = hashlib.sha256(skill_id.encode("utf-8")).digest()

        # 적당한 HSV 값 생성
        hue: int = int.from_bytes(digest[:2]) % 360
        sat: int = 192 + (digest[2] % 64)  # 192..255
        val: int = 192 + (digest[3] % 64)  # 192..255

        return QColor.fromHsv(hue, sat, val, 255)

    def _fill_transparent_pixels(self, pixmap: QPixmap, fill_color: QColor) -> QPixmap:
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


resource_registry = ResourceRegistry()

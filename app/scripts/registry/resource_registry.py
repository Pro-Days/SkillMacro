from __future__ import annotations

import os
from dataclasses import dataclass, field

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QPainter,
    QPen,
    QPixmap,
)

# 현재 다크 모드 여부 (테마 전환 시 갱신)
_dark_mode: bool = False

# 라이트 테마 이미지 출력 디렉터리 경로
_LIGHT_THEME_IMAGE_DIR: str = "resources\\image\\light"

# 다크 테마 이미지 출력 디렉터리 경로
_DARK_THEME_IMAGE_DIR: str = "resources\\image\\dark"


def convert_resource_path(relative_path: str) -> str:
    """리소스 경로 변경"""
    # todo: pathlib로 변경

    base_path: str = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(base_path)
    base_path = os.path.dirname(base_path)

    return os.path.join(base_path, relative_path)


def get_theme_image_path(filename: str, dark: bool) -> str:
    """테마별 이미지 경로 반환"""

    # 현재 테마에 맞는 리소스 디렉터리 선택
    theme_dir: str = _DARK_THEME_IMAGE_DIR if dark else _LIGHT_THEME_IMAGE_DIR

    # 테마 디렉터리 기준 최종 경로 반환
    return convert_resource_path(f"{theme_dir}\\{filename}")


def get_theme_image_url_path(filename: str, dark: bool) -> str:
    """QSS url() 용 테마 이미지 경로 반환"""

    # QSS 에서 사용하는 슬래시 형식 경로 반환
    return get_theme_image_path(filename, dark).replace("\\", "/")


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
    # 무공비급 아이콘 캐시
    _SCROLL_PIXMAP_CACHE: dict[str, QPixmap] = field(default_factory=dict)

    # 폰트 디렉토리 등록
    font_path: str = convert_resource_path("resources\\font\\NotoSansKR-Regular.ttf")
    # 텍스트 아이콘 렌더링용 폰트 패밀리
    _font_family: str = ""

    def __new__(cls) -> ResourceRegistry:
        if cls._instance is None:
            cls._instance = super(ResourceRegistry, cls).__new__(cls)
        return cls._instance

    def _ensure_initialized(self) -> None:
        """초기화 여부 확인 및 초기화 작업 수행"""

        if not self._initialized:
            self.initialize()
            self._initialized = True

    def set_dark_mode(self, dark: bool) -> None:
        """테마 전환 시 호출 — 캐시를 초기화해 다음 요청부터 새 색상으로 생성"""

        global _dark_mode
        _dark_mode = dark
        self._SKILL_PIXMAP_CACHE.clear()
        self._SCROLL_PIXMAP_CACHE.clear()
        # 빈 스킬 슬롯 아이콘은 캐시에 항상 있어야 함
        self._SKILL_PIXMAP_CACHE[""] = QPixmap(
            convert_resource_path("resources\\image\\emptySkill.png")
        )

    def initialize(self) -> None:
        """초기화 작업 수행"""

        # 빈 스킬 아이콘 로드
        self._SKILL_PIXMAP_CACHE[""] = QPixmap(
            convert_resource_path("resources\\image\\emptySkill.png")
        )

        # 폰트 등록
        font_id: int = QFontDatabase.addApplicationFont(self.font_path)
        if font_id == -1:
            return

        # 텍스트 아이콘 렌더링에 사용할 패밀리 보관
        font_families: list[str] = QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            self._font_family = font_families[0]

    def get_skill_pixmap(self, skill_id: str | None = None) -> QPixmap:
        """스킬 이미지 반환"""

        if skill_id is None:
            return QPixmap(convert_resource_path("resources\\image\\emptySkill.png"))

        self._ensure_initialized()

        # 스킬 이미지가 있으면 해당 이미지 반환
        if skill_id in self._SKILL_PIXMAP_CACHE:
            return self._SKILL_PIXMAP_CACHE[skill_id]

        # 스킬 이름 기반 텍스트 아이콘 생성
        skill_name: str = self._extract_icon_label(skill_id)
        colored: QPixmap = self._build_labeled_pixmap(label=skill_name)

        # 생성된 아이콘 캐시 반영
        self._SKILL_PIXMAP_CACHE[skill_id] = colored

        return colored

    def get_scroll_pixmap(self, scroll_id: str | None = None) -> QPixmap:
        """무공비급 이미지 반환"""

        if scroll_id is None:
            return QPixmap(convert_resource_path("resources\\image\\emptySkill.png"))

        self._ensure_initialized()

        if scroll_id in self._SCROLL_PIXMAP_CACHE:
            return self._SCROLL_PIXMAP_CACHE[scroll_id]

        # 무공비급 이름 기반 텍스트 아이콘 생성
        scroll_name: str = self._extract_icon_label(scroll_id)
        colored: QPixmap = self._build_labeled_pixmap(label=scroll_name)

        # 생성된 아이콘 캐시 반영
        self._SCROLL_PIXMAP_CACHE[scroll_id] = colored

        return colored

    def _build_labeled_pixmap(
        self,
        label: str,
    ) -> QPixmap:
        """이름 텍스트가 포함된 아이콘 생성"""

        # 배경 이미지 없는 투명 캔버스 생성
        result: QPixmap = QPixmap(640, 640)
        result.fill(Qt.GlobalColor.transparent)

        # 여러 글자 이름의 가독성 확보
        display_label: str = self._format_icon_label(label)
        text_rect: QRect = self._build_icon_text_rect(result)
        text_flags: int = int(Qt.AlignmentFlag.AlignCenter.value) | int(
            Qt.TextFlag.TextWordWrap.value
        )
        font: QFont = self._build_icon_font(display_label, text_rect, text_flags)
        shadow_offset: int = max(
            2,
            int(result.width() * 0.012),
        )

        # 외곽선과 본문 텍스트 순차 렌더링
        painter: QPainter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # 아이콘 외곽 회색 테두리 렌더링
        border_width: int = max(6, int(result.width() * 0.012))
        border_pen: QPen = QPen(QColor(150, 150, 150, 220))
        border_pen.setWidth(border_width)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            result.rect().adjusted(
                border_width,
                border_width,
                -border_width,
                -border_width,
            ),
            48,
            48,
        )

        # 텍스트 외곽선과 본문 렌더링
        # 텍스트 외곽선 색상 (다크: 검정, 라이트: 흰색)
        outline_color = (
            QColor(0, 0, 0, 220) if _dark_mode else QColor(255, 255, 255, 220)
        )
        painter.setFont(font)
        painter.setPen(outline_color)
        for offset_x in (-shadow_offset, 0, shadow_offset):
            for offset_y in (-shadow_offset, 0, shadow_offset):
                if offset_x == 0 and offset_y == 0:
                    continue

                outline_rect: QRect = text_rect.translated(offset_x, offset_y)
                painter.drawText(outline_rect, text_flags, display_label)

        # 본문 텍스트 색상 (테마에 따라 분기)
        painter.setPen(QColor(255, 255, 255) if _dark_mode else QColor(0, 0, 0))
        painter.drawText(text_rect, text_flags, display_label)
        painter.end()

        return result

    def _build_icon_text_rect(self, pixmap: QPixmap) -> QRect:
        """아이콘 텍스트 배치 영역 계산"""

        # 아이콘 외곽선과 겹치지 않는 내부 여백 계산
        horizontal_padding: int = max(
            18,
            int(pixmap.width() * 0.04),
        )
        vertical_padding: int = max(
            20,
            int(pixmap.height() * 0.05),
        )

        return pixmap.rect().adjusted(
            horizontal_padding,
            vertical_padding,
            -horizontal_padding,
            -vertical_padding,
        )

    def _build_icon_font(self, label: str, text_rect: QRect, text_flags: int) -> QFont:
        """아이콘 영역에 맞는 폰트 계산"""

        # 가능한 가장 큰 폰트 크기부터 순차 탐색
        point_size: int = 260
        while point_size >= 72:
            font: QFont = QFont()
            font.setBold(True)
            font.setPointSize(point_size)
            if self._font_family:
                font.setFamily(self._font_family)

            # 현재 폰트가 아이콘 내부에 들어가는지 측정
            metrics: QFontMetrics = QFontMetrics(font)
            bounding_rect: QRect = metrics.boundingRect(text_rect, text_flags, label)
            if (
                bounding_rect.width() <= text_rect.width()
                and bounding_rect.height() <= text_rect.height()
            ):
                return font

            point_size -= 6

        # 최소 크기 폰트 반환
        minimum_font: QFont = QFont()
        minimum_font.setBold(True)
        minimum_font.setPointSize(72)
        if self._font_family:
            minimum_font.setFamily(self._font_family)

        return minimum_font

    def _format_icon_label(self, label: str) -> str:
        """긴 이름을 아이콘 내부 다중 줄 텍스트로 정리"""

        # 공백이 포함된 이름은 Qt 줄바꿈 처리 유지
        if " " in label:
            return label

        # 짧은 이름은 한 줄 유지
        if len(label) <= 3:
            return label

        # 글자 수에 따라 2~3줄로 균등 분할
        line_count: int = 2 if len(label) <= 6 else 3
        chunk_size: int = (len(label) + line_count - 1) // line_count
        lines: list[str] = []
        for start in range(0, len(label), chunk_size):
            line: str = label[start : start + chunk_size]
            lines.append(line)

        return "\n".join(lines)

    def _extract_icon_label(self, resource_id: str) -> str:
        """리소스 ID의 마지막 이름 구간 추출"""

        # 서버 접두부를 제외한 마지막 이름만 아이콘 문자열로 사용
        return resource_id.rsplit(":", maxsplit=1)[-1]


resource_registry = ResourceRegistry()

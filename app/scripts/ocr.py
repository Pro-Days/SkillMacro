from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import cast


import winocr
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QGuiApplication, QImage, QPixmap, QScreen

from app.scripts.calculator_models import OVERALL_STAT_GRID_ROWS, STAT_SPECS, StatKey


def capture_screen_region(
    left: int,
    top: int,
    width: int,
    height: int,
) -> Image.Image:
    """화면 캡처 후 PIL 이미지 리턴"""

    # 선택 영역 기준 화면 확인
    rect: QRect = QRect(left, top, width, height)
    center: QPoint = rect.center()
    screen_candidate: QScreen | None = QGuiApplication.screenAt(center)
    if screen_candidate is None:
        screen_candidate = QGuiApplication.primaryScreen()

    screen: QScreen = cast(QScreen, screen_candidate)

    # 전역 좌표에서 선택 화면 내부 좌표로 변환
    screen_geometry: QRect = screen.geometry()
    local_left: int = rect.left() - screen_geometry.left()
    local_top: int = rect.top() - screen_geometry.top()

    # Qt 화면 캡처 및 PIL 변환용 이미지 포맷 정규화
    pixmap: QPixmap = screen.grabWindow(
        0,
        local_left,
        local_top,
        rect.width(),
        rect.height(),
    )
    image: QImage = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    image_bytes: bytes = bytes(image.bits())

    return Image.frombuffer(
        "RGBA",
        (image.width(), image.height()),
        image_bytes,
        "raw",
        "RGBA",
        image.bytesPerLine(),
        1,
    ).convert("RGB")


_TARGET_OCR_WIDTH: int = 1600
_ROW_Y_TOLERANCE: int = 10


def recognize_image(image: Image.Image) -> list[str]:
    """이미지로부터 텍스트 추출"""

    words: list[_OcrWord] = _recognize_words(image)
    return _build_lines_from_words(words)


def _build_lines_from_words(words: list[_OcrWord]) -> list[str]:
    """OCR 단어 좌표 기반 줄 텍스트 재구성"""

    if not words:
        return []

    y_tolerance: int = _ROW_Y_TOLERANCE
    words.sort(key=lambda word: (word.y, word.x))

    rows: list[list[_OcrWord]] = []
    current_row: list[_OcrWord] = [words[0]]
    current_y: float = words[0].y

    for word in words[1:]:
        y: float = word.y
        if abs(y - current_y) <= y_tolerance:
            current_row.append(word)
            continue
        rows.append(current_row)
        current_row = [word]
        current_y = y
    rows.append(current_row)

    lines_out: list[str] = []
    for row in rows:
        row.sort(key=lambda word: word.x)
        line_text: str = " ".join(word.text for word in row).strip()
        if line_text:
            lines_out.append(line_text)

    return lines_out


@dataclass(frozen=True)
class OcrStatCandidate:
    value: float
    source: str
    agreement_count: int = 1
    attempt_count: int = 1


@dataclass(frozen=True)
class _OcrWord:
    text: str
    x: float
    y: float
    width: float
    height: float

    @property
    def center_x(self) -> float:
        return self.x + (self.width / 2.0)

    @property
    def center_y(self) -> float:
        return self.y + (self.height / 2.0)


@dataclass(frozen=True)
class _ImageBand:
    start: int
    end: int

    @property
    def height(self) -> int:
        return self.end - self.start + 1


@dataclass(frozen=True)
class _CellRegion:
    stat_key: StatKey
    left: int
    top: int
    right: int
    bottom: int


_NUMBER_PATTERN: re.Pattern[str] = re.compile(
    r"[+\-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
)
_SPLIT_DECIMAL_PATTERN: re.Pattern[str] = re.compile(
    r"([+\-]?(?:\d{1,3}(?:,\d{3})+|\d+))\s+(\d{1,2})(?:\D|$)"
)
_PERCENT_TOKEN_PATTERN: re.Pattern[str] = re.compile(r"\([^)]{1,4}\)")
_LEADING_NOISE_PATTERN: re.Pattern[str] = re.compile(r"^[^0-9A-Za-z가-힣\-]+")
_TABLE_FILL_THRESHOLD: float = 0.35
_TABLE_COLUMN_THRESHOLD: float = 0.45
_VALUE_REGION_RATIO: float = 0.52
_SOURCE_EXACT: str = "exact"
_SOURCE_POSITION: str = "position"
_SOURCE_CELL: str = "cell"


def _recognize_words(image: Image.Image) -> list[_OcrWord]:
    """이미지 OCR 단어와 원본 이미지 기준 좌표 반환"""

    scale: int = max(1, (_TARGET_OCR_WIDTH + image.width - 1) // image.width)
    if scale > 1:
        image = image.resize(
            (image.width * scale, image.height * scale),
            Image.Resampling.LANCZOS,
        )

    loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(winocr.recognize_pil(image, lang="ko"))
    finally:
        loop.close()

    words: list[_OcrWord] = []
    for line in result.lines:
        for word in line.words:
            rect = word.bounding_rect
            words.append(
                _OcrWord(
                    text=word.text,
                    x=float(rect.x) / scale,
                    y=float(rect.y) / scale,
                    width=float(rect.width) / scale,
                    height=float(rect.height) / scale,
                )
            )

    return words


def _is_table_fill_pixel(r: int, g: int, b: int) -> bool:
    """스탯 표 행 배경색 범위 판정"""

    return 18 <= r <= 58 and 14 <= g <= 52 and 10 <= b <= 48


def _normalize_label_text(text: str) -> str:
    compact_text: str = "".join(text.split())
    compact_text = _PERCENT_TOKEN_PATTERN.sub("%", compact_text)
    return compact_text.replace("(%)", "%")


_SORTED_EXACT_LABELS: list[tuple[str, StatKey]] = sorted(
    (
        (_normalize_label_text(label), stat_key)
        for stat_key, label in STAT_SPECS.items()
    ),
    key=lambda item: len(item[0]),
    reverse=True,
)


def _normalize_ocr_line(text: str) -> str:
    text = _PERCENT_TOKEN_PATTERN.sub("(%)", text)
    text = _LEADING_NOISE_PATTERN.sub("", text)
    return " ".join(text.split())


def _extract_numbers(text: str) -> list[float]:
    return [
        float(match.group().replace(",", ""))
        for match in _NUMBER_PATTERN.finditer(text)
    ]


def _extract_cell_value(text: str) -> float | None:
    """값 셀 텍스트의 단일 수치 추출"""

    split_decimal_match: re.Match[str] | None = _SPLIT_DECIMAL_PATTERN.search(text)
    if split_decimal_match is not None:
        integer_part: str = split_decimal_match.group(1).replace(",", "")
        decimal_part: str = split_decimal_match.group(2)
        return float(f"{integer_part}.{decimal_part}")

    values: list[float] = _extract_numbers(text)
    if not values:
        return None

    return values[-1]


def _find_dark_bands(
    scores: list[float],
    threshold: float,
    min_size: int,
) -> list[_ImageBand]:
    """연속된 표 배경 픽셀 구간 추출"""

    bands: list[_ImageBand] = []
    band_start: int | None = None

    for index, score in enumerate(scores):
        if score > threshold and band_start is None:
            band_start = index
            continue

        if score > threshold:
            continue

        if band_start is None:
            continue

        band_end: int = index - 1
        if band_end - band_start + 1 >= min_size:
            bands.append(_ImageBand(band_start, band_end))

        band_start = None

    if band_start is not None:
        band_end = len(scores) - 1
        if band_end - band_start + 1 >= min_size:
            bands.append(_ImageBand(band_start, band_end))

    return bands


def _find_horizontal_table_bands(image: Image.Image) -> list[_ImageBand]:
    """스탯 표의 규칙적인 행 배경 구간 탐색"""

    rgb_image: Image.Image = image.convert("RGB")
    pixels = rgb_image.load()
    width: int = rgb_image.width
    height: int = rgb_image.height
    x_start: int = max(0, int(width * 0.04))
    x_end: int = min(width, int(width * 0.96))
    sample_width: int = x_end - x_start
    min_band_height: int = max(4, int(height * 0.008))
    row_scores: list[float] = []

    for y in range(height):
        fill_count: int = 0
        for x in range(x_start, x_end):
            r, g, b = pixels[x, y]  ## type: ignore
            if _is_table_fill_pixel(r, g, b):
                fill_count += 1

        row_scores.append(fill_count / sample_width)

    bands: list[_ImageBand] = _find_dark_bands(
        row_scores,
        _TABLE_FILL_THRESHOLD,
        min_band_height,
    )
    required_count: int = len(OVERALL_STAT_GRID_ROWS)
    best_start: int | None = None
    best_score: tuple[int, int, int] | None = None

    for start_index in range(0, len(bands) - required_count + 1):
        window: list[_ImageBand] = bands[start_index : start_index + required_count]
        starts: list[int] = [band.start for band in window]
        heights: list[int] = [band.height for band in window]
        deltas: list[int] = [
            starts[index + 1] - starts[index] for index in range(len(starts) - 1)
        ]
        median_delta: int = sorted(deltas)[len(deltas) // 2]
        median_height: int = sorted(heights)[len(heights) // 2]
        delta_limit: int = max(4, int(median_delta * 0.20))
        height_limit: int = max(3, int(median_height * 0.35))

        if max(deltas) - min(deltas) > delta_limit:
            continue

        if max(heights) - min(heights) > height_limit:
            continue

        if start_index == 0:
            preceding_gap: int = median_delta * 2
        else:
            preceding_gap = bands[start_index].start - bands[start_index - 1].start

        header_gap_score: int = 1 if preceding_gap >= int(median_delta * 1.4) else 0
        current_score: tuple[int, int, int] = (
            header_gap_score,
            len(bands) - start_index,
            -bands[start_index].start,
        )
        if best_score is None or current_score > best_score:
            best_score = current_score
            best_start = start_index

    if best_start is None:
        return []

    return bands[best_start : best_start + required_count]


def _find_vertical_table_bands(
    image: Image.Image,
    row_bands: list[_ImageBand],
) -> list[_ImageBand]:
    """스탯 표 좌우 열 배경 구간 탐색"""

    rgb_image: Image.Image = image.convert("RGB")
    pixels = rgb_image.load()
    width: int = rgb_image.width
    column_scores: list[float] = []
    sample_height: int = sum(band.height for band in row_bands)

    for x in range(width):
        fill_count: int = 0
        for row_band in row_bands:
            for y in range(row_band.start, row_band.end + 1):
                r, g, b = pixels[x, y]  ## type: ignore
                if _is_table_fill_pixel(r, g, b):
                    fill_count += 1

        column_scores.append(fill_count / sample_height)

    min_column_width: int = max(24, int(width * 0.12))
    bands: list[_ImageBand] = _find_dark_bands(
        column_scores,
        _TABLE_COLUMN_THRESHOLD,
        min_column_width,
    )
    if len(bands) < 2:
        return []

    widest_bands: list[_ImageBand] = sorted(
        bands,
        key=lambda band: band.height,
        reverse=True,
    )[:2]
    return sorted(widest_bands, key=lambda band: band.start)


def _build_stat_cell_regions(image: Image.Image) -> list[_CellRegion]:
    """스탯 표 행/열 기반 값 셀 영역 구성"""

    row_bands: list[_ImageBand] = _find_horizontal_table_bands(image)
    if not row_bands:
        return []

    column_bands: list[_ImageBand] = _find_vertical_table_bands(image, row_bands)
    if len(column_bands) != 2:
        return []

    cell_regions: list[_CellRegion] = []
    for row_index, row in enumerate(OVERALL_STAT_GRID_ROWS):
        row_band: _ImageBand = row_bands[row_index]

        for column_index, stat_key in enumerate(row):
            if stat_key is None:
                continue

            column_band: _ImageBand = column_bands[column_index]
            column_width: int = column_band.height
            value_left: int = column_band.start + int(
                column_width * _VALUE_REGION_RATIO
            )
            cell_regions.append(
                _CellRegion(
                    stat_key=stat_key,
                    left=value_left,
                    top=max(0, row_band.start - 2),
                    right=min(image.width - 1, column_band.end),
                    bottom=min(image.height - 1, row_band.end + 2),
                )
            )

    return cell_regions


def _find_stats_title_index(lines: list[str]) -> int | None:
    for index in range(len(lines) - 1, -1, -1):
        compact_line: str = "".join(lines[index].split())
        if "전체" in compact_line and (
            "스탯" in compact_line or "스텟" in compact_line
        ):
            return index
    return None


def _fill_missing_stats_by_row_order(
    lines: list[str],
    results: dict[StatKey, OcrStatCandidate],
) -> None:
    title_index = _find_stats_title_index(lines)

    # 타이틀이 있으면 그 다음 줄부터, 없으면 숫자가 있는 모든 줄 사용
    search_lines: list[str] = (
        lines[title_index + 1 :] if title_index is not None else lines
    )

    stat_rows: list[str] = []
    for line in search_lines:
        if not _extract_numbers(line):
            continue
        stat_rows.append(line)
        if len(stat_rows) >= len(OVERALL_STAT_GRID_ROWS):
            break

    if not stat_rows:
        return

    for row_index, line in enumerate(stat_rows):
        left_key, right_key = OVERALL_STAT_GRID_ROWS[row_index]
        values = _extract_numbers(line)
        if not values:
            continue

        if left_key is not None and left_key not in results:
            results[left_key] = OcrStatCandidate(
                value=values[0],
                source=_SOURCE_POSITION,
            )

        if right_key is None or right_key in results:
            continue

        if left_key is None:
            results[right_key] = OcrStatCandidate(
                value=values[0],
                source=_SOURCE_POSITION,
            )
            continue

        if len(values) >= 2:
            results[right_key] = OcrStatCandidate(
                value=values[1],
                source=_SOURCE_POSITION,
            )


def _build_ocr_variant_images(image: Image.Image) -> list[Image.Image]:
    """Build a few lightweight OCR variants from the same selected region."""

    base_image: Image.Image = image.convert("RGB")
    gray_image: Image.Image = ImageOps.grayscale(base_image)
    contrast_image: Image.Image = ImageEnhance.Contrast(gray_image).enhance(2.2)
    sharpened_image: Image.Image = ImageEnhance.Sharpness(base_image).enhance(2.0)
    threshold_image: Image.Image = contrast_image.point(
        lambda px: 255 if px >= 170 else 0  # type: ignore
    ).convert("L")

    return [
        base_image,
        ImageOps.autocontrast(gray_image),
        ImageOps.autocontrast(contrast_image),
        threshold_image.filter(ImageFilter.MedianFilter(size=3)),
        sharpened_image,
    ]


def _cell_contains_word(cell_region: _CellRegion, word: _OcrWord) -> bool:
    """값 셀 내부 OCR 단어 포함 여부 판정"""

    return (
        cell_region.left <= word.center_x <= cell_region.right
        and cell_region.top <= word.center_y <= cell_region.bottom
    )


def _parse_stat_candidates_from_cells(
    words: list[_OcrWord],
    cell_regions: list[_CellRegion],
) -> dict[StatKey, OcrStatCandidate]:
    """값 셀 단위 OCR 후보 구성"""

    results: dict[StatKey, OcrStatCandidate] = {}
    sorted_words: list[_OcrWord] = sorted(words, key=lambda word: word.x)

    for cell_region in cell_regions:
        cell_words: list[_OcrWord] = [
            word for word in sorted_words if _cell_contains_word(cell_region, word)
        ]
        if not cell_words:
            continue

        cell_text: str = " ".join(word.text for word in cell_words)
        cell_value: float | None = _extract_cell_value(cell_text)
        if cell_value is None:
            continue

        results[cell_region.stat_key] = OcrStatCandidate(
            value=cell_value,
            source=_SOURCE_CELL,
        )

    return results


def _score_candidate_group(
    candidates: list[OcrStatCandidate],
) -> tuple[int, int, int, int]:
    """반복 일치와 인식 출처 기반 후보 순위 계산"""

    exact_count: int = sum(
        1 for candidate in candidates if candidate.source == _SOURCE_EXACT
    )
    cell_count: int = sum(
        1 for candidate in candidates if candidate.source == _SOURCE_CELL
    )
    anchored_count: int = cell_count + exact_count
    return anchored_count, cell_count, exact_count, len(candidates)


def _candidate_source_priority(candidate: OcrStatCandidate) -> int:
    """대표 후보 출처 우선순위 계산"""

    if candidate.source == _SOURCE_CELL:
        return 3

    if candidate.source == _SOURCE_EXACT:
        return 2

    return 1


def extract_stat_candidates_from_image(
    image: Image.Image,
) -> dict[StatKey, OcrStatCandidate]:
    variant_images: list[Image.Image] = _build_ocr_variant_images(image)
    variant_results: list[dict[StatKey, OcrStatCandidate]] = []
    cell_regions: list[_CellRegion] = _build_stat_cell_regions(image)
    uses_cell_regions: bool = bool(cell_regions)

    for variant_image in variant_images:
        words: list[_OcrWord] = _recognize_words(variant_image)
        if uses_cell_regions:
            variant_results.append(
                _parse_stat_candidates_from_cells(words, cell_regions)
            )

        lines: list[str] = _build_lines_from_words(words)
        variant_results.append(
            parse_stat_candidates_from_text(
                lines,
                include_position=not uses_cell_regions,
            )
        )

    grouped_candidates: dict[StatKey, dict[float, list[OcrStatCandidate]]] = {}
    for candidates in variant_results:
        for stat_key, candidate in candidates.items():
            stat_groups = grouped_candidates.setdefault(stat_key, {})
            stat_groups.setdefault(candidate.value, []).append(candidate)

    attempt_count: int = len(variant_results)
    merged_candidates: dict[StatKey, OcrStatCandidate] = {}

    for stat_key, value_groups in grouped_candidates.items():
        best_group: list[OcrStatCandidate] = max(
            value_groups.values(),
            key=_score_candidate_group,
        )
        representative: OcrStatCandidate = max(
            best_group,
            key=_candidate_source_priority,
        )
        merged_candidates[stat_key] = OcrStatCandidate(
            value=representative.value,
            source=representative.source,
            agreement_count=len(best_group),
            attempt_count=attempt_count,
        )

    return merged_candidates


def parse_stat_candidates_from_text(
    lines: list[str],
    *,
    include_position: bool = True,
) -> dict[StatKey, OcrStatCandidate]:
    normalized_lines: list[str] = [
        normalized for line in lines if (normalized := _normalize_ocr_line(line))
    ]
    results: dict[StatKey, OcrStatCandidate] = {}

    for line in normalized_lines:
        compact_line: str = _normalize_label_text(line)
        consumed: set[int] = set()

        for label, stat_key in _SORTED_EXACT_LABELS:
            if stat_key in results:
                continue

            index = compact_line.find(label)
            if index == -1:
                continue

            label_range = set(range(index, index + len(label)))
            if label_range & consumed:
                continue

            after: str = compact_line[index + len(label) :]
            values = _extract_numbers(after[:30])
            if not values:
                continue

            results[stat_key] = OcrStatCandidate(
                value=values[0],
                source=_SOURCE_EXACT,
            )
            consumed.update(label_range)

    if include_position:
        _fill_missing_stats_by_row_order(normalized_lines, results)

    return results

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

import winocr
from PIL import Image, ImageEnhance, ImageFilter, ImageGrab, ImageOps

from app.scripts.calculator_models import OVERALL_STAT_GRID_ROWS, STAT_SPECS, StatKey


def capture_screen_region(
    left: int,
    top: int,
    width: int,
    height: int,
) -> Image.Image:
    """화면 캡처 후 PLI 이미지 리턴"""

    bbox: tuple[int, int, int, int] = (left, top, left + width, top + height)
    return ImageGrab.grab(bbox=bbox, all_screens=True)


_TARGET_OCR_WIDTH: int = 1600
_ROW_Y_TOLERANCE: int = 10


def recognize_image(image: Image.Image) -> list[str]:
    """이미지로부터 텍스트 추출"""

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

    words: list[tuple[str, float, float]] = []
    for line in result.lines:
        for word in line.words:
            rect = word.bounding_rect
            words.append((word.text, rect.x, rect.y))

    if not words:
        return []

    y_tolerance: int = _ROW_Y_TOLERANCE * scale
    words.sort(key=lambda word: (word[2], word[1]))

    rows: list[list[tuple[str, float, float]]] = []
    current_row: list[tuple[str, float, float]] = [words[0]]
    current_y: float = words[0][2]

    for text, x, y in words[1:]:
        if abs(y - current_y) <= y_tolerance:
            current_row.append((text, x, y))
            continue
        rows.append(current_row)
        current_row = [(text, x, y)]
        current_y = y
    rows.append(current_row)

    lines_out: list[str] = []
    for row in rows:
        row.sort(key=lambda word: word[1])
        line_text: str = " ".join(word[0] for word in row).strip()
        if line_text:
            lines_out.append(line_text)

    return lines_out


@dataclass(frozen=True)
class OcrStatCandidate:
    value: float
    source: str
    agreement_count: int = 1
    attempt_count: int = 1


_NUMBER_PATTERN: re.Pattern[str] = re.compile(
    r"[+\-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
)
_PERCENT_TOKEN_PATTERN: re.Pattern[str] = re.compile(r"\([^)]{1,4}\)")
_LEADING_NOISE_PATTERN: re.Pattern[str] = re.compile(r"^[^0-9A-Za-z가-힣\-]+")
_SOURCE_EXACT: str = "exact"
_SOURCE_POSITION: str = "position"


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


def _score_candidate_group(
    candidates: list[OcrStatCandidate],
) -> tuple[int, int]:
    """Rank value groups by repeated agreement first, exact label matches second."""

    exact_count: int = sum(
        1 for candidate in candidates if candidate.source == _SOURCE_EXACT
    )
    return len(candidates), exact_count


def extract_stat_candidates_from_image(
    image: Image.Image,
) -> dict[StatKey, OcrStatCandidate]:
    variant_images: list[Image.Image] = _build_ocr_variant_images(image)
    variant_results: list[dict[StatKey, OcrStatCandidate]] = []

    for variant_image in variant_images:
        lines = recognize_image(variant_image)
        variant_results.append(parse_stat_candidates_from_text(lines))

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
            key=lambda candidate: 1 if candidate.source == _SOURCE_EXACT else 0,
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

    _fill_missing_stats_by_row_order(normalized_lines, results)
    return results

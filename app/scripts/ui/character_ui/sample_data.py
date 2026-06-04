"""캐릭터 창 UI 표시용 정적 샘플 데이터

목업(character_creator_mockup.html)의 JS 상수를 옮긴 표시 전용 값.
실제 모델/엔진 연동 전까지 화면을 채우는 임시 데이터이며, 저장·계산에는 쓰이지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# 중앙 알약 탭 정의 (장비 + 6개 스펙업 수단)
@dataclass(frozen=True)
class TabSpec:
    key: str
    label: str
    color: str


TABS: tuple[TabSpec, ...] = (
    TabSpec("title", "기본정보", "#e6e0f5"),
    TabSpec("equip", "장비", "#dcecfa"),
    TabSpec("dist", "스탯·단전 분배", "#d9f3e1"),
    TabSpec("shelf", "진열대", "#f8f5e8"),
    TabSpec("talisman", "부적", "#fde0ec"),
    TabSpec("yeongdan", "영단", "#e6e0f5"),
    TabSpec("hwan", "환", "#fef7d6"),
)


# 경지별 요구 레벨 / 단전 포인트
@dataclass(frozen=True)
class RealmSpec:
    label: str
    min_level: int
    danjeon: int


REALMS: tuple[RealmSpec, ...] = (
    RealmSpec("삼류", 0, 1),
    RealmSpec("이류", 30, 2),
    RealmSpec("일류", 60, 5),
    RealmSpec("절정", 90, 10),
    RealmSpec("초절정", 120, 17),
    RealmSpec("화경", 150, 26),
    RealmSpec("현경", 180, 37),
    RealmSpec("생사경", 200, 50),
)
DEFAULT_REALM_INDEX: int = 6  # 현경


# 우측 전체 스탯 (표시용 샘플). None 은 빈 셀
STAT_ROWS: tuple[tuple[str | None, str | None], ...] = (
    ("공격력", "12,480"), ("공격력(%)", "214%"),
    ("체력", "38,900"), ("체력(%)", "63%"),
    ("힘", "1,920"), ("힘(%)", "58%"),
    ("민첩", "1,540"), ("민첩(%)", "42%"),
    ("생명력", "2,210"), ("생명력(%)", "47%"),
    ("행운", "2,860"), ("행운(%)", "71%"),
    ("스킬 피해량(%)", "38%"), ("최종 공격력(%)", "24%"),
    ("치명타 확률(%)", "46%"), ("치명타 공격력(%)", "318%"),
    ("경험치 획득량(%)", "52%"), ("보스 공격력(%)", "29%"),
    ("드랍률(%)", "61%"), ("회피(%)", "12%"),
    ("물약 회복량(%)", "34%"), ("저항(%)", "18%"),
    (None, None), ("스킬속도(%)", "9%"),
)

OFFICIAL_POWER_TEXT: str = "152,430,000"


# 좌측 캐릭터 목록 (표시용 샘플)
@dataclass
class CharacterSummary:
    name: str
    meta: str


CHARACTERS: tuple[CharacterSummary, ...] = (
    CharacterSummary("메인 캐릭터", "Lv. 180 · 현경"),
    CharacterSummary("부캐릭터", "Lv. 150 · 화경"),
    CharacterSummary("새 캐릭터", "미입력"),
)


# 스탯 분배 4종 (키, 라벨, 효과 설명, 값) — 1포인트당 해당 스탯 +1
STAT_DIST: tuple[tuple[str, str, str, int], ...] = (
    ("strength", "힘", "힘 +1", 200),
    ("dexterity", "민첩", "민첩 +1", 180),
    ("vitality", "생명력", "생명력 +1", 160),
    ("luck", "행운", "행운 +1", 200),
)

# 단전 분배 3종 (키, 라벨, 효과 설명)
DANJEON_DIST: tuple[tuple[str, str, str, int], ...] = (
    ("upper", "상단전 (上)", "치명타 확률% +1 · 치명타 공격력% +1", 6),
    ("middle", "중단전 (中)", "공격력% +1", 5),
    ("lower", "하단전 (下)", "드랍률% +1.5 · 경험치 획득량% +0.5", 26),
)


# 칭호 스탯 선택지
TITLE_STATS: tuple[str, ...] = (
    "미설정", "공격력", "공격력(%)", "체력", "체력(%)", "힘", "힘(%)", "민첩", "민첩(%)",
    "생명력", "생명력(%)", "행운", "행운(%)", "스킬 피해량(%)", "최종 공격력(%)",
    "치명타 확률(%)", "치명타 공격력%", "경험치 획득량(%)", "보스 공격력(%)", "드랍률(%)",
    "회피(%)", "물약 회복량(%)", "저항(%)", "스킬속도(%)",
)


@dataclass
class TitleData:
    name: str
    equipped: bool
    slots: list[tuple[str | None, str]]  # (스탯 종류, 수치 문자열)


def default_titles() -> list[TitleData]:
    """표시용 칭호 샘플 (편집 시 변형되므로 매번 새 리스트 생성)"""

    return [
        TitleData(
            "무림맹주",
            True,
            [("공격력(%)", "12"), ("치명타 공격력%", "25"), ("보스 공격력(%)", "8")],
        ),
        TitleData(
            "수련의 길",
            False,
            [("힘(%)", "6"), (None, ""), (None, "")],
        ),
    ]


# 부적 등급 색상 (등급명 → 배경색)
TALISMAN_GRADE_COLORS: dict[str, str] = {
    "일반": "#9b9690",
    "고급": "#2a9d99",
    "희귀": "#0075de",
    "영웅": "#7b3ff2",
    "전설": "#dd5b00",
}

# 부적 종류 선택지 (콤보용)
TALISMAN_TEMPLATES: tuple[str, ...] = (
    "백아멸심화 (전설)", "혈화잔멸 (영웅)", "해일포말겁 (영웅)",
    "구인 (희귀)", "풍운뇌전 (고급)", "청명부 (일반)",
)


@dataclass
class TalismanData:
    name: str
    grade: str
    stat: str
    level: int
    per_level: float

    def value(self) -> float:
        """레벨 기준 부적 스탯 수치"""

        return round(self.per_level * self.level, 2)


def default_talismans() -> list[TalismanData]:
    """표시용 보유 부적 샘플"""

    return [
        TalismanData("백아멸심화", "전설", "치명타 공격력%", 14, 1.8),
        TalismanData("혈화잔멸", "영웅", "스킬 피해량%", 14, 1.0),
        TalismanData("해일포말겁", "영웅", "보스 공격력%", 6, 1.2),
        TalismanData("구인", "희귀", "경험치 획득량%", 0, 0.8),
    ]


DEFAULT_EQUIPPED_TALISMANS: tuple[int, ...] = (0, 1, 2)  # 보유 목록 인덱스


# 진열대 27종 이름
SHELF_NAMES: tuple[str, ...] = (
    "잔인한 가죽 장비", "잔인한 장인 장비", "잔인한 광휘 장비", "잔인한 설한 장비",
    "잔인한 송골 장비", "잔인한 투혼 장비", "잔인한 백비 장비", "잔인한 호공 장비",
    "고요한 청류 장비", "고요한 묵화 장비", "고요한 월광 장비", "고요한 적염 장비",
    "고요한 풍랑 장비", "고요한 운무 장비", "고요한 천뢰 장비", "고요한 빙백 장비",
    "비룡 무쌍 장비", "비룡 파천 장비", "비룡 절명 장비", "비룡 광폭 장비",
    "신화 여명 장비", "신화 황혼 장비", "신화 성라 장비", "신화 심연 장비",
    "전설 용린 장비", "전설 봉황 장비", "전설 기린 장비",
)

# 진열대 열 머리글 (제목, 효과 설명)
SHELF_COLUMNS: tuple[tuple[str, str], ...] = (
    ("투구", "경험치%"),
    ("갑옷", "공격력"),
    ("허리띠", "드랍률%"),
    ("신발", "공격력%"),
    ("세트효과", "힘·민·생·행%"),
)


def shelf_rows() -> list[tuple[str, list[float]]]:
    """진열대 행별 표시용 샘플 수치 (이름, [투구, 갑옷, 허리띠, 신발, 세트])"""

    rows: list[tuple[str, list[float]]] = []
    for i, name in enumerate(SHELF_NAMES):
        tier: int = max(0, 6 - i // 4)
        rows.append(
            (
                name,
                [
                    round(tier * 0.4, 1),
                    float(tier * 2),
                    round(tier * 0.4, 1),
                    round(tier * 0.6, 1),
                    round(tier * 0.4, 1),
                ],
            )
        )
    return rows


# 영단 16종 (이름, 효과, 색, 보유 수)
@dataclass
class ElixirData:
    name: str
    effect: str
    color: str
    count: int


def default_elixirs() -> list[ElixirData]:
    """표시용 영단 샘플"""

    return [
        ElixirData("황환단", "힘·민·생·행 +2", "#e8c95a", 10),
        ElixirData("녹환단", "생명력% +1, 힘% +1", "#7bbf6a", 0),
        ElixirData("자환단", "민첩% +1, 행운% +1", "#a86fd0", 10),
        ElixirData("청환단", "공격력 +3, 보스공격력% +1", "#4f9bd9", 2),
        ElixirData("적환단", "체력% +1, 체력 +15", "#d75a5a", 9),
        ElixirData("백환단", "경험치% +1, 드랍률% +1", "#dcdcdc", 10),
        ElixirData("흑환단", "물약회복량% +3, 저항% +3", "#4a4a4a", 0),
        ElixirData("옥환단", "공격력% +1", "#6fcabf", 6),
        ElixirData("은환단", "최종 공격력% +1", "#b8c0cc", 0),
        ElixirData("금환단", "스킬속도% +1", "#e0b94a", 8),
        ElixirData("매화단", "체력 +5, 치명타공격력% +3", "#e87fb0", 5),
        ElixirData("용혈단", "체력% +3, 생명력 +5", "#c0392b", 0),
        ElixirData("명월단", "행운 +3, 보스공격력% +1", "#cfd6e0", 0),
        ElixirData("태극단", "힘 +3, 보스공격력% +1", "#d98b3a", 0),
        ElixirData("천경단", "행운% +1, 공격력 +3", "#8a7fd0", 3),
        ElixirData("시공단", "경험치% +1, 물약회복량% +3", "#5ac0c0", 10),
    ]


ELIXIR_MAX: int = 10


# 환 13종 (이름, 효과, 색, 장착 여부)
@dataclass
class PillData:
    name: str
    effect: str
    color: str
    active: bool


def default_pills() -> list[PillData]:
    """표시용 환 샘플"""

    return [
        PillData("활생환", "생명력 +5", "#7bbf6a", True),
        PillData("황토환", "물약 회복력% +5", "#c8a04a", False),
        PillData("회생환", "힘% +3", "#d75a5a", True),
        PillData("명목환", "경험치% +4", "#9aa86a", False),
        PillData("천목환", "경험치% +6", "#7a9a5a", False),
        PillData("신목환", "경험치% +8", "#5a8a4a", True),
        PillData("강근환", "공격력 +10", "#c0392b", True),
        PillData("청심환", "민첩 +5", "#4f9bd9", True),
        PillData("대력환", "힘 +5", "#d98b3a", True),
        PillData("용력환", "스킬속도% +3", "#a86fd0", False),
        PillData("천세환", "공격력% +3", "#6fcabf", True),
        PillData("천심환", "치명타 확률% +2", "#e87fb0", True),
        PillData("만년환", "드랍률% +10", "#e0b94a", False),
    ]


# 잠재능력 / 추가능력 옵션 (투구·갑옷·허리띠·신발 전용)
POTENTIAL_OPTS: tuple[str, ...] = (
    "힘% (1~4)", "민첩% (1~4)", "생명력% (1~4)", "행운% (1~4)", "스킬속도% (1~4)",
    "저항% (1~4)", "치명타 공격력% (1~4)", "체력% (1~10)", "보스 공격력% (1~5)",
)
ADDITIONAL_OPTS: tuple[str, ...] = (
    "힘 (1~10)", "민첩 (1~10)", "생명력 (1~10)", "행운 (1~10)", "체력 (10~50)",
    "치명타 확률% (0.1~2)", "드랍률% (1~5)", "물약 회복량% (1~10)",
)


# 주문서 종류/단계 세트 (부위별)
@dataclass(frozen=True)
class ScrollSet:
    stats: tuple[str, ...]
    tiers: tuple[str, ...]


SCROLL_SETS: dict[str, ScrollSet] = {
    "armorH": ScrollSet(("힘", "민첩", "생명력", "행운", "행운%"), ("10%", "20%", "50%", "60%", "100%")),
    "armorA": ScrollSet(("힘", "민첩", "생명력", "행운", "힘%"), ("10%", "20%", "50%", "60%", "100%")),
    "armorB": ScrollSet(("힘", "민첩", "생명력", "행운", "생명력%"), ("10%", "20%", "50%", "60%", "100%")),
    "armorS": ScrollSet(("힘", "민첩", "생명력", "행운", "민첩%"), ("10%", "20%", "50%", "60%", "100%")),
    "weapon": ScrollSet(("공격력", "힘", "민첩", "공격력%"), ("10%", "20%", "40%", "50%", "60%", "100%")),
    "ring": ScrollSet(("힘", "민첩", "생명력", "행운"), ("10%", "20%", "50%", "60%", "100%")),
}


# 재련 가능 스탯 (부위/목걸이 종류별) — 계획 파일 기준
REFORGE_STATS: dict[str, tuple[str, ...]] = {
    "투구": ("행운", "행운%", "경험치%"),
    "갑옷": ("힘", "힘%", "경험치%"),
    "허리띠": ("생명력", "생명력%", "경험치%"),
    "신발": ("민첩", "민첩%", "경험치%"),
    "무기": ("공격력", "공격력%", "스킬속도%"),
    "적옥목걸이": ("생명력", "생명력%", "스킬속도%", "최종 공격력%"),
    "청옥목걸이": ("힘", "힘%", "스킬속도%", "최종 공격력%"),
    "녹옥목걸이": ("행운", "행운%", "스킬속도%", "최종 공격력%"),
}

NECKLACE_TYPES: tuple[str, ...] = ("적옥목걸이", "청옥목걸이", "녹옥목걸이")


# 장비 슬롯 정의 (완갑 미출시 제외, 9슬롯)
@dataclass
class EquipSlotData:
    key: str
    name: str
    type: str            # 부위명
    level: int
    reforge: bool        # 재련 가능 여부
    scroll: str | None   # 주문서 세트 키
    necklace_type: str | None  # 목걸이 종류 (목걸이만)
    grade: str           # 기본 / 찬란한
    base: list[tuple[str, float]]        # 방어구/무기 기본 스탯 (자동 표시)
    free_base: list[tuple[str, str]]     # 반지/귀걸이 자유 기본 스탯 (스탯, 값)
    tier: int = 1        # 장비 티어 (1~5)


# 장비 레벨 / 티어 선택지
EQUIP_LEVELS: tuple[int, ...] = (0, 20, 50, 80, 110, 150, 180)
EQUIP_TIERS: tuple[int, ...] = (1, 2, 3, 4, 5)


# 등급(기본/찬란한)을 갖는 부위
GRADE_TYPES: tuple[str, ...] = ("무기", "투구", "갑옷", "허리띠", "신발")
# 잠재/추가능력을 갖는 부위
POTENTIAL_TYPES: tuple[str, ...] = ("투구", "갑옷", "허리띠", "신발")


def default_equip_slots() -> list[EquipSlotData]:
    """표시용 장비 슬롯 샘플 (완갑 제외 9슬롯)"""

    return [
        EquipSlotData("helmet", "적령투구", "투구", 150, True, "armorH", None, "기본",
                      [("행운", 38), ("행운%", 17), ("공격력", 10), ("체력", 95), ("체력%", 2)], []),
        EquipSlotData("armor", "적령갑옷", "갑옷", 150, True, "armorA", None, "기본",
                      [("힘", 40), ("힘%", 15), ("공격력", 12), ("체력", 110), ("체력%", 3)], []),
        EquipSlotData("belt", "적령허리띠", "허리띠", 150, True, "armorB", None, "기본",
                      [("생명력", 36), ("생명력%", 14), ("공격력", 9), ("체력", 88)], []),
        EquipSlotData("shoes", "적령신발", "신발", 150, True, "armorS", None, "기본",
                      [("민첩", 34), ("민첩%", 13), ("공격력", 9), ("체력", 80)], []),
        EquipSlotData("weapon", "적령신검", "무기", 150, True, "weapon", None, "기본",
                      [("공격력", 320), ("힘", 30), ("민첩", 22), ("치명타 공격력%", 12)], []),
        EquipSlotData("ring1", "적령반지", "반지", 150, False, "ring", None, "기본",
                      [], [("행운", "24"), ("체력", "70"), ("행운%", "5")]),
        EquipSlotData("ring2", "적령반지", "반지", 150, False, "ring", None, "기본",
                      [], [("힘", "24"), ("체력", "70"), ("힘%", "5")]),
        EquipSlotData("necklace", "적옥목걸이", "목걸이", 150, True, None, "적옥목걸이", "기본",
                      [("공격력", 80), ("치명타 공격력%", 14), ("보스 공격력%", 8)], []),
        EquipSlotData("earring", "적령귀걸이", "귀걸이", 150, False, None, None, "기본",
                      [], [("공격력", "72"), ("스킬 피해량%", "10"), ("최종 공격력%", "5")]),
    ]


# 장비창 2열 배치 (좌: 무기/투구/갑옷/허리띠/신발, 우: 반지/반지/목걸이/귀걸이)
EQUIP_COL_LEFT: tuple[int, ...] = (4, 0, 1, 2, 3)
EQUIP_COL_RIGHT: tuple[int, ...] = (5, 6, 7, 8)

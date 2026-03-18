from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum

from app.scripts.registry.resource_registry import convert_resource_path


class StatKey(str, Enum):
    """계산기 전체 스탯 키"""

    # 공격력
    ATTACK = "attack"
    # 공격력%
    ATTACK_PERCENT = "attack_percent"
    # 체력
    HP = "hp"
    # 체력%
    HP_PERCENT = "hp_percent"
    # 힘
    STR = "str"
    # 힘%
    STR_PERCENT = "str_percent"
    # 민첩
    DEXTERITY = "dexterity"
    # 민첩%
    DEXTERITY_PERCENT = "dexterity_percent"
    # 생명력
    VITALITY = "vitality"
    # 생명력%
    VITALITY_PERCENT = "vitality_percent"
    # 행운
    LUCK = "luck"
    # 행운%
    LUCK_PERCENT = "luck_percent"
    # 스킬 피해량
    SKILL_DAMAGE_PERCENT = "skill_damage_percent"
    # 최종 공격력%
    FINAL_ATTACK_PERCENT = "final_attack_percent"
    # 치명타 확률
    CRIT_RATE_PERCENT = "crit_rate_percent"
    # 치명타 공격력%
    CRIT_DAMAGE_PERCENT = "crit_damage_percent"
    # 경험치 획득량
    EXP_PERCENT = "exp_percent"
    # 보스 공격력%
    BOSS_ATTACK_PERCENT = "boss_attack_percent"
    # 드랍률
    DROP_RATE_PERCENT = "drop_rate_percent"
    # 회피
    DODGE_PERCENT = "dodge_percent"
    # 물약 회복량
    POTION_HEAL_PERCENT = "potion_heal_percent"
    # 저항
    RESIST_PERCENT = "resist_percent"
    # 스킬속도
    SKILL_SPEED_PERCENT = "skill_speed_percent"


class PowerMetric(str, Enum):
    """계산기 전투력 종류"""

    BOSS = "boss"
    NORMAL = "normal"
    BOSS_DAMAGE = "boss_damage"
    NORMAL_DAMAGE = "normal_damage"
    OFFICIAL = "official"


class RealmTier(str, Enum):
    """경지 선택 값"""

    # 삼류
    THIRD_RATE = "third_rate"
    # 이류
    SECOND_RATE = "second_rate"
    # 일류
    FIRST_RATE = "first_rate"
    # 절정
    PEAK = "peak"
    # 초절정
    TRANSCENDENT = "transcendent"
    # 화경
    HWAGYEONG = "hwagyeong"
    # 현경
    HYEONGYEONG = "hyeongyeong"
    # 생사경
    LIFE_AND_DEATH = "life_and_death"


@dataclass(frozen=True, slots=True)
class RealmSpec:
    """경지별 요구 레벨과 단전 포인트"""

    label: str
    min_level: int
    danjeon_points: int


@dataclass(slots=True)
class OwnedTitle:
    """보유 칭호 정의"""

    name: str = ""
    stats: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "OwnedTitle":
        """저장 데이터로부터 보유 칭호 복원"""

        # 동적 스탯 라인 저장 구조 직접 복원
        raw_stats: object = data["stats"]
        if not isinstance(raw_stats, dict):
            raise TypeError("title stats must be a dict")

        stats: dict[str, float] = {
            str(key): float(value) for key, value in raw_stats.items()
        }

        return cls(
            name=str(data["name"]),
            stats=stats,
        )

    def to_dict(self) -> dict[str, object]:
        """보유 칭호 직렬화"""

        # 값 타입을 float로 고정 저장
        stats: dict[str, float] = {
            key: float(value) for key, value in self.stats.items()
        }
        data: dict[str, object] = {
            "name": self.name,
            "stats": stats,
        }
        return data


@dataclass(slots=True)
class OwnedTalisman:
    """보유 부적 인스턴스"""

    name: str = ""
    level: int = 1

    @classmethod
    def from_dict(cls, data: dict[str, int | str]) -> "OwnedTalisman":
        """저장 데이터로부터 보유 부적 복원"""

        name: str = str(data["name"])
        level: int = int(data["level"])
        return cls(name=name, level=level)

    def to_dict(self) -> dict[str, int | str]:
        """보유 부적 직렬화"""

        data: dict[str, int | str] = {
            "name": self.name,
            "level": self.level,
        }
        return data


@dataclass(frozen=True, slots=True)
class TalismanSpec:
    """부적 정의"""

    name: str
    stat_key: StatKey
    level_stats: dict[int, float]


@dataclass(slots=True)
class DistributionState:
    """스탯 분배 입력 상태"""

    # 현재 분배 포인트 상태
    strength: int = 0
    dexterity: int = 0
    vitality: int = 0
    luck: int = 0

    # 잠금 및 초기화 옵션 상태
    is_locked: bool = False
    use_reset: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, int | bool]) -> "DistributionState":
        """저장 데이터로부터 스탯 분배 상태 복원"""

        strength: int = int(data["strength"])
        dexterity: int = int(data["dexterity"])
        vitality: int = int(data["vitality"])
        luck: int = int(data["luck"])
        is_locked: bool = bool(data["is_locked"])
        use_reset: bool = bool(data["use_reset"])

        return cls(
            strength=strength,
            dexterity=dexterity,
            vitality=vitality,
            luck=luck,
            is_locked=is_locked,
            use_reset=use_reset,
        )

    def to_dict(self) -> dict[str, int | bool]:
        """스탯 분배 상태 직렬화"""

        data: dict[str, int | bool] = {
            "strength": self.strength,
            "dexterity": self.dexterity,
            "vitality": self.vitality,
            "luck": self.luck,
            "is_locked": self.is_locked,
            "use_reset": self.use_reset,
        }
        return data


@dataclass(slots=True)
class DanjeonState:
    """단전 입력 상태"""

    # 현재 단전 포인트 분배 상태
    upper: int = 0
    middle: int = 0
    lower: int = 0

    # 잠금 및 초기화 옵션 상태
    is_locked: bool = False
    use_reset: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, int | bool]) -> "DanjeonState":
        """저장 데이터로부터 단전 상태 복원"""

        upper: int = int(data["upper"])
        middle: int = int(data["middle"])
        lower: int = int(data["lower"])
        is_locked: bool = bool(data["is_locked"])
        use_reset: bool = bool(data["use_reset"])

        return cls(
            upper=upper,
            middle=middle,
            lower=lower,
            is_locked=is_locked,
            use_reset=use_reset,
        )

    def to_dict(self) -> dict[str, int | bool]:
        """단전 상태 직렬화"""

        data: dict[str, int | bool] = {
            "upper": self.upper,
            "middle": self.middle,
            "lower": self.lower,
            "is_locked": self.is_locked,
            "use_reset": self.use_reset,
        }
        return data


@dataclass(slots=True)
class EquippedState:
    """현재 장착 선택 상태"""

    equipped_title_id: str | None = None
    equipped_talisman_ids: tuple[str | None, str | None, str | None] = field(
        default_factory=lambda: (None, None, None)
    )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "EquippedState":
        """저장 데이터로부터 현재 장착 상태 복원"""

        raw_ids: object = data["equipped_talisman_ids"]
        if not isinstance(raw_ids, list):
            raise TypeError("equipped_talisman_ids must be a list")
        if len(raw_ids) != 3:
            raise ValueError("equipped_talisman_ids must have length 3")

        equipped_talisman_ids: tuple[str | None, str | None, str | None] = (
            str(raw_ids[0]) if raw_ids[0] is not None else None,
            str(raw_ids[1]) if raw_ids[1] is not None else None,
            str(raw_ids[2]) if raw_ids[2] is not None else None,
        )

        raw_title_id: object = data["equipped_title_id"]
        equipped_title_id: str | None = None
        if raw_title_id is not None:
            equipped_title_id = str(raw_title_id)

        return cls(
            equipped_title_id=equipped_title_id,
            equipped_talisman_ids=equipped_talisman_ids,
        )

    def to_dict(self) -> dict[str, object]:
        """현재 장착 상태 직렬화"""

        data: dict[str, object] = {
            "equipped_title_id": self.equipped_title_id,
            "equipped_talisman_ids": self.equipped_talisman_ids,
        }
        return data


@dataclass(slots=True)
class CalculatorPresetInput:
    """계산기 입력 데이터 묶음"""

    # 전체 스탯과 정보 저장
    overall_stats: dict[str, float] = field(default_factory=dict)
    level: int = 0
    realm_tier: RealmTier = RealmTier.THIRD_RATE
    selected_metric: PowerMetric = PowerMetric.BOSS_DAMAGE

    # 현재 분배 상태 저장
    distribution: DistributionState = field(default_factory=DistributionState)
    danjeon: DanjeonState = field(default_factory=DanjeonState)

    # 보유 선택지 및 현재 장착 상태 저장
    owned_titles: list[OwnedTitle] = field(default_factory=list)
    owned_talismans: list[OwnedTalisman] = field(default_factory=list)
    equipped_state: EquippedState = field(default_factory=EquippedState)
    custom_stat_changes: dict[str, float] = field(default_factory=dict)

    @classmethod
    def create_default(cls) -> "CalculatorPresetInput":
        """기본 계산기 입력 상태 생성"""

        # 전체 스탯 입력창 초기 렌더링용 0값 맵 구성
        overall_stats: dict[str, float] = {
            stat_key.value: 0.0 for stat_key in OVERALL_STAT_ORDER
        }
        custom_stat_changes: dict[str, float] = {
            stat_key.value: 0.0 for stat_key in OVERALL_STAT_ORDER
        }
        return cls(
            overall_stats=overall_stats,
            custom_stat_changes=custom_stat_changes,
        )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CalculatorPresetInput":
        """저장 데이터로부터 계산기 입력 상태 복원"""

        # 전체 스탯 키 복원
        raw_stats: object = data["overall_stats"]
        if not isinstance(raw_stats, dict):
            raise TypeError("overall_stats must be a dict")

        overall_stats: dict[str, float] = {
            stat_key.value: float(raw_stats[stat_key.value])
            for stat_key in OVERALL_STAT_ORDER
        }

        # 스탯 변화 복원
        custom_stat_changes_raw: object = data["custom_stat_changes"]
        if not isinstance(custom_stat_changes_raw, dict):
            raise TypeError("custom_stat_changes must be a dict")

        custom_stat_changes: dict[str, float] = {
            stat_key.value: float(custom_stat_changes_raw[stat_key.value])
            for stat_key in OVERALL_STAT_ORDER
        }

        # 경지/분배/보유 목록 구조 직접 복원
        realm_tier: RealmTier = RealmTier(str(data["realm_tier"]))
        selected_metric: PowerMetric = PowerMetric(str(data["selected_metric"]))

        distribution_data: object = data["distribution"]
        if not isinstance(distribution_data, dict):
            raise TypeError("distribution must be a dict")
        distribution: DistributionState = DistributionState.from_dict(distribution_data)

        danjeon_data: object = data["danjeon"]
        if not isinstance(danjeon_data, dict):
            raise TypeError("danjeon must be a dict")
        danjeon: DanjeonState = DanjeonState.from_dict(danjeon_data)

        # 칭호
        owned_titles_raw: object = data["owned_titles"]
        if not isinstance(owned_titles_raw, list):
            raise TypeError("owned_titles must be a list")

        owned_titles: list[OwnedTitle] = []
        for item in owned_titles_raw:
            if not isinstance(item, dict):
                raise TypeError("owned_titles items must be dict")

            owned_titles.append(OwnedTitle.from_dict(item))

        # 부적
        owned_talismans_raw: object = data["owned_talismans"]
        if not isinstance(owned_talismans_raw, list):
            raise TypeError("owned_talismans must be a list")

        owned_talismans: list[OwnedTalisman] = []
        for item in owned_talismans_raw:
            if not isinstance(item, dict):
                raise TypeError("owned_talismans items must be dict")

            owned_talismans.append(OwnedTalisman.from_dict(item))

        # 장착 상태
        equipped_data: object = data["equipped"]
        if not isinstance(equipped_data, dict):
            raise TypeError("equipped must be a dict")
        equipped_state: EquippedState = EquippedState.from_dict(equipped_data)

        level: int = int(data["level"])  # type: ignore

        return cls(
            overall_stats=overall_stats,
            level=level,
            realm_tier=realm_tier,
            selected_metric=selected_metric,
            distribution=distribution,
            danjeon=danjeon,
            owned_titles=owned_titles,
            owned_talismans=owned_talismans,
            equipped_state=equipped_state,
            custom_stat_changes=custom_stat_changes,
        )

    def to_dict(self) -> dict[str, object]:
        """계산기 입력 상태 직렬화"""

        data: dict[str, object] = {
            "overall_stats": {
                key: float(value) for key, value in self.overall_stats.items()
            },
            "level": self.level,
            "realm_tier": self.realm_tier.value,
            "selected_metric": self.selected_metric.value,
            "distribution": self.distribution.to_dict(),
            "danjeon": self.danjeon.to_dict(),
            "owned_titles": [title.to_dict() for title in self.owned_titles],
            "owned_talismans": [
                talisman.to_dict() for talisman in self.owned_talismans
            ],
            "equipped_state": self.equipped_state.to_dict(),
            "custom_stat_changes": {
                key: float(value) for key, value in self.custom_stat_changes.items()
            },
        }
        return data


# 전체 스탯 UI 배치 순서
OVERALL_STAT_GRID_ROWS: tuple[tuple[StatKey | None, StatKey | None], ...] = (
    (StatKey.ATTACK, StatKey.ATTACK_PERCENT),
    (StatKey.HP, StatKey.HP_PERCENT),
    (StatKey.STR, StatKey.STR_PERCENT),
    (StatKey.DEXTERITY, StatKey.DEXTERITY_PERCENT),
    (StatKey.VITALITY, StatKey.VITALITY_PERCENT),
    (StatKey.LUCK, StatKey.LUCK_PERCENT),
    (StatKey.SKILL_DAMAGE_PERCENT, StatKey.FINAL_ATTACK_PERCENT),
    (StatKey.CRIT_RATE_PERCENT, StatKey.CRIT_DAMAGE_PERCENT),
    (StatKey.EXP_PERCENT, StatKey.BOSS_ATTACK_PERCENT),
    (StatKey.DROP_RATE_PERCENT, StatKey.DODGE_PERCENT),
    (StatKey.POTION_HEAL_PERCENT, StatKey.RESIST_PERCENT),
    (None, StatKey.SKILL_SPEED_PERCENT),
)


# 저장 및 순회 시 사용할 전체 스탯 순서 고정
OVERALL_STAT_ORDER: tuple[StatKey, ...] = tuple(
    stat_key
    for row in OVERALL_STAT_GRID_ROWS
    for stat_key in row
    if stat_key is not None
)


# 계산기 스탯 표시 스펙 고정
STAT_SPECS: dict[StatKey, str] = {
    StatKey.ATTACK: "공격력",
    StatKey.ATTACK_PERCENT: "공격력(%)",
    StatKey.HP: "체력",
    StatKey.HP_PERCENT: "체력(%)",
    StatKey.STR: "힘",
    StatKey.STR_PERCENT: "힘(%)",
    StatKey.DEXTERITY: "민첩",
    StatKey.DEXTERITY_PERCENT: "민첩(%)",
    StatKey.VITALITY: "생명력",
    StatKey.VITALITY_PERCENT: "생명력(%)",
    StatKey.LUCK: "행운",
    StatKey.LUCK_PERCENT: "행운(%)",
    StatKey.SKILL_DAMAGE_PERCENT: "스킬 피해량(%)",
    StatKey.FINAL_ATTACK_PERCENT: "최종 공격력(%)",
    StatKey.CRIT_RATE_PERCENT: "치명타 확률(%)",
    StatKey.CRIT_DAMAGE_PERCENT: "치명타 공격력(%)",
    StatKey.EXP_PERCENT: "경험치 획득량(%)",
    StatKey.BOSS_ATTACK_PERCENT: "보스 공격력(%)",
    StatKey.DROP_RATE_PERCENT: "드랍률(%)",
    StatKey.DODGE_PERCENT: "회피(%)",
    StatKey.POTION_HEAL_PERCENT: "물약 회복량(%)",
    StatKey.RESIST_PERCENT: "저항(%)",
    StatKey.SKILL_SPEED_PERCENT: "스킬속도(%)",
}


def get_stat_label(stat_key: StatKey | str) -> str:
    """스탯 키 표시 이름 반환"""

    resolved_stat_key: StatKey = StatKey(str(stat_key))
    return STAT_SPECS[resolved_stat_key]


# 경지 목록과 단전 포인트
REALM_TIER_SPECS: dict[RealmTier, RealmSpec] = {
    RealmTier.THIRD_RATE: RealmSpec(
        label="삼류",
        min_level=0,
        danjeon_points=1,
    ),
    RealmTier.SECOND_RATE: RealmSpec(
        label="이류",
        min_level=30,
        danjeon_points=2,
    ),
    RealmTier.FIRST_RATE: RealmSpec(
        label="일류",
        min_level=60,
        danjeon_points=5,
    ),
    RealmTier.PEAK: RealmSpec(
        label="절정",
        min_level=90,
        danjeon_points=10,
    ),
    RealmTier.TRANSCENDENT: RealmSpec(
        label="초절정",
        min_level=120,
        danjeon_points=17,
    ),
    RealmTier.HWAGYEONG: RealmSpec(
        label="화경",
        min_level=150,
        danjeon_points=26,
    ),
    RealmTier.HYEONGYEONG: RealmSpec(
        label="현경",
        min_level=180,
        danjeon_points=37,
    ),
    RealmTier.LIFE_AND_DEATH: RealmSpec(
        label="생사경",
        min_level=200,
        danjeon_points=50,
    ),
}


def _load_talismans() -> tuple[TalismanSpec, ...]:
    """부적 목록 로드"""

    resource_path: str = convert_resource_path("resources\\data\\talisman_data.json")
    with open(resource_path, "r", encoding="utf-8") as file:
        payload: dict[str, object] = json.load(file)

    raw_talismans: object = payload["talismans"]
    if not isinstance(raw_talismans, list):
        raise TypeError("talismans must be a list")

    specs: list[TalismanSpec] = []
    for raw_talisman in raw_talismans:
        if not isinstance(raw_talisman, dict):
            raise TypeError("talisman item must be a dict")

        specs.append(
            TalismanSpec(
                name=str(raw_talisman["name"]),
                stat_key=StatKey(str(raw_talisman["stat_key"])),
                level_stats={
                    int(level): float(value)
                    for level, value in raw_talisman["level_stats"].items()
                },
            )
        )

    return tuple(specs)


# 부적 정의 전체
TALISMAN_SPECS: tuple[TalismanSpec, ...] = _load_talismans()

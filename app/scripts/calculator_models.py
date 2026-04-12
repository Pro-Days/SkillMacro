from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

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


class TalismanGrade(str, Enum):
    """부적 등급 값"""

    # 일반 등급
    NORMAL = "일반"
    # 고급 등급
    ADVANCED = "고급"
    # 희귀 등급
    RARE = "희귀"
    # 영웅 등급
    HEROIC = "영웅"
    # 전설 등급
    LEGENDARY = "전설"


@dataclass(frozen=True, slots=True)
class RealmSpec:
    """경지별 요구 레벨과 단전 포인트"""

    label: str
    min_level: int
    danjeon_points: int


TITLE_STAT_SLOT_COUNT: int = 3


@dataclass(slots=True)
class OwnedTitleStat:
    """보유 칭호 스탯 슬롯"""

    stat_key: StatKey
    value: float

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "OwnedTitleStat":
        """저장 데이터로부터 칭호 스탯 슬롯 복원"""

        # 스탯 키와 수치 직접 복원
        stat_key: StatKey = StatKey(str(data["stat_key"]))
        value: float = float(data["value"])  # type: ignore
        return cls(stat_key=stat_key, value=value)

    def to_dict(self) -> dict[str, object]:
        """칭호 스탯 슬롯 직렬화"""

        # 직렬화 시 enum 값을 문자열로 고정 저장
        data: dict[str, object] = {
            "stat_key": self.stat_key.value,
            "value": float(self.value),
        }
        return data


@dataclass(slots=True)
class OwnedTitle:
    """보유 칭호 정의"""

    name: str = ""
    stats: list[OwnedTitleStat | None] = field(
        default_factory=lambda: [None] * TITLE_STAT_SLOT_COUNT
    )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "OwnedTitle":
        """저장 데이터로부터 보유 칭호 복원"""

        # 3칸 고정 스탯 슬롯 구조 직접 복원
        raw_stats: object = data["stats"]
        if not isinstance(raw_stats, list):
            raise TypeError("title stats must be a list")

        if len(raw_stats) != TITLE_STAT_SLOT_COUNT:
            raise ValueError("title stats must have exactly 3 slots")

        stats: list[OwnedTitleStat | None] = []
        for raw_stat in raw_stats:
            if raw_stat is None:
                stats.append(None)
                continue

            if not isinstance(raw_stat, dict):
                raise TypeError("title stat slot must be dict or null")

            stats.append(OwnedTitleStat.from_dict(raw_stat))

        return cls(
            name=str(data["name"]),
            stats=stats,
        )

    def to_dict(self) -> dict[str, object]:
        """보유 칭호 직렬화"""

        # 3칸 고정 슬롯 기준 null 포함 직렬화
        stats: list[dict[str, object] | None] = []
        for stat_slot in self.stats:
            if stat_slot is None:
                stats.append(None)
                continue

            stats.append(stat_slot.to_dict())

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
    grade: TalismanGrade
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
class TargetDistributionState:
    """목표 분배 입력 상태"""

    # 목표 분배 포인트 상태
    strength: int = 0
    dexterity: int = 0
    vitality: int = 0
    luck: int = 0

    # 최소분배 옵션 상태
    is_minimum: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, int | bool]) -> "TargetDistributionState":
        """저장 데이터로부터 목표 분배 상태 복원"""

        # 목표 분배 포인트 복원
        strength: int = int(data["strength"])
        dexterity: int = int(data["dexterity"])
        vitality: int = int(data["vitality"])
        luck: int = int(data["luck"])

        # 최소분배 옵션 복원
        is_minimum: bool = bool(data["is_minimum"])

        return cls(
            strength=strength,
            dexterity=dexterity,
            vitality=vitality,
            luck=luck,
            is_minimum=is_minimum,
        )

    def to_dict(self) -> dict[str, int | bool]:
        """목표 분배 상태 직렬화"""

        # 목표 분배 상태 저장 구조 구성
        data: dict[str, int | bool] = {
            "strength": self.strength,
            "dexterity": self.dexterity,
            "vitality": self.vitality,
            "luck": self.luck,
            "is_minimum": self.is_minimum,
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

    equipped_title_name: str | None = None
    equipped_talisman_names: list[str] = field(default_factory=lambda: [])

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "EquippedState":
        """저장 데이터로부터 현재 장착 상태 복원"""

        raw_names: object = data["equipped_talisman_names"]
        if not isinstance(raw_names, list):
            raise TypeError("equipped_talisman_names must be a list")

        equipped_talisman_names: list[str] = [str(item) for item in raw_names]

        raw_title_name: object = data["equipped_title_name"]
        equipped_title_name: str | None = None
        if raw_title_name is not None:
            equipped_title_name = str(raw_title_name)

        return cls(
            equipped_title_name=equipped_title_name,
            equipped_talisman_names=equipped_talisman_names,
        )

    def to_dict(self) -> dict[str, object]:
        """현재 장착 상태 직렬화"""

        data: dict[str, object] = {
            "equipped_title_name": self.equipped_title_name,
            "equipped_talisman_names": self.equipped_talisman_names,
        }
        return data


@dataclass(slots=True)
class BaseStats:
    """계산기 기준 원시 스탯 맵"""

    values: dict[str, float] = field(default_factory=dict)

    @classmethod
    def create_default(cls) -> "BaseStats":
        """기본 베이스 스탯 생성"""

        # 전체 스탯 기본값 맵 구성
        default_values: dict[str, float] = {
            stat_key.value: 0.0 for stat_key in OVERALL_STAT_ORDER
        }

        # 치명타 공격력 기본 입력값 반영
        default_values[StatKey.CRIT_DAMAGE_PERCENT.value] = 110.0
        return cls(values=default_values)

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "BaseStats":
        """저장 데이터로부터 베이스 스탯 복원"""

        return cls(
            values={
                stat_key.value: data[stat_key.value] for stat_key in OVERALL_STAT_ORDER
            }
        )

    def to_dict(self) -> dict[str, float]:
        """베이스 스탯 직렬화"""

        return {key: value for key, value in self.values.items()}

    @classmethod
    def from_stat_map(cls, data: dict[StatKey, float]) -> "BaseStats":
        """enum 키 기반 스탯 맵으로부터 베이스 스탯 구성"""

        return cls(
            values={
                stat_key.value: data.get(stat_key, 0.0)
                for stat_key in OVERALL_STAT_ORDER
            }
        )

    def to_stat_map(self) -> dict[StatKey, float]:
        """enum 키 기반 베이스 스탯 맵 반환"""

        return {
            stat_key: self.values[stat_key.value] for stat_key in OVERALL_STAT_ORDER
        }

    def with_changes(
        self,
        changes: dict[StatKey, float] | None,
        is_add: bool = True,
    ) -> "BaseStats":
        """조정이 반영된 새 베이스 스탯 반환"""

        next_values: dict[StatKey, float] = self.to_stat_map()

        if changes is None:
            return self

        for stat_key, value in changes.items():
            next_values[stat_key] = next_values[stat_key] + (
                value * (1.0 if is_add else -1.0)
            )

        return type(self).from_stat_map(next_values)

    def resolve(
        self,
        stat_changes: dict[StatKey, float] | None = None,
    ) -> "FinalStats":
        """베이스 스탯을 최종 스탯으로 변환"""

        # enum 키 상수를 로컬 변수로 캐시하여 반복 descriptor 접근 제거
        _STR: StatKey = StatKey.STR
        _STR_PERCENT: StatKey = StatKey.STR_PERCENT
        _DEXTERITY: StatKey = StatKey.DEXTERITY
        _DEXTERITY_PERCENT: StatKey = StatKey.DEXTERITY_PERCENT
        _VITALITY: StatKey = StatKey.VITALITY
        _VITALITY_PERCENT: StatKey = StatKey.VITALITY_PERCENT
        _LUCK: StatKey = StatKey.LUCK
        _LUCK_PERCENT: StatKey = StatKey.LUCK_PERCENT
        _ATTACK: StatKey = StatKey.ATTACK
        _ATTACK_PERCENT: StatKey = StatKey.ATTACK_PERCENT
        _HP: StatKey = StatKey.HP
        _HP_PERCENT: StatKey = StatKey.HP_PERCENT
        _CRIT_RATE_PERCENT: StatKey = StatKey.CRIT_RATE_PERCENT
        _CRIT_DAMAGE_PERCENT: StatKey = StatKey.CRIT_DAMAGE_PERCENT
        _DROP_RATE_PERCENT: StatKey = StatKey.DROP_RATE_PERCENT
        _EXP_PERCENT: StatKey = StatKey.EXP_PERCENT
        _DODGE_PERCENT: StatKey = StatKey.DODGE_PERCENT
        _POTION_HEAL_PERCENT: StatKey = StatKey.POTION_HEAL_PERCENT
        # stat_changes=None 최적화: with_changes + to_stat_map 우회
        if stat_changes is None:
            raw: dict[str, float] = self.values
            changed_stats: dict[StatKey, float] = {
                stat_key: raw.get(stat_key.value, 0.0)
                for stat_key in OVERALL_STAT_ORDER
            }
        else:
            changed_stats = self.with_changes(stat_changes).to_stat_map()

        # 스탯% 적용
        final_strength: float = changed_stats[_STR] * (
            1.0 + (changed_stats[_STR_PERCENT] * 0.01)
        )
        final_dexterity: float = changed_stats[_DEXTERITY] * (
            1.0 + (changed_stats[_DEXTERITY_PERCENT] * 0.01)
        )
        final_vitality: float = changed_stats[_VITALITY] * (
            1.0 + (changed_stats[_VITALITY_PERCENT] * 0.01)
        )
        final_luck: float = changed_stats[_LUCK] * (
            1.0 + (changed_stats[_LUCK_PERCENT] * 0.01)
        )

        resolved_values: dict[StatKey, float] = changed_stats.copy()

        resolved_values[_STR] = final_strength
        resolved_values[_DEXTERITY] = final_dexterity
        resolved_values[_VITALITY] = final_vitality
        resolved_values[_LUCK] = final_luck

        attack_percent: float = changed_stats[_ATTACK_PERCENT] + (final_dexterity * 0.3)
        resolved_values[_ATTACK_PERCENT] = attack_percent

        resolved_values[_ATTACK] = (changed_stats[_ATTACK] + final_strength) * (
            1.0 + (attack_percent * 0.01)
        )

        resolved_values[_HP] = (changed_stats[_HP] + (final_vitality * 5.0)) * (
            1.0 + (changed_stats[_HP_PERCENT] * 0.01)
        )

        resolved_values[_CRIT_RATE_PERCENT] = changed_stats[_CRIT_RATE_PERCENT] + (
            final_dexterity * 0.05
        )

        resolved_values[_CRIT_DAMAGE_PERCENT] = changed_stats[_CRIT_DAMAGE_PERCENT] + (
            final_strength * 0.1
        )

        resolved_values[_DROP_RATE_PERCENT] = changed_stats[_DROP_RATE_PERCENT] + (
            final_luck * 0.2
        )

        resolved_values[_EXP_PERCENT] = changed_stats[_EXP_PERCENT] + (final_luck * 0.2)

        resolved_values[_DODGE_PERCENT] = changed_stats[_DODGE_PERCENT] + (
            final_vitality * 0.03
        )

        resolved_values[_POTION_HEAL_PERCENT] = changed_stats[_POTION_HEAL_PERCENT] + (
            final_vitality * 0.5
        )

        return FinalStats(values=resolved_values)


@dataclass(frozen=True, slots=True)
class FinalStats:
    """2차 효과가 적용된 최종 스탯"""

    values: dict[StatKey, float]

    def __post_init__(self) -> None:
        """최종 스탯 값을 소수 둘째 자리까지 표시하게 정규화"""

        rounded_values: dict[StatKey, float] = {
            stat_key: round(value, 2) for stat_key, value in self.values.items()
        }

        object.__setattr__(self, "values", rounded_values)


@dataclass(slots=True)
class CustomPowerFormula:
    """사용자 정의 전투력 공식"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    formula: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CustomPowerFormula":
        """저장 데이터로부터 사용자 정의 전투력 공식 복원"""

        # 공식 식별자와 표시명, 수식 문자열 직접 복원
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            formula=str(data["formula"]),
        )

    def to_dict(self) -> dict[str, object]:
        """사용자 정의 전투력 공식 직렬화"""

        # 현재 공식 상태를 저장 가능한 원시 딕셔너리로 변환
        data: dict[str, object] = {
            "id": self.id,
            "name": self.name,
            "formula": self.formula,
        }
        return data


@dataclass(slots=True)
class CalculatorPresetInput:
    """계산기 입력 데이터 묶음"""

    # 기준 원시 스탯과 정보 저장
    base_stats: BaseStats = field(default_factory=BaseStats.create_default)
    level: int = 0
    realm_tier: RealmTier = RealmTier.THIRD_RATE
    selected_formula_id: str = PowerMetric.BOSS_DAMAGE.value

    # 현재 분배 상태 저장
    distribution: DistributionState = field(default_factory=DistributionState)
    target_distribution: TargetDistributionState = field(
        default_factory=TargetDistributionState
    )
    danjeon: DanjeonState = field(default_factory=DanjeonState)

    # 보유 선택지 및 현재 장착 상태 저장
    owned_titles: list[OwnedTitle] = field(default_factory=list)
    owned_talismans: list[OwnedTalisman] = field(default_factory=list)
    equipped_state: EquippedState = field(default_factory=EquippedState)
    custom_stat_changes: dict[str, float] = field(default_factory=dict)

    @classmethod
    def create_default(cls) -> "CalculatorPresetInput":
        """기본 계산기 입력 상태 생성"""

        custom_stat_changes: dict[str, float] = {
            stat_key.value: 0.0 for stat_key in OVERALL_STAT_ORDER
        }
        return cls(
            base_stats=BaseStats.create_default(),
            custom_stat_changes=custom_stat_changes,
            selected_formula_id=PowerMetric.BOSS_DAMAGE.value,
        )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CalculatorPresetInput":
        """저장 데이터로부터 계산기 입력 상태 복원"""

        # 베이스 스탯 키 복원
        raw_base_stats: object = data["base_stats"]
        if not isinstance(raw_base_stats, dict):
            raise TypeError("base_stats must be a dict")

        base_stats: BaseStats = BaseStats.from_dict(raw_base_stats)

        # 스탯 변화 복원
        custom_stat_changes_raw: object = data["custom_stat_changes"]
        if not isinstance(custom_stat_changes_raw, dict):
            raise TypeError("custom_stat_changes must be a dict")

        custom_stat_changes: dict[str, float] = {
            stat_key.value: float(custom_stat_changes_raw[stat_key.value])
            for stat_key in OVERALL_STAT_ORDER
        }

        # 경지/선택 공식/분배 구조 직접 복원
        realm_tier: RealmTier = RealmTier(str(data["realm_tier"]))
        selected_formula_id: str = str(data["selected_formula_id"])

        distribution_data: object = data["distribution"]
        if not isinstance(distribution_data, dict):
            raise TypeError("distribution must be a dict")
        distribution: DistributionState = DistributionState.from_dict(distribution_data)

        target_distribution_data: object = data.get("target_distribution")
        if target_distribution_data is not None and isinstance(
            target_distribution_data, dict
        ):
            target_distribution: TargetDistributionState = (
                TargetDistributionState.from_dict(target_distribution_data)
            )
        else:
            target_distribution = TargetDistributionState()

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
        equipped_data: object = data["equipped_state"]
        if not isinstance(equipped_data, dict):
            raise TypeError("equipped_state must be a dict")
        equipped_state: EquippedState = EquippedState.from_dict(equipped_data)

        level: int = int(data["level"])  # type: ignore

        return cls(
            base_stats=base_stats,
            level=level,
            realm_tier=realm_tier,
            selected_formula_id=selected_formula_id,
            distribution=distribution,
            target_distribution=target_distribution,
            danjeon=danjeon,
            owned_titles=owned_titles,
            owned_talismans=owned_talismans,
            equipped_state=equipped_state,
            custom_stat_changes=custom_stat_changes,
        )

    def to_dict(self) -> dict[str, object]:
        """계산기 입력 상태 직렬화"""

        data: dict[str, object] = {
            "base_stats": self.base_stats.to_dict(),
            "level": self.level,
            "realm_tier": self.realm_tier.value,
            "selected_formula_id": self.selected_formula_id,
            "distribution": self.distribution.to_dict(),
            "target_distribution": self.target_distribution.to_dict(),
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


# 전체 스탯 순서 고정
OVERALL_STAT_ORDER: tuple[StatKey, ...] = tuple(
    stat_key
    for row in OVERALL_STAT_GRID_ROWS
    for stat_key in row
    if stat_key is not None
)


# 계산기 스탯 표시 스펙
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

    # enum 인스턴스 직접 전달 경로 우선 처리
    if isinstance(stat_key, StatKey):
        resolved_stat_key: StatKey = stat_key

    # 문자열 기반 저장값 전달 경로 정규화
    else:
        resolved_stat_key = StatKey(stat_key)

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

        # 부적 등급과 스탯 정의 동시 복원
        specs.append(
            TalismanSpec(
                name=str(raw_talisman["name"]),
                grade=TalismanGrade(str(raw_talisman["grade"])),
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

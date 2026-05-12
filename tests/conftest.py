from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Callable

import pytest

# pytest 실행 위치와 무관하게 프로젝트 루트를 import 경로에 보장
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.scripts.calculator_models import (
    BaseStats,
    CalculatorPresetInput,
    DanjeonState,
    DistributionState,
    EquippedState,
    OVERALL_STAT_ORDER,
    OwnedTalisman,
    OwnedTitle,
    PowerMetric,
    RealmTier,
    StatKey,
    TargetDistributionState,
)
from app.scripts.macro_models import (
    LinkKeyType,
    LinkSkill,
    LinkUseType,
    MacroPreset,
    MacroSettings,
    MacroSkills,
    PresetInfo,
    SkillUsageSetting,
)
from app.scripts.registry.server_registry import ServerSpec
from app.scripts.registry.skill_registry import ScrollDef, SkillDef, SkillRegistry


# 테스트용 합성 서버 식별자
SYNTHETIC_SERVER_ID: str = "test_server"


def _make_levels(base_damage: float) -> dict[int, float]:
    """1~15 레벨 데미지 계수 단조 증가 시퀀스 구성"""

    # 레벨별로 0.1씩 증가하는 단순 계수 테이블
    return {level: round(base_damage + (level - 1) * 0.1, 4) for level in range(1, 16)}


def build_synthetic_server(
    scroll_count: int = 7,
    base_cooltime: float = 4.0,
    cooltime_step: float = 0.5,
    base_damage: float = 2.0,
    damage_step: float = 0.2,
    base_target_count: int = 1,
    target_count_step: int = 1,
) -> ServerSpec:
    """합성 ServerSpec 생성

    scroll_count개의 무공비급, 각 무공비급당 2개 스킬, 총 (scroll_count*2)개 스킬을 가진다.
    스킬별 cooltime, damage, target_count는 식별 가능한 단조 증가 시퀀스로 구성.
    """

    skills: dict[str, SkillDef] = {}
    scrolls: dict[str, ScrollDef] = {}
    skill_to_scroll: dict[str, str] = {}

    # 무공비급/스킬 ID 규칙: scroll_<i> 무공비급에 [scroll_<i>_skill_0, scroll_<i>_skill_1]
    for scroll_index in range(scroll_count):
        skill_a_id: str = f"builtin:{SYNTHETIC_SERVER_ID}:scroll_{scroll_index}_a"
        skill_b_id: str = f"builtin:{SYNTHETIC_SERVER_ID}:scroll_{scroll_index}_b"

        skills[skill_a_id] = SkillDef(
            id=skill_a_id,
            server_id=SYNTHETIC_SERVER_ID,
            name=f"S{scroll_index}A",
            cooltime=base_cooltime + scroll_index * cooltime_step,
            target_count=base_target_count + (scroll_index % 5) * target_count_step,
            levels=_make_levels(base_damage + scroll_index * damage_step),
        )
        skills[skill_b_id] = SkillDef(
            id=skill_b_id,
            server_id=SYNTHETIC_SERVER_ID,
            name=f"S{scroll_index}B",
            cooltime=base_cooltime + scroll_index * cooltime_step + 1.0,
            target_count=base_target_count + ((scroll_index + 2) % 5) * target_count_step,
            levels=_make_levels(base_damage + scroll_index * damage_step + 0.05),
        )

        scroll_id: str = f"builtin:{SYNTHETIC_SERVER_ID}:scroll_{scroll_index}"
        scrolls[scroll_id] = ScrollDef(
            id=scroll_id,
            server_id=SYNTHETIC_SERVER_ID,
            name=f"Scroll{scroll_index}",
            skills=(skill_a_id, skill_b_id),
        )
        skill_to_scroll[skill_a_id] = scroll_id
        skill_to_scroll[skill_b_id] = scroll_id

    registry: SkillRegistry = SkillRegistry(
        _skills=skills,
        _scrolls=scrolls,
        _skill_to_scroll=skill_to_scroll,
    )

    return ServerSpec(
        id=SYNTHETIC_SERVER_ID,
        scroll_slot_count=scroll_count,
        skill_line_count=2,
        skills_per_scroll=2,
        max_skill_level=15,
        skill_registry=registry,
    )


def build_full_equipped_preset(
    server_spec: ServerSpec,
    scroll_levels: int | None = None,
) -> MacroPreset:
    """모든 슬롯이 채워진 풀 장착 프리셋 구성

    14개 스킬 전부 우선순위 0, use_skill=True 기본 상태.
    """

    scroll_ids: list[str] = server_spec.skill_registry.get_all_scroll_ids()
    if len(scroll_ids) != server_spec.scroll_slot_count:
        raise ValueError(
            "synthetic server scroll count must match scroll_slot_count"
        )

    # 무공비급 순서를 7개 슬롯에 그대로 배치
    equipped_scrolls: list[str] = list(scroll_ids)

    # 하단 14칸에 각 무공비급의 두 스킬을 line_index 0/1로 배치
    placed_skills: list[str] = [""] * (server_spec.scroll_slot_count * 2)
    for scroll_index, scroll_id in enumerate(scroll_ids):
        scroll_def: ScrollDef = server_spec.skill_registry.get_scroll(scroll_id)
        placed_skills[scroll_index * 2 + 0] = scroll_def.skills[0]
        placed_skills[scroll_index * 2 + 1] = scroll_def.skills[1]

    # 무공비급 슬롯과 1대1 매핑되는 스킬 단축키 (테스트 식별용 임의 키)
    skill_keys: list[str] = [
        str(2 + i) for i in range(server_spec.scroll_slot_count)
    ]

    usage_settings: dict[str, SkillUsageSetting] = {
        skill_id: SkillUsageSetting()
        for skill_id in server_spec.skill_registry.get_all_skill_ids()
    }

    level_per_scroll: int = scroll_levels if scroll_levels is not None else 1
    info: PresetInfo = PresetInfo(
        scroll_levels={scroll_id: level_per_scroll for scroll_id in scroll_ids},
        calculator=CalculatorPresetInput.create_default(),
    )

    return MacroPreset(
        name="test",
        skills=MacroSkills(
            equipped_scrolls=equipped_scrolls,
            placed_skills=placed_skills,
            skill_keys=skill_keys,
        ),
        settings=MacroSettings(
            server_id=server_spec.id,
            custom_delay=300,
            use_custom_delay=False,
            custom_cooltime_reduction=0,
            use_custom_cooltime_reduction=False,
        ),
        usage_settings=usage_settings,
        link_skills=[],
        info=info,
    )


def make_calculator_input(
    level: int = 100,
    realm_tier: RealmTier = RealmTier.SECOND_RATE,
    distribution: DistributionState | None = None,
    danjeon: DanjeonState | None = None,
    selected_formula_id: str = PowerMetric.BOSS_DAMAGE.value,
    base_stats: BaseStats | None = None,
) -> CalculatorPresetInput:
    """테스트용 CalculatorPresetInput 구성"""

    # 호출자 인자 우선, 없으면 기본 상태 사용
    return CalculatorPresetInput(
        base_stats=base_stats if base_stats is not None else BaseStats.create_default(),
        level=level,
        realm_tier=realm_tier,
        selected_formula_id=selected_formula_id,
        distribution=distribution if distribution is not None else DistributionState(),
        target_distribution=TargetDistributionState(),
        danjeon=danjeon if danjeon is not None else DanjeonState(),
        owned_titles=[],
        owned_talismans=[],
        equipped_state=EquippedState(),
        custom_stat_changes={key.value: 0.0 for key in OVERALL_STAT_ORDER},
    )


def make_realistic_base_stats() -> BaseStats:
    """전투력 계산 검증용 현실적인 베이스 스탯 구성"""

    # 만렙 캐릭터 수준의 임의 입력값 (테스트 가독성용 라운드 값)
    values: dict[str, float] = {
        stat_key.value: 0.0 for stat_key in OVERALL_STAT_ORDER
    }
    values[StatKey.ATTACK.value] = 5000.0
    values[StatKey.ATTACK_PERCENT.value] = 50.0
    values[StatKey.HP.value] = 10000.0
    values[StatKey.HP_PERCENT.value] = 20.0
    values[StatKey.STR.value] = 1000.0
    values[StatKey.STR_PERCENT.value] = 30.0
    values[StatKey.DEXTERITY.value] = 500.0
    values[StatKey.DEXTERITY_PERCENT.value] = 20.0
    values[StatKey.VITALITY.value] = 800.0
    values[StatKey.VITALITY_PERCENT.value] = 10.0
    values[StatKey.LUCK.value] = 300.0
    values[StatKey.LUCK_PERCENT.value] = 5.0
    values[StatKey.SKILL_DAMAGE_PERCENT.value] = 40.0
    values[StatKey.FINAL_ATTACK_PERCENT.value] = 25.0
    values[StatKey.CRIT_RATE_PERCENT.value] = 30.0
    values[StatKey.CRIT_DAMAGE_PERCENT.value] = 180.0
    values[StatKey.BOSS_ATTACK_PERCENT.value] = 40.0
    values[StatKey.DROP_RATE_PERCENT.value] = 10.0
    values[StatKey.EXP_PERCENT.value] = 10.0
    values[StatKey.DODGE_PERCENT.value] = 5.0
    values[StatKey.POTION_HEAL_PERCENT.value] = 15.0
    values[StatKey.RESIST_PERCENT.value] = 5.0
    values[StatKey.SKILL_SPEED_PERCENT.value] = 0.0
    return BaseStats(values=values)


@pytest.fixture
def synthetic_server() -> ServerSpec:
    """7개 무공비급 14개 스킬을 가진 합성 ServerSpec"""

    return build_synthetic_server()


@pytest.fixture
def full_preset(synthetic_server: ServerSpec) -> MacroPreset:
    """풀 장착 (14스킬) 기본 프리셋"""

    return build_full_equipped_preset(synthetic_server)


@pytest.fixture
def realistic_base_stats() -> BaseStats:
    """전투력 평가에 쓸 만한 현실적인 베이스 스탯"""

    return make_realistic_base_stats()


@pytest.fixture
def isolated_data_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, str]:
    """data_manager의 데이터 경로를 임시 디렉터리로 격리"""

    # 사용자 환경의 실제 macros.json/custom_skills.json을 건드리지 않도록 격리
    from app.scripts import data_manager

    fake_file_dir: str = str(tmp_path / "macros.json")
    fake_custom_skills_dir: str = str(tmp_path / "custom_skills.json")
    monkeypatch.setattr(data_manager, "data_path", str(tmp_path))
    monkeypatch.setattr(data_manager, "file_dir", fake_file_dir)
    monkeypatch.setattr(
        data_manager,
        "custom_skills_file_dir",
        fake_custom_skills_dir,
    )

    return {
        "data_path": str(tmp_path),
        "file_dir": fake_file_dir,
        "custom_skills_file_dir": fake_custom_skills_dir,
    }

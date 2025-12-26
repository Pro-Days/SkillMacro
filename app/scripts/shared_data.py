from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pynput.keyboard import Key as PynputKey
from pynput.keyboard import KeyCode

from app.scripts.misc import convert_resource_path

from .custom_classes import Stats

if TYPE_CHECKING:
    from app.scripts.macro_models import MacroPreset


@dataclass(frozen=True)
class KeySpec:
    display: str
    key_id: str
    type: Literal["key", "char"]
    value: PynputKey | KeyCode

    @classmethod
    def from_key(cls, display: str, key_id: str, key: PynputKey) -> "KeySpec":
        return cls(display=display, key_id=key_id, type="key", value=key)

    @classmethod
    def from_char(cls, display: str, char: str) -> "KeySpec":
        return cls(
            display=display, key_id=char, type="char", value=KeyCode.from_char(char)
        )

    def __str__(self) -> str:
        return self.display


# 공유 데이터 클래스
# SharedData가 여러번 선언된다면, 리스트로 초기화된 변수들은 모든 SharedData 인스턴스에서 공유되어 오류가 발생할 수 있음
@dataclass(eq=False)
class SharedData:
    # 현재 프로그램 버전
    VERSION: str = "3.1.0-beta.2"

    # 전투력 계수
    COEF_BOSS_DMG: float = 1.0
    COEF_NORMAL_DMG: float = 1.3
    COEF_BOSS: float = 0.0002
    COEF_NORMAL: float = 0.7

    # 매크로 단위 시간
    UNIT_TIME: float = 0.05  # 1tick

    # AFK 모드 활성화 여부: 정식 버전에서는 True로 변경
    IS_AFK_ENABLED: bool = False
    # 버전 확인 모드 활성화 여부: 정식 버전에서는 True로 변경
    IS_VERSION_CHECK_ENABLED: bool = False

    # 딜레이 설정
    MIN_DELAY: int = 50
    MAX_DELAY: int = 1000
    DEFAULT_DELAY: int = 150

    # 쿨타임 감소 스탯 설정
    MIN_COOLTIME_REDUCTION: int = 0
    MAX_COOLTIME_REDUCTION: int = 50
    DEFAULT_COOLTIME_REDUCTION: int = 0

    STAT_RANGES: ClassVar[dict[str, tuple[int, int]]] = {
        "ATK": (1, 10000),
        "DEF": (1, 10000),
        "PWR": (0, 10000),
        "STR": (1, 10000),
        "INT": (1, 10000),
        "RES": (1, 10000),
        "CRIT_RATE": (0, 10000),
        "CRIT_DMG": (0, 10000),
        "BOSS_DMG": (0, 10000),
        "ACC": (0, 10000),
        "DODGE": (0, 10000),
        "STATUS_RES": (0, 10000),
        "NAEGONG": (0, 10000),
        "HP": (1, 10000),
        "ATK_SPD": (0, MAX_COOLTIME_REDUCTION),
        "POT_HEAL": (0, 10000),
        "LUK": (0, 10000),
        "EXP": (0, 10000),
    }

    # 내공 차이에 의한 데미지 배수 (몹-나)
    # 내공 1당 5%의 데미지 차이일 가능성 높음, 5차이 이상부터는 데미지 0
    NAEGONG_DIFF: ClassVar[dict[tuple[int, int], float]] = {
        (6, 1000): 0.0,
        (5, 5): 0.3,
        (4, 4): 0.5,
        (3, 3): 0.7,
        (2, 2): 0.85,
        (1, 1): 0.95,
        (0, 0): 1.0,
        (-1, -1): 1.025,
        (-2, -2): 1.05,
        (-4, -3): 1.075,
        (-6, -5): 1.1,
        (-9, -7): 1.15,
        (-13, -10): 1.2,
        (-18, -14): 1.3,
        (-25, -19): 1.4,
        (-1000, -26): 1.5,
    }

    # 스탯 목록
    STATS: ClassVar[dict[str, str]] = {
        "ATK": "공격력",
        "DEF": "방어력",
        "PWR": "파괴력",
        "STR": "근력",
        "INT": "지력",
        "RES": "경도",
        "CRIT_RATE": "치명타확률",
        "CRIT_DMG": "치명타데미지",
        "BOSS_DMG": "보스데미지",
        "ACC": "명중률",
        "DODGE": "회피율",
        "STATUS_RES": "상태이상저항",
        "NAEGONG": "내공",
        "HP": "체력",
        "ATK_SPD": "공격속도",
        "POT_HEAL": "포션회복력",
        "LUK": "운",
        "EXP": "경험치획득량",
    }
    POTENTIAL_STATS: ClassVar[dict[str, tuple[str, int]]] = {
        "내공 +3": ("NAEGONG", 3),
        "내공 +2": ("NAEGONG", 2),
        "내공 +1": ("NAEGONG", 1),
        "경도 +3": ("RES", 3),
        "경도 +2": ("RES", 2),
        "경도 +1": ("RES", 1),
        "치명타확률 +3": ("CRIT_RATE", 3),
        "치명타확률 +2": ("CRIT_RATE", 2),
        "치명타확률 +1": ("CRIT_RATE", 1),
        "치명타데미지 +4": ("CRIT_DMG", 4),
        "치명타데미지 +3": ("CRIT_DMG", 3),
        "치명타데미지 +2": ("CRIT_DMG", 2),
        "보스데미지 +3": ("BOSS_DMG", 3),
        "보스데미지 +2": ("BOSS_DMG", 2),
        "보스데미지 +1": ("BOSS_DMG", 1),
        "상태이상저항 +6": ("STATUS_RES", 6),
        "상태이상저항 +4": ("STATUS_RES", 4),
        "상태이상저항 +2": ("STATUS_RES", 2),
        "체력 +6": ("HP", 6),
        "체력 +4": ("HP", 4),
        "체력 +2": ("HP", 2),
        "공격속도 +3": ("ATK_SPD", 3),
        "공격속도 +2": ("ATK_SPD", 2),
        "공격속도 +1": ("ATK_SPD", 1),
        "포션회복량 +6": ("POT_HEAL", 6),
        "포션회복량 +4": ("POT_HEAL", 4),
        "포션회복량 +2": ("POT_HEAL", 2),
        "운 +6": ("LUK", 6),
        "운 +4": ("LUK", 4),
        "운 +2": ("LUK", 2),
    }
    SIM_DETAILS: ClassVar[dict[str, str]] = {
        "NORMAL_NAEGONG": "몬스터 내공",
        "BOSS_NAEGONG": "보스 내공",
        "POTION_HEAL": "포션 회복량",
    }

    POWER_TITLES: ClassVar[list[str]] = ["보스데미지", "일반데미지", "보스", "사냥"]
    POWER_DETAILS: ClassVar[list[str]] = ["min", "max", "std", "p25", "p50", "p75"]

    KEY_DICT: ClassVar[dict[str, KeySpec]] = {
        # F키
        "f1": KeySpec.from_key("F1", "f1", PynputKey.f1),
        "f2": KeySpec.from_key("F2", "f2", PynputKey.f2),
        "f3": KeySpec.from_key("F3", "f3", PynputKey.f3),
        "f4": KeySpec.from_key("F4", "f4", PynputKey.f4),
        "f5": KeySpec.from_key("F5", "f5", PynputKey.f5),
        "f6": KeySpec.from_key("F6", "f6", PynputKey.f6),
        "f7": KeySpec.from_key("F7", "f7", PynputKey.f7),
        "f8": KeySpec.from_key("F8", "f8", PynputKey.f8),
        "f9": KeySpec.from_key("F9", "f9", PynputKey.f9),
        "f10": KeySpec.from_key("F10", "f10", PynputKey.f10),
        "f11": KeySpec.from_key("F11", "f11", PynputKey.f11),
        "f12": KeySpec.from_key("F12", "f12", PynputKey.f12),
        # 알파벳
        "a": KeySpec.from_char("A", "a"),
        "b": KeySpec.from_char("B", "b"),
        "c": KeySpec.from_char("C", "c"),
        "d": KeySpec.from_char("D", "d"),
        "e": KeySpec.from_char("E", "e"),
        "f": KeySpec.from_char("F", "f"),
        "g": KeySpec.from_char("G", "g"),
        "h": KeySpec.from_char("H", "h"),
        "i": KeySpec.from_char("I", "i"),
        "j": KeySpec.from_char("J", "j"),
        "k": KeySpec.from_char("K", "k"),
        "l": KeySpec.from_char("L", "l"),
        "m": KeySpec.from_char("M", "m"),
        "n": KeySpec.from_char("N", "n"),
        "o": KeySpec.from_char("O", "o"),
        "p": KeySpec.from_char("P", "p"),
        "q": KeySpec.from_char("Q", "q"),
        "r": KeySpec.from_char("R", "r"),
        "s": KeySpec.from_char("S", "s"),
        "t": KeySpec.from_char("T", "t"),
        "u": KeySpec.from_char("U", "u"),
        "v": KeySpec.from_char("V", "v"),
        "w": KeySpec.from_char("W", "w"),
        "x": KeySpec.from_char("X", "x"),
        "y": KeySpec.from_char("Y", "y"),
        "z": KeySpec.from_char("Z", "z"),
        # 숫자
        "0": KeySpec.from_char("0", "0"),
        "1": KeySpec.from_char("1", "1"),
        "2": KeySpec.from_char("2", "2"),
        "3": KeySpec.from_char("3", "3"),
        "4": KeySpec.from_char("4", "4"),
        "5": KeySpec.from_char("5", "5"),
        "6": KeySpec.from_char("6", "6"),
        "7": KeySpec.from_char("7", "7"),
        "8": KeySpec.from_char("8", "8"),
        "9": KeySpec.from_char("9", "9"),
        # 기호
        "`": KeySpec.from_char("`", "`"),
        "-": KeySpec.from_char("-", "-"),
        "=": KeySpec.from_char("=", "="),
        "[": KeySpec.from_char("[", "["),
        "]": KeySpec.from_char("]", "]"),
        "\\": KeySpec.from_char("\\", "\\"),
        ";": KeySpec.from_char(";", ";"),
        "'": KeySpec.from_char("'", "'"),
        ",": KeySpec.from_char(",", ","),
        ".": KeySpec.from_char(".", "."),
        "/": KeySpec.from_char("/", "/"),
        # 특수키
        "up": KeySpec.from_key("Up", "up", PynputKey.up),
        "down": KeySpec.from_key("Down", "down", PynputKey.down),
        "left": KeySpec.from_key("Left", "left", PynputKey.left),
        "right": KeySpec.from_key("Right", "right", PynputKey.right),
        "print_screen": KeySpec.from_key(
            "PrtSc", "print screen", PynputKey.print_screen
        ),
        "scroll_lock": KeySpec.from_key("ScrLk", "scroll lock", PynputKey.scroll_lock),
        "pause": KeySpec.from_key("Pause", "pause", PynputKey.pause),
        "insert": KeySpec.from_key("Insert", "insert", PynputKey.insert),
        "home": KeySpec.from_key("Home", "home", PynputKey.home),
        "page_up": KeySpec.from_key("PageUp", "page up", PynputKey.page_up),
        "page_down": KeySpec.from_key("PageDown", "page down", PynputKey.page_down),
        "delete": KeySpec.from_key("Delete", "delete", PynputKey.delete),
        "end": KeySpec.from_key("End", "end", PynputKey.end),
    }

    # 시작 키 설정
    DEFAULT_START_KEY: KeySpec = KEY_DICT["f9"]

    SERVERS: ClassVar[list[str]] = ["한월 RPG"]

    DEFAULT_SERVER_ID: str = "한월 RPG"

    # 장착 가능한 스킬 개수
    USABLE_SKILL_COUNT: ClassVar[dict[str, int]] = {"한월 RPG": 6}

    # 스킬 레벨 최대값
    MAX_SKILL_LEVEL: ClassVar[dict[str, int]] = {"한월 RPG": 1}

    # pag.PAUSE = 0.01  # pag click delay 설정

    # 이 계수를 조정하여 time.sleep과 실제 시간 간의 괴리를 조정
    SLEEP_COEFFICIENT_NORMAL = 0.975
    SLEEP_COEFFICIENT_UNIT = 0.97

    # 스킬 데이터
    # 프로그램 실행 시 데이터를 다운로드받는 방식으로 변경
    with open(
        convert_resource_path("resources\\data\\skill_data.json"), "r", encoding="utf-8"
    ) as f:
        skill_data = json.load(f)

    # skillAttackData[serverID][jobID][skill][level:임시로 하나만][combo][attackNum]:
    # [time, [type(0: damage, 1: buff), [buff_type, buff_value, buff_duration] or damage_value]]
    # SKILL_ATTACK_DATA = skill_data["AttackData"]
    # SKILL_COOLTIME_LIST = skill_data["CooltimeList"]
    # SKILL_COMBO_COUNT_LIST = skill_data["ComboCounts"]
    # IS_SKILL_CASTING = skill_data["IsSkillCasting"]

    # 스킬 아이콘 디렉토리 정보
    # 이 딕셔너리에 없는 스킬은 기본 아이콘 사용
    # todo: 다른 파일에 저장해서 불러오는 방식으로 변경
    skill_images_dir: ClassVar[dict[str, str]] = {}

    # 변수 초기화

    # 계산기 페이지 번호
    sim_page_type: int = 0

    # 매크로가 실행중인지
    is_activated: bool = False

    # 매크로 실행 번호
    loop_num: int = 0

    # 사이드바 페이지 번호
    sidebar_type: int = -1

    # 팝업 정보
    # 현재 활성화된 팝업 이름
    active_popup: str = ""
    # 활성화된 팝업 리스트
    active_error_popup: ClassVar[list[list]] = []
    active_error_popup_count: int = 0  # len으로 변경
    is_tab_remove_popup_activated: bool = False

    powers: ClassVar[list[float]] = [0.0, 0.0, 0.0, 0.0]
    is_input_valid: ClassVar[dict[str, bool]] = {
        "stat": False,
        "skill": False,
        "simInfo": False,
    }
    is_card_updated: bool = False

    recent_version: str = "0.0.0"  # 최근 버전 정보
    update_url: str = ""  # 업데이트 URL

    # 매크로 데이터 초기화

    # 최근에 선택된 프리셋 번호
    recent_preset: int = 0

    # --- 점진적 마이그레이션용 프리셋 컨테이너 ---
    # 기존 코드(탭 UI 포함)가 SharedData의 ClassVar(예: equipped_skills)를 직접 읽고/쓰고 있어서,
    # 당장 제거하지 않고 병행한다. 다음 단계에서 load_data가 이 presets/current_preset을 채우도록 바꾼다.
    presets: list[MacroPreset] = field(default_factory=list, repr=False)

    # 탭 이름들
    tab_names: ClassVar[list[str]] = []

    # 장착된 스킬 목록, 각 스킬의 이름이 저장됨.
    equipped_skills: ClassVar[list[str]] = []

    # 스킬 사용 키 목록
    skill_keys: ClassVar[list[KeySpec]] = []

    # 서버 ID와 직업 ID
    # 기본값은 첫 번째 직업
    server_ID: str = SERVERS[0]
    # job_ID: str = JOBS[server_ID][0]

    # 딜레이 설정: 0이면 기본, 1이면 직접입력
    delay_type: int = 0
    # 입력된 딜레이
    delay_input: int = 0
    # 사용되는 딜레이
    delay: int = DEFAULT_DELAY

    # 쿨타임 감소 스탯 설정: 0이면 기본, 1이면 직접입력
    cooltime_reduction_type: int = 0
    # 입력된 쿨타임 감소 스탯
    cooltime_reduction_input: int = 0
    # 사용되는 쿨타임 감소 스탯
    cooltime_reduction: int = 0

    # 시작키 설정: 0이면 기본, 1이면 직접입력
    start_key_type: int = 0
    # 입력된 시작키
    start_key_input: KeySpec = DEFAULT_START_KEY
    # 사용되는 시작키
    start_key: KeySpec = DEFAULT_START_KEY
    # 시작키 설정 중인지
    is_setting_key: bool = False

    # 마우스 클릭 설정: 0이면 스킬 사용시에만, 1이면 평타도 사용
    mouse_click_type: int = 0

    # -- 스킬 사용설정 --

    # 사용 여부
    is_use_skill: ClassVar[dict[str, bool]] = {
        skill: False for skill in skill_data[server_ID]["skills"]
    }
    # 단독 사용
    is_use_sole: ClassVar[dict[str, bool]] = {
        skill: False for skill in skill_data[server_ID]["skills"]
    }
    # 우선 순위
    # todo: class, list로 변경
    skill_priority: ClassVar[dict[str, int]] = {
        skill: 0 for skill in skill_data[server_ID]["skills"]
    }  # 스킬 우선순위, 0: 지정되지 않음

    # todo: class로 변경
    link_skills: ClassVar[list[dict[str, Any]]] = []
    """
    [
        { "useType": "auto", "keyType": "on", "key": "A", "skills": ["스킬1"] },
        { "useType": "manual", "keyType": "off", "key": "B", "skills": ["스킬1", "스킬2"] }
    ]
    """

    # 매크로 실행 중 실행할 스킬 목록
    task_list: ClassVar[list[int]] = []

    # 준비된 스킬 리스트
    prepared_skills: ClassVar[list[list[int]]] = []

    # 스킬 사용 가능 여부
    is_skills_ready: ClassVar[list[bool]] = []

    # 준비된 연계스킬 리스트
    # todo: class로 변경
    prepared_link_skill_indices: ClassVar[list[int]] = []

    # 연계스킬 수행에 필요한 스킬 정보 리스트
    link_skills_requirements: ClassVar[list[list[int]]] = []

    # 매크로 작동 중 사용하는 연계스킬 리스트
    using_link_skills: ClassVar[list[list[int]]] = []

    # 연계가 아닌 스킬의 사용 순서
    skill_sequence: ClassVar[list[int]] = []

    # AFK 모드 시작 시간
    afk_started_time: float = 0.0

    # 스킬 쿨타임 타이머
    skill_cooltime_timers: ClassVar[list[float]] = []

    # 시뮬레이션 정보
    # 스탯
    info_stats: Stats = Stats()
    # 스킬 레벨
    info_skill_levels: ClassVar[dict[str, int]] = {}
    # 기타 시뮬레이션 세부정보
    info_sim_details: ClassVar[dict[str, int]] = {}

    info_stats_counts: int = 18
    info_skill_levels_counts: int = 8
    info_sim_details_counts: int = 3

    def __get_hashable_representation__(self) -> str:
        data_to_hash = (
            self.equipped_skills,
            self.server_ID,
            self.delay,
            self.cooltime_reduction,
            self.is_use_skill,
            self.is_use_sole,
            self.skill_priority,
            self.link_skills,
            self.info_stats,
            self.info_skill_levels,
            self.info_sim_details,
        )

        return json.dumps(
            data_to_hash,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def __hash__(self) -> int:
        return hash(self.__get_hashable_representation__())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SharedData):
            return NotImplemented

        return (
            self.__get_hashable_representation__()
            == other.__get_hashable_representation__()
        )


@dataclass(frozen=True)
class UI_Variable:
    DEFAULT_WINDOW_WIDTH = 960
    DEFAULT_WINDOW_HEIGHT = 540

    sim_colors4 = [
        "255, 130, 130",  # #FF8282
        "255, 230, 140",  # #FFE68C
        "170, 230, 255",  # #AAE6FF
        "150, 225, 210",  # #96E1D2
    ]
    sim_input_colors = ["#f0f0f0", "#D9D9D9"]  # [background, border]
    sim_input_colorsRed = "#FF6060"
    scrollBarWidth = 12
    sim_margin = 10
    sim_mainFrameMargin = 20

    sim_navHeight = 50
    sim_navBWidth = 200

    sim_title_H = 50

    sim_main1_D = 5
    sim_main_D = 40
    sim_widget_D = 20

    sim_label_H = 50
    sim_label_x = 50

    # Dict로 바꿔서 이름으로 접근할 수 있도록 수정
    sim_stat_margin = 50
    sim_stat_frame_H = 60
    sim_stat_label_H = 20
    sim_stat_input_H = 40
    sim_stat_width = 120

    sim_skill_margin = 100
    sim_skill_image_Size = 56
    sim_skill_right_W = 76
    sim_skill_width = 132
    sim_skill_frame_H = 86
    sim_skill_name_H = 30
    sim_skill_level_H = 24
    sim_skill_input_H = 24

    sim_simInfo_margin = 224
    sim_simInfo_frame_H = sim_stat_frame_H
    sim_simInfo_label_H = sim_stat_label_H
    sim_simInfo_input_H = sim_stat_input_H
    sim_simInfo_width = sim_stat_width

    sim_powerL_margin = 25
    sim_powerL_D = 20
    sim_powerL_width = 205
    sim_powerL_frame_H = 140
    sim_powerL_title_H = 50
    sim_powerL_number_H = 90

    sim_analysis_margin = sim_powerL_margin
    sim_analysis_D = sim_powerL_D
    sim_analysis_width = sim_powerL_width
    sim_analysis_color_W = 4
    sim_analysis_widthXC = sim_analysis_width - sim_analysis_color_W
    sim_analysis_frame_H = 140
    sim_analysis_title_H = 40
    sim_analysis_number_H = 55
    sim_analysis_number_marginH = 5
    sim_analysis_details_H = 20
    sim_analysis_details_W = 63
    sim_analysis_detailsT_W = 22
    sim_analysis_detailsN_W = 41
    sim_analysis_details_margin = 3

    sim_dps_margin = 25
    sim_dps_width = 430
    sim_dps_height = 300

    sim_skillDps_margin = 20
    sim_skillRatio_width = sim_dps_width
    sim_skillRatio_height = sim_dps_height

    sim_dmg_margin = 25
    sim_dmg_width = 880
    sim_dmg_height = 400

    sim_powerS_margin = 375
    sim_powerS_D = 15
    sim_powerS_width = 120
    sim_powerS_frame_H = 100
    sim_powerS_title_H = 40
    sim_powerS_number_H = 60

    sim_efficiency_frame_H = 100
    sim_potential_frame_H = 100

    sim_efficiency_statL_W = 110
    sim_efficiency_statL_H = 24
    sim_efficiency_statL_y = 15
    sim_efficiency_statL_margin = 33

    sim_efficiency_statInput_margin = 28
    sim_efficiency_statInput_W = 120
    sim_efficiency_statInput_H = 40
    sim_efficiency_statInput_y = sim_efficiency_statL_y + sim_efficiency_statL_H + 6

    sim_efficiency_arrow_margin = 28 + sim_efficiency_statInput_W
    sim_efficiency_arrow_W = 60
    sim_efficiency_arrow_H = 60
    sim_efficiency_arrow_y = 20

    sim_efficiency_statR_margin = sim_efficiency_arrow_margin + sim_efficiency_arrow_W
    sim_efficiency_statR_W = 120
    sim_efficiency_statR_H = 30
    sim_efficiency_statR_y = 35

    sim_potential_stat_margin = 50
    sim_potential_stat_W = 125
    sim_potential_stat_H = 30
    sim_potential_stat_D = 5

    sim_powerM_margin = 225
    sim_powerM_D = 20
    sim_powerM_width = 148
    sim_powerM_frame_H = 100
    sim_powerM_title_H = 40
    sim_powerM_number_H = 60

    sim_potentialRank_margin = 25
    sim_potentialRank_D = 20
    sim_potentialRank_width = 205
    sim_potentialRank_title_H = 50
    sim_potentialRank_rank_H = 25
    sim_potentialRank_ranks_H = sim_potentialRank_rank_H * 16
    sim_potentialRank_frame_H = (
        sim_potentialRank_title_H + sim_potentialRank_rank_H * 16
    )
    sim_potentialRank_rank_ranking_W = 30
    sim_potentialRank_rank_potential_W = 115
    sim_potentialRank_rank_power_W = 60

    # 캐릭터 카드
    sim_char_frame_H = 420
    sim_char_margin = 50
    sim_char_margin_y = 20

    sim_charInfo_marginX = 20
    sim_charInfo_marginY = 25
    sim_charInfo_label_y = 2
    sim_charInfo_label_H = 33
    sim_charInfo_W = int((928 - sim_char_margin * 4) * 0.5)  # 364
    sim_charInfo_H = sim_char_frame_H - sim_char_margin_y  # 400
    sim_charInfo_frame_W = sim_charInfo_W - sim_charInfo_marginX * 2  # 324

    sim_charInfo_nickname_H = 80
    sim_charInfo_nickname_input_margin = 20
    sim_charInfo_nickname_input_W = 200
    sim_charInfo_nickname_input_H = 35
    sim_charInfo_nickname_load_margin = (
        sim_charInfo_nickname_input_margin * 2 + sim_charInfo_nickname_input_W
    )  # 200
    sim_charInfo_nickname_load_W = 64
    sim_charInfo_nickname_load_H = 31
    sim_charInfo_nickname_load_y = sim_charInfo_label_y + sim_charInfo_label_H + 2  # 37

    sim_charInfo_char_H = 75
    sim_charInfo_char_button_margin = 12
    sim_charInfo_char_button_W = 92
    sim_charInfo_char_button_H = 30
    sim_charInfo_char_button_y = sim_charInfo_label_y + sim_charInfo_label_H  # 35

    sim_charInfo_power_H = 75
    sim_charInfo_power_button_margin = 12
    sim_charInfo_power_button_W = 66
    sim_charInfo_power_button_H = 30
    sim_charInfo_power_button_y = sim_charInfo_label_y + sim_charInfo_label_H  # 35

    sim_charInfo_complete_y = 30
    sim_charInfo_complete_margin = 50
    sim_charInfo_complete_W = 120
    sim_charInfo_complete_H = 40

    sim_charInfo_save_y = sim_charInfo_complete_y
    sim_charInfo_save_margin = (
        sim_charInfo_complete_margin + sim_charInfo_complete_W + 24
    )
    sim_charInfo_save_W = 120
    sim_charInfo_save_H = 40

    sim_charCard_W = int((928 - sim_char_margin * 4) * 0.5)  # 364
    sim_charCard_H = sim_char_frame_H - sim_char_margin_y  # 400
    sim_charCard_title_H = 50

    sim_charCard_image_margin = 19
    sim_charCard_image_W = 156
    sim_charCard_image_H = 312

    sim_charCard_name_margin = sim_charCard_image_margin + sim_charCard_image_W + 10
    sim_charCard_name_y = sim_charCard_title_H + 50
    sim_charCard_name_W = 166
    sim_charCard_name_H = 35

    sim_charCard_job_margin = sim_charCard_image_margin + sim_charCard_image_W + 30
    sim_charCard_job_y = sim_charCard_name_y + sim_charCard_name_H
    sim_charCard_job_W = 50  # 50 + 79 = 126
    sim_charCard_job_H = 40
    sim_charCard_level_margin = sim_charCard_job_margin + sim_charCard_job_W
    sim_charCard_level_y = sim_charCard_job_y
    sim_charCard_level_W = 76  # 50 + 76 = 126
    sim_charCard_level_H = sim_charCard_job_H

    sim_charCard_name_line_W = 146
    sim_charCard_info_line_H = 16

    sim_charCard_powerFrame_margin = (
        sim_charCard_image_margin + sim_charCard_image_W + 10
    )
    sim_charCard_powerFrame_y = sim_charCard_job_y + sim_charCard_job_H + 15
    sim_charCard_powerFrame_W = 166
    sim_charCard_powerFrame_H = 40
    sim_charCard_power_title_W = 80
    sim_charCard_power_number_W = 86

    comboboxStyle = f"""
        QComboBox {{
            background-color: {sim_input_colors[0]};
            border: 1px solid {sim_input_colors[1]};
            border-radius: 4px;
        }}
        QComboBox::drop-down {{
            width: 20px;
            border-left-width: 1px;
            border-left-color: darkgray;
            border-left-style: solid;
        }}
        QComboBox::down-arrow {{
            image: url({convert_resource_path("resources\\image\\down_arrow.png").replace("\\", "/")});
            width: 16px;
            height: 16px;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {sim_input_colors[1]};
        }}"""

import json
from dataclasses import dataclass
from .utils.data_manager import convertResourcePath


@dataclass(unsafe_hash=True)
class SharedData:
    # 상수 설정
    VERSION = "v3.1.0-alpha"

    DEFAULT_WINDOW_WIDTH = 960
    DEFAULT_WINDOW_HEIGHT = 540

    # ICON = QIcon(QPixmap(convertResourcePath("resources\\image\\icon\\icon.ico")))
    # ICON_ON = QIcon(QPixmap(convertResourcePath("resources\\image\\icon\\icon_on.ico")))

    # pag.PAUSE = 0.01  # pag click delay 설정

    # 이 계수를 조정하여 time.sleep과 실제 시간 간의 괴리를 조정
    SLEEP_COEFFICIENT_NORMAL = 0.975
    SLEEP_COEFFICIENT_UNIT = 0.97

    COEF_BOSS_DMG = 1.0
    COEF_NORMAL_DMG = 1.3
    COEF_BOSS = 0.0002
    COEF_NORMAL = 0.7

    UNIT_TIME = 0.05  # 1tick
    IS_AFK_ENABLED = True  # AFK 모드 활성화 여부: 정식 버전에서는 True로 변경
    MIN_DELAY = 50
    MAX_DELAY = 1000
    MIN_COOLTIME = 0
    MAX_COOLTIME = 50

    # 내공 차이에 의한 데미지 배수 (몹-나)
    NAEGONG_DIFF = {
        (6, 1000): 0,
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

    STAT_LIST = [
        "공격력",
        "방어력",
        "파괴력",
        "근력",
        "지력",
        "경도",
        "치명타확률",
        "치명타데미지",
        "보스데미지",
        "명중률",
        "회피율",
        "상태이상저항",
        "내공",
        "체력",
        "공격속도",
        "포션회복량",
        "운",
        "경험치획득량",
    ]
    STAT_RANGE_LIST = [
        [1, None],
        [1, None],
        [0, None],
        [1, None],
        [1, None],
        [1, None],
        [0, None],
        [0, None],
        [0, None],
        [0, None],
        [0, None],
        [0, None],
        [0, None],
        [1, None],
        [0, MAX_COOLTIME],
        [0, None],
        [0, None],
        [0, None],
    ]
    POTENTIAL_STAT_LIST = {
        "내공 +3": [12, 3],
        "내공 +2": [12, 2],
        "내공 +1": [12, 1],
        "경도 +3": [5, 3],
        "경도 +2": [5, 2],
        "경도 +1": [5, 1],
        "치명타확률 +3": [6, 3],
        "치명타확률 +2": [6, 2],
        "치명타확률 +1": [6, 1],
        "치명타데미지 +4": [7, 4],
        "치명타데미지 +3": [7, 3],
        "치명타데미지 +2": [7, 2],
        "보스데미지 +3": [8, 3],
        "보스데미지 +2": [8, 2],
        "보스데미지 +1": [8, 1],
        "상태이상저항 +6": [11, 6],
        "상태이상저항 +4": [11, 4],
        "상태이상저항 +2": [11, 2],
        "체력 +6": [13, 6],
        "체력 +4": [13, 4],
        "체력 +2": [13, 2],
        "공격속도 +3": [14, 3],
        "공격속도 +2": [14, 2],
        "공격속도 +1": [14, 1],
        "포션회복량 +6": [15, 6],
        "포션회복량 +4": [15, 4],
        "포션회복량 +2": [15, 2],
        "운 +6": [16, 6],
        "운 +4": [16, 4],
        "운 +2": [16, 2],
    }
    KEY_DICT = {
        "f1": "F1",
        "f2": "F2",
        "f3": "F3",
        "f4": "F4",
        "f5": "F5",
        "f6": "F6",
        "f7": "F7",
        "f8": "F8",
        "f9": "F9",
        "f10": "F10",
        "f11": "F11",
        "f12": "F12",
        "a": "A",
        "b": "B",
        "c": "C",
        "d": "D",
        "e": "E",
        "f": "F",
        "g": "G",
        "h": "H",
        "i": "I",
        "j": "J",
        "k": "K",
        "l": "L",
        "m": "M",
        "n": "N",
        "o": "O",
        "p": "P",
        "q": "Q",
        "r": "R",
        "s": "S",
        "t": "T",
        "u": "U",
        "v": "V",
        "w": "W",
        "x": "X",
        "y": "Y",
        "z": "Z",
        "tab": "Tab",
        "space": "Space",
        "enter": "Enter",
        "shift": "Shift",
        "right shift": "Shift",
        "ctrl": "Ctrl",
        "right ctrl": "Ctrl",
        "alt": "Alt",
        "right alt": "Alt",
        "up": "Up",
        "down": "Down",
        "left": "Left",
        "right": "Right",
        "print screen": "PrtSc",
        "scroll lock": "ScrLk",
        "pause": "Pause",
        "insert": "Insert",
        "home": "Home",
        "page up": "Page_Up",
        "page down": "Page_Down",
        "delete": "Delete",
        "end": "End",
    }
    SERVER_LIST = [
        "한월 RPG",
    ]
    JOB_LIST = [
        ["검호", "매화", "살수", "도제", "술사", "도사", "빙궁", "귀궁"],
    ]
    USABLE_SKILL_COUNT = [6]  # 장착 가능한 스킬 개수

    with open(convertResourcePath("resources\\data\\skill_data.json"), "r", encoding="utf-8") as f:
        skill_data = json.load(f)

    SKILL_NAME_LIST = skill_data["Names"]

    # skillAttackData[serverID][jobID][skill][level:임시로 하나만][combo][attackNum]:
    # [time, [type(0: damage, 1: buff), [buff_type, buff_value, buff_duration] or damage_value]]
    SKILL_ATTACK_DATA = skill_data["AttackData"]

    SKILL_COOLTIME_LIST = skill_data["CooltimeList"]

    SKILL_COMBO_COUNT_LIST = skill_data["ComboCounts"]

    IS_SKILL_CASTING = skill_data["IsSkillCasting"]

    # 변수 초기화
    sim_type = 0
    active_error_popup_count = 0
    is_tab_remove_popup_activated = False
    is_activated = False
    loop_num = 0
    selected_item_slot = -1
    is_skill_selecting = -1
    setting_type = -1
    layout_type = 0  # 0: 스킬, 1: 시뮬레이터
    active_popup = ""
    active_error_popup = []
    active_error_popup_count = 0
    skill_preview_list = []

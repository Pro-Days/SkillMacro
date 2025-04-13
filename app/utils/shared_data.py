import json
from dataclasses import dataclass
from .data_manager import convertResourcePath
from typing import Final


@dataclass(unsafe_hash=True)
class SharedData:
    # 상수 설정
    VERSION = "3.1.0-beta.1"

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
    # 내공 1당 5%의 데미지 차이일 가능성 높음, 5차이 이상부터는 데미지 0
    NAEGONG_DIFF = {
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
        [1, 10000],
        [1, 10000],
        [0, 10000],
        [1, 10000],
        [1, 10000],
        [1, 10000],
        [0, 10000],
        [0, 10000],
        [0, 10000],
        [0, 10000],
        [0, 10000],
        [0, 10000],
        [0, 10000],
        [1, 10000],
        [0, MAX_COOLTIME],
        [0, 10000],
        [0, 10000],
        [0, 10000],
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
    SIM_INFO_LIST = [
        "몬스터 내공",
        "보스 내공",
        "포션 회복량",
    ]
    POWER_TITLES = ["보스데미지", "일반데미지", "보스", "사냥"]
    POWER_DETAILS = ["min", "max", "std", "p25", "p50", "p75"]

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

    powers = []
    inputCheck = {"stat": False, "skill": False, "simInfo": False}
    card_updated = False


@dataclass
class UI_Variable:
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
    sim_potentialRank_frame_H = sim_potentialRank_title_H + sim_potentialRank_rank_H * 16
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
    sim_charInfo_save_margin = sim_charInfo_complete_margin + sim_charInfo_complete_W + 24
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

    sim_charCard_powerFrame_margin = sim_charCard_image_margin + sim_charCard_image_W + 10
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
            image: url({convertResourcePath("resources\\image\\down_arrow.png").replace("\\", "/")});
            width: 16px;
            height: 16px;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {sim_input_colors[1]};
        }}"""

from __future__ import annotations

from dataclasses import dataclass

from app.scripts.registry.resource_registry import convert_resource_path

# 런타임 경로
_CLOSE_BTN_PATH: str = convert_resource_path("resources\\image\\x.png").replace(
    "\\", "/"
)
_DOWN_ARROW_PATH: str = convert_resource_path(
    "resources\\image\\down_arrow.png"
).replace("\\", "/")
_CHECK_TRUE_PATH: str = convert_resource_path(
    "resources\\image\\checkTrue.png"
).replace("\\", "/")

# 동적 setStyleSheet에 쓰이는 색상 상수
# NavigationButton (사이드바) - 테마 전환 시 여기만 바꾸면 됨
NAV_BTN_BG: str = "#FFFFFF"
NAV_BTN_HOVER_BG: str = "#F0F0F0"
NAV_BTN_ACTIVE_BG: str = "#E0E0E0"
NAV_BTN_BORDER: str = "#b4b4b4"

# NavButton (시뮬레이터 상단) - 테마 전환 시 여기만 바꾸면 됨
SIM_NAV_BG: str = "rgb(255, 255, 255)"
SIM_NAV_HOVER_BG: str = "rgb(234, 234, 234)"
SIM_NAV_ACTIVE_BORDER: str = "#9180F7"
SIM_NAV_INACTIVE_BORDER: str = "#FFFFFF"

# SettingItem, LinkSkillEditor 활성/비활성 버튼 글자색
SETTING_BTN_ACTIVE_COLOR: str = "#000000"
SETTING_BTN_INACTIVE_COLOR: str = "#999999"

# NoticeContent 좌측 강조 바 색상
NOTICE_WARNING_ACCENT: str = "#E5AE45"
NOTICE_ERROR_ACCENT: str = "#F07C7C"

# value label 색상 (+/-)
VALUE_POSITIVE_COLOR: str = "#27AE60"
VALUE_NEGATIVE_COLOR: str = "#E74C3C"

# stat_label 색상 (시뮬레이터 결과)
STAT_POSITIVE_COLOR: str = "#27AE60"
STAT_NEGATIVE_COLOR: str = "#E74C3C"


# 그래프 테마 팔레트 구조
@dataclass(frozen=True)
class GraphPalette:
    card_background: str
    card_border: str
    tooltip_background: str
    tooltip_border: str
    tooltip_text: str
    canvas_background: str
    title_text: str
    axis_text: str
    skill_ratio_label_text: str
    dpm_median_bar: str
    dpm_center_bar: str
    dpm_hover_bar: str
    dpm_normal_bar: str
    ratio_series: tuple[str, ...]
    damage_max_line: str
    damage_mean_line: str
    damage_min_line: str
    guide_line: str
    contribution_series: tuple[str, ...]
    contribution_tooltip_point_fill: str


# 현재 화면과 동일한 라이트 그래프 팔레트 정의
LIGHT_GRAPH_PALETTE: GraphPalette = GraphPalette(
    card_background="#F8F8F8",
    card_border="#CCCCCC",
    tooltip_background="rgba(255, 255, 255, 0.8)",
    tooltip_border="gray",
    tooltip_text="#111111",
    canvas_background="#F8F8F8",
    title_text="black",
    axis_text="black",
    skill_ratio_label_text="black",
    dpm_median_bar="#4070FF",
    dpm_center_bar="#75A2FC",
    dpm_hover_bar="#BAD0FD",
    dpm_normal_bar="#F38181",
    ratio_series=(
        "#EF9A9A",
        "#90CAF9",
        "#A5D6A7",
        "#FFEB3B",
        "#CE93D8",
        "#F0B070",
        "#2196F3",
    ),
    damage_max_line="#F38181",
    damage_mean_line="#70AAF9",
    damage_min_line="#80C080",
    guide_line="gray",
    contribution_series=(
        "#EF9A9A",
        "#90CAF9",
        "#A5D6A7",
        "#FFEB3B",
        "#CE93D8",
        "#F0B070",
        "#2196F3",
    ),
    contribution_tooltip_point_fill="white",
)

# 라이트 테마 글로벌 QSS
LIGHT_THEME: str = f"""

/* ────────────────── 베이스 ────────────────── */
*:focus {{ outline: none; }}

/* 기본 글자색 라이트 팔레트 고정 */
QWidget {{
    color: #111111;
}}

QDialog {{
    background-color: #FFFFFF;
}}

/* 모든 QFrame 기본: 투명 (색이 있는 위젯은 아래 objectName 규칙으로 덮어씀) */
QFrame {{ background-color: transparent; }}

/* 기본 버튼 라이트 팔레트 고정 */
QPushButton {{
    background-color: #FFFFFF;
    color: #111111;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
}}
QPushButton:disabled {{
    color: #7A7A7A;
}}


/* ────────────────── 메인 윈도우 ────────────────── */
QWidget#mainWindow {{
    background-color: #FFFFFF;
}}

QPushButton#creatorLabel {{
    background-color: transparent;
    text-align: left;
    border: 0px;
}}


/* ────────────────── 탭 위젯 ────────────────── */
QTabWidget {{
    background: #eeeeff;
    border: 1px solid #cccccc;
    border-radius: 10px;
}}

QTabWidget::pane {{
    border: 1px solid #cccccc;
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
    border-top-right-radius: 10px;
    background: #eeeeff;
}}

QTabBar::tab {{
    background: #eeeeee;
    color: #111111;
    border: 1px solid #cccccc;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 6px 10px;
    margin-top: 0px;
}}

QTabBar::tab:selected {{ background: #eeeeff; }}
QTabBar::tab:hover    {{ background: #dddddd; }}

QTabBar::close-button {{
    image: url("{_CLOSE_BTN_PATH}");
    border-radius: 5px;
}}
QTabBar::close-button:hover   {{ background-color: #FF5555; }}
QTabBar::close-button:pressed {{ background-color: #CC0000; }}

QPushButton#tabAddButton {{
    border: 1px solid #cccccc;
    background: #eeeeff;
    border-radius: 4px;
}}
QPushButton#tabAddButton:hover {{ background: #dddddd; }}

/* Tab 내부 구분선 */
QFrame#tabDivider {{ background-color: #b4b4b4; }}


/* ────────────────── SkillPreview ────────────────── */
QFrame#skillPreview {{
    background-color: #ffffff;
    border-radius: 5px;
    border: 1px solid black;
}}


/* ────────────────── 아이콘 버튼 (무공비급·스킬) ────────────────── */
QPushButton#availScrollBtn,
QPushButton#availSkillBtn,
QPushButton#placedSkillBtn {{
    border: 0px;
    background-color: transparent;
    outline: none;
}}


/* ────────────────── 사이드바 ────────────────── */
QFrame#sidebar {{ background-color: #FFFFFF; }}

QScrollArea#sidebarScrollArea {{
    background-color: #FFFFFF;
    border: 0px solid black;
    border-right: 1px solid #bbbbbb;
}}

QFrame#navButtonsFrame {{ background-color: #FFFFFF; }}

QPushButton#sidebarNavButton {{
    background-color: {NAV_BTN_BG};
    border: 0px solid {NAV_BTN_BORDER};
}}
QPushButton#sidebarNavButton[variant="0"] {{
    border-top-width: 1px;
    border-right-width: 1px;
    border-bottom-width: 1px;
    border-left-width: 0px;
    border-top-left-radius: 0px;
    border-top-right-radius: 8px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}}
QPushButton#sidebarNavButton[variant="1"] {{
    border-top-width: 0px;
    border-right-width: 1px;
    border-bottom-width: 1px;
    border-left-width: 0px;
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}}
QPushButton#sidebarNavButton[variant="2"] {{
    border-top-width: 0px;
    border-right-width: 1px;
    border-bottom-width: 1px;
    border-left-width: 0px;
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}}
QPushButton#sidebarNavButton[variant="3"] {{
    border-top-width: 0px;
    border-right-width: 1px;
    border-bottom-width: 1px;
    border-left-width: 0px;
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 8px;
}}
QPushButton#sidebarNavButton[active=true] {{
    background-color: {NAV_BTN_ACTIVE_BG};
}}
QPushButton#sidebarNavButton:hover {{
    background-color: {NAV_BTN_HOVER_BG};
}}

/* 사이드바 Title 라벨 */
QLabel#sidebarTitle {{
    border: 0px solid black;
    border-radius: 10px;
    background-color: #CADEFC;
}}


/* ────────────────── 스킬 사용설정 ────────────────── */
QPushButton#selectedScrollButton {{
    background-color: #F4F8FD;
    border: 1px solid #CADEFC;
    border-radius: 10px;
    text-align: left;
}}
QPushButton#selectedScrollButton:hover {{ background-color: #E9F2FD; }}

QPushButton#editScrollBtn {{
    background-color: transparent;
    border: 1px solid #AAAAAA;
    border-radius: 5px;
    color: #444444;
    padding: 2px 10px;
}}
QPushButton#editScrollBtn:hover {{ background-color: #EEEEEE; }}

QPushButton#deleteScrollBtn {{
    background-color: transparent;
    border: 1px solid #E57373;
    border-radius: 5px;
    color: #E53935;
    padding: 2px 10px;
}}
QPushButton#deleteScrollBtn:hover {{ background-color: #FDECEA; }}

/* 옵션 라벨 글자색 */
QLabel#optionTitle {{ color: #4B5563; background-color: transparent; border: 0px; }}

QFrame#skillOptionCard {{
    background-color: #F8FAFD;
    border: 1px solid #DDE6F1;
    border-radius: 10px;
}}

/* 체크 버튼 (사용 여부·단독·단독스왑) */
QPushButton#checkBtn {{
    background-color: transparent;
    border-radius: 8px;
}}
QPushButton#checkBtn:hover {{ background-color: #dddddd; }}

QPushButton#priorityBtn {{
    background-color: #FFFFFF;
    border: 1px solid #C7D4E5;
    border-radius: 8px;
    padding: 2px 8px;
}}
QPushButton#priorityBtn:hover {{ background-color: #F1F5FA; }}

QFrame#skillSettingCard {{
    background-color: #FFFFFF;
    border: 1px solid #D7E2F0;
    border-radius: 12px;
}}


/* ────────────────── 연계스킬 목록 ────────────────── */
QFrame#linkSkillWidget {{
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 12px;
}}

/* 연계 구분선 */
QFrame#linkDivider {{ background-color: #F1F3F5; border: 0px; }}

/* 자동/수동 배지 */
QLabel#badgeAuto {{
    background-color: #E8F5E9;
    color: #2E7D32;
    border: 1px solid #C8E6C9;
    border-radius: 8px;
}}
QLabel#badgeManual {{
    background-color: #F1F3F5;
    color: #495057;
    border: 1px solid #DEE2E6;
    border-radius: 8px;
}}

/* 시작 키 라벨 */
QLabel#startKeyTitle {{
    color: #868E96;
    font-size: 12px;
    background: transparent;
    border: 0px;
}}
QLabel#startKeyValueSet {{
    background-color: #343A40;
    color: white;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 12px;
}}
QLabel#startKeyValueUnset {{
    color: #ADB5BD;
    font-size: 12px;
    background: transparent;
    border: 0px;
}}

/* 연계스킬 수정·삭제 버튼 */
QPushButton#linkEditBtn {{
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton#linkEditBtn:hover   {{ background-color: #2980b9; }}
QPushButton#linkEditBtn:pressed {{ background-color: #1f618d; }}

QPushButton#linkRemoveBtn {{
    background-color: transparent;
    color: #e74c3c;
    border: 1px solid #e74c3c;
    border-radius: 8px;
    padding: 8px;
    font-size: 12px;
}}
QPushButton#linkRemoveBtn:hover {{
    background-color: #e74c3c;
    color: white;
}}


/* ────────────────── 연계스킬 편집기 ────────────────── */
QPushButton#addSkillBtn {{
    background-color: transparent;
    border-radius: 18px;
}}
QPushButton#addSkillBtn:hover {{ background-color: #cccccc; }}

/* SettingItem 활성·비활성 버튼 (active 프로퍼티 사용) */
QPushButton#settingItemBtn[active=true]  {{ color: #000000; }}
QPushButton#settingItemBtn[active=false] {{ color: #999999; }}

QPushButton#skillItemBtn {{
    background-color: transparent;
    border: 0px;
    border-radius: 10px;
    outline: none;
}}
QPushButton#skillItemRemoveBtn {{ background-color: transparent; border-radius: 16px; }}
QPushButton#skillItemRemoveBtn:hover {{ background-color: #eeeeee; }}


/* ────────────────── GeneralSettings SettingItem 버튼 ────────────────── */
QPushButton#generalSettingBtn[active=true]  {{ color: #000000; }}
QPushButton#generalSettingBtn[active=false] {{ color: #999999; }}

QLabel#generalSettingTitle {{ border: 0px solid black; border-radius: 10px; }}


/* ────────────────── CustomLineEdit ────────────────── */
QLineEdit {{
    color: #111111;
    selection-background-color: #D9D9D9;
    selection-color: #111111;
}}
QLineEdit[valid=true] {{
    background-color: #f0f0f0;
    border: 1px solid #D9D9D9;
}}
QLineEdit[valid=false] {{
    background-color: #f0f0f0;
    border: 2px solid #FF6060;
}}
QLineEdit[radius="4"]  {{ border-radius: 4px; }}
QLineEdit[radius="6"]  {{ border-radius: 6px; }}
QLineEdit[radius="10"] {{ border-radius: 10px; }}


/* ────────────────── CustomComboBox ────────────────── */
QComboBox {{
    background-color: #f0f0f0;
    color: #111111;
    border: 1px solid #D9D9D9;
    border-radius: 4px;
}}
QComboBox::drop-down {{
    width: 20px;
    border-left-width: 1px;
    border-left-color: darkgray;
    border-left-style: solid;
}}
QComboBox::down-arrow {{
    image: url("{_DOWN_ARROW_PATH}");
    width: 16px;
    height: 16px;
}}
QComboBox QAbstractItemView {{
    background-color: #f0f0f0;
    color: #111111;
    border: 1px solid #D9D9D9;
    selection-background-color: #D9D9D9;
    selection-color: #111111;
}}


/* ────────────────── CheckBox ────────────────── */
QCheckBox {{
    background-color: transparent;
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid #C7D0DD;
    border-radius: 4px;
    background-color: #FFFFFF;
}}
QCheckBox::indicator:hover {{
    background-color: #F3F7FC;
    border-color: #B2BECD;
}}
QCheckBox::indicator:checked {{
    background-color: #4A90D9;
    border-color: #4A90D9;
    image: url("{_CHECK_TRUE_PATH}");
}}
QCheckBox::indicator:checked:hover {{
    background-color: #3A7BC8;
    border-color: #3A7BC8;
}}


/* ────────────────── ScrollBar ────────────────── */
QScrollBar:vertical {{
    background-color: #FFFFFF;
    width: 10px;
    margin: 0px;
    border: none;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background-color: #AEB4BE;
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: #8E97A4;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
    border: none;
    background: transparent;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background-color: #FFFFFF;
    height: 10px;
    margin: 0px;
    border: none;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background-color: #AEB4BE;
    min-width: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: #8E97A4;
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
    border: none;
    background: transparent;
}}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: transparent;
}}


/* ────────────────── Separator ────────────────── */
QFrame#separator {{ background-color: #E0E0E0; border: 0px; }}


/* ────────────────── SectionCard ────────────────── */
QFrame#SectionCard {{
    background-color: #FAFAFA;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
}}
QWidget#SectionCardContent {{ background-color: transparent; }}
QWidget#SectionCardHeader  {{ background-color: transparent; }}
QFrame#sectionCardAccentBar {{
    background-color: #4A90E2;
    border: 0px;
    border-radius: 2px;
}}
QLabel#sectionCardTitle    {{ background-color: transparent; border: 0px; color: #2C3E50; }}
QLabel#sectionCardSubTitle {{ background-color: transparent; border: 0px; color: #555555; }}


/* ────────────────── StyledButton ────────────────── */
QPushButton#styledButtonAdd {{
    background-color: #5AAA5A;
    color: white;
    border: 0px;
    border-radius: 4px;
    padding: 4px 12px;
}}
QPushButton#styledButtonAdd:hover,
QPushButton#styledButtonAdd:pressed {{ background-color: #4A9A4A; }}

QPushButton#styledButtonDanger {{
    background-color: #D94F4F;
    color: white;
    border: 0px;
    border-radius: 4px;
    padding: 4px 12px;
}}
QPushButton#styledButtonDanger:hover,
QPushButton#styledButtonDanger:pressed {{ background-color: #B83C3C; }}

QPushButton#styledButtonNormal {{
    background-color: #888888;
    color: white;
    border: 0px;
    border-radius: 4px;
    padding: 4px 12px;
}}
QPushButton#styledButtonNormal:hover,
QPushButton#styledButtonNormal:pressed {{ background-color: #6E6E6E; }}


/* ────────────────── 팝업 시스템 ────────────────── */

/* HoverCard */
QFrame#hoverCardContainer {{
    background-color: #110F17;
    border: 1px solid #5A5862;
    border-radius: 10px;
}}
QLabel#hoverCardTitle {{
    color: #F7F1A1;
    background-color: transparent;
    border: 0px;
}}
QLabel#hoverCardBody {{
    color: #D9D5E3;
    background-color: transparent;
    border: 0px;
}}

/* PopupHost 컨테이너 */
QFrame#popupContainer {{
    background-color: white;
    border-radius: 10px;
    border: none;
}}

/* NoticeHost 컨테이너 */
QFrame#noticeContainer {{
    background-color: #FFF9EE;
    border: 1px solid #E8DABE;
    border-radius: 10px;
}}

QFrame#noticeAccentBar[kind="warning"] {{
    background-color: {NOTICE_WARNING_ACCENT};
    border-radius: 3px;
}}
QFrame#noticeAccentBar[kind="error"] {{
    background-color: {NOTICE_ERROR_ACCENT};
    border-radius: 3px;
}}

/* 알림 닫기 버튼 */
QPushButton#noticeRemoveBtn {{
    background-color: transparent;
    border-radius: 12px;
}}
QPushButton#noticeRemoveBtn:hover {{ background-color: rgba(0, 0, 0, 20); }}

/* 알림 액션 버튼 */
QPushButton#noticeActionButton {{
    background-color: #86A7FC;
    border-radius: 4px;
}}
QPushButton#noticeActionButton:hover {{ background-color: #6498f0; }}

/* ActionListContent — 자식 QPushButton 스타일 */
QFrame#actionListContent QPushButton {{
    background-color: white;
    border-radius: 10px;
    border: none;
    padding: 2px;
    margin: 2px;
}}
QFrame#actionListContent QPushButton[selected=true] {{ background-color: #dddddd; }}
QFrame#actionListContent QPushButton:hover          {{ background-color: #cccccc; }}
QFrame#actionListContent QPushButton:!enabled       {{ background-color: #f0f0f0; }}

/* InputConfirm / KeyCapture 확인 버튼 & 라벨 */
QPushButton#popupConfirmBtn {{
    background-color: white;
    border-radius: 10px;
    border: 1px solid #bbbbbb;
}}
QPushButton#popupConfirmBtn:hover {{ background-color: #cccccc; }}

QLabel#keyCaptureLabel {{
    background-color: white;
    border-radius: 10px;
    border: 1px solid #bbbbbb;
    padding: 2px;
}}

/* 스킬·무공비급 선택 팝업 */
QFrame#skillScrollSelectPopup {{
    background-color: white;
    border: 1px solid gray;
    border-radius: 10px;
}}
QScrollArea#popupGridScrollArea {{
    background-color: white;
    border: 0px;
}}
QScrollArea#popupGridScrollArea QWidget#qt_scrollarea_viewport {{
    background-color: white;
}}
QWidget#popupGridContent {{ background-color: white; }}
QPushButton#gridSelectBtn {{
    background-color: transparent;
    border-radius: 10px;
    border: 0px;
    outline: none;
}}
QPushButton#gridAddBtn {{
    background-color: transparent;
    border: none;
    color: gray;
    padding: 2px 0px;
}}
QPushButton#gridAddBtn:hover {{ color: black; }}

/* 커스텀 무공비급 추가 다이얼로그 */
QDialog#customSkillDialog {{
    background-color: #FFFFFF;
}}
QScrollArea#dialogScrollArea {{
    border: none;
    background-color: #FFFFFF;
}}
QWidget#dialogScrollViewport {{
    background-color: #FFFFFF;
}}
QWidget#dialogScrollContent {{
    background-color: #FFFFFF;
}}
QLabel#dialogErrorLabel {{
    color: #E53935;
    border: none;
    background: transparent;
}}
QPushButton#dialogCancelBtn {{
    background-color: #F0F0F2;
    border: 1px solid #D0D5DD;
    border-radius: 6px;
    color: #555555;
    text-align: center;
}}
QPushButton#dialogCancelBtn:hover {{ background-color: #E4E4E8; }}

QPushButton#dialogConfirmBtn {{
    background-color: #4A90D9;
    border: none;
    border-radius: 6px;
    color: white;
    text-align: center;
}}
QPushButton#dialogConfirmBtn:hover {{ background-color: #3A7BC8; }}

QFrame#dialogCard {{
    background-color: #F8F9FA;
    border: 1px solid #E4E6EA;
    border-radius: 8px;
}}
QLabel#dialogSectionTitle {{
    font-weight: bold;
    color: #333333;
    border: none;
    background: transparent;
}}
QLabel#dialogFieldLabel {{
    color: #666666;
    border: none;
    background: transparent;
}}
QPushButton#dialogToggleBtn {{
    background-color: transparent;
    border: 1px solid #D0D5DD;
    border-radius: 4px;
    color: #666666;
    text-align: left;
    padding-left: 6px;
}}
QPushButton#dialogToggleBtn:hover {{ background-color: #EFEFEF; }}

/* 다이얼로그 내부 LineEdit (기본 LineEdit과 색상 다름) */
QDialog#customSkillDialog QLineEdit[valid=true] {{
    background-color: #FFFFFF;
    border: 1px solid #D0D5DD;
}}
QDialog#customSkillDialog QLineEdit[valid=false] {{
    background-color: #FFFFFF;
    border: 1px solid #E53935;
}}

/* 다이얼로그 내부 QComboBox */
QDialog#customSkillDialog QComboBox {{
    background-color: #FFFFFF;
    border: 1px solid #D0D5DD;
    border-radius: 4px;
    font-size: 9pt;
    padding-left: 4px;
}}
QDialog#customSkillDialog QComboBox::drop-down {{
    width: 16px;
    border: 0px;
}}
QDialog#customSkillDialog QComboBox::down-arrow {{
    image: url("{_DOWN_ARROW_PATH}");
    width: 12px;
    height: 12px;
}}


/* ────────────────── 시뮬레이터 UI ────────────────── */
QFrame#simMainFrame {{
    background-color: rgb(255, 255, 255);
    border: 0px solid;
}}
QScrollArea#simScrollArea {{
    background-color: #FFFFFF;
    border: 0px solid black;
    border-radius: 10px;
}}

/* 시뮬레이터 제목 라벨 */
QLabel#simTitle {{
    background-color: rgb(255, 255, 255);
    border: none;
    border-bottom: 1px solid #bbbbbb;
    padding: 10px 0;
}}

/* 시뮬레이터 상단 네비게이션 닫기 버튼 */
QPushButton#simNavCloseBtn {{
    background-color: rgb(255, 255, 255);
    border: none;
    border-radius: 10px;
}}
QPushButton#simNavCloseBtn:hover {{ background-color: rgb(234, 234, 234); }}

/* NavButton (활성·비활성) */
QPushButton#navBtn {{
    background-color: rgb(255, 255, 255);
    border: none;
    border-bottom: 2px solid #FFFFFF;
}}
QPushButton#navBtn:hover {{ background-color: rgb(234, 234, 234); }}
QPushButton#navBtn[active=true]  {{ border-bottom: 2px solid #9180F7; }}
QPushButton#navBtn[active=false] {{ border-bottom: 2px solid #FFFFFF; }}

/* 계산 오버레이 */
QFrame#calcOverlay {{ background-color: rgba(15, 23, 42, 110); }}
QFrame#calcOverlayCard {{
    background-color: #FFFFFF;
    border: 1px solid #D8DEE8;
    border-radius: 16px;
}}
QLabel#calcOverlayTitle   {{ background-color: transparent; border: 0px; color: #111827; }}
QLabel#calcOverlayMessage {{ background-color: transparent; border: 0px; color: #1F2937; }}
QLabel#calcOverlayDetail  {{ background-color: transparent; border: 0px; color: #6B7280; }}
QLabel#calcOverlayProgress {{ background-color: transparent; border: 0px; color: #4B5563; }}

QProgressBar#calcProgressBar {{
    background-color: #E5E7EB;
    border: 0px;
    border-radius: 6px;
}}
QProgressBar#calcProgressBar::chunk {{
    background-color: #9180F7;
    border-radius: 6px;
}}
QPushButton#calcCancelBtn {{
    background-color: #F3F4F6;
    border: 1px solid #D1D5DB;
    border-radius: 10px;
    color: #111827;
}}
QPushButton#calcCancelBtn:hover    {{ background-color: #E5E7EB; }}
QPushButton#calcCancelBtn:disabled {{
    background-color: #E5E7EB;
    color: #9CA3AF;
}}

/* 그래프 카드 */
QFrame#graphCard {{
    background-color: {LIGHT_GRAPH_PALETTE.card_background};
    border: 1px solid {LIGHT_GRAPH_PALETTE.card_border};
    border-radius: 10px;
}}

/* 그래프 캔버스 */
QWidget#dpmDistributionCanvas,
QWidget#skillDpsRatioCanvas,
QWidget#dmgCanvas,
QWidget#skillContributionCanvas {{
    border: 0px solid;
}}

/* 그래프 툴팁 */
QLabel#graphTooltipLabel {{
    background-color: {LIGHT_GRAPH_PALETTE.tooltip_background};
    color: {LIGHT_GRAPH_PALETTE.tooltip_text};
    padding: 5px;
    border: 1px solid {LIGHT_GRAPH_PALETTE.tooltip_border};
    border-radius: 10px;
}}

/* ResultsPage.Efficiency 흰 배경 */
QFrame#simEfficiency {{
    background-color: rgb(255, 255, 255);
    border: 0px solid;
}}


/* ── 칭호 목록 패널 ── */
QFrame#TitleEquippedPanel,
QFrame#TitleListPanel,
QFrame#TitleDetailPanel {{
    background-color: #FBFCFE;
    border: 1px solid #DDE5EF;
    border-radius: 8px;
}}
QScrollArea#titleListScrollArea {{
    background-color: transparent;
    border: 0px;
}}
QScrollArea#titleListScrollArea QWidget#qt_scrollarea_viewport {{
    background-color: transparent;
}}
QWidget#titleListScrollContent {{ background-color: transparent; }}

/* 칭호 편집 카드 */
QFrame#TitleCard {{
    background-color: #F8FAFC;
    border: 1px solid #DDE5EF;
    border-radius: 8px;
}}

/* 칭호 목록 선택 버튼 */
QPushButton#titleListSelectBtn {{
    background-color: #FFFFFF;
    color: #2C3E50;
    border: 1px solid #D9E0EA;
    border-radius: 6px;
    padding: 0px 124px 0px 12px;
    text-align: left;
}}
QPushButton#titleListSelectBtn:hover {{
    background-color: #F6FAFF;
    border: 1px solid #BFD4EC;
}}
QPushButton#titleListSelectBtn:checked {{
    background-color: #E8F2FF;
    border: 1px solid #4A90E2;
    color: #1F4E79;
}}

/* 칭호 장착/해제 버튼 */
QPushButton#titleEquipBtn[equipped=false] {{
    background-color: #4A90E2;
    color: white;
    border: 0px;
    border-radius: 4px;
    padding: 4px 12px;
}}
QPushButton#titleEquipBtn[equipped=false]:hover,
QPushButton#titleEquipBtn[equipped=false]:pressed {{
    background-color: #357ABD;
}}
QPushButton#titleEquipBtn[equipped=true] {{
    background-color: #C97A2B;
    color: white;
    border: 0px;
    border-radius: 4px;
    padding: 4px 12px;
}}
QPushButton#titleEquipBtn[equipped=true]:hover,
QPushButton#titleEquipBtn[equipped=true]:pressed {{
    background-color: #AD6420;
}}

/* 장착 패널 이름 라벨 */
QLabel#equippedNameLabel {{ color: #2C3E50; border: 0px; }}

/* 장착 패널 스탯 라벨 */
QLabel#equippedStatMuted {{ color: #7A8795; border: 0px; }}
QLabel#equippedStatValue {{ color: #2C3E50; border: 0px; }}

/* 패널 빈 상태 라벨 */
QLabel#panelEmptyLabel {{ color: #7A8795; border: 0px; }}


/* ── 부적 패널 ── */
QFrame#TalismanEquippedPanel,
QFrame#TalismanListPanel,
QFrame#TalismanDetailPanel {{
    background-color: #FBFCFE;
    border: 1px solid #DDE5EF;
    border-radius: 8px;
}}
QScrollArea#talismanListScrollArea {{
    background-color: transparent;
    border: 0px;
}}
QScrollArea#talismanListScrollArea QWidget#qt_scrollarea_viewport {{
    background-color: transparent;
}}
QWidget#talismanListScrollContent {{ background-color: transparent; }}

/* 부적 슬롯 패널 */
QFrame#TalismanEquippedSlotPanel {{
    background-color: #FFFFFF;
    border: 1px solid #D9E0EA;
    border-radius: 6px;
}}

/* 부적 슬롯 라벨 */
QLabel#slotTitleLabel {{ color: #5C6B7A; border: 0px; }}
QLabel#slotStatLabel[equipped=false] {{ color: #7A8795; border: 0px; }}
QLabel#slotStatLabel[equipped=true]  {{ color: #2C3E50; border: 0px; }}

/* 부적 슬롯 장착 버튼 */
QPushButton#slotEquipBtn {{
    background-color: #4A90E2;
    color: white;
    border: 0px;
    border-radius: 4px;
    padding: 4px 12px;
}}
QPushButton#slotEquipBtn:hover,
QPushButton#slotEquipBtn:pressed {{
    background-color: #357ABD;
}}
QPushButton#slotEquipBtn:disabled {{
    background-color: #C9D7E6;
    color: #F7FAFC;
}}

/* 부적 목록 선택 버튼 */
QPushButton#talismanListSelectBtn {{
    background-color: #FFFFFF;
    color: #2C3E50;
    border: 1px solid #D9E0EA;
    border-radius: 6px;
    padding: 0px 118px 0px 12px;
    text-align: left;
}}
QPushButton#talismanListSelectBtn:hover {{
    background-color: #F6FAFF;
    border: 1px solid #BFD4EC;
}}
QPushButton#talismanListSelectBtn:checked {{
    background-color: #E8F2FF;
    border: 1px solid #4A90E2;
    color: #1F4E79;
}}

/* 부적 장착 상태 라벨 */
QLabel#talismanEquippedStateLabel[state=unequipped] {{
    background-color: #EEF2F7;
    color: #5C6B7A;
    border: 0px;
    border-radius: 4px;
    padding: 4px 8px;
}}
QLabel#talismanEquippedStateLabel[state=equipped] {{
    background-color: #EAF5EA;
    color: #2F855A;
    border: 0px;
    border-radius: 4px;
    padding: 4px 8px;
}}

/* 부적 편집 카드 */
QFrame#TalismanCard {{
    background-color: #F8FAFC;
    border: 1px solid #DDE5EF;
    border-radius: 8px;
}}

/* 부적 등급 선택 버튼 */
QPushButton#talismanGradeBtn {{
    background-color: #FFFFFF;
    color: #2C3E50;
    border: 1px solid #D9E0EA;
    border-radius: 6px;
    padding: 6px 12px;
}}
QPushButton#talismanGradeBtn:hover {{
    background-color: #F6FAFF;
    border: 1px solid #BFD4EC;
}}
QPushButton#talismanGradeBtn:checked {{
    background-color: #E8F2FF;
    border: 1px solid #4A90E2;
    color: #1F4E79;
}}

/* 부적 선택 목록 무공비급 영역 */
QScrollArea#talismanTemplateScrollArea {{
    background-color: #FFFFFF;
    border: 1px solid #D9E0EA;
    border-radius: 6px;
}}
QScrollArea#talismanTemplateScrollArea QWidget#qt_scrollarea_viewport {{
    background-color: #FFFFFF;
}}
QWidget#talismanTemplateScrollContent {{ background-color: #FFFFFF; }}

/* 부적 템플릿 선택 버튼 */
QPushButton#talismanTemplateBtn {{
    background-color: #FFFFFF;
    color: #2C3E50;
    border: 1px solid #D9E0EA;
    border-radius: 6px;
    padding: 0px 12px;
    text-align: left;
}}
QPushButton#talismanTemplateBtn:hover {{
    background-color: #F6FAFF;
    border: 1px solid #BFD4EC;
}}
QPushButton#talismanTemplateBtn:checked {{
    background-color: #E8F2FF;
    border: 1px solid #4A90E2;
    color: #1F4E79;
}}

/* 부적 스탯 미리보기 라벨 */
QLabel#talismanPreviewLabel {{ color: #5C6B7A; border: 0px; }}


/* ── 결과 목록 ── */

/* ResultList 값 라벨 부호 색상 */
QLabel#resultValueLabel[sign=positive] {{ color: #27AE60; }}
QLabel#resultValueLabel[sign=negative] {{ color: #E74C3C; }}
QLabel#resultValueLabel[sign=neutral]  {{ color: inherit; }}

/* PowerResultList 행 */
QFrame#powerResultRow[selected=true] {{
    background-color: #EBF5FB;
    border-radius: 4px;
    border: 0px;
}}
QFrame#powerResultRow[selected=false] {{
    background-color: transparent;
    border: 0px;
}}

/* PowerResultList 라벨 */
QLabel#powerResultLabel {{ background: transparent; border: 0px; color: #2C3E50; }}

/* RankedResultList */
QLabel#rankedBadgeLabel {{ color: #F39C12; background: transparent; border: 0px; }}
QLabel#rankedTitleLabel {{ background: transparent; border: 0px; }}
QFrame#rankedBarContainer {{
    background-color: #E8E8E8;
    border-radius: 3px;
    border: 0px;
}}
QFrame#rankedBarFill[sign="positive"] {{
    background-color: #27AE60;
    border-radius: 3px;
    border: 0px;
}}
QFrame#rankedBarFill[sign="negative"] {{
    background-color: #E74C3C;
    border-radius: 3px;
    border: 0px;
}}

/* 결과 뷰 구분선 */
QFrame#resultsVSep {{ background-color: #E0E0E0; border: 0px; }}

/* 결과 뷰 소제목 */
QLabel#resultsSubTitle {{
    background-color: transparent;
    border: 0px;
    color: #555555;
}}

/* OverallStatsGrid */
QFrame#statsGridCell {{
    background-color: #F5F5F5;
    border-radius: 4px;
    border: 0px;
}}
QLabel#statsGridCellLabel {{ color: #555555; background: transparent; border: 0px; }}
QLabel#statsGridCellValue {{ color: #2C3E50; background: transparent; border: 0px; }}
QLabel#statsGridUnavailLabel {{ color: #888888; background: transparent; border: 0px; }}


/* ── 분석 카드 ── */
QFrame#analysisCard {{
    background-color: #F8F8F8;
    border: 1px solid #CCCCCC;
    border-left: 0px solid;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
}}
QLabel#analysisCardLabel {{ background-color: transparent; border: 0px solid; }}
QFrame#analysisAccentBar[slot="0"] {{
    background-color: rgb(255, 130, 130);
    border: 0px solid;
    border-radius: 0px;
    border-left: 1px solid #CCCCCC;
}}
QFrame#analysisAccentBar[slot="1"] {{
    background-color: rgb(255, 230, 140);
    border: 0px solid;
    border-radius: 0px;
    border-left: 1px solid #CCCCCC;
}}
QFrame#analysisAccentBar[slot="2"] {{
    background-color: rgb(170, 230, 255);
    border: 0px solid;
    border-radius: 0px;
    border-left: 1px solid #CCCCCC;
}}
QFrame#analysisAccentBar[slot="3"] {{
    background-color: rgb(150, 225, 210);
    border: 0px solid;
    border-radius: 0px;
    border-left: 1px solid #CCCCCC;
}}
QLabel#statisticNameLabel {{
    background-color: transparent;
    border: 0px solid;
    color: #A0A0A0;
}}
QLabel#statisticValueLabel {{ background-color: transparent; border: 0px solid; }}


/* ── PowerLabels ── */
QFrame#powerLabels {{ background-color: white; border: 0px solid; }}
QLabel#powerLabelHeader[slot="0"] {{
    background-color: rgb(255, 130, 130);
    border: 1px solid rgb(255, 130, 130);
    border-bottom: 0px solid;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}}
QLabel#powerLabelNumber[slot="0"] {{
    background-color: rgba(255, 130, 130, 120);
    border: 1px solid rgb(255, 130, 130);
    border-top: 0px solid;
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
}}
QLabel#powerLabelHeader[slot="1"] {{
    background-color: rgb(255, 230, 140);
    border: 1px solid rgb(255, 230, 140);
    border-bottom: 0px solid;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}}
QLabel#powerLabelNumber[slot="1"] {{
    background-color: rgba(255, 230, 140, 120);
    border: 1px solid rgb(255, 230, 140);
    border-top: 0px solid;
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
}}
QLabel#powerLabelHeader[slot="2"] {{
    background-color: rgb(170, 230, 255);
    border: 1px solid rgb(170, 230, 255);
    border-bottom: 0px solid;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}}
QLabel#powerLabelNumber[slot="2"] {{
    background-color: rgba(170, 230, 255, 120);
    border: 1px solid rgb(170, 230, 255);
    border-top: 0px solid;
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
}}
QLabel#powerLabelHeader[slot="3"] {{
    background-color: rgb(150, 225, 210);
    border: 1px solid rgb(150, 225, 210);
    border-bottom: 0px solid;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}}
QLabel#powerLabelNumber[slot="3"] {{
    background-color: rgba(150, 225, 210, 120);
    border: 1px solid rgb(150, 225, 210);
    border-top: 0px solid;
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
}}
QLabel#powerLabelHeader[slot="4"] {{
    background-color: rgb(210, 180, 255);
    border: 1px solid rgb(210, 180, 255);
    border-bottom: 0px solid;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}}
QLabel#powerLabelNumber[slot="4"] {{
    background-color: rgba(210, 180, 255, 120);
    border: 1px solid rgb(210, 180, 255);
    border-top: 0px solid;
    border-top-left-radius: 0px;
    border-top-right-radius: 0px;
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
}}


/* ── SkillInput 라벨 ── */
QLabel#skillInputLabel {{ border: 0px solid; border-radius: 4px; }}

"""

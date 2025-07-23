from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QColor
from PyQt6.QtWidgets import (
    QLineEdit,
    QComboBox,
    QLabel,
    QWidget,
    QGraphicsDropShadowEffect,
)

from dataclasses import dataclass, field


class CustomLineEdit(QLineEdit):
    """
    유저 입력을 받는 라인에딧 위젯
    """

    def __init__(
        self,
        parent: QWidget,
        connected_function=None,
        text: str = "",
        point_size: int = 14,
    ) -> None:
        super().__init__(text, parent)

        from .shared_data import UI_Variable

        ui_var = UI_Variable()

        self.setFont(CustomFont(point_size))
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.setStyleSheet(
            f"QLineEdit {{ background-color: {ui_var.sim_input_colors[0]}; border: 1px solid {ui_var.sim_input_colors[1]}; border-radius: 4px; }}"
        )

        if connected_function:
            self.textChanged.connect(connected_function)


class CustomComboBox(QComboBox):
    """
    유저 입력을 받는 콤보박스 위젯
    """

    def __init__(
        self,
        parent: QWidget,
        items: list[str],
        connected_function=None,
        point_size: int = 10,
    ) -> None:
        super().__init__(parent)

        from .shared_data import UI_Variable

        ui_var = UI_Variable()

        self.setFont(CustomFont(point_size))
        self.addItems(items)
        self.setStyleSheet(ui_var.comboboxStyle)

        if connected_function:
            self.currentIndexChanged.connect(connected_function)


class SkillImage(QLabel):
    """
    스킬 아이콘만을 표시하는 위젯
    """

    def __init__(
        self, parent: QWidget, pixmap: QPixmap, size: int, x: int, y: int
    ) -> None:
        super().__init__(parent)

        self.setStyleSheet("QLabel { background-color: transparent; border: 0px; }")

        pixmap = pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.setPixmap(pixmap)
        self.setFixedSize(size, size)
        self.move(x, y)


class CustomShadowEffect(QGraphicsDropShadowEffect):
    """
    위젯 그림자 효과
    """

    def __init__(self, offset_x=5, offset_y=5, blur_radius=10, transparent=100):
        super().__init__()

        self.setBlurRadius(blur_radius)
        self.setColor(QColor(0, 0, 0, transparent))
        self.setOffset(offset_x, offset_y)


class CustomFont(QFont):
    """
    커스텀 폰트 클래스
    """

    def __init__(self, point_size: int = 10, font_name: str = "Noto Sans KR") -> None:
        super().__init__(font_name, point_size)

        self.setStyleHint(QFont.StyleHint.SansSerif)
        self.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        # 폰트 안티에일리어싱 설정
        self.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)


@dataclass
class SimBuff:
    """
    시뮬레이션에서 버프의 정보를 담는 클래스
    """

    start_time: float
    end_time: float
    stat: str
    value: float
    skill_name: str


@dataclass
class SimAttack:
    """
    시뮬레이션에서 공격의 정보를 담는 클래스
    """

    skill_name: str
    time: float
    damage: float


@dataclass
class SimSkillApplyDelay:
    """
    시뮬레이션에서 스킬 사용을 적용하기까지 지연 정보를 담는 클래스
    """

    # 스킬 슬롯
    skill: int | None = None
    # 지연 시간
    delay: int | None = None

    def clear(self) -> None:
        """
        정보를 None으로 초기화하는 메서드
        """

        self.skill = None
        self.delay = None


@dataclass
class SimSkill:
    """
    시뮬레이션에서 스킬의 정보를 담는 클래스
    """

    # 스킬 슬롯 번호
    skill: int

    # 사용 시간
    time: float

    # 스킬 콤보 번호
    combo: int


@dataclass(unsafe_hash=True)
class Stats:
    """
    스탯 클래스
    """

    # 공격력
    ATK: int | float = 0
    # 방어력
    DEF: int | float = 0
    # 파괴력
    PWR: int | float = 0
    # 근력
    STR: int | float = 0
    # 지력
    INT: int | float = 0
    # 경도 RESISTANCE
    RES: int | float = 0
    # 치명타확률
    CRIT_RATE: int | float = 0
    # 치명타데미지
    CRIT_DMG: int | float = 0
    # 보스데미지
    BOSS_DMG: int | float = 0
    # 명중률
    ACC: int | float = 0
    # 회피율
    DODGE: int | float = 0
    # 상태이상저항
    STATUS_RES: int | float = 0
    # 내공
    NAEGONG: int = 0
    # 체력
    HP: int | float = 0
    # 공격속도
    ATK_SPD: int | float = 0
    # 포션회복량
    POT_HEAL: int | float = 0
    # 운
    LUK: int | float = 0
    # 경험치획득량
    EXP: int | float = 0

    def copy(self) -> "Stats":
        """
        현재 Stats 객체를 복사하여 새로운 객체를 반환
        """

        return Stats(
            ATK=self.ATK,
            DEF=self.DEF,
            PWR=self.PWR,
            STR=self.STR,
            INT=self.INT,
            RES=self.RES,
            CRIT_RATE=self.CRIT_RATE,
            CRIT_DMG=self.CRIT_DMG,
            BOSS_DMG=self.BOSS_DMG,
            ACC=self.ACC,
            DODGE=self.DODGE,
            STATUS_RES=self.STATUS_RES,
            NAEGONG=self.NAEGONG,
            HP=self.HP,
            ATK_SPD=self.ATK_SPD,
            POT_HEAL=self.POT_HEAL,
            LUK=self.LUK,
            EXP=self.EXP,
        )

    def get_stat_from_name(self, stat: str) -> int | float:
        """
        특정 스탯의 값을 반환
        """

        if hasattr(self, stat):
            return getattr(self, stat)

        else:
            raise AttributeError(f"{stat} 항목이 존재하지 않습니다.")

    def get_stat_from_index(self, index: int) -> int | float:
        """
        인덱스의 스탯의 값을 반환
        """

        if 0 <= index < len(self.__dataclass_fields__):
            return list(self.__dict__.values())[index]

        else:
            raise IndexError(f"{index} 번째 항목이 존재하지 않습니다.")

    def set_stat_from_name(self, stat: str, value: float | int) -> None:
        """
        스탯을 현재 Stats 객체에 설정
        """

        if hasattr(self, stat):
            setattr(self, stat, value)

            # 스탯을 설정한 후 캐스팅
            self.cast()

        else:
            raise AttributeError(f"{stat} 항목이 존재하지 않습니다.")

    def set_stat_from_index(self, index: int, value: float | int) -> None:
        """
        스탯을 현재 Stats 객체에 설정
        """

        if 0 <= index < len(self.__dataclass_fields__):
            # 인덱스에 해당하는 스탯 이름 가져오기
            stat: str = list(self.__dataclass_fields__.keys())[index]

            # 스탯 설정
            setattr(self, stat, value)

            # 스탯을 설정한 후 캐스팅
            self.cast()

        else:
            raise IndexError(f"{index} 번째 항목이 존재하지 않습니다.")

    def add_stat_from_name(self, stat: str, value: float | int) -> None:
        """
        스탯을 현재 Stats 객체에서 더함
        """

        current_value: int | float = self.get_stat_from_name(stat=stat)
        self.set_stat_from_name(stat=stat, value=current_value + value)

        # 스탯을 설정한 후 캐스팅
        self.cast()

    def add_stat_from_index(self, index: int, value: float | int) -> None:
        """
        스탯을 현재 Stats 객체에서 더함
        """

        current_value: int | float = self.get_stat_from_index(index=index)
        self.set_stat_from_index(index=index, value=current_value + value)

        # 스탯을 설정한 후 캐스팅
        self.cast()

    def apply_buff(self, buff: SimBuff) -> None:
        """
        버프를 현재 Stats 객체에 적용
        """

        current_value: int | float = self.get_stat_from_name(stat=buff.stat)
        setattr(self, buff.stat, current_value + buff.value)

        # 버프가 적용된 후 스탯을 캐스팅
        self.cast()

    def cast(self) -> None:
        """
        스탯들을 특정 타입들로 변환
        """

        if isinstance(self.NAEGONG, float):
            self.NAEGONG = int(self.NAEGONG)


@dataclass
class SimAnalysis:
    """
    시뮬레이션 분석 결과를 담는 클래스
    """

    title: str

    value: str

    min: str
    max: str

    std: str

    p25: str
    p50: str
    p75: str

    def get_data_from_str(self, data_name: str) -> str:
        """
        결과의 세부 정보를 반환
        """

        if hasattr(self, data_name):
            return getattr(self, data_name)

        else:
            raise AttributeError(f"{data_name} 항목이 존재하지 않습니다.")


@dataclass
class SimResult:
    """
    시뮬레이션 결과를 담는 클래스
    """

    powers: list[float]
    analysis: list[SimAnalysis] = field(default_factory=list)
    deterministic_boss_attacks: list[SimAttack] = field(default_factory=list)
    random_boss_attacks: list[list[SimAttack]] = field(default_factory=list)

    str_powers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """
        클래스 초기화 후 실행되는 메서드
        powers -> str_powers 변환해서 저장
        """

        self.str_powers = [str(int(i)) for i in self.powers]

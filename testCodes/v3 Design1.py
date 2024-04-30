import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QLineEdit,
)
from PyQt5.QtGui import (
    QPainter,
    QPen,
    QFont,
    QColor,
    QPixmap,
    QIcon,
    QBrush,
    QTransform,
    QDragEnterEvent,
)
from PyQt5.QtCore import Qt, QSize, QTimer
from functools import partial
from webbrowser import open_new
from requests import get


def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class MyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setFont()
        self.resetVar()
        self.setWindowIcon(QIcon(resource_path("resource//icon.png")))
        self.dataLoad()
        self.initUI()

        delay_timer = QTimer(self)
        delay_timer.singleShot(1000, self.version_check)  # 1000 밀리초 = 1초

    def dragEnterEvent(self, e: QDragEnterEvent):
        # e.accept()
        print(e)

    def resetVar(self):
        self.activePopup = ""
        self.activeErrorPopup = []
        self.activeErrorPopupCount = 0
        self.serverList = [
            "한월 RPG",
        ]
        self.jobList = [
            ["검호", "검문", "술사", "도사", "빙궁", "귀궁", "도제", "살수"],
        ]
        self.skillCooltimeList = [
            [
                [1.0, 1.5, 2.5, 3.0, 3.5, 5],
                [1.0, 1.5, 2.5, 3.0, 3.5, 5],
                [1.0, 1.5, 2.5, 3.0, 3.5, 5],
                [1.0, 1.5, 2.5, 3.0, 3.5, 5],
                [1.0, 1.5, 2.5, 3.0, 3.5, 5],
                [1.0, 1.5, 2.5, 3.0, 3.5, 5],
            ]
        ]
        self.skillComboCountList = [
            [
                [2, 3, 0, 2, 4, 0],
                [2, 3, 0, 2, 4, 0],
                [2, 3, 0, 2, 4, 0],
                [2, 3, 0, 2, 4, 0],
                [2, 3, 0, 2, 4, 0],
                [2, 3, 0, 2, 4, 0],
            ]
        ]
        self.ComboSelectionList = [-1, -1]

    def setFont(self):
        self.font10 = QFont("맑은 고딕", 10)
        self.font12 = QFont("맑은 고딕", 12)
        self.font12.setBold(True)
        self.font24 = QFont("맑은 고딕", 24)
        self.font24.setBold(True)
        self.font32 = QFont("맑은 고딕", 32)
        self.font32.setBold(True)
        self.font20 = QFont("맑은 고딕", 20)
        self.font20.setBold(True)
        self.font16 = QFont("맑은 고딕", 16)
        self.font16.setBold(True)

    def adjustFontSize(self, label, text, maxSize):
        label.setText(text)

        width = label.width()
        height = label.height()

        size = 1

        font = QFont("맑은 고딕")
        font.setBold(True)
        font.setPointSize(size)
        label.setFont(font)

        while (
            label.fontMetrics().boundingRect(text).width() < width
            and label.fontMetrics().boundingRect(text).height() < height
            and size <= maxSize
        ):
            font.setPointSize(size)
            label.setFont(font)
            size += 1

        size -= 3
        font.setPointSize(size)
        label.setFont(font)

    def limit_text(self, text, widget):
        font_metrics = widget.fontMetrics()
        max_width = widget.width() - 40

        for i in range(len(text), 0, -1):
            if font_metrics.boundingRect(text[:i]).width() < max_width:
                return text[:i]

        return ""

    def isKeyUsing(self, key):
        usingKey = []
        if self.activeStartKeySlot == 1:
            usingKey.append(self.inputStartKey)
        else:
            usingKey.append("F9")

        for i in self.skillKeys:
            usingKey.append(i)

        for i in self.comboConnection:
            usingKey.append(i[2])

        return True if key in usingKey else False

    def version_check(self):
        try:
            response = get(
                "https://api.github.com/repos/pro-days/skillmacro/releases/latest"
            )
            self.recentVersion = response.json()["name"]
            if response.status_code == 200:
                if version != self.recentVersion:
                    self.update_url = response.json()["html_url"]
                    self.makeNoticePopup("RequireUpdate")
            else:
                self.makeNoticePopup("FailedUpdateCheck")
        except:
            self.makeNoticePopup("FailedUpdateCheck")

    def initUI(self):
        self.setWindowTitle("데이즈 스킬매크로 " + version)
        self.setStyleSheet("background-color: white;")
        self.setMinimumSize(1470, 815)
        self.setGeometry(300, 200, 1470, 815)

        self.labelCreator = QPushButton(
            "제작자: 프로데이즈  |  디스코드: prodays", self
        )
        self.labelCreator.setFont(self.font10)
        self.labelCreator.setStyleSheet(
            "background-color: transparent; text-align: left;"
        )
        self.labelCreator.clicked.connect(
            lambda: open_new("https://github.com/Pro-Days")
        )
        self.labelCreator.setFixedSize(500, 24)
        self.labelCreator.move(2, self.height() - 25)

        # 위젯 배치

        self.tabButtonList = []
        self.tabList = []
        self.tabRemoveList = []
        for tabNum in range(len(self.tabNames)):
            tabBackground = QLabel("", self)
            if tabNum == self.recentPreset:
                tabBackground.setStyleSheet(
                    """background-color: #eeeef5; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )
            else:
                tabBackground.setStyleSheet(
                    """background-color: #cccccc; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )
            tabBackground.setFixedSize(250, 50)
            tabBackground.move(340 + 250 * tabNum, 20)
            tabBackground.setGraphicsEffect(self.getShadow(5, -2))

            tabButton = QPushButton("", self)
            tabButton.setFont(self.font12)
            tabButton.setFixedSize(240, 40)
            tabButton.setText(self.limit_text(f" {self.tabNames[tabNum]}", tabButton))
            tabButton.clicked.connect(partial(lambda x: self.onTabClick(x), tabNum))
            if tabNum == self.recentPreset:
                tabButton.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #eeeef5; border-radius: 15px; text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #fafaff;
                    }
                """
                )
            else:
                tabButton.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #cccccc; border-radius: 15px; text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #dddddd;
                    }
                """
                )
            tabButton.move(345 + 250 * tabNum, 25)

            tabRemoveButton = QPushButton("", self)
            tabRemoveButton.clicked.connect(
                partial(lambda x: self.onTabRemoveClick(x), tabNum)
            )
            tabRemoveButton.setFont(self.font16)
            tabRemoveButton.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent; border-radius: 20px;
                }
                QPushButton:hover {
                    background-color: #dddddd;
                }
            """
            )
            pixmap = QPixmap(f"resource/x.png")
            tabRemoveButton.setIcon(QIcon(pixmap))
            tabRemoveButton.setFixedSize(40, 40)
            tabRemoveButton.move(545 + 250 * tabNum, 25)

            self.tabButtonList.append(tabButton)
            self.tabList.append(tabBackground)
            self.tabRemoveList.append(tabRemoveButton)

        self.tabAddButton = QPushButton("", self)
        self.tabAddButton.clicked.connect(self.onTabAddClick)
        self.tabAddButton.setFont(self.font16)
        self.tabAddButton.setStyleSheet(
            """
            QPushButton {
                background-color: transparent; border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )
        pixmap = QPixmap(f"resource/plus.png")
        self.tabAddButton.setIcon(QIcon(pixmap))
        self.tabAddButton.setFixedSize(40, 40)
        self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)

        # 스킬
        self.skillColorList = [
            "#E63946",
            "#EC9A9A",
            "#C1BADE",
            "#A8DADC",
            "#457B9D",
            "#1D3557",
        ]
        self.skillFrameList = []
        self.skillImageList = []
        self.skillBarList = []
        self.skillKeyList = []
        self.skillComboList = []
        self.skillSelectionList = []
        for skillIndex in range(6):
            skillFrame = QFrame(self)
            skillFrame.setStyleSheet(
                f"background-color: {self.skillColorList[skillIndex]}; border-radius: 15px;"
            )
            skillFrame.setFixedSize(150, 380)
            skillFrame.move(370 + (30 + 150) * skillIndex, 128)
            skillFrame.setGraphicsEffect(self.getShadow())

            # skillBarButton = QPushButton("", skillFrame)
            # skillBarButton.clicked.connect(
            #     partial(lambda x: self.onSkillBarClick(x), skillIndex)
            # )
            # skillBarButton.setStyleSheet(
            #     """
            #     QPushButton {
            #         background-color: #b0b0b0; border-radius: 5px;
            #     }
            # """
            # )
            # skillBarButton.setFont(self.font24)
            # skillBarButton.setFixedSize(80, 10)
            # skillBarButton.move(35, 15)
            # skillBarButton.setGraphicsEffect(self.getShadow())

            skillImageButton = QPushButton("", skillFrame)
            skillImageButton.setStyleSheet("background-color: rgba(255, 255, 255, 0);")
            pixmap = QPixmap(
                f"resource/skill/{self.serverID}/{self.jobID}/{self.skillList[skillIndex]}.png"
            )
            skillImageButton.clicked.connect(
                partial(lambda x: self.onSkillClick(x), skillIndex)
            )
            skillImageButton.setIcon(QIcon(pixmap))
            skillImageButton.setIconSize(QSize(96, 96))
            skillImageButton.move(25, 25)
            # skillImageButton.setGraphicsEffect(self.getShadow())

            skillButtonKey = QPushButton(self.skillKeys[skillIndex], skillFrame)
            skillButtonKey.clicked.connect(
                partial(lambda x: self.onSkillKeyClick(x), skillIndex)
            )
            skillButtonKey.setStyleSheet(
                """
                QPushButton {
                    background-color: white; border-radius: 15px;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
            """
            )
            self.adjustFontSize(skillButtonKey, self.skillKeys[skillIndex], 24)
            skillButtonKey.setFixedSize(110, 80)
            skillButtonKey.move(20, 203)
            skillButtonKey.setGraphicsEffect(self.getShadow())

            skillButtonCombo = QPushButton("콤보", skillFrame)
            skillButtonCombo.clicked.connect(
                partial(lambda x: self.onSkillComboClick(x), skillIndex)
            )
            if self.comboBool[skillIndex]:
                skillButtonCombo.setStyleSheet(
                    """
                    QPushButton {
                        background-color: white; border-radius: 15px; color: rgb(0, 0, 0);
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
                )
            else:
                skillButtonCombo.setStyleSheet(
                    """
                    QPushButton {
                        background-color: white; border-radius: 15px; color: #999999;
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
                )

            skillButtonCombo.setFont(self.font24)
            skillButtonCombo.setFixedSize(110, 80)
            skillButtonCombo.move(20, 310)
            skillButtonCombo.setGraphicsEffect(self.getShadow())

            skillSelectionButton = QPushButton("", self)
            skillSelectionButton.clicked.connect(
                partial(lambda x: self.onSkillSelectionClick(x), skillIndex)
            )
            skillSelectionButton.setStyleSheet(
                """
                QPushButton {
                    background-color: white; border-radius: 10px; border: 1px solid black;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
            """
            )
            skillSelectionButton.setFont(self.font24)
            skillSelectionButton.setFixedSize(20, 20)
            skillSelectionButton.move(435 + (30 + 150) * skillIndex, 518)
            skillSelectionButton.setGraphicsEffect(self.getShadow())

            self.skillFrameList.append(skillFrame)
            # self.skillBarList.append(skillBarButton)
            self.skillImageList.append(skillImageButton)
            self.skillKeyList.append(skillButtonKey)
            self.skillComboList.append(skillButtonCombo)
            self.skillSelectionList.append(skillSelectionButton)

        self.comboConnectionButtonList = []
        for i, j in enumerate(self.comboConnection):
            comboConnectionButton = QPushButton(self.comboConnection[i][2], self)
            self.adjustFontSize(comboConnectionButton, self.comboConnection[i][2], 24)
            comboConnectionButton.clicked.connect(
                partial(lambda x: self.onComboConnectionClick(x), i)
            )
            comboConnectionButton.setStyleSheet(
                """
                QPushButton {
                    background-color: #eeeef5; border-radius: 5px; border: 3px solid black;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
            """
            )
            # comboConnectionButton.setFont(self.font20)
            comboConnectionButton.setFixedSize(50, 50)
            startX = 445 + (30 + 150) * j[0]
            endX = 445 + (30 + 150) * j[1]
            comboConnectionButton.move(round((startX + endX) * 0.5) - 25, 553 + 70 * i)

            self.comboConnectionButtonList.append(comboConnectionButton)

        ## 사이트바
        # 설정 레이블
        self.labelSettings = QLabel("설정", self)
        self.labelSettings.setFont(self.font24)
        self.labelSettings.setStyleSheet(
            "border: 0px solid black; border-radius: 10px; background-color: #CADEFC;"
        )
        self.labelSettings.setFixedSize(200, 100)
        self.labelSettings.setAlignment(Qt.AlignCenter)
        self.labelSettings.move(60, 20)
        self.labelSettings.setGraphicsEffect(self.getShadow())

        # 서버 - 직업
        self.labelServerJob = self.getSettingName("서버 - 직업", 70, 160)
        self.buttonServerList = self.getSettingButton(
            self.serverList[self.serverID], 30, 220, self.onServerClick
        )
        self.buttonJobList = self.getSettingButton(
            self.jobList[self.serverID][self.jobID], 170, 220, self.onJobClick
        )

        # 딜레이
        self.labelDelay = self.getSettingName("딜레이", 70, 160 + 130)
        if self.activeDelaySlot == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.buttonDefaultDelay = self.getSettingCheck(
            "기본: 15", 30, 220 + 130, self.onDefaultDelayClick, disable=temp[0]
        )
        self.buttonInputDelay = self.getSettingCheck(
            str(self.inputDelay),
            170,
            220 + 130,
            self.onInputDelayClick,
            disable=temp[1],
        )

        # 쿨타임 감소
        self.labelCooltime = self.getSettingName("쿨타임 감소", 70, 160 + 130 * 2)
        if self.activeCooltimeSlot == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.buttonDefaultCooltime = self.getSettingCheck(
            "기본: 0", 30, 220 + 130 * 2, self.onDefaultCooltimeClick, disable=temp[0]
        )
        self.buttonInputCooltime = self.getSettingCheck(
            str(self.inputCooltime),
            170,
            220 + 130 * 2,
            self.onInputCooltimeClick,
            disable=temp[1],
        )

        # 시작키 설정
        self.labelStartKey = self.getSettingName("시작키 설정", 70, 160 + 130 * 3)
        if self.activeStartKeySlot == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.buttonDefaultStartKey = self.getSettingCheck(
            "기본: F9", 30, 220 + 130 * 3, self.onDefaultStartKeyClick, disable=temp[0]
        )
        self.buttonInputStartKey = self.getSettingCheck(
            str(self.inputStartKey),
            170,
            220 + 130 * 3,
            self.onInputStartKeyClick,
            disable=temp[1],
        )

        # 마우스 클릭
        self.labelMouse = self.getSettingName("마우스 클릭", 70, 160 + 130 * 4)
        if self.activeMouseClickSlot == 0:
            temp = [False, True]
        else:
            temp = [True, False]
        self.button1stMouseType = self.getSettingCheck(
            "스킬 사용시", 30, 220 + 130 * 4, self.on1stMouseTypeClick, disable=temp[0]
        )
        self.button2ndMouseType = self.getSettingCheck(
            "평타 포함",
            170,
            220 + 130 * 4,
            self.on2ndMouseTypeClick,
            disable=temp[1],
        )

        self.show()

    def onSkillSelectionClick(self, num):
        index = -1
        for i, j in enumerate(self.comboConnection):
            if j[0] == num or j[1] == num:
                index = i

        if index != -1:
            self.comboConnection.pop(index)
            self.comboConnectionButtonList[index].deleteLater()
            self.comboConnectionButtonList.pop(index)

            self.update()
            self.updatePosition()
            self.dataSave()
            return

        if self.ComboSelectionList[0] == -1:
            self.ComboSelectionList[0] = num
            self.skillSelectionList[num].setStyleSheet(
                """
                QPushButton {
                    background-color: #cccccc; border-radius: 5px; border: 3px solid black;
                }
            """
            )
        elif num == self.ComboSelectionList[0]:
            self.skillSelectionList[num].setStyleSheet(
                """
                QPushButton {
                    background-color: white; border-radius: 10px; border: 1px solid black;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
            """
            )
            self.ComboSelectionList[0] = -1
        elif self.ComboSelectionList[1] == -1:
            self.ComboSelectionList[1] = num
            self.skillSelectionList[num].setStyleSheet(
                """
                QPushButton {
                    background-color: #cccccc; border-radius: 10px; border: 3px solid black;
                }
            """
            )

            ableKeyList = [
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
                "G",
                "H",
                "I",
                "J",
            ]
            i = 0
            while self.isKeyUsing(ableKeyList[i]):
                i += 1
            key = ableKeyList[i]
            self.comboConnection.append(
                [self.ComboSelectionList[0], self.ComboSelectionList[1], key]
            )

            comboConnectionButton = QPushButton(key, self)
            self.adjustFontSize(comboConnectionButton, key, 24)
            comboConnectionButton.clicked.connect(
                lambda: self.onComboConnectionClick(len(self.comboConnection))
            )
            comboConnectionButton.setStyleSheet(
                """
                QPushButton {
                    background-color: #eeeef5; border-radius: 5px; border: 3px solid black;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
            """
            )
            # comboConnectionButton.setFont(self.font20)
            comboConnectionButton.setFixedSize(50, 50)
            startX = 445 + (30 + 150) * self.ComboSelectionList[0]
            endX = 445 + (30 + 150) * self.ComboSelectionList[1]
            comboConnectionButton.move(
                round((startX + endX) * 0.5) - 25, 553 + 70 * len(self.comboConnection)
            )
            comboConnectionButton.show()

            self.comboConnectionButtonList.append(comboConnectionButton)

            self.ComboSelectionList[1] = num
            self.skillSelectionList[self.ComboSelectionList[0]].setStyleSheet(
                """
                QPushButton {
                    background-color: white; border-radius: 10px; border: 1px solid black;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
            """
            )
            self.skillSelectionList[num].setStyleSheet(
                """
                QPushButton {
                    background-color: white; border-radius: 10px; border: 1px solid black;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
            """
            )

            self.ComboSelectionList = [-1, -1]

        self.update()
        self.updatePosition()
        self.dataSave()
        # print(self.ComboSelectionList)
        # print(self.comboConnection)

    def changeTab(self, num):
        self.dataLoad(num)

        for tabNum in range(len(self.tabNames)):
            if tabNum == self.recentPreset:
                self.tabList[tabNum].setStyleSheet(
                    """background-color: #eeeef5; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )
            else:
                self.tabList[tabNum].setStyleSheet(
                    """background-color: #cccccc; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
                )

            if tabNum == self.recentPreset:
                self.tabButtonList[tabNum].setStyleSheet(
                    """
                    QPushButton {
                        background-color: #eeeef5; border-radius: 15px; text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #fafaff;
                    }
                """
                )
            else:
                self.tabButtonList[tabNum].setStyleSheet(
                    """
                    QPushButton {
                        background-color: #cccccc; border-radius: 15px; text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #dddddd;
                    }
                """
                )
            self.tabRemoveList[tabNum].setStyleSheet(
                """
                QPushButton {
                    background-color: transparent; border-radius: 20px;
                }
                QPushButton:hover {
                    background-color: #dddddd;
                }
            """
            )

        for skillIndex in range(6):
            pixmap = QPixmap(
                f"resource/skill/{self.serverID}/{self.jobID}/{self.skillList[skillIndex]}.png"
            )
            self.skillImageList[skillIndex].setIcon(QIcon(pixmap))

            self.skillKeyList[skillIndex].setText(self.skillKeys[skillIndex])

            if self.comboBool[skillIndex]:
                self.skillComboList[skillIndex].setStyleSheet(
                    """
                    QPushButton {
                        background-color: white; border-radius: 15px; color: rgb(0, 0, 0);
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
                )
            else:
                self.skillComboList[skillIndex].setStyleSheet(
                    """
                    QPushButton {
                        background-color: white; border-radius: 15px; color: #999999;
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
                )

        for i in self.comboConnectionButtonList:
            i.deleteLater()
        self.comboConnectionButtonList = []
        for i, j in enumerate(self.comboConnection):
            comboConnectionButton = QPushButton(j[2], self)
            self.adjustFontSize(comboConnectionButton, j[2], 24)
            comboConnectionButton.clicked.connect(
                partial(lambda x: self.onComboConnectionClick(x), i)
            )
            comboConnectionButton.setStyleSheet(
                """
                QPushButton {
                    background-color: #eeeef5; border-radius: 5px; border: 3px solid black;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
            """
            )
            comboConnectionButton.setFixedSize(50, 50)
            startX = 445 + (30 + 150) * j[0]
            endX = 445 + (30 + 150) * j[1]
            comboConnectionButton.move(round((startX + endX) * 0.5) - 25, 553 + 70 * i)
            comboConnectionButton.show()

            self.comboConnectionButtonList.append(comboConnectionButton)

        self.buttonServerList.setText(self.serverList[self.serverID])
        self.buttonJobList.setText(self.jobList[self.serverID][self.jobID])

        self.buttonInputDelay.setText(str(self.inputDelay))
        rgb = 153 if self.activeDelaySlot == 1 else 0
        self.buttonDefaultDelay.setStyleSheet(
            f"""
                QPushButton {{
                    background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb({rgb}, {rgb}, {rgb});
                }}
                QPushButton:hover {{
                    background-color: #cccccc;
                }}
            """
        )
        rgb = 153 if self.activeDelaySlot == 0 else 0
        self.buttonInputDelay.setStyleSheet(
            f"""
                    QPushButton {{
                        background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb({rgb}, {rgb}, {rgb});
                    }}
                    QPushButton:hover {{
                        background-color: #cccccc;
                    }}
                """
        )

        self.buttonInputCooltime.setText(str(self.inputCooltime))
        rgb = 153 if self.activeCooltimeSlot == 1 else 0
        self.buttonDefaultCooltime.setStyleSheet(
            f"""
                QPushButton {{
                    background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb({rgb}, {rgb}, {rgb});
                }}
                QPushButton:hover {{
                    background-color: #cccccc;
                }}
            """
        )
        rgb = 153 if self.activeCooltimeSlot == 0 else 0
        self.buttonInputCooltime.setStyleSheet(
            f"""
                    QPushButton {{
                        background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb({rgb}, {rgb}, {rgb});
                    }}
                    QPushButton:hover {{
                        background-color: #cccccc;
                    }}
                """
        )

        self.buttonInputStartKey.setText(str(self.inputStartKey))
        rgb = 153 if self.activeStartKeySlot == 1 else 0
        self.buttonDefaultStartKey.setStyleSheet(
            f"""
                QPushButton {{
                    background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb({rgb}, {rgb}, {rgb});
                }}
                QPushButton:hover {{
                    background-color: #cccccc;
                }}
            """
        )
        rgb = 153 if self.activeStartKeySlot == 0 else 0
        self.buttonInputStartKey.setStyleSheet(
            f"""
                    QPushButton {{
                        background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb({rgb}, {rgb}, {rgb});
                    }}
                    QPushButton:hover {{
                        background-color: #cccccc;
                    }}
                """
        )

        rgb = 153 if self.activeMouseClickSlot == 1 else 0
        self.button1stMouseType.setStyleSheet(
            f"""
                QPushButton {{
                    background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb({rgb}, {rgb}, {rgb});
                }}
                QPushButton:hover {{
                    background-color: #cccccc;
                }}
            """
        )
        rgb = 153 if self.activeMouseClickSlot == 0 else 0
        self.button2ndMouseType.setStyleSheet(
            f"""
                    QPushButton {{
                        background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb({rgb}, {rgb}, {rgb});
                    }}
                    QPushButton:hover {{
                        background-color: #cccccc;
                    }}
                """
        )

        self.update()
        self.updatePosition()
        self.dataSave()

    def getSettingButton(self, text, x, y, cmd):
        button = QPushButton(text, self)
        button.clicked.connect(cmd)
        button.setFont(self.font12)
        button.setStyleSheet(
            """
                QPushButton {
                    background-color: white; border-radius: 10px; border: 1px solid black;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
            """
        )
        button.setFixedSize(120, 30)
        button.move(x, y)
        return button

    def getSettingCheck(self, text, x, y, cmd, disable=False):
        button = QPushButton(text, self)
        button.clicked.connect(cmd)
        button.setFont(self.font12)
        rgb = 153 if disable else 0
        button.setStyleSheet(
            f"""
                    QPushButton {{
                        background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb({rgb}, {rgb}, {rgb});
                    }}
                    QPushButton:hover {{
                        background-color: #cccccc;
                    }}
                """
        )
        button.setFixedSize(120, 30)
        button.move(x, y)
        return button

    def getSettingName(self, text, x, y):
        label = QLabel(text, self)
        label.setFont(self.font16)
        label.setStyleSheet("border: 1px solid black; border-radius: 10px;")
        label.setFixedSize(180, 40)
        label.setAlignment(Qt.AlignCenter)
        label.move(x, y)
        return label

    def getShadow(self, first=5, second=5, radius=10, transparent=100):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(radius)
        shadow.setColor(QColor(0, 0, 0, transparent))
        shadow.setOffset(first, second)
        return shadow

    def makeNoticePopup(self, e):
        noticePopup = QFrame(self)

        frameHeight = 78
        match e:
            case "delayInputError":
                text = "딜레이는 1~100까지의 수를 입력해야 합니다."
                icon = "error"
            case "cooltimeInputError":
                text = "쿨타임은 0~50까지의 수를 입력해야 합니다."
                icon = "error"
            case "StartKeyChangeError":
                text = "해당 키는 이미 사용중입니다."
                icon = "error"
            case "RequireUpdate":
                text = f"프로그램 업데이트가 필요합니다.\n현재 버전: {version}, 최신버전: {self.recentVersion}"
                icon = "warning"

                button = QPushButton("다운로드 링크", noticePopup)
                button.setFont(self.font12)
                button.setStyleSheet(
                    """
                                QPushButton {
                                    background-color: #86A7FC; border-radius: 4px;
                                }
                                QPushButton:hover {
                                    background-color: #3468C0;
                                }
                            """
                )
                button.setFixedSize(150, 32)
                button.move(48, 80)
                button.clicked.connect(lambda: open_new(self.update_url))
                button.show()

                frameHeight = 125
            case "FailedUpdateCheck":
                text = f"프로그램 업데이트 확인에 실패하였습니다."
                icon = "warning"

        noticePopup.setStyleSheet("background-color: white; border-radius: 10px;")
        noticePopup.setFixedSize(500, frameHeight)
        noticePopup.move(
            self.width() - 520,
            self.height() - frameHeight - 25 - self.activeErrorPopupCount * 10,
        )
        noticePopup.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
        noticePopup.show()

        noticePopupIcon = QPushButton(noticePopup)
        noticePopupIcon.setStyleSheet("background-color: transparent;")
        noticePopupIcon.setFixedSize(24, 24)
        noticePopupIcon.move(15, 15)
        pixmap = QPixmap(f"resource/{icon}.png")
        noticePopupIcon.setIcon(QIcon(pixmap))
        noticePopupIcon.setIconSize(QSize(24, 24))
        noticePopupIcon.show()

        noticePopupLabel = QLabel(text, noticePopup)
        noticePopupLabel.setWordWrap(True)
        noticePopupLabel.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        noticePopupLabel.setFont(self.font12)
        noticePopupLabel.setStyleSheet("background-color: white; border-radius: 10px;")
        noticePopupLabel.setFixedSize(404, 54)
        noticePopupLabel.move(48, 12)
        noticePopupLabel.show()

        noticePopupRemove = QPushButton(noticePopup)
        noticePopupRemove.setStyleSheet(
            """
                        QPushButton {
                            background-color: white; border-radius: 16px;
                        }
                        QPushButton:hover {
                            background-color: #cccccc;
                        }
                    """
        )
        noticePopupRemove.setFixedSize(32, 32)
        noticePopupRemove.move(455, 12)
        noticePopupRemove.clicked.connect(self.removeNoticePopup)
        pixmap = QPixmap("resource/x.png")
        noticePopupRemove.setIcon(QIcon(pixmap))
        noticePopupRemove.setIconSize(QSize(24, 24))
        noticePopupRemove.show()

        self.activeErrorPopup.append([noticePopup, frameHeight])
        self.activeErrorPopupCount += 1

    def removeNoticePopup(self):
        self.activeErrorPopup[-1][0].deleteLater()
        self.activeErrorPopup.pop()
        self.activeErrorPopupCount -= 1

    def disablePopup(self):
        if self.activePopup == "":
            return
        else:
            self.settingPopupFrame.deleteLater()
        self.activePopup = ""

    def activatePopup(self, text):
        self.disablePopup()
        self.activePopup = text

    def makePopupInput(self, type):
        match type:
            case "delay":
                x = 160
                y = 390
                width = 140
            case "cooltime":
                x = 160
                y = 520
                width = 140
            case ("tabName", _):
                x = 340 + 250 * self.recentPreset
                y = 80
                width = 250
        self.settingPopupFrame = QFrame(self)
        self.settingPopupFrame.setStyleSheet(
            "background-color: white; border-radius: 10px;"
        )
        self.settingPopupFrame.setFixedSize(width, 40)
        self.settingPopupFrame.move(x, y)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 0, 30, 150))
        self.settingPopupFrame.show()

        match type:
            case "delay":
                default = str(self.inputDelay)
            case "cooltime":
                default = str(self.inputCooltime)
            case ("tabName", _):
                default = self.tabNames[self.recentPreset]
        self.settingPopupInput = QLineEdit(default, self.settingPopupFrame)
        self.settingPopupInput.setFont(self.font12)
        self.settingPopupInput.setAlignment(Qt.AlignCenter)
        self.settingPopupInput.setStyleSheet(
            "border: 1px solid black; border-radius: 10px;"
        )
        self.settingPopupInput.setFixedSize(width - 70, 30)
        self.settingPopupInput.move(5, 5)

        self.settingPopupButton = QPushButton("적용", self.settingPopupFrame)
        self.settingPopupButton.setFont(self.font12)
        self.settingPopupButton.clicked.connect(lambda: self.onInputPopupClick(type))
        self.settingPopupButton.setStyleSheet(
            """
                            QPushButton {
                                background-color: "white"; border-radius: 10px; border: 1px solid black;
                            }
                            QPushButton:hover {
                                background-color: #cccccc;
                            }
                        """
        )
        self.settingPopupButton.setFixedSize(50, 30)
        self.settingPopupButton.move(width - 60, 5)
        # self.settingServerFrame.setGraphicsEffect(self.getShadow(0, 5))

        self.settingPopupButton.show()
        self.settingPopupInput.show()

        self.update()
        self.updatePosition()

    def onInputPopupClick(self, type):
        text = self.settingPopupInput.text()

        if type == "delay" or type == "cooltime":
            try:
                text = int(text)
            except:
                self.disablePopup()
                self.makeNoticePopup(
                    "delayInputError" if type == "delay" else "cooltimeInputError"
                )
                return

        match type:
            case "delay":
                if not (1 <= text <= 100):
                    self.disablePopup()
                    self.makeNoticePopup("delayInputError")
                    return
                self.buttonInputDelay.setText(str(text))
                self.inputDelay = text
                self.delay = text
            case "cooltime":
                if not (0 <= text <= 50):
                    self.disablePopup()
                    self.makeNoticePopup("cooltimeInputError")
                    return
                self.buttonInputCooltime.setText(str(text))
                self.inputCooltime = text
                self.cooltime = text
            case ("tabName", _):
                self.tabButtonList[type[1]].setText(" " + text)
                self.tabNames[type[1]] = text

        self.dataSave()
        self.disablePopup()

        self.update()
        self.updatePosition()

    def onServerClick(self):
        if self.activePopup == "settingServer":
            self.disablePopup()
        else:
            self.activatePopup("settingServer")

            self.settingPopupFrame = QFrame(self)
            self.settingPopupFrame.setStyleSheet(
                "background-color: white; border-radius: 10px;"
            )
            self.settingPopupFrame.setFixedSize(130, 5 + 35 * len(self.serverList))
            self.settingPopupFrame.move(25, 260)
            self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
            self.settingPopupFrame.show()

            for i in range(len(self.serverList)):
                self.settingServerButton = QPushButton(
                    self.serverList[i], self.settingPopupFrame
                )
                self.settingServerButton.setFont(self.font12)
                self.settingServerButton.clicked.connect(
                    partial(lambda x: self.onServerPopupClick(x), i)
                )
                self.settingServerButton.setStyleSheet(
                    f"""
                                QPushButton {{
                                    background-color: {"white" if i != self.serverID else "#dddddd"}; border-radius: 10px;
                                }}
                                QPushButton:hover {{
                                    background-color: #cccccc;
                                }}
                            """
                )
                self.settingServerButton.setFixedSize(120, 30)
                self.settingServerButton.move(5, 5 + 35 * i)
                # self.settingServerFrame.setGraphicsEffect(self.getShadow(0, 5))

                self.settingServerButton.show()

    def onServerPopupClick(self, num):
        if self.serverID != num:
            self.serverID = num
            self.jobID = 0
            self.skillList = ["0", "1", "2", "3", "4", "5"]

            self.buttonServerList.setText(self.serverList[num])
            self.buttonJobList.setText(self.jobList[num][0])

            for i in range(6):
                pixmap = QPixmap(f"resource/skill/{num}/0/{self.skillList[i]}.png")
                self.skillImageList[i].setIcon(QIcon(pixmap))

            self.dataSave()
        self.disablePopup()

    def onJobClick(self):
        if self.activePopup == "settingJob":
            self.disablePopup()
        else:
            self.activatePopup("settingJob")

            self.settingPopupFrame = QFrame(self)
            self.settingPopupFrame.setStyleSheet(
                "background-color: white; border-radius: 10px;"
            )
            self.settingPopupFrame.setFixedSize(
                130, 5 + 35 * len(self.jobList[self.serverID])
            )
            self.settingPopupFrame.move(165, 260)
            self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 5, 30, 150))
            self.settingPopupFrame.show()

            for i in range(len(self.jobList[self.serverID])):
                self.settingJobButton = QPushButton(
                    self.jobList[self.serverID][i], self.settingPopupFrame
                )
                self.settingJobButton.setFont(self.font12)
                self.settingJobButton.clicked.connect(
                    partial(lambda x: self.onJobPopupClick(x), i)
                )
                self.settingJobButton.setStyleSheet(
                    f"""
                                QPushButton {{
                                    background-color: {"white" if i != self.jobID else "#dddddd"}; border-radius: 10px;
                                }}
                                QPushButton:hover {{
                                    background-color: #cccccc;
                                }}
                            """
                )
                self.settingJobButton.setFixedSize(120, 30)
                self.settingJobButton.move(5, 5 + 35 * i)
                # self.settingServerFrame.setGraphicsEffect(self.getShadow(0, 5))

                self.settingJobButton.show()

    def onJobPopupClick(self, num):
        if self.jobID != num:
            self.jobID = num
            self.skillList = ["0", "1", "2", "3", "4", "5"]

            self.buttonJobList.setText(self.jobList[self.serverID][num])

            for i in range(6):
                pixmap = QPixmap(
                    f"resource/skill/{self.serverID}/{num}/{self.skillList[i]}.png"
                )
                self.skillImageList[i].setIcon(QIcon(pixmap))

            self.dataSave()
        self.disablePopup()

    def onDefaultDelayClick(self):
        self.disablePopup()

        if self.activeDelaySlot == 0:
            return

        self.activeDelaySlot = 0
        self.delay = 15

        self.buttonDefaultDelay.setStyleSheet(
            """
                    QPushButton {
                        background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb(0, 0, 0);
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
        )
        self.buttonInputDelay.setStyleSheet(
            """
                    QPushButton {
                        background-color: white; border-radius: 10px; border: 1px solid black; color: #999999;
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
        )

        self.dataSave()

    def onInputDelayClick(self):
        if self.activePopup == "settingDelay":
            self.disablePopup()
            return
        self.disablePopup()

        if self.activeDelaySlot == 1:
            self.activatePopup("settingDelay")

            self.makePopupInput("delay")
        else:
            self.activeDelaySlot = 1
            self.delay = self.inputDelay

            self.buttonDefaultDelay.setStyleSheet(
                """
                        QPushButton {
                            background-color: white; border-radius: 10px; border: 1px solid black;  color: #999999;
                        }
                        QPushButton:hover {
                            background-color: #cccccc;
                        }
                    """
            )
            self.buttonInputDelay.setStyleSheet(
                """
                        QPushButton {
                            background-color: white; border-radius: 10px; border: 1px solid black; color: rgb(0, 0, 0);
                        }
                        QPushButton:hover {
                            background-color: #cccccc;
                        }
                    """
            )

            self.dataSave()

    def onDefaultCooltimeClick(self):
        self.disablePopup()

        if self.activeCooltimeSlot == 0:
            return

        self.activeCooltimeSlot = 0
        self.cooltime = 0

        self.buttonDefaultCooltime.setStyleSheet(
            """
                    QPushButton {
                        background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb(0, 0, 0);
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
        )
        self.buttonInputCooltime.setStyleSheet(
            """
                    QPushButton {
                        background-color: white; border-radius: 10px; border: 1px solid black; color: #999999;
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
        )

        self.dataSave()

    def onInputCooltimeClick(self):
        if self.activePopup == "settingCooltime":
            self.disablePopup()
            return
        self.disablePopup()

        if self.activeCooltimeSlot == 1:
            self.activatePopup("settingCooltime")

            self.makePopupInput("cooltime")
        else:
            self.activeCooltimeSlot = 1
            self.cooltime = self.inputCooltime

            self.buttonDefaultCooltime.setStyleSheet(
                """
                        QPushButton {
                            background-color: white; border-radius: 10px; border: 1px solid black;  color: #999999;
                        }
                        QPushButton:hover {
                            background-color: #cccccc;
                        }
                    """
            )
            self.buttonInputCooltime.setStyleSheet(
                """
                        QPushButton {
                            background-color: white; border-radius: 10px; border: 1px solid black; color: rgb(0, 0, 0);
                        }
                        QPushButton:hover {
                            background-color: #cccccc;
                        }
                    """
            )

            self.dataSave()

    def onStartKeyPopupKeyboardClick(self, key, disabled):
        match key:
            case "PrtSc":
                key = "Print"
            case "ScrLk":
                key = "Scroll"
            case "Page\nUp":
                key = "Page_Up"
            case "Page\nDown":
                key = "Page_Down"

        if disabled:
            return

        self.buttonInputStartKey.setText(key)
        self.inputStartKey = key
        self.startKey = key

        self.dataSave()
        self.disablePopup()

    def onKeyboardPopupClick(self, type):
        def makePresetKey(key, row, column, disabled=False):
            button = QPushButton(key, self.settingPopupFrame)
            button.setFont(self.font12)

            match type:
                case "StartKey":
                    button.clicked.connect(
                        lambda: self.onStartKeyPopupKeyboardClick(key, disabled)
                    )
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(
                            key, disabled, type[1]
                        )
                    )
                case ("ComboConnection", _):
                    button.clicked.connect(
                        lambda: self.onComboConnectionPopupKeyboardClick(
                            key, disabled, type[1]
                        )
                    )
            color1 = "#999999" if disabled else "white"
            color2 = "#999999" if disabled else "#cccccc"
            button.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: {color1}; border-radius: 10px; border: 1px solid black;;
                    }}
                    QPushButton:hover {{
                        background-color: {color2};
                    }}
                """
            )
            button.setFixedSize(60, 60)
            match column:
                case 0:
                    defaultX = 115
                case 1:
                    defaultX = 10
                case 2:
                    defaultX = 115
                case 3:
                    defaultX = 130
                case 4:
                    defaultX = 165
            defaultY = 10

            button.move(defaultX + row * 70, defaultY + column * 70)
            button.show()

        def makeKey(key, x, y, width, height, disabled=False):
            button = QPushButton(key, self.settingPopupFrame)
            button.setFont(self.font12)
            match type:
                case "StartKey":
                    button.clicked.connect(
                        lambda: self.onStartKeyPopupKeyboardClick(key, disabled)
                    )
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(
                            key, disabled, type[1]
                        )
                    )
                case ("ComboConnection", _):
                    button.clicked.connect(
                        lambda: self.onComboConnectionPopupKeyboardClick(
                            key, disabled, type[1]
                        )
                    )
            color1 = "#999999" if disabled else "white"
            color2 = "#999999" if disabled else "#cccccc"
            button.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: {color1}; border-radius: 10px; border: 1px solid black;;
                    }}
                    QPushButton:hover {{
                        background-color: {color2};
                    }}
                """
            )
            button.setFixedSize(width, height)
            button.move(x, y)
            button.show()

        def makeImageKey(key, x, y, width, height, image, size, rot, disabled=False):
            button = QPushButton(self.settingPopupFrame)
            pixmap = QPixmap(image)
            pixmap = pixmap.transformed(QTransform().rotate(rot))
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(size, size))
            match type:
                case "StartKey":
                    button.clicked.connect(
                        lambda: self.onStartKeyPopupKeyboardClick(key, disabled)
                    )
                case ("skillKey", _):
                    button.clicked.connect(
                        lambda: self.onSkillKeyPopupKeyboardClick(
                            key, disabled, type[1]
                        )
                    )
                case ("ComboConnection", _):
                    button.clicked.connect(
                        lambda: self.onComboConnectionPopupKeyboardClick(
                            key, disabled, type[1]
                        )
                    )
            color1 = "#999999" if disabled else "white"
            color2 = "#999999" if disabled else "#cccccc"
            button.setStyleSheet(
                f"""
                    QPushButton {{
                        background-color: {color1}; border-radius: 10px; border: 1px solid black;;
                    }}
                    QPushButton:hover {{
                        background-color: {color2};
                    }}
                """
            )
            button.setFixedSize(width, height)
            button.move(x, y)
            button.show()

        self.settingPopupFrame = QFrame(self)
        self.settingPopupFrame.setStyleSheet(
            "background-color: white; border-radius: 10px;"
        )
        self.settingPopupFrame.setFixedSize(1270, 430)
        self.settingPopupFrame.move(30, 150)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 0, 30, 150))
        self.settingPopupFrame.show()

        k0 = [
            "Esc",
            "F1",
            "F2",
            "F3",
            "F4",
            "F5",
            "F6",
            "F7",
            "F8",
            "F9",
            "F10",
            "F11",
            "F12",
        ]
        k1 = ["~", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "+"]
        k2 = ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "\\"]
        k3 = ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'"]
        k4 = ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/"]

        for i, key in enumerate(k0):
            x = 10 + 70 * i
            if i >= 1:
                x += 35
            if i >= 5:
                x += 35
            if i >= 9:
                x += 35

            if key == "Esc":
                makeKey(key, x, 10, 60, 60, True)
            else:
                makeKey(key, x, 10, 60, 60, self.isKeyUsing(key))

        row = 0
        column = 1
        for key in k1:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1
        makeKey("Back", 920, 80, 95, 60, True)

        makeKey("Tab", 10, 150, 95, 60, self.isKeyUsing("Tab"))
        row = 0
        column += 1
        for key in k2:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1

        makeKey("Caps Lock", 10, 220, 110, 60, True)
        row = 0
        column += 1
        for key in k3:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1
        makeKey("Enter", 900, 220, 115, 60, self.isKeyUsing("Enter"))

        makeKey("Shift", 10, 290, 145, 60, self.isKeyUsing("Shift"))
        row = 0
        column += 1
        for key in k4:
            makePresetKey(key, row, column, self.isKeyUsing(key))
            row += 1
        makeKey("Shift", 865, 290, 150, 60, self.isKeyUsing("Shift"))

        makeKey("Crtl", 10, 360, 90, 60, self.isKeyUsing("Crtl"))
        makeImageKey("Window", 110, 360, 90, 60, "resource/window", 64, 0, True)
        makeKey("Alt", 210, 360, 90, 60, self.isKeyUsing("Alt"))
        makeKey("Space", 310, 360, 305, 60, self.isKeyUsing("Space"))
        makeKey("Alt", 625, 360, 90, 60, self.isKeyUsing("Alt"))
        makeImageKey("Window", 725, 360, 90, 60, "resource/window", 64, 0, True)
        makeKey("Fn", 825, 360, 90, 60, True)
        makeKey("Crtl", 925, 360, 90, 60, self.isKeyUsing("Crtl"))

        k5 = [
            ["PrtSc", "ScrLk", "Pause"],
            ["Insert", "Home", "Page\nUp"],
            ["Delete", "End", "Page\nDown"],
        ]
        for i1, i2 in enumerate(k5):
            for j1, j2 in enumerate(i2):
                makeKey(j2, 1060 + j1 * 70, 10 + 70 * i1, 60, 60, self.isKeyUsing(j2))

        makeImageKey(
            "Up", 1130, 290, 60, 60, "resource/arrow", 32, 0, self.isKeyUsing("Up")
        )
        makeImageKey(
            "Left",
            1060,
            360,
            60,
            60,
            "resource/arrow",
            32,
            270,
            self.isKeyUsing("Left"),
        )
        makeImageKey(
            "Down",
            1130,
            360,
            60,
            60,
            "resource/arrow",
            32,
            180,
            self.isKeyUsing("Down"),
        )
        makeImageKey(
            "Right",
            1200,
            360,
            60,
            60,
            "resource/arrow",
            32,
            90,
            self.isKeyUsing("Right"),
        )

    def onDefaultStartKeyClick(self):
        self.disablePopup()

        if self.activeStartKeySlot == 0:
            return

        if self.inputStartKey != "F9" and self.isKeyUsing("F9"):
            self.makeNoticePopup("StartKeyChangeError")
            return

        self.activeStartKeySlot = 0
        self.startKey = "F9"

        self.buttonDefaultStartKey.setStyleSheet(
            """
                    QPushButton {
                        background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb(0, 0, 0);
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
        )
        self.buttonInputStartKey.setStyleSheet(
            """
                    QPushButton {
                        background-color: white; border-radius: 10px; border: 1px solid black; color: #999999;
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
        )

        self.dataSave()

    def onInputStartKeyClick(self):
        if self.activePopup == "settingStartKey":
            self.disablePopup()
            return
        self.disablePopup()

        if self.activeStartKeySlot == 1:
            self.activatePopup("settingStartKey")

            self.onKeyboardPopupClick("StartKey")
        else:
            self.activeStartKeySlot = 1
            self.startKey = self.inputStartKey

            self.buttonDefaultStartKey.setStyleSheet(
                """
                        QPushButton {
                            background-color: white; border-radius: 10px; border: 1px solid black;  color: #999999;
                        }
                        QPushButton:hover {
                            background-color: #cccccc;
                        }
                    """
            )
            self.buttonInputStartKey.setStyleSheet(
                """
                        QPushButton {
                            background-color: white; border-radius: 10px; border: 1px solid black; color: rgb(0, 0, 0);
                        }
                        QPushButton:hover {
                            background-color: #cccccc;
                        }
                    """
            )

            self.dataSave()

    def on1stMouseTypeClick(self):
        self.disablePopup()

        if self.activeMouseClickSlot == 0:
            return

        self.activeMouseClickSlot = 0

        self.button1stMouseType.setStyleSheet(
            """
                    QPushButton {
                        background-color: white; border-radius: 10px; border: 1px solid black;  color: rgb(0, 0, 0);
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
        )
        self.button2ndMouseType.setStyleSheet(
            """
                    QPushButton {
                        background-color: white; border-radius: 10px; border: 1px solid black; color: #999999;
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
        )

        self.dataSave()

    def on2ndMouseTypeClick(self):
        self.disablePopup()

        if self.activeMouseClickSlot == 1:
            return

        self.activeMouseClickSlot = 1

        self.button1stMouseType.setStyleSheet(
            """
                    QPushButton {
                        background-color: white; border-radius: 10px; border: 1px solid black;  color: #999999;
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
        )
        self.button2ndMouseType.setStyleSheet(
            """
                    QPushButton {
                        background-color: white; border-radius: 10px; border: 1px solid black; color: rgb(0, 0, 0);
                    }
                    QPushButton:hover {
                        background-color: #cccccc;
                    }
                """
        )

        self.dataSave()

    def onTabClick(self, num):
        if self.recentPreset == num:
            if self.activePopup == "changeTabName":
                self.disablePopup()
            else:
                self.activatePopup("changeTabName")
                self.makePopupInput(("tabName", num))
            return
        self.disablePopup()

        self.changeTab(num)

    def onTabAddClick(self):
        self.disablePopup()

        self.dataAdd()

        tabNum = len(self.tabNames)
        self.dataLoad(tabNum)

        tabBackground = QLabel("", self)
        tabBackground.setStyleSheet(
            """background-color: #eeeef5; border-top-left-radius :20px; border-top-right-radius : 20px; border-bottom-left-radius : 0px; border-bottom-right-radius : 0px"""
        )
        tabBackground.setFixedSize(250, 50)
        tabBackground.move(340 + 250 * tabNum, 20)
        tabBackground.setGraphicsEffect(self.getShadow(5, -2))
        tabBackground.show()

        tabButton = QPushButton(f" {self.tabNames[tabNum]}", self)
        tabButton.clicked.connect(lambda: self.onTabClick(tabNum))
        tabButton.setFont(self.font12)
        tabButton.setStyleSheet(
            """
            QPushButton {
                background-color: #eeeef5; border-radius: 15px; text-align: left;
            }
            QPushButton:hover {
                background-color: #fafaff;
            }
        """
        )
        tabButton.setFixedSize(240, 40)
        tabButton.move(345 + 250 * tabNum, 25)
        tabButton.show()

        tabRemoveButton = QPushButton("", self)
        tabRemoveButton.clicked.connect(lambda: self.onTabRemoveClick(tabNum))
        tabRemoveButton.setFont(self.font16)
        tabRemoveButton.setStyleSheet(
            """
            QPushButton {
                background-color: transparent; border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #dddddd;
            }
        """
        )
        pixmap = QPixmap(f"resource/x.png")
        tabRemoveButton.setIcon(QIcon(pixmap))
        tabRemoveButton.setFixedSize(40, 40)
        tabRemoveButton.move(545 + 250 * tabNum, 25)
        tabRemoveButton.show()

        self.tabButtonList.append(tabButton)
        self.tabList.append(tabBackground)
        self.tabRemoveList.append(tabRemoveButton)

        self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)

        self.changeTab(tabNum)

    def onTabRemoveClick(self, num):
        # print("act")
        self.disablePopup()

        tabCount = len(self.tabNames)
        # print(tabCount)

        if tabCount != 1:
            if self.recentPreset == num:
                if (tabCount - 1) > num:
                    self.tabNames.pop(num)
                    self.dataRemove(num)
                    self.tabButtonList[num].deleteLater()
                    self.tabButtonList.pop(num)
                    self.tabList[num].deleteLater()
                    self.tabList.pop(num)
                    self.tabRemoveList[num].deleteLater()
                    self.tabRemoveList.pop(num)

                    # print(self.tabButtonList)

                    for i, j in enumerate(self.tabButtonList):
                        j.clicked.disconnect()
                        j.clicked.connect(partial(lambda x: self.onTabClick(x), i))
                        self.tabRemoveList[i].clicked.disconnect()
                        self.tabRemoveList[i].clicked.connect(
                            partial(lambda x: self.onTabRemoveClick(x), i)
                        )

                        self.tabList[i].move(340 + 250 * i, 20)
                        self.tabButtonList[i].move(345 + 250 * i, 25)
                        self.tabRemoveList[i].move(545 + 250 * i, 25)
                    self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)

                    for i, j in enumerate(self.comboConnectionButtonList):
                        j.clicked.connect(
                            partial(lambda x: self.onComboConnectionClick(x), i)
                        )

                    self.changeTab(num)
                else:
                    self.tabNames.pop(num)
                    self.dataRemove(num)
                    self.tabButtonList[num].deleteLater()
                    self.tabButtonList.pop(num)
                    self.tabList[num].deleteLater()
                    self.tabList.pop(num)
                    self.tabRemoveList[num].deleteLater()
                    self.tabRemoveList.pop(num)

                    self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)

                    self.changeTab(num - 1)
                    self.recentPreset = num - 1
            elif self.recentPreset > num:
                self.tabNames.pop(num)
                self.dataRemove(num)
                self.tabButtonList[num].deleteLater()
                self.tabButtonList.pop(num)
                self.tabList[num].deleteLater()
                self.tabList.pop(num)
                self.tabRemoveList[num].deleteLater()
                self.tabRemoveList.pop(num)

                for i, j in enumerate(self.tabButtonList):
                    j.clicked.disconnect()
                    j.clicked.connect(partial(lambda x: self.onTabClick(x), i))
                    self.tabRemoveList[i].clicked.disconnect()
                    self.tabRemoveList[i].clicked.connect(
                        partial(lambda x: self.onTabRemoveClick(x), i)
                    )

                    self.tabList[i].move(340 + 250 * i, 20)
                    self.tabButtonList[i].move(345 + 250 * i, 25)
                    self.tabRemoveList[i].move(545 + 250 * i, 25)
                self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)

                self.changeTab(self.recentPreset - 1)
            elif self.recentPreset < num:
                # print(self.tabNames)
                # print(num)
                self.tabNames.pop(num)
                self.dataRemove(num)
                self.tabButtonList[num].deleteLater()
                self.tabButtonList.pop(num)
                self.tabList[num].deleteLater()
                self.tabList.pop(num)
                self.tabRemoveList[num].deleteLater()
                self.tabRemoveList.pop(num)

                for i, j in enumerate(self.tabButtonList):
                    j.clicked.disconnect()
                    j.clicked.connect(partial(lambda x: self.onTabClick(x), i))
                    self.tabRemoveList[i].clicked.disconnect()
                    self.tabRemoveList[i].clicked.connect(
                        partial(lambda x: self.onTabRemoveClick(x), i)
                    )

                    self.tabList[i].move(340 + 250 * i, 20)
                    self.tabButtonList[i].move(345 + 250 * i, 25)
                    self.tabRemoveList[i].move(545 + 250 * i, 25)
                self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)
        else:
            self.dataRemove(0)
            self.dataLoad(0)
            self.changeTab(0)
            self.tabButtonList[0].setText(" " + self.tabNames[0])

        self.update()
        self.updatePosition()
        self.dataSave()

    def onSkillKeyPopupKeyboardClick(self, key, disabled, num):
        match key:
            case "PrtSc":
                key = "Print"
            case "ScrLk":
                key = "Scroll"
            case "Page\nUp":
                key = "Page_Up"
            case "Page\nDown":
                key = "Page_Down"

        if disabled:
            return

        self.skillKeyList[num].setText(key)
        self.adjustFontSize(self.skillKeyList[num], key, 24)
        self.skillKeys[num] = key

        self.dataSave()
        self.disablePopup()

    def onSkillKeyClick(self, num):
        if self.activePopup == "skillKey":
            self.disablePopup()
            return
        self.disablePopup()

        self.activatePopup("skillKey")
        self.onKeyboardPopupClick(["skillKey", num])

    def onSkillComboClick(self, num):
        self.disablePopup()

        self.comboBool[num] = False if self.comboBool[num] else True

        if self.comboBool[num]:
            self.skillComboList[num].setStyleSheet(
                """
                QPushButton {
                    background-color: white; border-radius: 15px; color: rgb(0, 0, 0);
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
            """
            )
        else:
            self.skillComboList[num].setStyleSheet(
                """
                QPushButton {
                    background-color: white; border-radius: 15px; color: #999999;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
            """
            )

        self.dataSave()

    def onSkillClick(self, num):
        self.activatePopup("Skill")
        self.makeSkillFrame(num)

    def makeSkillFrame(self, num):
        x = 500
        y = 200
        width = 360
        height = 200
        self.settingPopupFrame = QFrame(self)
        self.settingPopupFrame.setStyleSheet(
            "background-color: white; border-radius: 10px;"
        )
        self.settingPopupFrame.setFixedSize(width, height)
        self.settingPopupFrame.move(x, y)
        self.settingPopupFrame.setGraphicsEffect(self.getShadow(0, 0, 30, 150))
        self.settingPopupFrame.show()

        skillList = []
        for i in range(6):
            skillImageButton = QPushButton("", self.settingPopupFrame)
            skillImageButton.setStyleSheet("background-color: rgba(255, 255, 255, 0);")
            pixmap = QPixmap(f"resource/skill/{self.serverID}/{self.jobID}/{i}.png")
            # skillImageButton.clicked.connect(
            #     partial(lambda x: self.(x), i)
            # )
            skillImageButton.setIcon(QIcon(pixmap))
            skillImageButton.setIconSize(QSize(64, 64))
            skillImageButton.move(25 + 89 * (i % 3), 25 + 89 * (i & 3))
            print(str(25 + 89 * (i % 3)), str(25 + 89 * (i // 3)))
            skillImageButton.show()

            skillList.append(skillImageButton)

        self.update()
        self.updatePosition()

    def onComboConnectionPopupKeyboardClick(self, key, disabled, num):
        match key:
            case "PrtSc":
                key = "Print"
            case "ScrLk":
                key = "Scroll"
            case "Page\nUp":
                key = "Page_Up"
            case "Page\nDown":
                key = "Page_Down"

        if disabled:
            return

        self.comboConnectionButtonList[num].setText(key)
        self.adjustFontSize(self.comboConnectionButtonList[num], key, 24)
        self.comboConnection[num][2] = key

        self.dataSave()
        self.disablePopup()

    def onComboConnectionClick(self, num):
        if self.activePopup == "ComboConnection":
            self.disablePopup()
            return
        self.disablePopup()

        self.activatePopup("ComboConnection")
        self.onKeyboardPopupClick(["ComboConnection", num])

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.disablePopup()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen()
        pen.setColor(Qt.transparent)
        pen.setWidth(0)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(238, 238, 245)))
        painter.drawRoundedRect(340, 70, self.width() - 360, self.height() - 90, 30, 30)
        painter.drawRect(340, 70, 30, 30)

        # 설정
        painter.setPen(
            QPen(
                QColor(0, 0, 0, 50),
                1,
                Qt.SolidLine,
            )
        )
        painter.drawLine(50, 270, 270, 270)
        painter.drawLine(50, 400, 270, 400)
        painter.drawLine(50, 530, 270, 530)
        painter.drawLine(50, 660, 270, 660)

        painter.setPen(
            QPen(
                QColor(0, 0, 0),
                round((self.paddingY + self.paddingX) * 0.0125 + 2.25),
                Qt.SolidLine,
            )
        )
        # 화살표
        for i, j in enumerate(self.comboConnection):
            startX = (
                415
                + self.paddingX
                + (self.paddingX + self.frameWidth) * j[0]
                + round(self.frameAddWidth * 0.5)
            )
            endX = (
                415
                + self.paddingX
                + (self.paddingX + self.frameWidth) * j[1]
                + round(self.frameAddWidth * 0.5)
            )
            painter.drawLine(
                startX,
                478
                + self.paddingY
                + self.frameAddHeight
                + 30
                + round((self.width() - 1470 + self.height() - 760) * 0.0025 + 7),
                startX,
                508
                + self.paddingY * 2
                + self.paddingY * 2 * i
                + self.frameAddHeight
                + 20,
            )
            painter.drawEllipse(
                startX
                - round((self.width() - 1470 + self.height() - 760) * 0.0025 + 7),
                478
                + self.paddingY
                + self.frameAddHeight
                + 30
                - round((self.width() - 1470 + self.height() - 760) * 0.0025 + 7),
                round((self.width() - 1470 + self.height() - 760) * 0.005 + 14),
                round((self.width() - 1470 + self.height() - 760) * 0.005 + 14),
            )
            painter.drawLine(
                endX,
                478 + self.paddingY + self.frameAddHeight + 20,
                endX,
                508
                + self.paddingY * 2
                + self.paddingY * 2 * i
                + self.frameAddHeight
                + 20,
            )
            painter.drawLine(
                endX,
                478 + self.paddingY + self.frameAddHeight + 20,
                endX - round((self.width() - 1470 + self.height() - 760) * 0.005 + 10),
                478
                + self.paddingY
                + round((self.width() - 1470 + self.height() - 760) * 0.005 + 10)
                + self.frameAddHeight
                + 20,
            )
            painter.drawLine(
                endX,
                478 + self.paddingY + self.frameAddHeight + 20,
                endX + round((self.width() - 1470 + self.height() - 760) * 0.005 + 10),
                478
                + self.paddingY
                + round((self.width() - 1470 + self.height() - 760) * 0.005 + 10)
                + self.frameAddHeight
                + 20,
            )
            painter.drawLine(
                startX,
                508
                + self.paddingY * 2
                + self.paddingY * 2 * i
                + self.frameAddHeight
                + 20,
                endX,
                508
                + self.paddingY * 2
                + self.paddingY * 2 * i
                + self.frameAddHeight
                + 20,
            )

        painter.setPen(QPen(QColor(180, 180, 180), 1, Qt.SolidLine))

        painter.drawLine(320, 0, 320, self.height())

    def resizeEvent(self, event):
        self.update()
        self.updatePosition()

    def updatePosition(self):
        self.paddingAddX = round((self.width() - 1470) * 0.1 / 7)
        self.paddingX = 30 + self.paddingAddX
        self.paddingAddY = round((self.height() - 760) * 0.7 / 8)
        self.paddingY = 30 + self.paddingAddY

        self.frameAddWidth = round((self.width() - 1470) * 0.9 / 6)
        self.frameWidth = 150 + self.frameAddWidth
        self.frameAddHeight = round((self.height() - 760) * 0.3)
        self.frameHeight = 360 + self.frameAddHeight

        if 420 + 250 * len(self.tabNames) <= self.width():
            for tabNum in range(len(self.tabNames)):
                self.tabList[tabNum].move(340 + 250 * tabNum, 20)
                self.tabList[tabNum].setFixedSize(250, 50)
                self.tabButtonList[tabNum].move(345 + 250 * tabNum, 25)
                self.tabButtonList[tabNum].setFixedSize(240, 40)
                self.tabButtonList[tabNum].setText(
                    self.limit_text(
                        f" {self.tabNames[tabNum]}", self.tabButtonList[tabNum]
                    )
                )
                self.tabRemoveList[tabNum].move(545 + 250 * tabNum, 25)
                self.tabAddButton.move(350 + 250 * len(self.tabNames), 25)
        else:
            width = round((self.width() - 420) / len(self.tabNames))
            for tabNum in range(len(self.tabNames)):
                self.tabList[tabNum].move(340 + width * tabNum, 20)
                self.tabList[tabNum].setFixedSize(width, 50)
                self.tabButtonList[tabNum].move(345 + width * tabNum, 25)
                self.tabButtonList[tabNum].setFixedSize(width - 10, 40)
                self.tabButtonList[tabNum].setText(
                    self.limit_text(
                        f" {self.tabNames[tabNum]}", self.tabButtonList[tabNum]
                    )
                )
                self.tabRemoveList[tabNum].move(295 + width * (tabNum + 1), 25)
                self.tabAddButton.move(self.width() - 60, 25)
                # self.tabAddButton.move(350 + width * len(self.tabNames), 25)
            if self.activePopup == "changeTabName":
                self.settingPopupFrame.move(340 + width * self.recentPreset, 80)

        for skillIndex in range(6):
            self.skillFrameList[skillIndex].move(
                340 + self.paddingX + (self.paddingX + self.frameWidth) * skillIndex,
                120 + self.paddingY,
            )
            self.skillFrameList[skillIndex].setFixedSize(
                self.frameWidth, self.frameHeight
            )

            # self.skillBarList[skillIndex].move(round((self.frameWidth - 80) * 0.5), 15)
            self.skillImageList[skillIndex].move(
                round((self.frameWidth - 96) * 0.5),
                30 + round(self.frameAddHeight * 0.15),
            )
            self.skillKeyList[skillIndex].setFixedSize(
                110 + round(self.frameAddWidth * 0.6),
                80 + round(self.frameAddHeight * 0.25),
            )
            self.adjustFontSize(
                self.skillKeyList[skillIndex], self.skillKeyList[skillIndex].text(), 24
            )
            self.skillKeyList[skillIndex].move(
                round((self.frameWidth - 110 - self.frameAddWidth * 0.6) * 0.5),
                153 + round(self.frameAddHeight * 0.3),
            )
            self.skillComboList[skillIndex].setFixedSize(
                110 + round(self.frameAddWidth * 0.6),
                80 + round(self.frameAddHeight * 0.25),
            )
            self.skillComboList[skillIndex].move(
                round((self.frameWidth - 110 - self.frameAddWidth * 0.6) * 0.5),
                260 + round(self.frameAddHeight * 0.65),
            )

            self.skillSelectionList[skillIndex].move(
                330
                + self.paddingX
                + (self.paddingX + self.frameWidth) * skillIndex
                + round(self.frameWidth * 0.5),
                110 + self.paddingY + self.frameHeight,
            )

        for i, j in enumerate(self.comboConnection):
            startX = (
                415
                + self.paddingX
                + (self.paddingX + self.frameWidth) * j[0]
                + round(self.frameAddWidth * 0.5)
            )
            endX = (
                415
                + self.paddingX
                + (self.paddingX + self.frameWidth) * j[1]
                + round(self.frameAddWidth * 0.5)
            )

            comboButtonWidth = ((self.paddingX - 30) * 10 + 30) * 0.5 + 100
            comboButtonHeight = (self.paddingY + 30) * 0.25 + 35

            self.comboConnectionButtonList[i].setFixedSize(
                round(comboButtonWidth),
                round(comboButtonHeight),
            )
            self.adjustFontSize(
                self.comboConnectionButtonList[i],
                self.comboConnectionButtonList[i].text(),
                24,
            )
            self.comboConnectionButtonList[i].move(
                round((startX + endX) * 0.5) - round(comboButtonWidth * 0.5),
                508
                + self.paddingY * 2
                + self.paddingY * 2 * i
                - round(comboButtonHeight * 0.5)
                + self.frameAddHeight
                + 20,
            )
            self.comboConnectionButtonList[i].setStyleSheet(
                f"""
                QPushButton {{
                    background-color: #eeeef5; border-radius: 5px; border: {round((self.paddingY + self.paddingX) * 0.0125 + 2.25)}px solid black;
                }}
                QPushButton:hover {{
                    background-color: #cccccc;
                }}
            """
            )
        self.labelCreator.move(2, self.height() - 25)

        for i, j in enumerate(self.activeErrorPopup):
            j[0].move(
                self.width() - 520,
                self.height() - j[1] - 15 - self.activeErrorPopupCount * 10,
            )

        for i in self.activeErrorPopup:
            i[0].raise_()

    def dataLoad(self, num=-1):
        try:
            if os.path.isfile(fileDir):
                with open(fileDir, "r", encoding="UTF8") as f:
                    jsonObject = json.load(f)
                    if num == -1:
                        self.recentPreset = jsonObject["recentPreset"]
                    else:
                        self.recentPreset = num
                    data = jsonObject["preset"][self.recentPreset]

                    try:
                        self.serverID = data["serverID"]
                    except:
                        self.serverID = 0
                    try:
                        self.jobID = data["jobID"]
                    except:
                        self.jobID = 0
                    try:
                        self.activeDelaySlot = data["delay"][0]
                        self.inputDelay = data["delay"][1]
                        if self.activeDelaySlot == 0:
                            self.delay = 15
                        else:
                            self.delay = self.inputDelay
                    except:
                        self.activeDelaySlot = 0
                        self.inputDelay = 0
                        self.delay = 15
                    try:
                        self.activeCooltimeSlot = data["cooltime"][0]
                        self.inputCooltime = data["cooltime"][1]
                        if self.activeCooltimeSlot == 0:
                            self.cooltime = 0
                        else:
                            self.cooltime = self.inputCooltime
                    except:
                        self.activeCooltimeSlot = 0
                        self.inputCooltime = 0
                        self.cooltime = 0
                    try:
                        self.activeStartKeySlot = data["startKey"][0]
                        self.inputStartKey = data["startKey"][1]
                        if self.activeStartKeySlot == 0:
                            self.startKey = "F9"
                        else:
                            self.startKey = self.inputStartKey
                    except:
                        self.activeStartKeySlot = 0
                        self.inputStartKey = "F9"
                        self.startKey = "F9"
                    try:
                        self.activeMouseClickSlot = data["mouseClickType"]
                    except:
                        self.activeMouseClickSlot = 0
                    try:
                        self.tabNames = [
                            jsonObject["preset"][i]["name"]
                            for i in range(len(jsonObject["preset"]))
                        ]
                    except:
                        self.tabNames = ["스킬 매크로"]
                    try:
                        self.skillList = data["skills"]
                    except:
                        self.skillList = ["0", "1", "2", "3", "4", "5"]
                    try:
                        self.skillKeys = data["skillKeys"]
                    except:
                        self.skillKeys = ["2", "3", "4", "5", "6", "7"]
                    try:
                        self.comboBool = data["comboBool"]
                    except:
                        self.comboBool = [True, True, True, True, True, True]
                    try:
                        self.comboConnection = data["comboConnection"]
                    except:
                        self.comboConnection = []

            else:
                self.dataMake()
                self.dataLoad()
        except:
            self.dataMake()
            self.dataLoad()

    def dataMake(self):
        jsonObject = {
            "recentPreset": 0,
            "preset": [
                {
                    "serverID": 0,
                    "jobID": 0,
                    "delay": [0, 15],
                    "cooltime": [0, 0],
                    "startKey": [0, "F9"],
                    "mouseClickType": 0,
                    "name": "스킬 매크로",
                    "skills": ["0", "1", "2", "3", "4", "5"],
                    "skillKeys": ["2", "3", "4", "5", "6", "7"],
                    "comboBool": [True, True, True, True, True, True],
                    "comboConnection": [],
                }
            ],
        }

        if not os.path.isdir("C:\\ProDays"):
            os.mkdir("C:\\ProDays")
        with open(fileDir, "w", encoding="UTF8") as f:
            json.dump(jsonObject, f)

    def dataSave(self):
        with open(fileDir, "r", encoding="UTF8") as f:
            jsonObject = json.load(f)

        jsonObject["recentPreset"] = self.recentPreset

        jsonObject["preset"][self.recentPreset]["serverID"] = self.serverID
        jsonObject["preset"][self.recentPreset]["jobID"] = self.jobID
        jsonObject["preset"][self.recentPreset]["delay"] = [
            self.activeDelaySlot,
            self.inputDelay,
        ]
        jsonObject["preset"][self.recentPreset]["cooltime"] = [
            self.activeCooltimeSlot,
            self.inputCooltime,
        ]
        jsonObject["preset"][self.recentPreset]["startKey"] = [
            self.activeStartKeySlot,
            self.inputStartKey,
        ]
        jsonObject["preset"][self.recentPreset][
            "mouseClickType"
        ] = self.activeMouseClickSlot
        jsonObject["preset"][self.recentPreset]["name"] = self.tabNames[
            self.recentPreset
        ]
        jsonObject["preset"][self.recentPreset]["skills"] = self.skillList
        jsonObject["preset"][self.recentPreset]["skillKeys"] = self.skillKeys
        jsonObject["preset"][self.recentPreset]["comboBool"] = self.comboBool
        jsonObject["preset"][self.recentPreset][
            "comboConnection"
        ] = self.comboConnection

        with open(fileDir, "w", encoding="UTF8") as f:
            json.dump(jsonObject, f)

    def dataRemove(self, num):
        with open(fileDir, "r", encoding="UTF8") as f:
            jsonObject = json.load(f)

        jsonObject["preset"].pop(num)

        with open(fileDir, "w", encoding="UTF8") as f:
            json.dump(jsonObject, f)

    def dataAdd(self):
        with open(fileDir, "r", encoding="UTF8") as f:
            jsonObject = json.load(f)

        jsonObject["preset"].append(
            {
                "serverID": 0,
                "jobID": 0,
                "delay": [0, 15],
                "cooltime": [0, 0],
                "startKey": [0, "F9"],
                "mouseClickType": 0,
                "name": "스킬 매크로",
                "skills": ["0", "1", "2", "3", "4", "5"],
                "skillKeys": ["2", "3", "4", "5", "6", "7"],
                "comboBool": [True, True, True, True, True, True],
                "comboConnection": [],
            }
        )

        with open(fileDir, "w", encoding="UTF8") as f:
            json.dump(jsonObject, f)


if __name__ == "__main__":
    version = "v3.0.0"
    fileDir = "C:\\ProDays\\PDSkillMacro.json"
    app = QApplication(sys.argv)
    window = MyWindow()
    sys.exit(app.exec_())

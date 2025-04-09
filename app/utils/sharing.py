import os
import requests
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QMessageBox,
    QDialog,
    QFileDialog,
    QScrollArea,
    QWidget,
)


class Sharing:
    """
    Sharing class
    """

    def __init__(self, window):
        self.window = window
        self.sharing_frame = None
        self.username = ""
        self.password = ""
        self.macro_list_widget = None
        self.refresh_button = None

    # ================ UI Creation Functions ================
    def create_sharing_widget(self, parent_frame):
        """매크로 공유 서비스를 위한 UI 위젯 생성"""
        # 메인 프레임 생성
        self.sharing_frame = QFrame(parent_frame)
        self.sharing_frame.setStyleSheet("QFrame { background-color: rgb(29, 29, 29); border: 0px solid; }")

        # 레이아웃 설정
        main_layout = QVBoxLayout(self.sharing_frame)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        self.sharing_frame.setLayout(main_layout)

        # 상단 섹션 (헤더와 업로드 버튼)
        header_layout = QHBoxLayout()

        # 타이틀 레이블
        title_label = QLabel("Macro Sharing Service", self.sharing_frame)
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")

        # 업로드 버튼
        self.upload_button = QPushButton("Upload Macro", self.sharing_frame)
        self.upload_button.setFont(QFont("Arial", 12))
        self.upload_button.setStyleSheet(
            "background-color: #3B71CA; color: white; border-radius: 5px; padding: 10px 20px;"
        )
        self.upload_button.clicked.connect(self._handle_upload)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.upload_button)

        main_layout.addLayout(header_layout)

        # 다운로드 버튼
        self.download_button = QPushButton("Download", self.sharing_frame)
        self.download_button.setFont(QFont("Arial", 12))
        self.download_button.setStyleSheet(
            "background-color: #3B71CA; color: white; border-radius: 5px; padding: 10px 20px; max-width: 200px;"
        )
        self.download_button.clicked.connect(self._handle_download)
        main_layout.addWidget(self.download_button, 0, Qt.AlignmentFlag.AlignLeft)

        # "All Macros" 레이블
        all_macros_label = QLabel("All Macros", self.sharing_frame)
        all_macros_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        all_macros_label.setStyleSheet("color: white;")
        main_layout.addWidget(all_macros_label)

        # 매크로 목록 섹션
        self.macro_list_container = QWidget()
        self.macro_list_layout = QVBoxLayout(self.macro_list_container)
        self.macro_list_layout.setSpacing(20)

        # 매크로 카드 생성
        self._create_macro_cards()

        # 스크롤 영역 추가
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.macro_list_container)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #1d1d1d; }")

        main_layout.addWidget(scroll_area)

        # 상태 표시 레이블 (필요시 나중에 추가)
        self.status_label = QLabel("", self.sharing_frame)
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setStyleSheet("color: #666;")
        self.status_label.hide()  # 기본적으로 숨김
        main_layout.addWidget(self.status_label)

        # 로그인 설정 (백그라운드에서 작동하지만 UI는 보이지 않음)
        self.username = "default_user"
        self.password = "default_pass"

        return self.sharing_frame

    def _create_macro_cards(self):
        """매크로 카드 UI 생성"""
        # 임시 매크로 데이터
        macros = [
            {
                "name": "Skill Combo A",
                "creator": "Player123",
                "damage": "18,540",
                "description": "This macro combines powerful melee and ranged abilities, focusing on dealing fire and ice damage to enemies.",
                "icons": ["0/0/0.png", "0/0/1.png", "0/0/2.png", "0/0/3.png"],
            },
            {
                "name": "Burst Rotation",
                "creator": "MacroMaker",
                "damage": "26,780",
                "description": "A macro designed for quick burst damage using a sequence of high-impact abilities to maximize DPS on a single target.",
                "icons": ["0/1/0.png", "0/1/1.png", "0/1/2.png", "0/1/3.png"],
            },
            {
                "name": "PvP Skills",
                "creator": "GamerX",
                "damage": "14,320",
                "description": "Recommended for PvP situations to control and pressure opponents with a mix of crowd control and burst damage abilities.",
                "icons": ["0/2/0.png", "0/2/1.png", "0/2/2.png", "0/2/3.png"],
            },
            {
                "name": "Fire/ice Rotation",
                "creator": "User456",
                "damage": "25,910",
                "description": "A balanced macro alternating between fire and ice epplionm maintain consistent damage outout while exploiting enemy vuinerabilities.",
                "icons": ["0/3/0.png", "0/3/1.png", "0/3/2.png", "0/3/3.png"],
            },
        ]

        # 각 매크로에 대한 카드 생성 (2개씩 열 배치)
        row = 0
        col = 0
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)

        for i, macro in enumerate(macros):
            macro_card = self._create_macro_card(macro)
            grid_layout.addWidget(macro_card, row, col)

            col += 1
            if col > 1:  # 2개의 카드가 한 행에 배치되면 다음 행으로
                col = 0
                row += 1

        self.macro_list_layout.addLayout(grid_layout)

    def _create_macro_card(self, macro):
        """개별 매크로 카드 생성"""
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: #222222; border-radius: 5px; padding: 10px; }")
        card.setFixedSize(600, 180)  # 카드 크기 조절

        card_layout = QVBoxLayout(card)

        # 상단부 레이아웃 (아이콘들과 이름/점수)
        top_layout = QHBoxLayout()

        # 아이콘 레이아웃
        icons_layout = QHBoxLayout()
        icons_layout.setSpacing(5)

        # 아이콘 이미지
        for icon_path in macro["icons"]:
            icon_frame = QFrame()
            icon_frame.setFixedSize(60, 60)
            icon_frame.setStyleSheet("background-color: #111111; border-radius: 5px;")

            icon_layout = QVBoxLayout(icon_frame)
            icon_layout.setContentsMargins(0, 0, 0, 0)

            icon_label = QLabel()
            pixmap = QPixmap(os.path.join("app/resources/image/skill", icon_path))
            if pixmap.isNull():
                # 이미지가 없을 경우 대체 이미지 또는 색상 사용
                icon_label.setStyleSheet("background-color: #333333; border-radius: 5px;")
            else:
                icon_label.setPixmap(pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio))

            icon_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)
            icons_layout.addWidget(icon_frame)

        # 이름과 점수 레이아웃
        info_layout = QVBoxLayout()

        name_label = QLabel(macro["name"])
        name_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white;")

        creator_label = QLabel(macro["creator"])
        creator_label.setFont(QFont("Arial", 12))
        creator_label.setStyleSheet("color: #aaaaaa;")

        damage_label = QLabel(macro["damage"])
        damage_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        damage_label.setStyleSheet("color: #f0a33e;")  # Orange color
        damage_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        info_layout.addWidget(name_label)
        info_layout.addWidget(creator_label)

        # 상단부 조합
        top_layout.addLayout(icons_layout)
        top_layout.addStretch()
        top_layout.addWidget(damage_label)

        # 설명 텍스트
        description_label = QLabel(macro["description"])
        description_label.setFont(QFont("Arial", 12))
        description_label.setStyleSheet("color: #cccccc;")
        description_label.setWordWrap(True)

        # 카드에 모든 요소 추가
        card_layout.addLayout(top_layout)
        card_layout.addWidget(name_label)
        card_layout.addWidget(creator_label)
        card_layout.addWidget(description_label)

        return card

    # ================ Event Handlers ================
    def _handle_upload(self):
        """매크로 업로드 처리"""
        dialog = QDialog(self.window)
        dialog.setWindowTitle("매크로 업로드")
        dialog.setFixedSize(400, 150)

        layout = QVBoxLayout()

        # 파일 이름 입력
        filename_layout = QHBoxLayout()
        filename_label = QLabel("파일 이름:")
        filename_input = QLineEdit()
        filename_layout.addWidget(filename_label)
        filename_layout.addWidget(filename_input)

        # 버튼
        buttons_layout = QHBoxLayout()
        upload_btn = QPushButton("업로드")
        cancel_btn = QPushButton("취소")
        buttons_layout.addWidget(upload_btn)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(filename_layout)
        layout.addLayout(buttons_layout)

        dialog.setLayout(layout)

        # 이벤트 연결
        cancel_btn.clicked.connect(dialog.reject)

        def do_upload():
            filename = filename_input.text().strip()
            if not filename:
                self._show_message("경고", "파일 이름을 입력하세요.", QMessageBox.Icon.Warning)
                return

            # 데이터는 실제 애플리케이션에서 가져와야 함
            # 여기서는 샘플 데이터 사용
            data = {"name": filename, "content": {"content": "abc"}}

            result = self.upload_file(self.username, self.password, data, filename)

            if result and result.get("status") == "success":
                self._show_message(
                    "성공", "매크로가 성공적으로 업로드되었습니다.", QMessageBox.Icon.Information
                )
                dialog.accept()
            else:
                self._show_message("오류", "매크로 업로드에 실패했습니다.", QMessageBox.Icon.Critical)

        upload_btn.clicked.connect(do_upload)

        dialog.exec()

    def _handle_download(self):
        """매크로 다운로드 처리"""
        # 실제 구현에서는 선택된 매크로를 다운로드
        self._show_message("정보", "선택한 매크로를 다운로드합니다.", QMessageBox.Icon.Information)

        # 여기서는 모의 다운로드만 구현
        self.status_label.setText("매크로 다운로드 중...")
        self.status_label.show()

        # 실제 다운로드가 발생하는 코드로 대체해야 함
        # 예시: self.download_macro_file(owner, filename)

    def _show_message(self, title, message, icon=QMessageBox.Icon.Information):
        """메시지 박스 표시"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.exec()

    # ================ API Communication Functions ================
    def _handle_remote_request(self, payload):
        """Lambda 함수에 API 요청을 보내고 응답을 처리하는 함수"""

        headers = {"Content-Type": "application/json"}
        lambda_url = "https://khgusinpp5jsnynzhicbyid3k40ezcrf.lambda-url.ap-northeast-2.on.aws/"

        try:
            response = requests.post(
                lambda_url, headers=headers, json=payload, timeout=10  # Set a reasonable timeout
            )

            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            return None

    # ================ Data Operations Functions ================
    def upload_file(self, username, password, data, filename):
        """S3에 파일을 업로드하는 함수 - 인증 필요"""
        payload = {"username": username, "password": password, "data": data, "filename": filename}
        return self._handle_remote_request(payload)

    def delete_file(self, username, password, filename):
        """S3 파일을 삭제하는 함수 - 인증 필요"""
        payload = {"username": username, "password": password, "action": "delete_file", "filename": filename}
        return self._handle_remote_request(payload)

    def login(self, username, password):
        """로그인 함수 - 인증 필요"""
        payload = {"username": username, "password": password, "action": "login"}
        return self._handle_remote_request(payload)

    # ================ Non-authenticated Access Functions ================
    def list_macro_files(self):
        """macro_data 디렉토리의 파일 목록을 인증 없이 가져오는 함수"""
        payload = {"action": "list_all_files_no_auth"}
        return self._handle_remote_request(payload)

    def download_macro_file(self, owner, filename):
        """macro_data 디렉토리의 파일을 인증 없이 다운로드하는 함수"""
        payload = {"action": "download_file_no_auth", "owner": owner, "filename": filename}
        return self._handle_remote_request(payload)

    def download_skill_file(self):
        """skill_data 디렉토리의 파일을 인증 없이 다운로드하는 함수"""
        payload = {"action": "download_skill_file_no_auth"}
        return self._handle_remote_request(payload)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow

    app = QApplication([])
    window = QMainWindow()
    sharing = Sharing(window)
    sharing_widget = sharing.create_sharing_widget(window)
    window.setCentralWidget(sharing_widget)
    window.show()
    app.exec()

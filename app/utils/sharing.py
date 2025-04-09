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
        self.sharing_frame.setStyleSheet(
            "QFrame { background-color: rgb(255, 255, 255); border: 0px solid; }"
        )

        # 레이아웃 설정
        main_layout = QVBoxLayout(self.sharing_frame)
        main_layout.setContentsMargins(20, 20, 20, 20)
        self.sharing_frame.setLayout(main_layout)

        # 타이틀 레이블
        title_label = QLabel("매크로 공유 서비스", self.sharing_frame)
        title_label.setFont(QFont("나눔스퀘어라운드 ExtraBold", 16))
        title_label.setStyleSheet("color: #333;")
        main_layout.addWidget(title_label)

        # 로그인 섹션
        login_frame = self._create_login_section()
        main_layout.addWidget(login_frame)

        # 매크로 목록 섹션
        list_frame = self._create_macro_list_section()
        main_layout.addWidget(list_frame)

        # 업로드/다운로드/삭제 버튼 섹션
        buttons_frame = self._create_buttons_section()
        main_layout.addWidget(buttons_frame)

        # 상태 표시 레이블
        self.status_label = QLabel("", self.sharing_frame)
        self.status_label.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.status_label.setStyleSheet("color: #666;")
        main_layout.addWidget(self.status_label)

        return self.sharing_frame

    def _create_login_section(self):
        """로그인 섹션 생성"""
        login_frame = QFrame(self.sharing_frame)
        login_frame.setFrameShape(QFrame.Shape.StyledPanel)
        login_frame.setStyleSheet("QFrame { background-color: #f5f5f5; border-radius: 5px; padding: 10px; }")

        login_layout = QGridLayout(login_frame)

        # 사용자명 입력
        username_label = QLabel("사용자명:", login_frame)
        username_label.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.username_input = QLineEdit(login_frame)
        self.username_input.setPlaceholderText("사용자명 입력")

        # 비밀번호 입력
        password_label = QLabel("비밀번호:", login_frame)
        password_label.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.password_input = QLineEdit(login_frame)
        self.password_input.setPlaceholderText("비밀번호 입력")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        # 로그인 상태
        self.login_status = QLabel("로그인 필요", login_frame)
        self.login_status.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.login_status.setStyleSheet("color: #999;")

        # 로그인/로그아웃 버튼
        self.login_button = QPushButton("로그인", login_frame)
        self.login_button.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.login_button.setStyleSheet(
            "background-color: #4CAF50; color: white; border-radius: 3px; padding: 5px;"
        )
        self.login_button.clicked.connect(self._handle_login)

        # 레이아웃에 위젯 추가
        login_layout.addWidget(username_label, 0, 0)
        login_layout.addWidget(self.username_input, 0, 1, 1, 2)
        login_layout.addWidget(password_label, 1, 0)
        login_layout.addWidget(self.password_input, 1, 1, 1, 2)
        login_layout.addWidget(self.login_status, 2, 0, 1, 2)
        login_layout.addWidget(self.login_button, 2, 2)

        return login_frame

    def _create_macro_list_section(self):
        """매크로 목록 섹션 생성"""
        list_frame = QFrame(self.sharing_frame)
        list_frame.setFrameShape(QFrame.Shape.StyledPanel)
        list_frame.setStyleSheet("QFrame { background-color: #1e1e1e; border-radius: 5px; padding: 10px; }")

        list_layout = QVBoxLayout(list_frame)

        # 목록 타이틀
        list_title = QLabel("All Macros", list_frame)
        list_title.setFont(QFont("나눔스퀘어라운드 Bold", 14))
        list_title.setStyleSheet("color: white;")

        # 스크롤 영역 추가
        scroll_area = QScrollArea(list_frame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

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
                "name": "Fire/Ice Rotation",
                "creator": "User456",
                "damage": "25,910",
                "description": "A balanced macro alternating between fire and ice abilities to maintain consistent damage output while exploiting enemy vulnerabilities.",
                "icons": ["0/3/0.png", "0/3/1.png", "0/3/2.png", "0/3/3.png"],
            },
        ]

        for macro in macros:
            macro_frame = QFrame(scroll_content)
            macro_frame.setStyleSheet(
                "QFrame { background-color: #2e2e2e; border-radius: 5px; padding: 10px; }"
            )
            macro_layout = QHBoxLayout(macro_frame)

            # 스킬 아이콘
            icons_layout = QVBoxLayout()
            for icon_path in macro["icons"]:
                icon_label = QLabel(macro_frame)
                pixmap = QPixmap(os.path.join("app/resources/image/skill", icon_path))
                icon_label.setPixmap(pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio))
                icons_layout.addWidget(icon_label)

            # 매크로 정보
            info_layout = QVBoxLayout()
            name_label = QLabel(macro["name"], macro_frame)
            name_label.setFont(QFont("나눔스퀘어라운드 Bold", 12))
            name_label.setStyleSheet("color: white;")

            creator_label = QLabel(macro["creator"], macro_frame)
            creator_label.setFont(QFont("나눔스퀘어라운드 Regular", 10))
            creator_label.setStyleSheet("color: #aaaaaa;")

            damage_label = QLabel(macro["damage"], macro_frame)
            damage_label.setFont(QFont("나눔스퀘어라운드 Bold", 12))
            damage_label.setStyleSheet("color: orange;")

            description_label = QLabel(macro["description"], macro_frame)
            description_label.setFont(QFont("나눔스퀘어라운드 Regular", 10))
            description_label.setStyleSheet("color: #cccccc;")
            description_label.setWordWrap(True)

            info_layout.addWidget(name_label)
            info_layout.addWidget(creator_label)
            info_layout.addWidget(damage_label)
            info_layout.addWidget(description_label)

            macro_layout.addLayout(icons_layout)
            macro_layout.addLayout(info_layout)

            scroll_layout.addWidget(macro_frame)

        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)

        # 레이아웃에 추가
        list_layout.addWidget(list_title)
        list_layout.addWidget(scroll_area)

        return list_frame

    def _create_buttons_section(self):
        """버튼 섹션 생성"""
        buttons_frame = QFrame(self.sharing_frame)
        buttons_layout = QHBoxLayout(buttons_frame)

        # 업로드 버튼
        self.upload_button = QPushButton("매크로 업로드", buttons_frame)
        self.upload_button.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.upload_button.setStyleSheet(
            "background-color: #2196F3; color: white; border-radius: 3px; padding: 7px;"
        )
        self.upload_button.clicked.connect(self._handle_upload)

        # 다운로드 버튼
        self.download_button = QPushButton("매크로 다운로드", buttons_frame)
        self.download_button.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.download_button.setStyleSheet(
            "background-color: #FF9800; color: white; border-radius: 3px; padding: 7px;"
        )
        self.download_button.clicked.connect(self._handle_download)

        # 삭제 버튼
        self.delete_button = QPushButton("매크로 삭제", buttons_frame)
        self.delete_button.setFont(QFont("나눔스퀘어라운드 Bold", 10))
        self.delete_button.setStyleSheet(
            "background-color: #F44336; color: white; border-radius: 3px; padding: 7px;"
        )
        self.delete_button.clicked.connect(self._handle_delete)

        # 레이아웃에 버튼 추가
        buttons_layout.addWidget(self.upload_button)
        buttons_layout.addWidget(self.download_button)
        buttons_layout.addWidget(self.delete_button)

        return buttons_frame

    # ================ Event Handlers ================
    def _handle_login(self):
        """로그인 처리"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self._show_message("경고", "사용자명과 비밀번호를 입력하세요.", QMessageBox.Icon.Warning)
            return

        # 실제 인증 로직은 여기서 구현해야 함
        result = self.login(username, password)
        if not result or not result.get("status") == "success":
            self._show_message("오류", "로그인에 실패했습니다.", QMessageBox.Icon.Critical)
            return

        # 임시로 성공했다고 가정
        self.username = username
        self.password = password
        self.login_status.setText(f"로그인됨: {self.username}")
        self.login_status.setStyleSheet("color: green;")
        self.login_button.setText("로그아웃")
        self.login_button.clicked.disconnect()
        self.login_button.clicked.connect(self._handle_logout)

        self.refresh_macro_list()

    def _handle_logout(self):
        """로그아웃 처리"""
        self.username = ""
        self.password = ""
        self.username_input.clear()
        self.password_input.clear()
        self.login_status.setText("로그인 필요")
        self.login_status.setStyleSheet("color: #999;")
        self.login_button.setText("로그인")
        self.login_button.clicked.disconnect()
        self.login_button.clicked.connect(self._handle_login)

        self.refresh_macro_list()

    def refresh_macro_list(self):
        """매크로 목록 새로고침"""
        self.macro_list_widget.clear()
        self.status_label.setText("매크로 목록을 불러오는 중...")

        # 매크로 목록 가져오기
        result = self.list_macro_files()

        if result and "files" in result:
            files = result["files"]
            if files:
                for file_info in files:
                    filename = file_info.get("filename", "Unknown")
                    owner = file_info.get("owner", "Unknown")
                    created = file_info.get("created", "Unknown")

                    item = QListWidgetItem(f"{owner}/{filename} (생성일: {created})")
                    item.setData(Qt.ItemDataRole.UserRole, file_info)  # 파일 정보 저장
                    self.macro_list_widget.addItem(item)

                self.status_label.setText(f"{len(files)}개의 매크로를 불러왔습니다.")
            else:
                self.status_label.setText("공유된 매크로가 없습니다.")
        else:
            self.status_label.setText("매크로 목록을 불러오지 못했습니다.")

    def _handle_upload(self):
        """매크로 업로드 처리"""
        if not self._check_login():
            self._show_message("경고", "로그인 후 업로드할 수 있습니다.", QMessageBox.Icon.Warning)
            return

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
                self.refresh_macro_list()
                dialog.accept()
            else:
                self._show_message("오류", "매크로 업로드에 실패했습니다.", QMessageBox.Icon.Critical)

        upload_btn.clicked.connect(do_upload)

        dialog.exec()

    def _handle_download(self):
        """매크로 다운로드 처리"""
        selected_items = self.macro_list_widget.selectedItems()

        if not selected_items:
            self._show_message("경고", "다운로드할 매크로를 선택하세요.", QMessageBox.Icon.Warning)
            return

        file_info = selected_items[0].data(Qt.ItemDataRole.UserRole)
        owner = file_info.get("owner")
        filename = file_info.get("filename")

        self.status_label.setText(f"{owner}/{filename} 다운로드 중...")

        result = self.download_macro_file(owner, filename)

        if result and result.get("data"):
            self._show_message(
                "성공", f"{filename} 매크로를 성공적으로 다운로드했습니다.", QMessageBox.Icon.Information
            )
            self.status_label.setText(f"{filename} 매크로를 다운로드했습니다.")

            # 여기서 다운로드한 데이터 처리
            # 예: 애플리케이션에 매크로 적용 또는 파일로 저장
        else:
            self._show_message("오류", "매크로 다운로드에 실패했습니다.", QMessageBox.Icon.Critical)
            self.status_label.setText("매크로 다운로드에 실패했습니다.")

    def _handle_delete(self):
        """매크로 삭제 처리"""
        if not self._check_login():
            self._show_message("경고", "로그인 후 삭제할 수 있습니다.", QMessageBox.Icon.Warning)
            return

        selected_items = self.macro_list_widget.selectedItems()

        if not selected_items:
            self._show_message("경고", "삭제할 매크로를 선택하세요.", QMessageBox.Icon.Warning)
            return

        file_info = selected_items[0].data(Qt.ItemDataRole.UserRole)
        owner = file_info.get("owner")
        filename = file_info.get("filename")

        # 자신의 매크로만 삭제 가능
        if owner != self.username:
            self._show_message(
                "경고", "자신이 업로드한 매크로만 삭제할 수 있습니다.", QMessageBox.Icon.Warning
            )
            return

        confirm = self._show_confirm("확인", f"{filename} 매크로를 삭제하시겠습니까?")

        if confirm:
            self.status_label.setText(f"{filename} 삭제 중...")

            result = self.delete_file(self.username, self.password, filename)

            if result and result.get("status") == "success":
                self._show_message(
                    "성공", f"{filename} 매크로를 성공적으로 삭제했습니다.", QMessageBox.Icon.Information
                )
                self.refresh_macro_list()
            else:
                self._show_message("오류", "매크로 삭제에 실패했습니다.", QMessageBox.Icon.Critical)
                self.status_label.setText("매크로 삭제에 실패했습니다.")

    def _check_login(self):
        """로그인 상태 확인"""
        if not self.username or not self.password:
            return False
        return True

    def _show_message(self, title, message, icon=QMessageBox.Icon.Information):
        """메시지 박스 표시"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.exec()

    def _show_confirm(self, title, message):
        """확인 대화상자 표시"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        return msg_box.exec() == QMessageBox.StandardButton.Yes

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

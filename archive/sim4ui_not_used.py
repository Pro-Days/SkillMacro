# class Sim4UI:
#     def __init__(self, parent, shared_data: SharedData):
#         self.shared_data = shared_data
#         self.parent = parent

#         self.ui_var = UI_Variable()

#         self.makeSim4UI()

#     def makeSim4UI(self):
#         self.shared_data.is_card_updated = False

#         powers = detSimulate(
#             self.shared_data,
#             self.shared_data.info_stats,
#             self.shared_data.info_sim_details,
#         ).powers
#         for i, power in enumerate(powers):
#             self.shared_data.powers[i] = power
#         # self.sim_powers = [str(int(i)) for i in self.sim_powers]

#         self.name = ""
#         self.prev_name = ""
#         self.real_name = ""
#         self.char_image = None
#         self.info_char_data = None

#         # 카드 프레임
#         self.mainframe = QFrame(self.parent)
#         self.mainframe.setGeometry(
#             0,
#             0,
#             928,
#             self.ui_var.sim_char_frame_H,
#         )
#         self.mainframe.setStyleSheet(
#             """QFrame {
#             background-color: rgb(255, 255, 255);
#             border: 0px solid;
#         }"""
#         )

#         ## 캐릭터 정보 입력
#         self.info_frame = QFrame(self.mainframe)
#         self.info_frame.setGeometry(
#             self.ui_var.sim_char_margin,
#             self.ui_var.sim_char_margin_y,
#             self.ui_var.sim_charInfo_W,
#             self.ui_var.sim_charInfo_H,
#         )
#         self.info_frame.setStyleSheet(
#             """QFrame {
#             background-color: #F8F8F8;
#             border: 1px solid #CCCCCC;
#             border-radius: 4px;
#         }"""
#         )

#         # 닉네임 입력
#         self.info_name_frame = QFrame(self.info_frame)
#         self.info_name_frame.setGeometry(
#             self.ui_var.sim_charInfo_marginX,
#             self.ui_var.sim_charInfo_marginY,
#             self.ui_var.sim_charInfo_frame_W,
#             self.ui_var.sim_charInfo_nickname_H,
#         )
#         self.info_name_frame.setStyleSheet(
#             """QFrame {
#             background-color: #FFFFFF;
#             border: 1px solid #DDDDDD;
#             border-radius: 4px;
#         }"""
#         )

#         self.info_name_label = QLabel("닉네임", self.info_name_frame)
#         self.info_name_label.setGeometry(
#             self.ui_var.sim_charInfo_nickname_input_margin,
#             self.ui_var.sim_charInfo_label_y,
#             self.ui_var.sim_charInfo_nickname_input_W,
#             self.ui_var.sim_charInfo_label_H,
#         )
#         self.info_name_label.setStyleSheet(
#             """QLabel {
#             background-color: transparent;
#             border: 0px solid;
#         }"""
#         )
#         self.info_name_label.setFont(CustomFont(14))
#         self.info_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         self.info_name_input = CustomLineEdit(self.info_name_frame, None, "", 12)
#         self.info_name_input.setGeometry(
#             self.ui_var.sim_charInfo_nickname_input_margin,
#             self.ui_var.sim_charInfo_label_y + self.ui_var.sim_charInfo_label_H,
#             self.ui_var.sim_charInfo_nickname_input_W,
#             self.ui_var.sim_charInfo_nickname_input_H,
#         )
#         self.info_name_input.setFocus()

#         self.info_name_button = QPushButton("불러오기", self.info_name_frame)
#         self.info_name_button.setGeometry(
#             self.ui_var.sim_charInfo_nickname_load_margin,
#             self.ui_var.sim_charInfo_nickname_load_y,
#             self.ui_var.sim_charInfo_nickname_load_W,
#             self.ui_var.sim_charInfo_nickname_load_H,
#         )
#         self.info_name_button.setStyleSheet(
#             f"""QPushButton {{
#             background-color: #70BB70;
#             border: 1px solid {self.ui_var.sim_input_colors[1]};
#             border-radius: 4px;
#             }}
#             QPushButton:hover {{
#                 background-color: #60A060;
#             }}"""
#         )
#         self.info_name_button.setFont(CustomFont(10))
#         self.info_name_button.clicked.connect(self.load_char_info)

#         # 캐릭터 선택
#         # 캐릭터 불러오면 시뮬레이션 진행한 직업과 같은 것만 선택 가능하도록
#         self.info_char_frame = QFrame(self.info_frame)
#         self.info_char_frame.setGeometry(
#             self.ui_var.sim_charInfo_marginX,
#             self.ui_var.sim_charInfo_marginY * 2 + self.ui_var.sim_charInfo_nickname_H,
#             self.ui_var.sim_charInfo_frame_W,
#             self.ui_var.sim_charInfo_char_H,
#         )
#         self.info_char_frame.setStyleSheet(
#             """QFrame {
#             background-color: #FFFFFF;
#             border: 1px solid #DDDDDD;
#             border-radius: 4px;
#         }"""
#         )

#         self.info_char_label = QLabel("캐릭터 선택", self.info_char_frame)
#         self.info_char_label.setGeometry(
#             0,
#             self.ui_var.sim_charInfo_label_y,
#             self.ui_var.sim_charInfo_frame_W,
#             self.ui_var.sim_charInfo_label_H,
#         )
#         self.info_char_label.setStyleSheet(
#             """QLabel {
#             background-color: transparent;
#             border: 0px solid;
#         }"""
#         )
#         self.info_char_label.setFont(CustomFont(14))
#         self.info_char_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         self.info_char_buttons = []
#         for i in range(3):
#             button = QPushButton("", self.info_char_frame)
#             button.setGeometry(
#                 self.ui_var.sim_charInfo_char_button_margin
#                 + (
#                     self.ui_var.sim_charInfo_char_button_W
#                     + self.ui_var.sim_charInfo_char_button_margin
#                 )
#                 * i,
#                 self.ui_var.sim_charInfo_char_button_y,
#                 self.ui_var.sim_charInfo_char_button_W,
#                 self.ui_var.sim_charInfo_char_button_H,
#             )
#             button.setStyleSheet(
#                 f"""QPushButton {{
#                 background-color: {self.ui_var.sim_input_colors[0]};
#                 border: 1px solid {self.ui_var.sim_input_colors[1]};
#                 border-radius: 8px;
#                 }}"""
#             )
#             button.setFont(CustomFont(10))

#             self.info_char_buttons.append(button)

#         # 전투력 표시
#         self.info_power_display = [True, True, True, True]

#         self.info_power_frame = QFrame(self.info_frame)
#         self.info_power_frame.setGeometry(
#             self.ui_var.sim_charInfo_marginX,
#             self.ui_var.sim_charInfo_marginY * 3
#             + self.ui_var.sim_charInfo_nickname_H
#             + self.ui_var.sim_charInfo_char_H,
#             self.ui_var.sim_charInfo_frame_W,
#             self.ui_var.sim_charInfo_char_H,
#         )
#         self.info_power_frame.setStyleSheet(
#             """QFrame {
#             background-color: #FFFFFF;
#             border: 1px solid #DDDDDD;
#             border-radius: 4px;
#         }"""
#         )

#         self._info_power_label = QLabel("전투력 표시", self.info_power_frame)
#         self._info_power_label.setGeometry(
#             0,
#             self.ui_var.sim_charInfo_label_y,
#             self.ui_var.sim_charInfo_frame_W,
#             self.ui_var.sim_charInfo_label_H,
#         )
#         self._info_power_label.setStyleSheet(
#             """QLabel {
#             background-color: transparent;
#             border: 0px solid;
#         }"""
#         )
#         self._info_power_label.setFont(CustomFont(14))
#         self._info_power_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         self.info_power_buttons = []
#         for i in range(4):
#             button = QPushButton(
#                 self.shared_data.POWER_TITLES[i], self.info_power_frame
#             )
#             button.setGeometry(
#                 self.ui_var.sim_charInfo_power_button_margin
#                 + (
#                     self.ui_var.sim_charInfo_power_button_W
#                     + self.ui_var.sim_charInfo_power_button_margin
#                 )
#                 * i,
#                 self.ui_var.sim_charInfo_power_button_y,
#                 self.ui_var.sim_charInfo_power_button_W,
#                 self.ui_var.sim_charInfo_power_button_H,
#             )
#             button.setStyleSheet(
#                 f"""QPushButton {{
#                 background-color: #FFFFFF;
#                 border: 1px solid {self.ui_var.sim_input_colors[1]};
#                 border-radius: 5px;
#                 }}
#                 QPushButton:hover {{
#                     background-color: #F0F0F0;
#                 }}"""
#             )
#             button.setFont(CustomFont(10))
#             button.clicked.connect(partial(lambda x: self.info_powers_clicked(x), i))

#             self.info_power_buttons.append(button)

#         # 입력 완료
#         self.info_complete_button = QPushButton("입력 완료", self.info_frame)
#         self.info_complete_button.setGeometry(
#             self.ui_var.sim_charInfo_complete_margin,
#             self.ui_var.sim_charInfo_marginY * 3
#             + self.ui_var.sim_charInfo_nickname_H
#             + self.ui_var.sim_charInfo_char_H
#             + self.ui_var.sim_charInfo_power_H
#             + self.ui_var.sim_charInfo_complete_y,
#             self.ui_var.sim_charInfo_complete_W,
#             self.ui_var.sim_charInfo_complete_H,
#         )
#         self.info_complete_button.setStyleSheet(
#             f"""QPushButton {{
#             background-color: #70BB70;
#             border: 1px solid {self.ui_var.sim_input_colors[1]};
#             border-radius: 8px;
#             }}
#             QPushButton:hover {{
#                 background-color: #60A060;
#             }}"""
#         )
#         self.info_complete_button.setFont(CustomFont(14))
#         self.info_complete_button.clicked.connect(self.card_update)

#         self.info_save_button = QPushButton("저장", self.info_frame)
#         self.info_save_button.setGeometry(
#             self.ui_var.sim_charInfo_save_margin,
#             self.ui_var.sim_charInfo_marginY * 3
#             + self.ui_var.sim_charInfo_nickname_H
#             + self.ui_var.sim_charInfo_char_H
#             + self.ui_var.sim_charInfo_power_H
#             + self.ui_var.sim_charInfo_save_y,
#             self.ui_var.sim_charInfo_save_W,
#             self.ui_var.sim_charInfo_save_H,
#         )
#         self.info_save_button.setStyleSheet(
#             f"""QPushButton {{
#             background-color: #FF8282;
#             border: 1px solid {self.ui_var.sim_input_colors[1]};
#             border-radius: 8px;
#             }}
#             QPushButton:hover {{
#                 background-color: #FF6060;
#             }}"""
#         )
#         self.info_save_button.setFont(CustomFont(14))
#         self.info_save_button.clicked.connect(self.card_save)

#         ## 캐릭터 카드
#         self.card_frame = QFrame(self.mainframe)
#         self.card_frame.setGeometry(
#             self.ui_var.sim_char_margin * 3 + self.ui_var.sim_charInfo_W,
#             self.ui_var.sim_char_margin_y,
#             self.ui_var.sim_charCard_W,
#             self.ui_var.sim_charCard_H,
#         )
#         self.card_frame.setStyleSheet(
#             """QFrame {
#             background-color: #FFFFFF;
#             border: 3px solid #CCCCCC;
#             border-radius: 0px;
#         }"""
#         )

#         # 타이틀
#         self.card_title = QLabel("한월 캐릭터 카드", self.card_frame)
#         self.card_title.setGeometry(
#             0,
#             0,
#             self.ui_var.sim_charCard_W,
#             self.ui_var.sim_charCard_title_H,
#         )
#         self.card_title.setStyleSheet(
#             """QLabel {
#             background-color: #CADEFC;
#             border: 3px solid #CCCCCC;
#             border-bottom: 0px solid;
#             border-radius: 0px;
#         }"""
#         )
#         self.card_title.setFont(CustomFont(18))
#         self.card_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         # 이미지
#         self.card_image_bg = QLabel("", self.card_frame)
#         self.card_image_bg.setGeometry(
#             self.ui_var.sim_charCard_image_margin,
#             self.ui_var.sim_charCard_image_margin + self.ui_var.sim_charCard_title_H,
#             self.ui_var.sim_charCard_image_W,
#             self.ui_var.sim_charCard_image_H,
#         )
#         self.card_image_bg.setStyleSheet(
#             """QLabel {
#             background-color: transparent;
#             border: 5px solid #AAAAAA;
#             border-radius: 5px;
#         }"""
#         )
#         self.card_image_bg.setScaledContents(True)

#         self.card_image = QLabel("", self.card_frame)
#         self.card_image.setGeometry(
#             self.ui_var.sim_charCard_image_margin + 15,
#             self.ui_var.sim_charCard_image_margin
#             + self.ui_var.sim_charCard_title_H
#             + 15,
#             self.ui_var.sim_charCard_image_W - 30,  # 126
#             self.ui_var.sim_charCard_image_H - 30,  # 282
#         )
#         self.card_image.setStyleSheet(
#             """QLabel {
#             background-color: transparent;
#             border: 0px solid;
#         }"""
#         )
#         self.card_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         self.card_image.setScaledContents(True)

#         # 캐릭터 정보
#         self.card_name = QLabel("", self.card_frame)
#         self.card_name.setGeometry(
#             self.ui_var.sim_charCard_name_margin,
#             self.ui_var.sim_charCard_name_y,
#             self.ui_var.sim_charCard_name_W,
#             self.ui_var.sim_charCard_name_H,
#         )
#         self.card_name.setStyleSheet(
#             """QLabel {
#             background-color: transparent;
#             border: 0px solid;
#         }"""
#         )
#         self.card_name.setFont(CustomFont(18))
#         self.card_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         self.card_job = QLabel("", self.card_frame)
#         self.card_job.setGeometry(
#             self.ui_var.sim_charCard_job_margin,
#             self.ui_var.sim_charCard_job_y,
#             self.ui_var.sim_charCard_job_W,
#             self.ui_var.sim_charCard_job_H,
#         )
#         self.card_job.setStyleSheet(
#             """QLabel {
#             background-color: transparent;
#             border: 0px solid;
#         }"""
#         )
#         self.card_job.setFont(CustomFont(12))
#         self.card_job.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         self.card_level = QLabel("", self.card_frame)
#         self.card_level.setGeometry(
#             self.ui_var.sim_charCard_level_margin,
#             self.ui_var.sim_charCard_level_y,
#             self.ui_var.sim_charCard_level_W,
#             self.ui_var.sim_charCard_level_H,
#         )
#         self.card_level.setStyleSheet(
#             """QLabel {
#             background-color: transparent;
#             border: 0px solid;
#         }"""
#         )
#         self.card_level.setFont(CustomFont(12))
#         self.card_level.setAlignment(Qt.AlignmentFlag.AlignCenter)

#         self.card_name_line = QFrame(self.card_frame)
#         self.card_name_line.setGeometry(
#             self.ui_var.sim_charCard_name_margin + 10,
#             self.ui_var.sim_charCard_name_y + self.ui_var.sim_charCard_name_H,
#             self.ui_var.sim_charCard_name_line_W,
#             1,
#         )
#         self.card_name_line.setStyleSheet(
#             """QFrame {
#             background-color: #CCCCCC;
#             border: 0px solid;
#         }"""
#         )

#         self.card_info_line = QFrame(self.card_frame)
#         self.card_info_line.setGeometry(
#             self.ui_var.sim_charCard_level_margin + 1,
#             self.ui_var.sim_charCard_level_y + 12,
#             1,
#             self.ui_var.sim_charCard_info_line_H,
#         )
#         self.card_info_line.setStyleSheet(
#             """QFrame {
#             background-color: #CCCCCC;
#             border: 0px solid;
#         }"""
#         )

#         # 전투력
#         self.card_powers = [[], [], [], []]
#         for i in range(4):
#             frame = QFrame(self.card_frame)
#             frame.setGeometry(
#                 self.ui_var.sim_charCard_powerFrame_margin,
#                 self.ui_var.sim_charCard_powerFrame_y
#                 + self.ui_var.sim_charCard_powerFrame_H * i,
#                 self.ui_var.sim_charCard_powerFrame_W,
#                 self.ui_var.sim_charCard_powerFrame_H,
#             )
#             frame.setStyleSheet(
#                 """QFrame {
#                 background-color: transparent;
#                 border: 0px solid;
#             }"""
#             )

#             title = QLabel(self.shared_data.POWER_TITLES[i], frame)
#             title.setStyleSheet(
#                 f"""QLabel {{
#                     background-color: rgb({self.ui_var.sim_colors4[i]});
#                     border: 1px solid rgb({self.ui_var.sim_colors4[i]});
#                     border-top-left-radius: 4px;
#                     border-top-right-radius: 0px;
#                     border-bottom-left-radius: 4px;
#                     border-bottom-right-radius: 0px;
#                 }}"""
#             )
#             title.setGeometry(
#                 0,
#                 0,
#                 self.ui_var.sim_charCard_power_title_W,
#                 self.ui_var.sim_charCard_powerFrame_H,
#             )
#             title.setFont(CustomFont(12))
#             title.setAlignment(Qt.AlignmentFlag.AlignCenter)

#             number = QLabel("", frame)
#             number.setStyleSheet(
#                 f"""QLabel {{
#                     background-color: rgba({self.ui_var.sim_colors4[i]}, 120);
#                     border: 1px solid rgb({self.ui_var.sim_colors4[i]});
#                     border-left: 0px solid;
#                     border-top-left-radius: 0px;
#                     border-top-right-radius: 4px;
#                     border-bottom-left-radius: 0px;
#                     border-bottom-right-radius: 4px
#                 }}"""
#             )
#             number.setGeometry(
#                 self.ui_var.sim_charCard_power_title_W,
#                 0,
#                 self.ui_var.sim_charCard_power_number_W,
#                 self.ui_var.sim_charCard_powerFrame_H,
#             )
#             number.setFont(CustomFont(14))
#             number.setAlignment(Qt.AlignmentFlag.AlignCenter)

#             self.card_powers[i].append(frame)
#             self.card_powers[i].append(title)
#             self.card_powers[i].append(number)

#     def load_char_info(self):
#         self.info_char_data = None

#         try:
#             data = get_character_info(self.info_name_input.text())
#         except:
#             print("error")
#             return

#         for i, j in enumerate(data):
#             job, level = j["job"], j["level"]
#             if job == self.shared_data.job_ID:
#                 self.info_char_buttons[i].setText(f"{job} | Lv.{level}")
#                 self.info_char_buttons[i].setStyleSheet(
#                     f"""QPushButton {{
#                     background-color: #FFFFFF;
#                     border: 1px solid {self.ui_var.sim_input_colors[1]};
#                     border-radius: 8px;
#                     color: #000000;
#                     }}
#                     QPushButton:hover {{
#                         background-color: #F0F0F0;
#                     }}"""
#                 )

#                 self.info_char_buttons[i].clicked.connect(
#                     partial(lambda x, y: self.select_char(x, y), i, j)
#                 )
#             else:
#                 self.info_char_buttons[i].setText(f"{job} | Lv.{level}")
#                 self.info_char_buttons[i].setStyleSheet(
#                     f"""QPushButton {{
#                     background-color: #FFFFFF;
#                     border: 1px solid {self.ui_var.sim_input_colors[1]};
#                     border-radius: 8px;
#                     color: rgb(153, 153, 153);
#                     }}"""
#                 )

#                 try:
#                     self.info_char_buttons[i].clicked.disconnect()
#                 except:
#                     pass

#     def select_char(self, index, data):
#         self.load_char_info()

#         self.info_char_data = data

#         self.info_char_buttons[index].setStyleSheet(
#             f"""QPushButton {{
#             background-color: #CCCCCC;
#             border: 1px solid {self.ui_var.sim_input_colors[1]};
#             border-radius: 8px;
#             color: #000000;
#             }}"""
#         )

#     def info_powers_clicked(self, num):
#         self.info_power_display[num] = not self.info_power_display[num]

#         for i in range(4):
#             self.info_power_buttons[i].setStyleSheet(
#                 f"""QPushButton {{
#                 background-color: #FFFFFF;
#                 border: 1px solid {self.ui_var.sim_input_colors[1]};
#                 border-radius: 5px;
#                 color: {"#000000" if self.info_power_display[i] else "rgb(153, 153, 153)"};
#                 }}
#                 QPushButton:hover {{
#                     background-color: #F0F0F0;
#                 }}"""
#             )

#     def card_save(self):
#         if not self.shared_data.is_card_updated:
#             return

#         scale_factor = 3
#         original_size = self.card_frame.size()
#         scaled_size = original_size * scale_factor

#         pixmap = QPixmap(scaled_size)
#         pixmap.fill()

#         painter = QPainter(pixmap)
#         painter.scale(scale_factor, scale_factor)
#         self.card_frame.render(painter)
#         painter.end()

#         # Open a file dialog to save the image
#         file_dialog = QFileDialog()
#         file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
#         file_dialog.setNameFilters(["Images (*.png *.jpg *.bmp)"])
#         file_dialog.setDefaultSuffix("png")
#         if file_dialog.exec():
#             file_path = file_dialog.selectedFiles()[0]
#             pixmap.save(file_path)
#             os.startfile(file_path)

#     def card_update(self):
#         if self.info_char_data is None:
#             self.shared_data.is_card_updated = False
#             return

#         if not any(self.info_power_display):
#             self.shared_data.is_card_updated = False
#             return

#         self.name = self.info_name_input.text()
#         if self.name != self.prev_name:
#             try:
#                 self.real_name, url = get_character_card_data(self.name)
#             except:
#                 self.shared_data.is_card_updated = False
#                 return

#             self.char_image = requests.get(url).content
#             self.prev_name = self.name

#         pixmap = QPixmap(convert_resource_path("resources\\image\\card_bg.png"))
#         self.card_image_bg.setPixmap(pixmap)
#         pixmap = QPixmap()
#         pixmap.loadFromData(self.char_image)

#         h_ratio = 282 / pixmap.height()
#         width = round(pixmap.width() * h_ratio)
#         dWidth = width - (self.ui_var.sim_charCard_image_W - 30)

#         self.card_image.setGeometry(
#             self.ui_var.sim_charCard_image_margin + 15 - dWidth // 2,
#             self.ui_var.sim_charCard_image_margin
#             + self.ui_var.sim_charCard_title_H
#             + 15,
#             round(pixmap.width() * h_ratio),
#             self.ui_var.sim_charCard_image_H - 30,
#         )
#         self.card_image.setPixmap(pixmap)

#         adjust_font_size(self.card_name, self.real_name, 18)
#         self.card_job.setText(self.shared_data.job_ID)
#         self.card_level.setText(f"Lv.{self.info_char_data['level']}")

#         countF = self.info_power_display.count(False)
#         count = 0
#         for i in range(4):
#             if self.info_power_display[i]:
#                 self.card_powers[i][0].setGeometry(
#                     self.ui_var.sim_charCard_powerFrame_margin,
#                     self.ui_var.sim_charCard_powerFrame_y
#                     + self.ui_var.sim_charCard_powerFrame_H * count
#                     + 20 * countF,
#                     self.ui_var.sim_charCard_powerFrame_W,
#                     self.ui_var.sim_charCard_powerFrame_H,
#                 )
#                 self.card_powers[i][2].setText(f"{int(self.shared_data.powers[i])}")

#                 self.card_powers[i][0].show()
#                 count += 1

#             else:
#                 self.card_powers[i][0].hide()

#         self.shared_data.is_card_updated = True

from PyQt5.QtWidgets import QApplication, QWidget, QStackedLayout, QPushButton

app = QApplication([])

window = QWidget()
layout = QStackedLayout()

page1 = QPushButton("Page 1")
page2 = QPushButton("Page 2")

layout.addWidget(page1)
layout.addWidget(page2)

window.setLayout(layout)
layout.setCurrentIndex(0)  # 첫 번째 페이지 표시

window.show()

app.exec_()

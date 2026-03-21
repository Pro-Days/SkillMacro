import multiprocessing
import sys

from PySide6.QtWidgets import QApplication

from app.scripts.ui.main_window import MainWindow


def main() -> None:
    app: QApplication = QApplication(sys.argv)
    MainWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    # 패키징된 윈도우 실행 파일의 멀티프로세스 워커 초기화
    multiprocessing.freeze_support()

    # 메인 UI 프로세스 진입
    main()

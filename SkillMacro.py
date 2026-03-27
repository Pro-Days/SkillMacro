import sys
from multiprocessing import freeze_support


def main() -> None:
    # Windows frozen 멀티프로세싱 재진입 차단 블록
    freeze_support()

    # 워커 프로세스 UI 모듈 import 차단 블록
    from PySide6.QtWidgets import QApplication

    from app.scripts.ui.main_window import MainWindow

    # Qt 애플리케이션 생성 블록
    app: QApplication = QApplication(sys.argv)
    MainWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

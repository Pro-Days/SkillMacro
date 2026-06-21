import sys
from multiprocessing import freeze_support


def main() -> None:
    # Windows frozen 멀티프로세싱 재진입 차단
    freeze_support()

    # 워커 프로세스 UI 모듈 import 차단
    from PySide6.QtWidgets import QApplication

    from app.scripts.ui.main_window import MainWindow, warmup_qt_type_bindings

    # Qt 애플리케이션 생성
    app: QApplication = QApplication(sys.argv)

    # 위젯 생성 전 Qt 타입 바인딩 초기화
    warmup_qt_type_bindings()

    MainWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

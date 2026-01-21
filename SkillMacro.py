import sys

from PyQt6.QtWidgets import QApplication

from app.scripts.ui.main_window import MainWindow


def main() -> None:
    app: QApplication = QApplication(sys.argv)
    MainWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

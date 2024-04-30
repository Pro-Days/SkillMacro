import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QSystemTrayIcon,
    QMenu,
)
from PyQt6.QtGui import QIcon


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Taskbar Badge Example")

        # Create a button to update the badge count
        self.button = QPushButton("Update Badge Count", self)
        self.button.clicked.connect(self.updateBadgeCount)
        self.setCentralWidget(self.button)

        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("resource\\icon.png"))  # Set your own icon here
        self.tray_icon.setToolTip("Taskbar Badge Example")

        # Create a context menu for the system tray icon
        menu = QMenu(self)
        self.tray_icon.setContextMenu(menu)

        self.show()

    def updateBadgeCount(self):
        # Update badge count
        count = 5  # Example count
        if hasattr(
            self.tray_icon, "setOverlayIcon"
        ):  # Check if overlay icon is supported
            self.tray_icon.setIcon(
                QIcon("resource\\icon.png")
            )  # Set your own icon here
            self.tray_icon.setToolTip(f"Taskbar Badge Example ({count})")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())

import requests

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class VersionChecker(QObject):
    """
    최신버전 확인 후 알림 팝업 띄움
    """

    versionChecked = pyqtSignal(str)

    @pyqtSlot()
    def checkVersion(self):
        try:
            response = requests.get("https://api.github.com/repos/pro-days/skillmacro/releases/latest")
            if response.status_code == 200:
                recentVersion = response.json()["name"]
                self.updateUrl = response.json()["html_url"]
                self.versionChecked.emit(recentVersion)
            else:
                self.versionChecked.emit("FailedUpdateCheck")
        except:
            self.versionChecked.emit("FailedUpdateCheck")

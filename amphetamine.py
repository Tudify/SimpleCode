from PyQt6.QtCore import QUrl, Qt, QSettings, QEvent, QObject, pyqtSlot, QEventLoop
from PyQt6.QtWidgets import QApplication, QMessageBox, QMainWindow, QDialog, QDialogButtonBox, QDockWidget, QWidget, QPlainTextEdit
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePermission, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from pathlib import Path
from enum import Enum, IntFlag
import json, random

ver = 1.0

def version():
    return ver()

class QtPTEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

class MainWindowQt(QMainWindow):
    def __init__(self):
        super().__init__()

class WidgetQt(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class DockWidgetQt(QDockWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class SWEinstance(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)


class QtApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)

class DialogWindowQt(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

class WebEngineProfile(QWebEngineProfile):
    def __init__(self, parent=None):
        super().__init__(parent)

_currentUA = None

def setUA(user_agent: str):
    global _currentUA
    _currentUA = user_agent

    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpUserAgent(user_agent)

class ObjectAlign(IntFlag):
    Left = Qt.AlignmentFlag.AlignLeft.value
    Right = Qt.AlignmentFlag.AlignRight.value
    Central = Qt.AlignmentFlag.AlignCenter.value

    DockRight = Qt.DockWidgetArea.RightDockWidgetArea.value
    DockLeft = Qt.DockWidgetArea.LeftDockWidgetArea.value
    DockBottom = Qt.DockWidgetArea.BottomDockWidgetArea.value
    DockTop = Qt.DockWidgetArea.TopDockWidgetArea.value


class BrowserPermission(Enum):
    audio = QWebEnginePermission.PermissionType.MediaAudioCapture
    video = QWebEnginePermission.PermissionType.MediaVideoCapture
    audio_video = QWebEnginePermission.PermissionType.MediaAudioVideoCapture
    location = QWebEnginePermission.PermissionType.Geolocation
    display_video = QWebEnginePermission.PermissionType.DesktopVideoCapture
    display_audio_video = QWebEnginePermission.PermissionType.DesktopAudioVideoCapture

class BrowserSetting(Enum):
    WebRTCPublicOnly = QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly
    InsecureContentPolicy = QWebEngineSettings.WebAttribute.AllowRunningInsecureContent
    AutoloadFavicon = QWebEngineSettings.WebAttribute.AutoLoadIconsForPage
    DNSPrefetch = QWebEngineSettings.WebAttribute.DnsPrefetchEnabled
    JSPolicy = QWebEngineSettings.WebAttribute.JavascriptEnabled
    WebGLAllowed = QWebEngineSettings.WebAttribute.WebGLEnabled
    PluginsAllowed = QWebEngineSettings.WebAttribute.PluginsEnabled
    LocalStoragePolicy = QWebEngineSettings.WebAttribute.LocalStorageEnabled
    CookiesDisallowed = QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
    CookiesAllowed = QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
    CacheDeny = QWebEngineProfile.HttpCacheType.NoCache
    CacheAllow = QWebEngineProfile.HttpCacheType.DiskHttpCache
    AdvertiseFullScreen = QWebEngineSettings.WebAttribute.FullScreenSupportEnabled
    DefaultFont = QWebEngineSettings.FontFamily.StandardFont

def getUA():
    return _currentUA

def getinfo():
    base_dir = Path(__file__).resolve().parent
    info_path = base_dir / "info.json"
    if info_path.exists():
        try:
            with info_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

settings = QSettings("Tudify", "SimpleWeb")
font_name = getinfo().get("font", "Hack")
accent = str(settings.value("accent_colour", "#0a6cff"))

def get_or_create_key():
    settings = QSettings("tudify", "Amphetamine")
    key = settings.value("random_key")
    if key is not None:
        print(f"Amphetamine key: {key}")
        print(f"Keep your key safe, its not important, but it distinctly is you.")
        return key
    key = ''.join(str(random.randint(0, 9)) for _ in range(16))
    settings.setValue("random_key", key)
    print(f"Amphetamine key: {key}")
    print(f"Keep your key safe, its not important, but it distinctly is you.")
    return key

def supportissuewindow(self):
    msg = QMessageBox()
    msg.setWindowTitle("Insecure Operating System")
    msg.setText(
        f"""You are using an older OS, which is no longer supported and is
        insecure. Please consider upgrading to a newer version of your OS. 
        tudify and the SimpleWeb team accept zero liability for any damage 
        caused by using this software on an insecure OS.""")
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()

def msg(title: str, body: str):
    box = QMessageBox()
    box.setWindowTitle(title)
    box.setText(body)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    return box.exec()

def style_breeze_dark():
    return f"""
        *{{font-family:{font_name}, hack, arial;}}
        QMainWindow {{
            background-color: #202326;
            color: #ffffff;
            border: none;
        }}
        QLabel#h1 {{
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 7px;
        }}
        QLabel#h2 {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 7px;
        }}
        QWebEngineView {{
            border: none;
            outline: none;
            background: transparent;
        }}
        QMenu {{
            background-color: #2b2b2b;
            color: white;
            border-radius: 8px;
            border: 1px solid #444;
            padding: 6px;
        }}
        QMenu::item {{
            padding: 6px 20px;
            background-color: transparent;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: #3c3c3c;
            border-radius: 4px;
        }}
        QComboBox{{
            background-color: #292c30;
            color: #ffffff;
            padding: 10px 16px;
            border-radius: 6px;
            border: 1px solid #414346;
            padding: 10px 16px 10px 16px;
        }}
        QComboBox:focus {{
            background-color: #292c30;
            border: 1px solid {accent};
        }}
        QDialog{{
            background-color: #202326;
            color: #ffffff;
        }}
        QPushButton {{
            background-color: #292c30;
            color: #ffffff;
            padding: 10px 16px;
            border-radius: 6px;
            border: 1px solid #414346;
        }}
        QPushButton:hover {{
            background-color: #292c30;
            border: 1px solid #414346;
        }}
        QLineEdit {{
            background-color: #292c30;
            color: #ffffff;
            padding: 10px 16px;
            border-radius: 6px;
            border: 1px solid {accent};
        }}
        QLineEdit:focus {{
            background-color: #292c30;
            border: 1px solid {accent};
        }}
        QTabBar::tab {{
            background-color: #292c30;
            color: #ffffff;
            padding: 10px 16px;
            border-radius: 6px;
            border: 1px solid #414346;
        }}
        QTabBar::tab:selected {{
            background-color: #292c30;
            border: 1px solid {accent};
        }}
    """

def style_breeze_light():
    return f"""
        *{{font-family:{font_name}, hack, arial;}}
        QMainWindow {{
            background-color: #f5f5f5;
        }}
        QDialog {{
            background-color: #f5f5f5;
        }}
        QWebEngineView {{
            border: none;
            outline: none;
            background: transparent;
        }}
        QLabel#h1 {{
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 7px;
        }}
        QLabel#h2 {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 7px;
        }}
        QMenu {{
            background-color: #e3e3e3;
            color: black;
            border-radius: 8px;
            border: 1px solid #ccc;
            padding: 6px;
        }}
        QMenu::item {{
            padding: 6px 20px;
            background-color: transparent;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: #ffffff;
            border-radius: 4px;
        }}
        QPushButton {{
            background-color: #e0e0e0;
            color: #000000;
            padding: 10px 16px;
            border-radius: 6px;
            border: 1px solid #cccccc;
        }}
        QPushButton:hover {{
            border: 1px solid {accent};
        }}
        QLineEdit {{
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #cccccc;
            padding: 10px;
            border-radius: 6px;
        }}
        QLineEdit:focus {{
            border: 1px solid {accent};
        }}
        QTabBar::tab {{
            background-color: #e0e0e0;
            color: #000000;
            padding: 8px 20px;
            border-radius: 6px;
            margin-right: 4px;
        }}
        QTabBar::tab:selected {{
            border: 1px solid {accent};
        }}
    """
def style_metro():
    return f"""
        *{{font-family: 'Segoe UI', arial;}}
        QMainWindow {{
            background-color: #212833;
            color: #ffffff;
            border: none;
        }}
        QLabel#h1 {{
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 7px;
        }}
        QLabel#h2 {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 7px;
        }}
        QWebEngineView {{
            border: none;
            outline: none;
            background: transparent;
        }}
        QMenu {{
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #333;
            padding: 6px;
        }}
        QMenu::item {{
            padding: 6px 20px;
            background-color: transparent;
        }}
        QMenu::item:selected {{
            background-color: #3c3c3c;
        }}
        QComboBox{{
            background-color: #292c30;
            color: #ffffff;
            padding: 10px 16px;
            border: 1px solid #333;
            padding: 10px 16px 10px 16px;
        }}
        QComboBox:focus {{
            background-color: #292c30;
            border: 1px solid {accent};
        }}
        QDialog{{
            background-color: #202326;
            color: #ffffff;
        }}
        QPushButton {{
            background-color: #292c30;
            color: #ffffff;
            padding: 10px 16px;
            border: 1px solid #414346;
        }}
        QPushButton:hover {{
            background-color: #292c30;
            border: 1px solid #414346;
        }}
        QLineEdit {{
            background-color: #292c30;
            color: #ffffff;
            padding: 10px 16px;
            border: 1px solid {accent};
        }}
        QLineEdit:focus {{
            background-color: #292c30;
            border: 1px solid {accent};
        }}
        QTabBar::tab {{
            background-color: #292c30;
            color: #ffffff;
            padding: 10px 16px;
            border: 1px solid #414346;
        }}
        QTabBar::tab:selected {{
            background-color: #292c30;
            border: 1px solid {accent};
        }}
    """

def __init__(self):
    print("Amphetamine Engine")
    print("Version 1.0")
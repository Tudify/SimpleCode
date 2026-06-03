from PyQt6.QtCore import QUrl, Qt, QSettings, QEvent, QObject, pyqtSlot, QEventLoop
from PyQt6.QtWidgets import QApplication, QMessageBox, QMainWindow, QDialog, QDialogButtonBox
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePermission, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from pathlib import Path
from enum import Enum, IntFlag
import json, random, darkdetect, inspect, psutil, urllib.parse
from plyer import notification

def theme():
    return darkdetect.theme()

class notify:
    def __init__(self, title, message, app):
        self.title = title
        self.message = message
        self.app = app
        notification.notify(
            title=self.title,
            message=self.message,
            app_name=self.app
        )


def getmemGB():
    mem = psutil.virtual_memory().total / (1024 ** 3)
    return mem

import urllib.parse

class Browser_SearchURL:
    def __init__(self, text):
        self.text = text

    def __str__(self):
        # When object is used in an f-string, this will be returned
        return urllib.parse.quote_plus(self.text)

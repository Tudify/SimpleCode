import sys
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QDockWidget, QTextEdit,
    QFileDialog, QAction, QToolBar, QMessageBox, QWidget, QVBoxLayout, QPushButton
)
from PyQt5.QtCore import Qt, QProcess, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEngineSettings
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
import re

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlightingRules = []

        # Keyword format
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("#569CD6"))
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else',
            'except', 'False', 'finally', 'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'None', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'True', 'try', 'while', 'with', 'yield'
        ]
        for word in keywords:
            pattern = r'\b' + word + r'\b'
            self.highlightingRules.append((re.compile(pattern), keywordFormat))

        # String format
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor("#CE9178"))
        self.highlightingRules.append((re.compile(r'(\".*?\"|\'.*?\')'), stringFormat))

        # Comment format
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor("#6A9955"))
        self.highlightingRules.append((re.compile(r'#.*'), commentFormat))

        # Number format
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor("#B5CEA8"))
        self.highlightingRules.append((re.compile(r'\b[0-9]+(\.[0-9]+)?\b'), numberFormat))

        # Function format
        functionFormat = QTextCharFormat()
        functionFormat.setForeground(QColor("#DCDCAA"))
        self.highlightingRules.append((re.compile(r'\bdef\s+([A-Za-z_][A-Za-z0-9_]*)'), functionFormat))

        # Class format
        classFormat = QTextCharFormat()
        classFormat.setForeground(QColor("#4EC9B0"))
        self.highlightingRules.append((re.compile(r'\bclass\s+([A-Za-z_][A-Za-z0-9_]*)'), classFormat))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlightingRules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)

class SimpleCode(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SimpleCode")
        self.setGeometry(100, 100, 1000, 650)
        self.setStyleSheet("""
            QMainWindow { background-color: #202326; color: white; }
            QPlainTextEdit, QTextEdit {
                background-color: #1e1f22;
                color: #e0e0e0;
                font-family: Hack, monospace;
                font-size: 14px;
                border: none;
            }
            QPushButton {
                background-color: #30343a;
                border-radius: 6px;
                padding: 6px;
                color: white;
            }
            QPushButton:hover {
                background-color: #40444a;
            }
            QToolBar { background-color: #262a2f; border: none; }
        """)

        # Settings
        self.current_file = None
        self.AI_service = "Claude"  # Default AI
        self.UserAgent = "SimpleCode/1.0 (PyQt5)"

        # Core UI
        self.editor = QPlainTextEdit()
        self.highlighter = PythonHighlighter(self.editor.document())
        self.setCentralWidget(self.editor)
        self.console = self._create_console()
        self._create_ai_sidebar()  # Use SimpleWeb’s AI sidebar logic
        self._create_shortcuts()

    # --- Console Dock ---
    def _create_console(self):
        dock = QDockWidget("Console", self)
        dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        console_output = QTextEdit()
        console_output.setReadOnly(True)
        dock.setWidget(console_output)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        self.console_output = console_output
        return dock

    # --- AI Sidebar (from SimpleWeb) ---
    def _create_ai_sidebar(self):
        self.ai_sidebar = QDockWidget("AI Sidebar", self)
        self.ai_sidebar.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)

        self.ai_browser = QWebEngineView()

        # Map AI service names to URLs
        ai_services = {
            "ChatGPT": "https://chat.openai.com/",
            "Amanda AI 2": "https://poe.com/Amanda-AI/",
            "Claude": "https://claude.ai/",
            "Gemini": "https://gemini.google.com/"
        }
        ai_url = ai_services.get(self.AI_service, "https://chat.openai.com/")
        self.ai_browser.setUrl(QUrl(ai_url))

        # Enable features
        self.ai_browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.ai_browser.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)

        # Apply UA
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent(self.UserAgent)

        self.ai_sidebar.setWidget(self.ai_browser)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ai_sidebar)
        self.ai_sidebar.hide()

    # --- Shortcuts ---
    def _create_shortcuts(self):
    # Use a proper event filter instead of hijacking the editor’s keyPressEvent
        self.editor.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.editor and event.type() == event.KeyPress:
            if event.modifiers() == Qt.ControlModifier:
                if event.key() == Qt.Key_O:
                    self.open_file()
                    return True
                elif event.key() == Qt.Key_S:
                    self.save_file()
                    return True
                elif event.key() == Qt.Key_E:
                    self.run_file()
                    return True
                elif event.key() == Qt.Key_I:
                    self.toggle_ai_sidebar()
                    return True
            # otherwise let the editor handle typing normally
        return super().eventFilter(obj, event)

    # --- File Handling ---
    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Python Files (*.py);;All Files (*)")
        if file_name:
            with open(file_name, "r", encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self.current_file = file_name
            self.setWindowTitle(f"SimpleCode - {file_name}")

    def save_file(self):
        if not self.current_file:
            file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Python Files (*.py);;All Files (*)")
            if not file_name:
                return
            self.current_file = file_name
        with open(self.current_file, "w", encoding="utf-8") as f:
            f.write(self.editor.toPlainText())
        self.console_output.append(f"[INFO] Saved {self.current_file}")

    # --- Run File ---
        # --- Run File ---
    def run_file(self):
        if not self.current_file:
            QMessageBox.warning(self, "No file", "Please save your file before running.")
            return

        self.save_file()
        self.console_output.append(f"[RUNNING] {self.current_file}\n")

        # Kill old process if still running
        if hasattr(self, "process") and self.process.state() != QProcess.NotRunning:
            self.process.kill()

        # Initialize a new QProcess
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyRead.connect(self.read_process_output)
        self.process.finished.connect(self.on_process_finished)

        # Start Python interpreter
        self.process.start(sys.executable, [self.current_file])

    def read_process_output(self):
        data = self.process.readAll().data().decode("utf-8", errors="ignore")
        self.console_output.append(data)

    def on_process_finished(self):
        self.console_output.append("\n[FINISHED]\n")

    # --- Toggle AI Sidebar ---
    def toggle_ai_sidebar(self):
        self.ai_sidebar.setVisible(not self.ai_sidebar.isVisible())

# --- Run App ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SimpleCode()
    win.show()
    sys.exit(app.exec_())
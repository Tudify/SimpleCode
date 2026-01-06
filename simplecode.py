import sys, re, amphetamine
from PyQt6.QtWidgets import (QTextEdit, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QRect, QProcess, QEvent, QUrl
from PyQt6.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor)

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self.rules = []

        def add(pattern, color):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            self.rules.append((re.compile(pattern), fmt))

        add(r'\b(class|def|return|if|else|elif|for|while|try|except|import|from|as|with|pass|break|continue)\b', "#569CD6")
        add(r'\".*?\"|\'.*?\'', "#CE9178")
        add(r'#.*', "#6A9955")
        add(r'\b[0-9]+(\.[0-9]+)?\b', "#B5CEA8")

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt) 

class LineNumberArea(amphetamine.WidgetQt):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#1c1c1c"))

        block = self.editor.firstVisibleBlock()
        number = block.blockNumber()
        top = int(self.editor.blockBoundingGeometry(block)
                  .translated(self.editor.contentOffset()).top())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible():
                painter.setPen(QColor("#858585"))
                painter.drawText(
                    0, top, self.width() - 5,
                    self.editor.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(number + 1)
                )
            block = block.next()
            top += int(self.editor.blockBoundingRect(block).height())
            number += 1

class CodeEditor(amphetamine.QtPTEdit):
    def __init__(self):
        super().__init__()
        self.lineArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateMargins)
        self.updateRequest.connect(self.updateLineArea)
        self.cursorPositionChanged.connect(self.highlightLine)
        self.updateMargins()
    def updateMargins(self):
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        self.setViewportMargins(space, 0, 0, 0)
    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.lineArea.setGeometry(QRect(cr.left(), cr.top(), self.viewportMargins().left(), cr.height()))
    def updateLineArea(self, rect, dy):
        if dy:
            self.lineArea.scroll(0, dy)
        else:
            self.lineArea.update(0, rect.y(), self.lineArea.width(), rect.height())
    def highlightLine(self):
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(QColor("#2a2a2a"))
        sel.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        self.setExtraSelections([sel])
class SimpleCode(amphetamine.MainWindowQt):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SimpleCode")
        self.resize(1000, 650)
        self.setStyleSheet(amphetamine.style_breeze_dark())
        self.current_file = None
        self.editor = CodeEditor()
        self.setCentralWidget(self.editor)
        PythonHighlighter(self.editor.document())
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.consoleDock = amphetamine.DockWidgetQt()
        self.consoleDock.setWidget(self.console_output)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.consoleDock)
        self.ai_browser = amphetamine.SWEinstance()
        self.ai_browser.setUrl(QUrl("https://claude.ai"))
        self.ai_browser.settings().setAttribute(amphetamine.BrowserSetting.JSPolicy.value, True)
        amphetamine.setUA("SimpleCode/1.0")
        self.aiDock = amphetamine.DockWidgetQt()
        self.aiDock.setWidget(self.ai_browser)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.aiDock)
        self.aiDock.hide()
        self.editor.installEventFilter(self)
    def eventFilter(self, obj, event):
        if obj is self.editor and event.type() == QEvent.Type.KeyPress:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                k = event.key()
                if k == Qt.Key.Key_O:
                    self.open_file(); return True
                if k == Qt.Key.Key_S:
                    self.save_file(); return True
                if k == Qt.Key.Key_E:
                    self.run_file(); return True
                if k == Qt.Key.Key_I:
                    self.aiDock.setVisible(not self.aiDock.isVisible())
                    return True
        return super().eventFilter(obj, event)
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Python Files (*.py)")
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self.current_file = path
            self.setWindowTitle(f"SimpleCode — {path}")
    def save_file(self):
        if not self.current_file:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save File", "", "Python Files (*.py)"
            )
            if not path:
                return
            self.current_file = path
        with open(self.current_file, "w", encoding="utf-8") as f:
            f.write(self.editor.toPlainText())
        self.console_output.append(f"[INFO] Saved {self.current_file}")
    def run_file(self):
        if not self.current_file:
            QMessageBox.warning(self, "No file", "Save the file before running.")
            return
        self.save_file()
        self.console_output.append(f"\n[RUNNING] {self.current_file}\n")
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyRead.connect(self.read_output)
        self.process.finished.connect(
            lambda: self.console_output.append("\n[FINISHED]\n")
        )
        self.process.start(sys.executable, [self.current_file])

    def read_output(self):
        text = self.process.readAll().data().decode("utf-8", errors="ignore")
        self.console_output.append(text)
if __name__ == "__main__":
    app = amphetamine.QtApp(sys.argv)
    amphetamine.get_or_create_key()
    win = SimpleCode()
    win.show()
    sys.exit(app.exec())
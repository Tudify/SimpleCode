import os
import re
import sys
import tempfile
import json
from pathlib import Path

import amphetamine
from PyQt6.QtCore import QDir, QProcess, QRect, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (QAction, QColor, QDesktopServices, QFileSystemModel,
                         QTextCharFormat, QTextCursor, QTextDocument, QTextOption,
                         QSyntaxHighlighter)
from PyQt6.QtWidgets import (QFileDialog, QInputDialog, QMessageBox, QSplitter,
                             QTabWidget, QTextEdit, QToolBar, QTreeView, QWidget,
                             QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
                             QListWidgetItem)


LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".pyw": "python",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".h": "cpp",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".json": "json",
    ".js": "javascript",
    ".todo": "todo",
}


def detect_language(path: str | None) -> str:
    if not path:
        return "text"
    ext = Path(path).suffix.lower()
    return LANGUAGE_BY_EXTENSION.get(ext, "text")


class LanguageHighlighter(QSyntaxHighlighter):
    KEYWORDS = {
        "python": (
            "and", "as", "assert", "break", "class", "continue",
            "def", "del", "elif", "else", "except", "False", "finally",
            "for", "from", "global", "if", "import", "in", "is",
            "lambda", "None", "nonlocal", "not", "or", "pass", "raise",
            "return", "True", "try", "while", "with", "yield"
        ),
        "cpp": (
            "alignas", "alignof", "and", "auto", "bool", "break",
            "case", "catch", "class", "const", "constexpr", "continue",
            "decltype", "delete", "do", "double", "else", "enum",
            "explicit", "export", "extern", "false", "float", "for",
            "friend", "if", "inline", "int", "long", "mutable",
            "namespace", "new", "noexcept", "nullptr", "operator", "or",
            "private", "protected", "public", "return", "short", "signed",
            "sizeof", "static", "struct", "switch", "template", "this",
            "throw", "true", "try", "typedef", "typename", "union",
            "unsigned", "using", "virtual", "void", "volatile", "while"
        ),
        "javascript": (
            "break", "case", "catch", "class", "const", "continue",
            "debugger", "default", "delete", "do", "else", "export",
            "extends", "finally", "for", "function", "if", "import",
            "in", "instanceof", "let", "new", "return", "super", "switch",
            "this", "throw", "try", "typeof", "var", "void", "while",
            "with", "yield"
        ),
        "css": (
            "background", "border", "color", "content", "display",
            "flex", "font", "grid", "height", "justify", "margin",
            "padding", "position", "width", "z-index"
        ),
        "json": ("true", "false", "null"),
    }

    def __init__(self, doc, language: str = "text") -> None:
        super().__init__(doc)
        self.language = language
        self.rules: list[tuple[re.Pattern, QTextCharFormat]] = []
        self._build_rules()

    def set_language(self, language: str) -> None:
        language = (language or "text").lower()
        if language == self.language:
            return
        self.language = language
        self._build_rules()
        self.rehighlight()

    def _build_rules(self) -> None:
        self.rules.clear()

        def add(pattern: str, color: str, flags: re.RegexFlag | int = 0) -> None:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            self.rules.append((re.compile(pattern, flags), fmt))

        add(r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'', "#CE9178")
        add(r"`([^`\\]|\\.)*`", "#CE9178")
        add(r"\b[0-9]+(\.[0-9]+)?\b", "#B5CEA8")

        if self.language in {"python", "javascript", "text"}:
            add(r"#.*", "#6A9955")
        if self.language in {"cpp", "javascript"}:
            add(r"//.*", "#6A9955")
            add(r"/\*.*?\*/", "#6A9955", re.DOTALL)

        keywords = self.KEYWORDS.get(self.language, ())
        if keywords:
            pattern = r"\b(" + "|".join(map(re.escape, keywords)) + r")\b"
            add(pattern, "#569CD6")

        if self.language == "html":
            add(r"</?[A-Za-z0-9\-:]+", "#569CD6")
            add(r"\b[A-Za-z\-]+=", "#9CDCFE")
        elif self.language == "css":
            add(r"\.[A-Za-z0-9_-]+", "#DCDCAA")
            add(r"#[A-Fa-f0-9]{3,6}", "#D16969")
        elif self.language == "json":
            add(r'"[^"\\]*(?:\\.[^"\\]*)*"(?=\s*:)', "#9CDCFE")
        elif self.language == "python":
            add(r"@\w+", "#C586C0")
            add(r"\b(self|cls)\b", "#4EC9B0")
            add(r"\b(def|class)\s+[A-Za-z_]\w*", "#DCDCAA")
        elif self.language == "javascript":
            add(r"\b[A-Za-z_]\w*(?=\s*\()", "#DCDCAA")

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class LineNumberArea(amphetamine.WidgetQt):
    def __init__(self, editor) -> None:
        super().__init__(editor)
        self.editor = editor

    def paintEvent(self, event) -> None:
        from PyQt6.QtGui import QPainter

        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#14161a"))
        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.editor.blockBoundingGeometry(block)
                  .translated(self.editor.contentOffset()).top())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible():
                painter.setPen(QColor("#5c6370"))
                painter.drawText(
                    0,
                    top,
                    self.width() - 6,
                    self.editor.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1)
                )
            block = block.next()
            top += int(self.editor.blockBoundingRect(block).height())
            block_number += 1


class CodeEditor(amphetamine.QtPTEdit):
    def __init__(self) -> None:
        super().__init__()
        self.lineArea = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_margins)
        self.updateRequest.connect(self._update_line_area)
        self.cursorPositionChanged.connect(self._highlight_line)
        self.document().modificationChanged.connect(self._refresh_line_area)
        self._update_margins()

        self.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #0f1217;
                color: #e7e8eb;
                border: none;
                selection-background-color: #264f78;
            }
            """
        )
        self.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.setCenterOnScroll(True)
        self.verticalScrollBar().setSingleStep(3)
        tab_width = 4 * self.fontMetrics().horizontalAdvance(' ')
        self.setTabStopDistance(tab_width)
        self.highlighter = LanguageHighlighter(self.document())
        self.file_path: str | None = None
        self.language = "text"

    def set_language(self, language: str) -> None:
        self.language = language or "text"
        self.highlighter.set_language(self.language)

    def lineNumberAreaWidth(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 6 + self.fontMetrics().horizontalAdvance('9') * digits

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineArea.setGeometry(
            QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
        )

    def _update_margins(self) -> None:
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def _update_line_area(self, rect, dy) -> None:
        if dy:
            self.lineArea.scroll(0, dy)
        else:
            self.lineArea.update(0, rect.y(), self.lineArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_margins()

    def _highlight_line(self) -> None:
        if self.isReadOnly():
            return
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#1b2633"))
        selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def _refresh_line_area(self, _changed: bool) -> None:
        self.lineArea.update()


class TodoEditor(QWidget):
    modificationChanged = pyqtSignal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.file_path: str | None = None
        self.language = "todo"
        self._modified = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        controls = QHBoxLayout()
        self.add_button = QPushButton("+")
        self.add_button.setToolTip("Add todo")
        self.clear_button = QPushButton("Clear Completed")
        controls.addWidget(self.add_button)
        controls.addWidget(self.clear_button)
        controls.addStretch(1)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)

        layout.addLayout(controls)
        layout.addWidget(self.list_widget)

        self.add_button.clicked.connect(self._add_default_todo)
        self.clear_button.clicked.connect(self.clear_completed)
        self.list_widget.itemChanged.connect(self._on_item_changed)

    def _set_modified(self, changed: bool) -> None:
        changed = bool(changed)
        if changed == self._modified:
            return
        self._modified = changed
        self.modificationChanged.emit(changed)

    def is_modified(self) -> bool:
        return self._modified

    def set_modified(self, changed: bool) -> None:
        self._set_modified(changed)

    def _create_item(self, title: str, completed: bool) -> QListWidgetItem:
        item = QListWidgetItem(title or "New todo")
        item.setFlags(
            item.flags()
            | Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )
        state = Qt.CheckState.Checked if completed else Qt.CheckState.Unchecked
        item.setCheckState(state)
        return item

    def add_todo(self, title: str = "New todo", completed: bool = False, *, mark_modified: bool = True) -> None:
        item = self._create_item(title, completed)
        self.list_widget.addItem(item)
        self.list_widget.setCurrentItem(item)
        self.list_widget.editItem(item)
        if mark_modified:
            self._set_modified(True)

    def _add_default_todo(self) -> None:
        self.add_todo()

    def clear_completed(self) -> None:
        removed = 0
        for idx in range(self.list_widget.count() - 1, -1, -1):
            item = self.list_widget.item(idx)
            if item.checkState() == Qt.CheckState.Checked:
                self.list_widget.takeItem(idx)
                removed += 1
        if removed:
            self._set_modified(True)

    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        self._set_modified(True)

    def load_from_text(self, content: str) -> None:
        text = content.strip()
        if not text:
            self.list_widget.clear()
            self._set_modified(False)
            return
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid .todo JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Invalid .todo format: expected object at top level.")
        todos = parsed.get("todos", [])
        if not isinstance(todos, list):
            raise ValueError("Invalid .todo format: 'todos' must be a list.")

        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for todo in todos:
            if not isinstance(todo, dict):
                continue
            title = str(todo.get("title", "New todo"))
            completed = bool(todo.get("completed", False))
            self.list_widget.addItem(self._create_item(title, completed))
        self.list_widget.blockSignals(False)
        self._set_modified(False)

    def to_storage_text(self) -> str:
        todos: list[dict[str, str | bool]] = []
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            todos.append(
                {
                    "title": item.text().strip() or "New todo",
                    "completed": item.checkState() == Qt.CheckState.Checked,
                }
            )
        payload = {
            "type": "simplecode.todo",
            "version": 1,
            "todos": todos,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


class SimpleCode(amphetamine.MainWindowQt):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SimpleCode")
        self.resize(1280, 780)
        self.setStyleSheet(self._build_stylesheet())
        self.project_root: str | None = None
        self.process: QProcess | None = None
        self._last_find_query = ""

        self.project_model = QFileSystemModel(self)
        self.project_model.setFilter(
            QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs | QDir.Filter.Files
        )
        default_root = str(Path.home())
        self.project_model.setRootPath(default_root)

        self.sidebar = QTreeView()
        self.sidebar.setModel(self.project_model)
        self.sidebar.setHeaderHidden(True)
        self.sidebar.setUniformRowHeights(True)
        self.sidebar.setExpandsOnDoubleClick(True)
        self.sidebar.hideColumn(1)
        self.sidebar.hideColumn(2)
        self.sidebar.hideColumn(3)
        self.sidebar.doubleClicked.connect(self._handle_tree_double_click)
        self.sidebar.setRootIndex(self.project_model.index(default_root))
        self.sidebar.setMinimumWidth(240)
        self.sidebar.setVerticalScrollMode(QTreeView.ScrollMode.ScrollPerPixel)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        self.setCentralWidget(splitter)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.console_output.setStyleSheet(
            "background-color: #050607; color: #a9b1bc; border-top: 1px solid #22252b;"
        )
        self.consoleDock = amphetamine.DockWidgetQt()
        self.consoleDock.setWidget(self.console_output)
        self.consoleDock.setWindowTitle("Console")
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.consoleDock)

        self.ai_browser = amphetamine.SWEinstance()
        self.ai_browser.setUrl(QUrl("https://claude.ai"))
        self.ai_browser.settings().setAttribute(amphetamine.BrowserSetting.JSPolicy.value, True)
        amphetamine.setUA("SimpleCode/2.0")
        self.aiDock = amphetamine.DockWidgetQt()
        self.aiDock.setWidget(self.ai_browser)
        self.aiDock.setWindowTitle("AI Sidebar")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.aiDock)
        self.aiDock.hide()

        self.preview_browser = amphetamine.SWEinstance()
        self.preview_browser.settings().setAttribute(amphetamine.BrowserSetting.JSPolicy.value, True)
        self.previewDock = amphetamine.DockWidgetQt()
        self.previewDock.setWidget(self.preview_browser)
        self.previewDock.setWindowTitle("HTML Preview")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.previewDock)
        self.previewDock.hide()

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(200)
        self._preview_timer.timeout.connect(self._refresh_html_preview)

        self._create_toolbar()
        self._create_new_tab()
        self._append_info("Ready.")

    def _build_stylesheet(self) -> str:
        base = amphetamine.style_breeze_dark()
        overrides = """
            QSplitter::handle {
                background-color: #14181d;
                width: 4px;
            }
            QTreeView {
                background-color: #0c0f13;
                border-right: 1px solid #1f2329;
                color: #d0d5dc;
            }
            QTreeView::item:selected {
                background-color: #1d3a5c;
            }
            QTabWidget::pane {
                border: 1px solid #1f2329;
                background-color: #0f1217;
            }
            QTabBar::tab {
                background-color: #11151b;
                padding: 8px 16px;
                color: #cfd5df;
            }
            QTabBar::tab:selected {
                background-color: #1b2330;
            }
            QToolBar {
                border: none;
                padding: 4px 12px;
                background-color: #11151b;
            }
            QTextEdit {
                font-family: Hack, Consolas, "Fira Code", monospace;
                font-size: 12pt;
            }
        """
        return base + overrides

    def _create_toolbar(self) -> None:
        self.toolbar = QToolBar("Project", self)
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        actions = [
            ("New", "Ctrl+N", self._new_file),
            ("Open File", "Ctrl+O", self._open_file_dialog),
            ("Open Folder", "Ctrl+Shift+O", self._open_folder_dialog),
            ("Save", "Ctrl+S", self._save_current),
            ("Save As", "Ctrl+Shift+S", self._save_current_as),
            ("Find", "Ctrl+F", self._find_in_editor),
            ("Find Next", "F3", self._find_next),
            ("Run", "Ctrl+E", self._run_current),
            ("Toggle AI", "Ctrl+I", self._toggle_ai),
        ]

        for text, shortcut, handler in actions:
            action = QAction(text, self)
            action.triggered.connect(handler)
            if shortcut:
                action.setShortcut(shortcut)
                self.addAction(action)
            self.toolbar.addAction(action)

    def _create_new_tab(self, *, content: str = "", path: str | None = None) -> None:
        language = detect_language(path)
        if language == "todo":
            editor = TodoEditor()
            editor.file_path = path
            try:
                editor.load_from_text(content)
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid .todo file", str(exc))
                editor.load_from_text("")
            editor.modificationChanged.connect(
                lambda changed, e=editor: self._on_document_modified(e, changed)
            )
        else:
            editor = CodeEditor()
            editor.setPlainText(content)
            editor.file_path = path
            editor.set_language(language)
            editor.document().setModified(False)
            editor.document().modificationChanged.connect(
                lambda changed, e=editor: self._on_document_modified(e, changed)
            )
            editor.document().contentsChanged.connect(
                lambda e=editor: self._schedule_html_preview_update(e)
            )
        index = self.tabs.addTab(editor, self._format_tab_title(path))
        self.tabs.setCurrentIndex(index)
        if path:
            self.tabs.setTabToolTip(index, path)
        self._update_html_preview_visibility()

    def _new_file(self) -> None:
        self._create_new_tab()

    def _open_file_dialog(self) -> None:
        start = self.project_root or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            start,
            "All Files (*.*);;Source Files (*.py *.cpp *.hpp *.html *.htm *.css *.json *.js)"
        )
        if path:
            self._load_file(Path(path))

    def _open_folder_dialog(self) -> None:
        start = self.project_root or str(Path.home())
        directory = QFileDialog.getExistingDirectory(self, "Open Folder", start)
        if directory:
            self.project_root = directory
            self.sidebar.setRootIndex(self.project_model.index(directory))
            self.setWindowTitle(f"SimpleCode — {Path(directory).name}")

    def _load_file(self, path: Path) -> None:
        index = self._find_tab_by_path(path)
        if index != -1:
            self.tabs.setCurrentIndex(index)
            return
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            QMessageBox.warning(self, "Encoding error", f"Unable to open {path.name} as UTF-8.")
            return
        except OSError as exc:
            QMessageBox.critical(self, "File error", str(exc))
            return

        self._create_new_tab(content=content, path=str(path))
        current = self.tabs.currentWidget()
        if isinstance(current, CodeEditor):
            current.document().setModified(False)
        elif isinstance(current, TodoEditor):
            current.set_modified(False)
        self._append_info(f"Opened {path}")

    def _find_tab_by_path(self, path: Path) -> int:
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            if isinstance(widget, (CodeEditor, TodoEditor)) and widget.file_path:
                if Path(widget.file_path) == path:
                    return idx
        return -1

    def _handle_tree_double_click(self, index) -> None:
        if not index.isValid():
            return
        path = Path(self.project_model.filePath(index))
        if path.is_file():
            self._load_file(path)

    def _current_editor(self) -> CodeEditor | TodoEditor | None:
        widget = self.tabs.currentWidget()
        if isinstance(widget, (CodeEditor, TodoEditor)):
            return widget
        return None

    def _format_tab_title(self, path: str | None) -> str:
        return Path(path).name if path else "Untitled"

    def _on_document_modified(self, editor: CodeEditor | TodoEditor, changed: bool) -> None:
        idx = self.tabs.indexOf(editor)
        if idx == -1:
            return
        title = self._format_tab_title(editor.file_path)
        if changed:
            title = f"* {title}"
        self.tabs.setTabText(idx, title)

    def _close_tab(self, index: int) -> None:
        editor = self.tabs.widget(index)
        if self._is_modified(editor):
            res = QMessageBox.question(
                self,
                "Unsaved changes",
                "Save changes before closing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if res == QMessageBox.StandardButton.Cancel:
                return
            if res == QMessageBox.StandardButton.Yes and not self._save_editor(editor):
                return
        self.tabs.removeTab(index)
        editor.deleteLater()
        if self.tabs.count() == 0:
            self._create_new_tab()

    def _on_tab_changed(self, index: int) -> None:
        editor = self.tabs.widget(index)
        path = editor.file_path if isinstance(editor, (CodeEditor, TodoEditor)) else None
        context = f" — {path}" if path else ""
        self.setWindowTitle(f"SimpleCode{context}")
        self._update_html_preview_visibility()

    def _save_current(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        self._save_editor(editor)

    def _save_current_as(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        self._save_editor(editor, save_as=True)

    def _find_in_editor(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        if isinstance(editor, TodoEditor):
            query, accepted = QInputDialog.getText(self, "Find Todo", "Find todo title:")
            if not accepted or not query.strip():
                return
            self._last_find_query = query.strip()
            if not self._find_query_todo(editor, self._last_find_query):
                self._append_info(f'"{self._last_find_query}" not found.')
            return

        selected_text = editor.textCursor().selectedText().strip()
        initial_text = selected_text or self._last_find_query
        query, accepted = QInputDialog.getText(self, "Find", "Find text:", text=initial_text)
        if not accepted:
            return

        query = query.strip()
        if not query:
            self._append_info("Find query is empty.")
            return

        self._last_find_query = query
        if self._find_query(editor, query):
            return

        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        editor.setTextCursor(cursor)
        if self._find_query(editor, query):
            self._append_info(f'Wrapped search for "{query}".')
            return

        self._append_info(f'"{query}" not found.')

    def _find_next(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        if isinstance(editor, TodoEditor):
            if not self._last_find_query:
                self._find_in_editor()
                return
            if not self._find_query_todo(editor, self._last_find_query):
                self._append_info(f'"{self._last_find_query}" not found.')
            return
        if not self._last_find_query:
            self._find_in_editor()
            return
        if self._find_query(editor, self._last_find_query):
            return

        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        editor.setTextCursor(cursor)
        if not self._find_query(editor, self._last_find_query):
            self._append_info(f'"{self._last_find_query}" not found.')

    def _find_query(self, editor: CodeEditor, query: str) -> bool:
        found = editor.find(query, QTextDocument.FindFlag(0))
        if found:
            editor.ensureCursorVisible()
        return found

    def _find_query_todo(self, editor: TodoEditor, query: str) -> bool:
        needle = query.casefold()
        count = editor.list_widget.count()
        if count == 0:
            return False
        start_row = editor.list_widget.currentRow()
        if start_row < 0:
            start_row = 0
        for offset in range(1, count + 1):
            row = (start_row + offset) % count
            item = editor.list_widget.item(row)
            if needle in item.text().casefold():
                editor.list_widget.setCurrentRow(row)
                editor.list_widget.scrollToItem(item)
                return True
        return False

    def _is_modified(self, widget) -> bool:
        if isinstance(widget, CodeEditor):
            return widget.document().isModified()
        if isinstance(widget, TodoEditor):
            return widget.is_modified()
        return False

    def _save_editor(self, editor: CodeEditor | TodoEditor, save_as: bool = False) -> bool:
        path = Path(editor.file_path) if editor.file_path else None
        if save_as or not path:
            start_dir = str(path.parent) if path else (self.project_root or str(Path.home()))
            chosen, _ = QFileDialog.getSaveFileName(
                self,
                "Save File",
                start_dir,
                "All Files (*.*);;Todo (*.todo);;Python (*.py);;C++ (*.cpp *.hpp);;HTML (*.html *.htm);;CSS (*.css);;JSON (*.json);;JavaScript (*.js)"
            )
            if not chosen:
                return False
            path = Path(chosen)

        try:
            if isinstance(editor, TodoEditor):
                path.write_text(editor.to_storage_text(), encoding="utf-8")
            else:
                path.write_text(editor.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Save error", str(exc))
            return False

        editor.file_path = str(path)
        if isinstance(editor, CodeEditor):
            editor.set_language(detect_language(editor.file_path))
            editor.document().setModified(False)
        else:
            editor.set_modified(False)
        idx = self.tabs.indexOf(editor)
        if idx != -1:
            self.tabs.setTabText(idx, self._format_tab_title(editor.file_path))
            self.tabs.setTabToolTip(idx, editor.file_path)
        self._append_info(f"Saved {path}")
        self._schedule_html_preview_update(editor)
        return True

    def _run_current(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        if not editor.file_path and not self._save_editor(editor):
            return
        language = editor.language
        path = editor.file_path
        if not path:
            return
        language = detect_language(path)
        file_path = Path(path)
        if language == "python":
            self._launch_process(sys.executable, [str(file_path)])
        elif language == "cpp":
            self._run_cpp(file_path)
        elif language == "html":
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))
            self._append_info(f"Opened {file_path} in default browser.")
        elif language in {"css", "json", "javascript", "text"}:
            self._append_info(f"No runtime configured for .{file_path.suffix.lstrip('.')}.")
        else:
            self._append_info("No runner available for this file type.")

    def _run_cpp(self, file_path: Path) -> None:
        exe_suffix = ".exe" if os.name == "nt" else ""
        temp_dir = Path(tempfile.mkdtemp(prefix="simplecode_cpp_"))
        output_path = temp_dir / f"build{exe_suffix}"
        args = [str(file_path), "-std=c++17", "-O2", "-o", str(output_path)]
        self._append_info(f"[BUILD] g++ {' '.join(args)}")

        compiler = QProcess(self)
        compiler.setProgram("g++")
        compiler.setArguments(args)
        compiler.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        compiler.readyRead.connect(lambda: self._append_console_bytes(compiler.readAll()))

        def after_compile(exit_code, status) -> None:
            if status != QProcess.ExitStatus.NormalExit or exit_code != 0:
                self._append_info("[ERROR] Compilation failed.")
                compiler.deleteLater()
                return
            self._append_info("[OK] Compilation succeeded. Running...")
            compiler.deleteLater()
            self._launch_process(str(output_path), [], working_dir=str(temp_dir))

        compiler.finished.connect(after_compile)
        compiler.start()

    def _launch_process(
        self,
        program: str,
        arguments: list[str],
        working_dir: str | None = None,
    ) -> None:
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
        self.console_output.append(f"\n[RUN] {program} {' '.join(arguments)}\n")
        self.process = QProcess(self)
        if working_dir:
            self.process.setWorkingDirectory(working_dir)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyRead.connect(self._read_runtime_output)
        self.process.finished.connect(
            lambda code, _status: self.console_output.append(f"\n[FINISHED] Exit {code}\n")
        )
        self.process.start(program, arguments)

    def _read_runtime_output(self) -> None:
        if not self.process:
            return
        self._append_console_bytes(self.process.readAll())

    def _append_console_bytes(self, data) -> None:
        decoded = bytes(data).decode("utf-8", errors="ignore")
        if decoded:
            self.console_output.append(decoded)

    def _append_info(self, message: str) -> None:
        self.console_output.append(f"[INFO] {message}")

    def _toggle_ai(self) -> None:
        self.aiDock.setVisible(not self.aiDock.isVisible())

    def _is_html_editor(self, widget) -> bool:
        return isinstance(widget, CodeEditor) and detect_language(widget.file_path) == "html"

    def _update_html_preview_visibility(self) -> None:
        editor = self._current_editor()
        if not self._is_html_editor(editor):
            self.previewDock.hide()
            self._preview_timer.stop()
            return
        self.previewDock.show()
        self._schedule_html_preview_update(editor)

    def _schedule_html_preview_update(self, editor) -> None:
        if editor is not self._current_editor():
            return
        if not self._is_html_editor(editor):
            return
        self._preview_timer.start()

    def _refresh_html_preview(self) -> None:
        editor = self._current_editor()
        if not self._is_html_editor(editor):
            return
        base_path = Path(editor.file_path).parent if editor.file_path else Path(self.project_root or Path.home())
        base_url = QUrl.fromLocalFile(str(base_path) + "/")
        self.preview_browser.setHtml(editor.toPlainText(), base_url)


if __name__ == "__main__":
    app = amphetamine.QtApp(sys.argv)
    amphetamine.get_or_create_key()
    window = SimpleCode()
    window.show()
    sys.exit(app.exec())

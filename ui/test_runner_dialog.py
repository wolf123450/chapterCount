try:
    from PyQt5.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
        QPushButton, QLabel, QApplication, Qt,
    )
except ImportError:
    from PyQt6.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
        QPushButton, QLabel, QApplication, Qt,
    )

try:
    from PyQt5.Qt import QThread, pyqtSignal
except ImportError:
    from PyQt6.Qt import QThread, pyqtSignal


class _TestRunner(QThread):
    result = pyqtSignal(str, bool, str)   # name, passed, detail
    done   = pyqtSignal()

    def run(self):
        from calibre_plugins.chapter_count.tests.integration import test_integration
        for name, passed, detail in test_integration.run_all():
            self.result.emit(name, passed, detail)
        self.done.emit()


class TestRunnerDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Chapter Count — Diagnostic Tests')
        self.setMinimumSize(600, 400)
        self._build_ui()
        self._run()

    def _build_ui(self):
        root = QVBoxLayout(self)
        self._status = QLabel('Running tests…')
        root.addWidget(self._status)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(['Test', 'Result', 'Detail'])
        self._tree.setColumnWidth(0, 300)
        root.addWidget(self._tree)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton('Copy results to clipboard')
        copy_btn.clicked.connect(self._copy)
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _run(self):
        self._runner = _TestRunner(parent=self)
        self._runner.result.connect(self._add_result)
        self._runner.done.connect(self._on_done)
        self._runner.start()

    def _add_result(self, name: str, passed: bool, detail: str):
        item = QTreeWidgetItem([name, 'PASS' if passed else 'FAIL', detail])
        color = Qt.green if passed else Qt.red
        item.setForeground(1, color)
        self._tree.addTopLevelItem(item)

    def _on_done(self):
        total  = self._tree.topLevelItemCount()
        passed = sum(
            1 for i in range(total)
            if self._tree.topLevelItem(i).text(1) == 'PASS'
        )
        self._status.setText(f'Completed: {passed}/{total} passed')

    def _copy(self):
        lines = []
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            lines.append(f"{item.text(1):4}  {item.text(0)}  {item.text(2)}")
        QApplication.clipboard().setText('\n'.join(lines))

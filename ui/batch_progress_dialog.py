try:
    from PyQt5.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
        QProgressBar, QPushButton, QRadioButton, QButtonGroup,
        QDialogButtonBox, Qt,
    )
except ImportError:
    from PyQt6.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
        QProgressBar, QPushButton, QRadioButton, QButtonGroup,
        QDialogButtonBox, Qt,
    )

from batch_processor import BatchProcessor
from config import load_per_book_config


# ─────────────────────────────────────────── Book Selector Dialog

class BookSelectorDialog(QDialog):
    """Lets the user choose which books to scan before launching the batch."""

    SCOPE_ALL        = 'all'
    SCOPE_SELECTED   = 'selected'
    SCOPE_MISSING    = 'missing'
    SCOPE_UNDETECTED = 'undetected'

    def __init__(self, selected_ids: list, parent=None):
        super().__init__(parent)
        self._selected_ids = selected_ids
        self.chosen_scope  = self.SCOPE_ALL
        self.setWindowTitle('Select Books to Scan')
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        g = QGroupBox('Scan which books?')
        v = QVBoxLayout(g)
        self._bg = QButtonGroup(self)
        options = [
            (self.SCOPE_ALL,        'All books in library'),
            (self.SCOPE_SELECTED,   f'Selected books ({len(self._selected_ids)})'),
            (self.SCOPE_MISSING,    'Books with missing chapter count'),
            (self.SCOPE_UNDETECTED, 'Books with undetected method'),
        ]
        self._radios = {}
        for scope, label in options:
            rb = QRadioButton(label)
            if scope == self.SCOPE_ALL:
                rb.setChecked(True)
            self._bg.addButton(rb)
            self._radios[scope] = rb
            v.addWidget(rb)
        root.addWidget(g)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self):
        for scope, rb in self._radios.items():
            if rb.isChecked():
                self.chosen_scope = scope
                break
        self.accept()


# ─────────────────────────────────────────── Progress Dialog

class BatchProgressDialog(QDialog):

    def __init__(self, db, book_ids: list, prefs: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Counting Chapters…')
        self.setMinimumWidth(480)
        self._build_ui(len(book_ids))

        self._processor = BatchProcessor(
            db=db,
            book_ids=book_ids,
            prefs=prefs,
            per_book_loader=lambda d: load_per_book_config(d) if d else {},
            parent=self,
        )
        self._processor.progress.connect(self._on_progress)
        self._processor.book_done.connect(self._on_book_done)
        self._processor.finished_.connect(self._on_finished)
        self._processor.start()

    def _build_ui(self, total: int):
        root = QVBoxLayout(self)
        self._current_lbl  = QLabel('Starting…')
        self._bar          = QProgressBar()
        self._bar.setRange(0, total)
        self._tally_lbl    = QLabel('Detected: 0  Skipped: 0  Failed: 0')
        self._cancel_btn   = QPushButton('Cancel')
        self._cancel_btn.clicked.connect(self._cancel)
        root.addWidget(self._current_lbl)
        root.addWidget(self._bar)
        root.addWidget(self._tally_lbl)
        root.addWidget(self._cancel_btn, alignment=Qt.AlignRight)
        self._tally = {'detected': 0, 'skipped': 0, 'failed': 0}

    def _on_progress(self, current: int, total: int, title: str):
        self._bar.setValue(current)
        self._current_lbl.setText(f'{current}/{total} — {title}')

    def _on_book_done(self, book_id: int, result):
        if result.method not in ('undetected',):
            self._tally['detected'] += 1
        else:
            self._tally['failed'] += 1
        self._refresh_tally()

    def _refresh_tally(self):
        t = self._tally
        self._tally_lbl.setText(
            f"Detected: {t['detected']}  Skipped: {t['skipped']}  Failed: {t['failed']}"
        )

    def _on_finished(self, summary: dict):
        self._tally = summary
        self._refresh_tally()
        self._cancel_btn.setText('Close')
        self._cancel_btn.clicked.disconnect()
        self._cancel_btn.clicked.connect(self.accept)
        self._current_lbl.setText('Done.')

    def _cancel(self):
        self._processor.cancel()
        self._cancel_btn.setEnabled(False)
        self._current_lbl.setText('Cancelling…')

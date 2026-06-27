try:
    from PyQt5.Qt import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
        QLabel, QLineEdit, QComboBox, QSpinBox, QPlainTextEdit,
        QPushButton, Qt,
    )
except ImportError:
    from PyQt6.Qt import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
        QLabel, QLineEdit, QComboBox, QSpinBox, QPlainTextEdit,
        QPushButton, Qt,
    )

from calibre_plugins.chapter_count.config import PREFS, DEFAULTS


class PreferencesWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load()

    # ------------------------------------------------------------------ build

    def _build_ui(self):
        root = QVBoxLayout(self)

        root.addWidget(self._general_group())
        root.addWidget(self._columns_group())
        root.addWidget(self._epub_group())
        root.addWidget(self._mobi_group())
        root.addWidget(self._pdf_group())

        diag_btn = QPushButton('Run Diagnostic Tests')
        diag_btn.clicked.connect(self._run_diagnostics)
        root.addWidget(diag_btn)
        root.addStretch()

    def _general_group(self):
        g = QGroupBox('General')
        v = QVBoxLayout(g)

        self.auto_scan_cb   = QCheckBox('Auto-scan books when added to library')
        self.notify_err_cb  = QCheckBox('Show notification on auto-scan error')

        pol_row = QHBoxLayout()
        pol_row.addWidget(QLabel('Overwrite policy:'))
        self.overwrite_combo = QComboBox()
        self.overwrite_combo.addItems([
            'Preserve manual, overwrite auto-detected',
            'Always overwrite',
            'Never overwrite if set',
        ])
        pol_row.addWidget(self.overwrite_combo)
        pol_row.addStretch()

        batch_row = QHBoxLayout()
        batch_row.addWidget(QLabel('Batch size:'))
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 5000)
        batch_row.addWidget(self.batch_spin)
        batch_row.addStretch()

        v.addWidget(self.auto_scan_cb)
        v.addWidget(self.notify_err_cb)
        v.addLayout(pol_row)
        v.addLayout(batch_row)
        return g

    def _columns_group(self):
        g = QGroupBox('Column Names')
        v = QVBoxLayout(g)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel('Chapter count column:'))
        self.count_col_edit = QLineEdit()
        row1.addWidget(self.count_col_edit)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel('Detection method column:'))
        self.method_col_edit = QLineEdit()
        row2.addWidget(self.method_col_edit)
        v.addLayout(row1)
        v.addLayout(row2)
        return g

    def _epub_group(self):
        g = QGroupBox('EPUB')
        v = QVBoxLayout(g)
        self.epub_toc_cb        = QCheckBox('Use TOC (toc.ncx / nav.xhtml)')
        self.epub_structural_cb = QCheckBox('Use structural heading scan')
        tag_row = QHBoxLayout()
        tag_row.addWidget(QLabel('Heading tags to scan:'))
        self.epub_tags_edit = QLineEdit()
        tag_row.addWidget(self.epub_tags_edit)
        v.addWidget(self.epub_toc_cb)
        v.addWidget(self.epub_structural_cb)
        v.addLayout(tag_row)
        return g

    def _mobi_group(self):
        g = QGroupBox('MOBI / AZW3')
        v = QVBoxLayout(g)
        self.mobi_toc_cb = QCheckBox('Use TOC record')
        v.addWidget(self.mobi_toc_cb)
        return g

    def _pdf_group(self):
        g = QGroupBox('PDF')
        v = QVBoxLayout(g)
        self.pdf_bookmarks_cb = QCheckBox('Use bookmark tree')
        self.pdf_heuristic_cb = QCheckBox('Enable heuristic text scan (slower)')
        v.addWidget(self.pdf_bookmarks_cb)
        v.addWidget(self.pdf_heuristic_cb)
        v.addWidget(QLabel('Heuristic patterns (regex, one per line):'))
        self.pdf_patterns_edit = QPlainTextEdit()
        self.pdf_patterns_edit.setMaximumHeight(80)
        v.addWidget(self.pdf_patterns_edit)
        return g

    # ------------------------------------------------------------------ I/O

    _POLICY_VALUES = ['preserve_manual', 'always', 'never']

    def _load(self):
        p = PREFS
        self.auto_scan_cb.setChecked(p.get('auto_scan_on_add', DEFAULTS['auto_scan_on_add']))
        self.notify_err_cb.setChecked(p.get('notify_on_error',   DEFAULTS['notify_on_error']))
        self.overwrite_combo.setCurrentIndex(
            self._POLICY_VALUES.index(p.get('overwrite_policy', DEFAULTS['overwrite_policy']))
        )
        self.batch_spin.setValue(p.get('batch_size', DEFAULTS['batch_size']))
        self.count_col_edit.setText(p.get('count_column',  DEFAULTS['count_column']))
        self.method_col_edit.setText(p.get('method_column', DEFAULTS['method_column']))
        self.epub_toc_cb.setChecked(p.get('epub_use_toc', DEFAULTS['epub_use_toc']))
        self.epub_structural_cb.setChecked(p.get('epub_use_structural', DEFAULTS['epub_use_structural']))
        self.epub_tags_edit.setText(', '.join(p.get('epub_heading_tags', DEFAULTS['epub_heading_tags'])))
        self.mobi_toc_cb.setChecked(p.get('mobi_use_toc', DEFAULTS['mobi_use_toc']))
        self.pdf_bookmarks_cb.setChecked(p.get('pdf_use_bookmarks',     DEFAULTS['pdf_use_bookmarks']))
        self.pdf_heuristic_cb.setChecked(p.get('pdf_heuristic_enabled', DEFAULTS['pdf_heuristic_enabled']))
        self.pdf_patterns_edit.setPlainText(
            '\n'.join(p.get('pdf_heuristic_patterns', DEFAULTS['pdf_heuristic_patterns']))
        )

    def save_settings(self):
        PREFS['auto_scan_on_add']      = self.auto_scan_cb.isChecked()
        PREFS['notify_on_error']       = self.notify_err_cb.isChecked()
        PREFS['overwrite_policy']      = self._POLICY_VALUES[self.overwrite_combo.currentIndex()]
        PREFS['batch_size']            = self.batch_spin.value()
        PREFS['count_column']          = self.count_col_edit.text().strip()
        PREFS['method_column']         = self.method_col_edit.text().strip()
        PREFS['epub_use_toc']          = self.epub_toc_cb.isChecked()
        PREFS['epub_use_structural']   = self.epub_structural_cb.isChecked()
        PREFS['epub_heading_tags']     = [t.strip() for t in self.epub_tags_edit.text().split(',') if t.strip()]
        PREFS['mobi_use_toc']          = self.mobi_toc_cb.isChecked()
        PREFS['pdf_use_bookmarks']     = self.pdf_bookmarks_cb.isChecked()
        PREFS['pdf_heuristic_enabled'] = self.pdf_heuristic_cb.isChecked()
        PREFS['pdf_heuristic_patterns'] = [
            ln.strip() for ln in self.pdf_patterns_edit.toPlainText().splitlines() if ln.strip()
        ]

    def _run_diagnostics(self):
        from calibre_plugins.chapter_count.ui.test_runner_dialog import TestRunnerDialog
        dlg = TestRunnerDialog(parent=self)
        dlg.exec_()

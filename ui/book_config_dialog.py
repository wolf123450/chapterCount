try:
    from PyQt5.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
        QRadioButton, QComboBox, QSpinBox, QCheckBox, QPushButton,
        QDialogButtonBox, QButtonGroup, Qt, QLineEdit,
    )
except ImportError:
    from PyQt6.Qt import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
        QRadioButton, QComboBox, QSpinBox, QCheckBox, QPushButton,
        QDialogButtonBox, QButtonGroup, Qt, QLineEdit,
    )

from config import load_per_book_config, save_per_book_config

_FORCE_OPTIONS = ['', 'toc', 'structural', 'heuristic']
_FORCE_LABELS  = ['(auto)', 'TOC', 'Structural', 'Heuristic']


class BookConfigDialog(QDialog):

    def __init__(self, book_id: int, title: str, fmt: str,
                 book_data_dir: str, current_count, current_method,
                 parent=None):
        super().__init__(parent)
        self._book_data_dir = book_data_dir
        self._fmt           = (fmt or '').lower()
        self.setWindowTitle(f'Chapter Detection — {title}')
        self._cfg = load_per_book_config(book_data_dir)
        self._build_ui(title, current_count, current_method)
        self._load()

    # ------------------------------------------------------------------ build

    def _build_ui(self, title, current_count, current_method):
        root = QVBoxLayout(self)

        info = QGroupBox()
        info_v = QVBoxLayout(info)
        info_v.addWidget(QLabel(f'<b>{title}</b>'))
        count_str  = str(current_count) if current_count is not None else '—'
        method_str = current_method or 'not yet detected'
        info_v.addWidget(QLabel(f'Current count: {count_str}  [{method_str}]'))
        root.addWidget(info)

        override = QGroupBox('Override')
        ov = QVBoxLayout(override)

        self._btn_group = QButtonGroup(self)
        self.rb_default = QRadioButton('Use library defaults')
        self.rb_force   = QRadioButton('Force method:')
        self.rb_manual  = QRadioButton('Set manual count:')
        for btn in (self.rb_default, self.rb_force, self.rb_manual):
            self._btn_group.addButton(btn)

        force_row = QHBoxLayout()
        force_row.addWidget(self.rb_force)
        self.force_combo = QComboBox()
        self.force_combo.addItems(_FORCE_LABELS)
        force_row.addWidget(self.force_combo)
        force_row.addStretch()

        manual_row = QHBoxLayout()
        manual_row.addWidget(self.rb_manual)
        self.manual_spin = QSpinBox()
        self.manual_spin.setRange(0, 9999)
        manual_row.addWidget(self.manual_spin)
        manual_row.addStretch()

        ov.addWidget(self.rb_default)
        ov.addLayout(force_row)
        ov.addLayout(manual_row)
        root.addWidget(override)

        if self._fmt == 'epub':
            root.addWidget(self._epub_options())
        elif self._fmt == 'pdf':
            root.addWidget(self._pdf_options())

        btn_row = QHBoxLayout()
        clear_btn = QPushButton('Clear override')
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        btn_row.addWidget(buttons)
        root.addLayout(btn_row)

    def _epub_options(self):
        g = QGroupBox('EPUB options (this book only)')
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        row.addWidget(QLabel('Heading tags:'))
        self.epub_tags_edit = QLineEdit()
        row.addWidget(self.epub_tags_edit)
        v.addLayout(row)
        return g

    def _pdf_options(self):
        g = QGroupBox('PDF options (this book only)')
        v = QVBoxLayout(g)
        self.pdf_heuristic_cb = QCheckBox('Enable heuristic text scan')
        v.addWidget(self.pdf_heuristic_cb)
        return g

    # ------------------------------------------------------------------ I/O

    def _load(self):
        manual = self._cfg.get('manual_count')
        force  = self._cfg.get('force_method')

        if manual is not None:
            self.rb_manual.setChecked(True)
            self.manual_spin.setValue(int(manual))
        elif force:
            self.rb_force.setChecked(True)
            idx = _FORCE_OPTIONS.index(force) if force in _FORCE_OPTIONS else 0
            self.force_combo.setCurrentIndex(idx)
        else:
            self.rb_default.setChecked(True)

        if self._fmt == 'epub' and hasattr(self, 'epub_tags_edit'):
            tags = self._cfg.get('heading_tags') or []
            self.epub_tags_edit.setText(', '.join(tags))
        if self._fmt == 'pdf' and hasattr(self, 'pdf_heuristic_cb'):
            self.pdf_heuristic_cb.setChecked(bool(self._cfg.get('heuristic_enabled')))

    def _clear(self):
        self._cfg = {}
        save_per_book_config(self._book_data_dir, self._cfg)
        self.accept()

    def _save_and_accept(self):
        cfg = {'manual_count': None, 'force_method': None, 'heading_tags': None, 'heuristic_enabled': None}

        if self.rb_manual.isChecked():
            cfg['manual_count'] = self.manual_spin.value()
        elif self.rb_force.isChecked():
            idx = self.force_combo.currentIndex()
            cfg['force_method'] = _FORCE_OPTIONS[idx] or None

        if self._fmt == 'epub' and hasattr(self, 'epub_tags_edit'):
            text = self.epub_tags_edit.text().strip()
            cfg['heading_tags'] = [t.strip() for t in text.split(',') if t.strip()] or None
        if self._fmt == 'pdf' and hasattr(self, 'pdf_heuristic_cb'):
            cfg['heuristic_enabled'] = self.pdf_heuristic_cb.isChecked() or None

        save_per_book_config(self._book_data_dir, cfg)
        self.accept()

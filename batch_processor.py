"""
Runs detection across a list of book IDs in a QThread.
Emits Qt signals so the UI can update without polling.
Caller provides a Calibre DB reference and merged config factory.
"""
try:
    from PyQt5.Qt import QThread, pyqtSignal
except ImportError:
    from PyQt6.Qt import QThread, pyqtSignal  # Calibre 7+

import os
import time

from detectors.factory import get_result_for_book
from column_manager import should_write, write_result


class BatchProcessor(QThread):
    progress   = pyqtSignal(int, int, str)   # current, total, book_title
    book_done  = pyqtSignal(int, object)     # book_id, DetectionResult
    finished_  = pyqtSignal(dict)            # summary: {detected, skipped, failed}

    def __init__(self, db, book_ids: list, prefs: dict, per_book_loader, parent=None):
        super().__init__(parent)
        self._db              = db
        self._book_ids        = list(book_ids)
        self._prefs           = prefs
        self._per_book_loader = per_book_loader  # callable(book_data_dir) -> dict
        self._cancelled       = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        summary  = {'detected': 0, 'skipped': 0, 'failed': 0}
        total    = len(self._book_ids)
        batch_sz = self._prefs.get('batch_size', 50)

        for idx, book_id in enumerate(self._book_ids):
            if self._cancelled:
                break

            try:
                title = self._db.field_for('title', book_id) or f'Book {book_id}'
                self.progress.emit(idx + 1, total, title)

                result = self._detect_one(book_id)

                if should_write(self._db, book_id, result, self._prefs):
                    write_result(self._db, book_id, result, self._prefs)
                    if result.method != 'undetected':
                        summary['detected'] += 1
                    else:
                        summary['failed'] += 1
                else:
                    summary['skipped'] += 1

                self.book_done.emit(book_id, result)

            except Exception:
                summary['failed'] += 1

            # Yield between batches so Calibre UI stays responsive
            if (idx + 1) % batch_sz == 0:
                time.sleep(0.01)

        self.finished_.emit(summary)

    def _detect_one(self, book_id: int):
        from config import load_per_book_config, merge_config

        fmts = self._db.formats(book_id, index_is_id=True)
        if not fmts:
            from detectors.base import UNDETECTED
            return UNDETECTED

        preferred = preferred_format(fmts)
        book_path = self._db.format_abspath(book_id, preferred, index_is_id=True)
        data_dir  = os.path.join(self._db.library_path, self._db.field_for('path', book_id) or '')

        per_book = self._per_book_loader(data_dir) if data_dir else {}
        merged   = merge_config(per_book, dict(self._prefs))

        return get_result_for_book(book_path, preferred.lower(), merged)


_FORMAT_PRIORITY = ['epub', 'azw3', 'mobi', 'azw', 'pdf']


def preferred_format(fmts: list) -> str:
    lower = [f.lower() for f in fmts]
    for fmt in _FORMAT_PRIORITY:
        if fmt in lower:
            return fmt
    return fmts[0].lower()

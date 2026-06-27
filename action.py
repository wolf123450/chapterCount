import os

from calibre.gui2.actions import InterfaceAction
from calibre.gui2 import error_dialog, info_dialog

from calibre_plugins.chapter_count.config import PREFS, DEFAULTS, load_per_book_config, merge_config
from calibre_plugins.chapter_count.column_manager import ensure_columns, should_write, write_result
from calibre_plugins.chapter_count.detectors.factory import get_result_for_book


class ChapterCountAction(InterfaceAction):
    name        = 'Chapter Count'
    action_spec = ('Chapter Count', None, 'Count chapters in selected books', None)

    # ─────────────────────────────── Calibre lifecycle

    def genesis(self):
        self.qaction.triggered.connect(self.bulk_scan_triggered)
        self.create_menu_action(
            self.qaction.menu() or self._make_menu(),
            'count_selected',
            'Count Chapters',
            triggered=self.count_selected,
        )
        self.create_menu_action(
            self.qaction.menu() or self._make_menu(),
            'configure_selected',
            'Configure Chapter Detection',
            triggered=self.configure_selected,
        )

    def _make_menu(self):
        try:
            from PyQt5.Qt import QMenu
        except ImportError:
            from PyQt6.Qt import QMenu
        m = QMenu()
        self.qaction.setMenu(m)
        return m

    def initialization_complete(self):
        self._first_run_check()
        if PREFS.get('auto_scan_on_add', DEFAULTS['auto_scan_on_add']):
            try:
                self.gui.current_db.new_api.add_listener(self._on_books_added)
            except AttributeError:
                pass  # API not available in this Calibre version

    # ─────────────────────────────── First-run

    def _first_run_check(self):
        if PREFS.get('_installed'):
            return
        PREFS['_installed'] = True
        db    = self.gui.current_db
        count = db.count()
        ensure_columns(db, dict(PREFS))
        if count == 0:
            return
        from calibre.gui2 import question_dialog
        if question_dialog(
            self.gui,
            'Chapter Count',
            f'{count} book(s) found in your library. Run a bulk scan now?',
            default_yes=False,
        ):
            self.bulk_scan_triggered()

    # ─────────────────────────────── Auto-scan hook

    def _on_books_added(self, event, library_id, book_ids, **kwargs):
        if event != 'books-added':
            return
        db    = self.gui.current_db
        prefs = dict(PREFS)
        ensure_columns(db, prefs)
        for book_id in book_ids:
            try:
                self._scan_one_silent(db, book_id, prefs)
            except Exception as exc:
                from calibre.utils.logging import default_log
                default_log.error(f'Chapter Count auto-scan failed for book {book_id}: {exc}')
                if prefs.get('notify_on_error', DEFAULTS['notify_on_error']):
                    error_dialog(self.gui, 'Chapter Count', str(exc), show=True)

    def _scan_one_silent(self, db, book_id: int, prefs: dict):
        fmts = db.formats(book_id, index_is_id=True)
        if not fmts:
            return
        from calibre_plugins.chapter_count.batch_processor import preferred_format
        preferred = preferred_format(list(fmts))
        book_path = db.format_abspath(book_id, preferred, index_is_id=True)
        data_dir  = db.abspath(book_id, index_is_id=True) or ''
        per_book  = load_per_book_config(data_dir) if data_dir else {}
        merged    = merge_config(per_book, prefs)
        result    = get_result_for_book(book_path, preferred.lower(), merged)
        if should_write(db, book_id, result, prefs):
            write_result(db, book_id, result, prefs)

    # ─────────────────────────────── Manual actions

    def count_selected(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            return
        book_ids = [self.gui.library_view.model().id(r) for r in rows]
        self._launch_batch(book_ids)

    def configure_selected(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            return
        book_id = self.gui.library_view.model().id(rows[0])
        db      = self.gui.current_db
        title   = db.title(book_id, index_is_id=True) or ''
        fmts    = db.formats(book_id, index_is_id=True) or []
        from calibre_plugins.chapter_count.batch_processor import preferred_format
        fmt      = preferred_format(list(fmts)) if fmts else ''
        data_dir = db.abspath(book_id, index_is_id=True) or ''
        prefs    = dict(PREFS)
        count_label  = prefs.get('count_column',  '#chapter_count').lstrip('#')
        method_label = prefs.get('method_column', '#chapter_detection_method').lstrip('#')
        current_count  = db.get_custom(book_id, label=count_label,  index_is_id=True)
        current_method = db.get_custom(book_id, label=method_label, index_is_id=True)

        from calibre_plugins.chapter_count.ui.book_config_dialog import BookConfigDialog
        dlg = BookConfigDialog(
            book_id=book_id, title=title, fmt=fmt,
            book_data_dir=data_dir,
            current_count=current_count, current_method=current_method,
            parent=self.gui,
        )
        dlg.exec_()

    def bulk_scan_triggered(self):
        from calibre_plugins.chapter_count.ui.batch_progress_dialog import BookSelectorDialog, BatchProgressDialog
        db       = self.gui.current_db
        selected = [
            self.gui.library_view.model().id(r)
            for r in self.gui.library_view.selectionModel().selectedRows()
        ]
        selector = BookSelectorDialog(selected_ids=selected, parent=self.gui)
        if selector.exec_() != BookSelectorDialog.Accepted:
            return

        book_ids = self._resolve_scope(selector.chosen_scope, selected, db)
        if not book_ids:
            info_dialog(self.gui, 'Chapter Count', 'No books matched the selected scope.', show=True)
            return

        ensure_columns(db, dict(PREFS))
        dlg = BatchProgressDialog(db=db, book_ids=book_ids, prefs=dict(PREFS), parent=self.gui)
        dlg.exec_()
        self.gui.library_view.model().refresh()

    def _resolve_scope(self, scope: str, selected_ids: list, db) -> list:
        from calibre_plugins.chapter_count.ui.batch_progress_dialog import BookSelectorDialog as BS
        prefs        = dict(PREFS)
        method_label = prefs.get('method_column', '#chapter_detection_method').lstrip('#')
        count_label  = prefs.get('count_column',  '#chapter_count').lstrip('#')

        if scope == BS.SCOPE_ALL:
            return db.all_ids()
        if scope == BS.SCOPE_SELECTED:
            return selected_ids
        if scope == BS.SCOPE_MISSING:
            return [bid for bid in db.all_ids()
                    if db.get_custom(bid, label=count_label, index_is_id=True) is None]
        if scope == BS.SCOPE_UNDETECTED:
            return [bid for bid in db.all_ids()
                    if 'undetected' in str(db.get_custom(bid, label=method_label, index_is_id=True) or '')]
        return []

    def apply_settings(self):
        pass  # JSONConfig reflects disk changes immediately; no cached state to refresh

    def _launch_batch(self, book_ids):
        from calibre_plugins.chapter_count.ui.batch_progress_dialog import BatchProgressDialog
        db = self.gui.current_db
        ensure_columns(db, dict(PREFS))
        dlg = BatchProgressDialog(db=db, book_ids=book_ids, prefs=dict(PREFS), parent=self.gui)
        dlg.exec_()
        self.gui.library_view.model().refresh()

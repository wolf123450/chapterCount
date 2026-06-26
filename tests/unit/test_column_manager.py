import sys
import types
from unittest.mock import MagicMock, call

# Stub out calibre before importing column_manager
calibre_stub = types.ModuleType('calibre')
sys.modules.setdefault('calibre', calibre_stub)

from column_manager import ensure_columns, should_write, write_result  # noqa: E402
from detectors.base import DetectionResult  # noqa: E402


def _prefs(**overrides):
    base = {
        'count_column':  '#chapter_count',
        'method_column': '#chapter_detection_method',
        'overwrite_policy': 'preserve_manual',
    }
    base.update(overrides)
    return base


# ─── should_write ────────────────────────────────────────────────────────────

def test_should_write_no_existing_value():
    db = MagicMock()
    db.get_custom.return_value = None
    assert should_write(db, 1, MagicMock(), _prefs()) is True


def test_should_write_policy_always():
    db = MagicMock()
    db.get_custom.return_value = 'manual · high'
    assert should_write(db, 1, MagicMock(), _prefs(overwrite_policy='always')) is True


def test_should_write_policy_never():
    db = MagicMock()
    db.get_custom.return_value = 'toc · high'
    assert should_write(db, 1, MagicMock(), _prefs(overwrite_policy='never')) is False


def test_should_write_preserve_manual_auto_method():
    db = MagicMock()
    db.get_custom.return_value = 'toc · high'
    assert should_write(db, 1, MagicMock(), _prefs(overwrite_policy='preserve_manual')) is True


def test_should_write_preserve_manual_blocks_manual():
    db = MagicMock()
    db.get_custom.return_value = 'manual · high'
    assert should_write(db, 1, MagicMock(), _prefs(overwrite_policy='preserve_manual')) is False


# ─── write_result ─────────────────────────────────────────────────────────────

def test_write_result_calls_both_columns():
    db = MagicMock()
    db.custom_column_list.return_value = [
        {'label': 'chapter_count'},
        {'label': 'chapter_detection_method'},
    ]
    result = DetectionResult(count=5, method='toc', confidence='high')
    prefs  = _prefs()
    write_result(db, 42, result, prefs)

    db.set_custom.assert_any_call(42, 5, label='chapter_count', index_is_id=True)
    db.set_custom.assert_any_call(42, 'toc · high', label='chapter_detection_method', index_is_id=True)
    assert db.set_custom.call_count == 2


# ─── ensure_columns ──────────────────────────────────────────────────────────

def test_ensure_columns_skips_existing():
    db = MagicMock()
    db.custom_column_list.return_value = [
        {'label': 'chapter_count'},
        {'label': 'chapter_detection_method'},
    ]
    ensure_columns(db, _prefs())
    db.create_custom_column.assert_not_called()


def test_ensure_columns_creates_missing_count():
    db = MagicMock()
    db.custom_column_list.return_value = [
        {'label': 'chapter_detection_method'},
    ]
    ensure_columns(db, _prefs())
    db.create_custom_column.assert_called_once()
    kwargs = db.create_custom_column.call_args.kwargs
    assert kwargs['label'] == 'chapter_count'
    assert kwargs['datatype'] == 'int'

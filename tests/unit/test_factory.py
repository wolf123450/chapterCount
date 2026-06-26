import os
import pytest
from unittest.mock import patch, MagicMock
from detectors.factory import get_result_for_book
from detectors.base import DetectionResult


def _mock_db(book_id, fmt='epub', path='/books/book.epub', data_dir='/books/data'):
    db = MagicMock()
    db.formats.return_value = [fmt.upper()]
    db.format_abspath.return_value = path
    db.field_for.return_value = None           # no existing column value
    book_data = MagicMock()
    book_data.__str__ = lambda self: data_dir
    db.field_for.return_value = None
    db.new_api.format_abspath.return_value = path
    db.new_api.field_for.return_value = None
    return db


def test_manual_count_returns_immediately(tmp_path):
    p = tmp_path / 'book.epub'
    p.write_bytes(b'dummy')
    cfg = {'manual_count': 42}
    result = get_result_for_book(str(p), 'epub', cfg)
    assert result.count == 42
    assert result.method == 'manual'
    assert result.confidence == 'high'


def test_dispatches_epub(epub_with_ncx):
    result = get_result_for_book(epub_with_ncx, 'epub', {})
    assert result.method == 'toc'
    assert result.count == 5


def test_dispatches_mobi(mobi_with_nav_points):
    result = get_result_for_book(mobi_with_nav_points, 'mobi', {'mobi_use_toc': True})
    assert result.method == 'toc'
    assert result.count == 7


def test_unknown_format_returns_undetected(tmp_path):
    p = tmp_path / 'book.cbz'
    p.write_bytes(b'dummy')
    result = get_result_for_book(str(p), 'cbz', {})
    assert result.method == 'undetected'


def test_force_method_propagates_to_detector(epub_with_ncx):
    result = get_result_for_book(epub_with_ncx, 'epub', {'force_method': 'structural', 'epub_use_structural': True, 'epub_heading_tags': ['h1']})
    assert result.method in ('structural', 'undetected')  # no h1 in spine → undetected or structural

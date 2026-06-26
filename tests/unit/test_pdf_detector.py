from unittest.mock import patch
from detectors.pdf_detector import PdfDetector


_ADAPTER = 'detectors.pdf_detector._adapter'


def test_detects_bookmarks(pdf_file):
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=['Chapter 1', 'Chapter 2', 'Chapter 3']):
        result = PdfDetector().detect(pdf_file, {'pdf_use_bookmarks': True})
    assert result.count == 3
    assert result.method == 'toc'
    assert result.confidence == 'high'


def test_returns_undetected_when_no_bookmarks_and_no_heuristic(pdf_file):
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=[]):
        result = PdfDetector().detect(pdf_file, {'pdf_use_bookmarks': True, 'pdf_heuristic_enabled': False})
    assert result.method == 'undetected'


def test_heuristic_detects_chapter_headings(pdf_file):
    text = 'Chapter 1\nSome text\nChapter 2\nMore text\nChapter 3\n'
    patterns = [r'^Chapter\s+\d+']
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=[]), \
         patch(f'{_ADAPTER}.extract_pdf_text', return_value=text):
        result = PdfDetector().detect(pdf_file, {
            'pdf_use_bookmarks': True,
            'pdf_heuristic_enabled': True,
            'pdf_heuristic_patterns': patterns,
        })
    assert result.count == 3
    assert result.method == 'heuristic'
    assert result.confidence == 'low'


def test_heuristic_disabled_returns_undetected(pdf_file):
    text = 'Chapter 1\nChapter 2\n'
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=[]), \
         patch(f'{_ADAPTER}.extract_pdf_text', return_value=text):
        result = PdfDetector().detect(pdf_file, {
            'pdf_use_bookmarks': True,
            'pdf_heuristic_enabled': False,
        })
    assert result.method == 'undetected'


def test_returns_undetected_for_corrupted_file(corrupted_pdf):
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=[]):
        result = PdfDetector().detect(corrupted_pdf, {})
    assert result.method == 'undetected'


def test_force_method_toc_skips_heuristic(pdf_file):
    with patch(f'{_ADAPTER}.get_pdf_bookmarks', return_value=[]):
        result = PdfDetector().detect(pdf_file, {
            'force_method': 'toc',
            'pdf_use_bookmarks': True,
            'pdf_heuristic_enabled': True,
        })
    assert result.method == 'undetected'  # forced toc, no bookmarks → undetected


def test_bookmarks_disabled_falls_through(pdf_file):
    text = 'Chapter 1\nChapter 2\n'
    patterns = [r'^Chapter\s+\d+']
    with patch(f'{_ADAPTER}.extract_pdf_text', return_value=text):
        result = PdfDetector().detect(pdf_file, {
            'pdf_use_bookmarks': False,
            'pdf_heuristic_enabled': True,
            'pdf_heuristic_patterns': patterns,
        })
    assert result.method == 'heuristic'
    assert result.count == 2
